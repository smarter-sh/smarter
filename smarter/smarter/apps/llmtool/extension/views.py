"""
The web console's Extensions pages, and their api.

Superusers manage extensions on two pages of the single-page console (ADR-035), which renders
``@smarter/extension-console``'s list or an extension's page at their paths. Every other user sees
the same pages read-only: the extensions that their account may use, without their settings, their
availability or the platform admin's Secrets, and without any action.

- **Extensions** (``/extensions/``): the installed extensions, and the registry's, which can be
  installed, and an archive's upload.
- **An extension** (``/extensions/<slug>/``): its documentation, tools, settings, availability,
  versions and resources, and every action on it.

The api is a set of POST endpoints in the web console's api, under ``/api/web/llmtool/extensions/``
(see :mod:`smarter.apps.llmtool.extension.api.web.urls`). The actions are for superusers only; the
list, the registry and an extension's detail are read-only for everyone else. Each validates its request and builds its response with the models of
:mod:`~smarter.apps.llmtool.extension.contract`, and carries out its action with the
:class:`~smarter.apps.llmtool.extension.installer.ExtensionInstaller` or the
:mod:`~smarter.apps.llmtool.extension.registry` client, as the admin console and the management
commands do. An action's failure is a 400 with ``{"error": "..."}``, whose message is meant for
the person who tried it.
"""

from http import HTTPStatus
from typing import Optional, Union

from django.core.handlers.asgi import ASGIRequest
from django.http import JsonResponse
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ValidationError
from waffle import get_waffle_switch_model

from smarter.apps.account.models import Account, User
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.dashboard.views.console_app import ConsoleAppView
from smarter.apps.llmtool.models import Extension, ExtensionVersion
from smarter.apps.secret.models import Secret
from smarter.lib import json, logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from . import registry
from .contract import (
    TRUST_BADGE_LABELS,
    AccountRef,
    AccountsResponse,
    ActionResponse,
    AvailabilityRequest,
    ConfigureRequest,
    ErrorResponse,
    ExtensionConsoleModel,
    ExtensionDetail,
    ExtensionDetailResponse,
    ExtensionListResponse,
    ExtensionResource,
    ExtensionSummary,
    ExtensionSwitch,
    ExtensionTool,
    InstallRequest,
    RegistryExtension,
    RegistryRequest,
    RegistryResponse,
    RegistryVersionInfo,
    RollbackRequest,
    SecretRef,
    setting_states,
    version_infos,
)
from .docs import render_rst
from .exceptions import SmarterExtensionException
from .installer import ExtensionInstaller, SettingInput
from .loader import load_version
from .manifest import ExtensionSettingType, describe_validation_errors
from .protocol import switch_name
from .toolkit import ExtensionToolkit

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])

FORBIDDEN = "Only superusers may manage extensions."
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def detail_url(slug: str) -> str:
    """Return the url of an extension's detail page."""
    # pylint: disable=import-outside-toplevel
    from .urls import ExtensionReverseNames

    return reverse(f"{ExtensionReverseNames.namespace}:{ExtensionReverseNames.detailview}", kwargs={"slug": slug})


def list_url() -> str:
    """Return the url of the Extensions list page."""
    # pylint: disable=import-outside-toplevel
    from .urls import ExtensionReverseNames

    return reverse(f"{ExtensionReverseNames.namespace}:{ExtensionReverseNames.listview}")


def secret_name(slug: str, setting: str) -> str:
    """
    Return the name of the Secret that holds a secret setting's typed value.

    :param slug: The extension's slug. Its hyphens become underscores.
    :param setting: The setting's name.
    :returns: The Secret's name, e.g. ``extension_date_calculator_api_key``.
    """
    return f"extension_{slug.replace('-', '_')}_{setting}"


def extension_detail(extension: Extension) -> ExtensionDetail:
    """
    Return everything that an extension's detail page shows.

    :param extension: The extension.
    """
    summary = ExtensionSummary.from_model(extension, detail_url(extension.slug))
    version = extension.installed_version
    manifest = version.parsed_manifest if version else None
    tools: list[ExtensionTool] = []
    load_error: Optional[str] = None
    if version is not None:
        try:
            loaded = load_version(version)
            naming = ExtensionToolkit([])
            tools = [
                ExtensionTool(
                    name=tool.name,
                    function_name=naming.function_name(extension.slug, tool.name),
                    description=tool.tool_description(),
                    parameters=tool.parameters(),
                )
                for tool in loaded.tools.values()
            ]
        except SmarterExtensionException as e:
            load_error = e.message
    switch_model = get_waffle_switch_model()
    switches = []
    for spec in manifest.smarter.switches if manifest else []:
        name = switch_name(extension.slug, spec.name)
        switch = switch_model.objects.filter(name=name).first()
        switches.append(ExtensionSwitch(name=name, description=spec.description, active=bool(switch and switch.active)))
    owner = smarter_cached_objects.smarter_admin_user_profile
    versions = list(
        ExtensionVersion.objects.filter(extension=extension).defer("archive").select_related("installed_by")
    )
    # pylint: disable=import-outside-toplevel
    from .settings import missing_required_settings

    return ExtensionDetail(
        **summary.model_dump(),
        homepage=manifest.project.urls.get("Homepage") if manifest else None,
        license=manifest.project.license if manifest else None,
        docs_html=version.docs_html if version else "",
        tools=tools,
        load_error=load_error,
        settings=setting_states(extension),
        missing_settings=missing_required_settings(extension, manifest) if manifest else [],
        versions=version_infos(extension, versions),
        resources=[
            ExtensionResource(
                kind=resource.kind,
                name=resource.name,
                owner=resource.user_profile.user.username,
                version=resource.version,
                managed=resource.managed,
            )
            for resource in extension.resources.select_related("user_profile__user").order_by("kind", "name")  # type: ignore[attr-defined]
        ],
        switches=switches,
        all_accounts=extension.all_accounts,
        accounts=[AccountRef.from_model(account) for account in extension.accounts.order_by("account_number")],
        available_secrets=[
            SecretRef.from_model(secret) for secret in Secret.objects.filter(user_profile=owner).order_by("name")
        ],
    )


def read_only_detail(detail: ExtensionDetail) -> ExtensionDetail:
    """
    Return what a user who is not a superuser may see of an extension's detail page.

    Its settings, the accounts that may use it, the platform admin's Secrets and who installed each
    version are left out.

    :param detail: Everything that the detail page shows a superuser.
    """
    return detail.model_copy(
        update={
            "settings": [],
            "accounts": [],
            "available_secrets": [],
            "versions": [version.model_copy(update={"installed_by": None}) for version in detail.versions],
        }
    )


def is_newer(candidate: str, current: Optional[str]) -> bool:
    """
    Return whether a version is newer than another; an unparsable version is never newer.

    :param candidate: The version that may be newer.
    :param current: The version to compare with, or None, which every parsable version is newer than.
    :returns: True if ``candidate`` is newer.
    """
    try:
        return current is None or Version(candidate) > Version(current)
    except InvalidVersion:
        return False


def registry_extensions(index: "registry.RegistryIndex") -> list[RegistryExtension]:
    """
    Return the registry's extensions, with what each card offers on this platform.

    :param index: The registry's verified index.
    """
    installed = {extension.slug: extension for extension in Extension.objects.select_related("installed_version")}
    entries = []
    for entry in sorted(index.extensions, key=lambda item: item.display_name.lower()):
        publisher = index.publisher(entry.publisher)
        badge = index.badge_of(entry)
        latest = entry.latest_compatible()
        extension = installed.get(entry.slug)
        version = extension.installed_version.version if extension and extension.installed_version else None
        if extension is not None and extension.source != "registry":
            action = "uploaded"
        elif latest is None:
            action = "incompatible"
        elif extension is None:
            action = "install"
        else:
            action = "update" if is_newer(latest.version, version) else "installed"
        entries.append(
            RegistryExtension(
                slug=entry.slug,
                display_name=entry.display_name,
                description=entry.description,
                publisher=publisher.name if publisher else entry.publisher,
                publisher_url=publisher.url if publisher else None,
                trust_badge=badge,  # type: ignore[arg-type]
                trust_badge_label=TRUST_BADGE_LABELS.get(badge, badge),
                homepage=entry.homepage,
                license=entry.license,
                docs_html=render_rst(entry.docs_rst),
                latest_version=latest.version if latest else None,
                versions=[
                    RegistryVersionInfo(
                        version=item.version,
                        requires_smarter=item.requires_smarter,
                        released_at=item.released_at,
                        compatible=item.is_compatible(),
                    )
                    for item in sorted(entry.versions, key=lambda item: item.sort_key(), reverse=True)
                ],
                installed_version=version,
                action=action,  # type: ignore[arg-type]
                detail_url=detail_url(entry.slug) if extension else None,
            )
        )
    return entries


# ------------------------------------------------------------------------------
# pages
# ------------------------------------------------------------------------------
class ExtensionListView(ConsoleAppView):
    """The Extensions page, ``/extensions/``: the single-page console's, at the path that Django served it at."""


class ExtensionDetailView(ConsoleAppView):
    """
    An extension's page, ``/extensions/<slug>/``: the single-page console's.

    The console shows anyone the page, and the api refuses an extension that the requesting user may not see, as
    :meth:`ExtensionApiView.visible` decides.
    """


# ------------------------------------------------------------------------------
# the api's handlers, which the web console's api and /api/v1/extensions/ share
# ------------------------------------------------------------------------------
class ExtensionApiHandler:
    """
    The logic of one endpoint of the Extensions api, apart from how its request arrives and its response leaves.

    Two transports mix it in: :class:`ExtensionApiView`, the web console's api (POST only, a Django session,
    errors as ``{"error": ...}``), and :class:`smarter.apps.llmtool.extension.api.v1.views.ExtensionApiV1View`,
    the REST api under ``/api/v1/extensions/`` (an api key, errors as ``{"detail": ...}``). A transport
    implements :meth:`request_data`, calls :meth:`respond`, and turns its result into a response.

    Subclasses implement :meth:`handle`, which returns a contract model, and set :attr:`request_model`
    if the request has a body.
    """

    request_model: Optional[type[BaseModel]] = None
    read_only: bool = False
    """Whether every user may call it.

    It then shows a user who is not a superuser only what they may see.
    """

    # provided by the transport's view, which is a SmarterRequestMixin. Declared for type checkers.
    account: Optional[Account]
    formatted_class_name: str

    def request_data(self, request) -> SmarterDictType:
        """
        Return the request's data, as a dict, for :attr:`request_model` to validate: its JSON body.

        The web console's api sends JSON. The REST api's transport overrides it with DRF's parsed data.

        :param request: The request.
        :returns: The body, or an empty dict if it has none, or it is not an object.
        :raises ValueError: If the body is not JSON.
        """
        try:
            body = json.loads(request.body or b"{}")
        except json.JSONDecodeError as e:
            raise ValueError(f"The request is not JSON: {e}") from e
        if isinstance(body, dict):
            return body
        return {}

    def installer(self, request) -> ExtensionInstaller:
        """Return an installer that acts as the requesting superuser."""
        return ExtensionInstaller(user=request.user)  # type: ignore[arg-type]

    def extension(self, slug: str) -> Extension:
        """Return an installed extension, or raise Extension.DoesNotExist."""
        return Extension.objects.select_related("installed_version").get(slug=slug)

    def parse(self, request) -> Optional[BaseModel]:
        """
        Validate the request's data with :attr:`request_model`.

        A request without a model is not read at all: a multipart upload's body can't be read again.

        :param request: The request.
        :returns: The validated request, or None if the endpoint takes none.
        :raises ValueError: If the request is not valid.
        """
        if self.request_model is None:
            return None
        data = self.request_data(request)
        try:
            return self.request_model.model_validate(data)
        except ValidationError as e:
            problems = describe_validation_errors(e, whole_location="request")
            raise ValueError(f"The request is not valid: {problems}") from e

    def visible(self, request, extension: Extension) -> bool:
        """
        Return whether the requesting user may see an extension: a superuser sees every one.

        :param request: The request.
        :param extension: The extension.
        :returns: True for a superuser, or if the extension is available to the user's account.
        """
        if request.user.is_superuser:
            return True
        return extension.is_available_to(self.account)  # type: ignore[arg-type]

    def respond(self, request, **kwargs) -> tuple[HTTPStatus, Union[ExtensionConsoleModel, str]]:
        """
        Check permission, validate the request, and call :meth:`handle`, turning its exceptions into errors.

        :param request: The request.
        :param kwargs: Keyword arguments from the url, e.g. ``slug``, passed to :meth:`handle`.
        :returns: The status and the model that :meth:`handle` returns, or an error's status and message:
            403 for a user who is not a superuser, unless :attr:`read_only` is set, 400 for a request that
            is not valid or an extension error, 404 for an extension that is not installed, and 500 for
            anything else.
        """
        if not self.read_only and not request.user.is_superuser:
            return HTTPStatus.FORBIDDEN, FORBIDDEN
        try:
            body = self.parse(request)
            result = self.handle(request, body, **kwargs)
        except ValueError as e:
            return HTTPStatus.BAD_REQUEST, str(e)
        except Extension.DoesNotExist:
            return HTTPStatus.NOT_FOUND, f"No extension {kwargs.get('slug')} is installed."
        except SmarterExtensionException as e:
            return HTTPStatus.BAD_REQUEST, e.message
        # a lifecycle hook is an extension's code, which can fail in any way at all.
        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.exception("%s.respond() failed", self.formatted_class_name)
            return HTTPStatus.INTERNAL_SERVER_ERROR, f"{type(e).__name__}: {e}"
        return HTTPStatus.OK, result

    def handle(self, request, body: Optional[BaseModel], **kwargs) -> ExtensionConsoleModel:
        """
        Carry out the request, and return its response's model.

        :param request: The request.
        :param body: The request's body, validated by :attr:`request_model`, or None if it has none.
        :param kwargs: Keyword arguments from the url.
        :returns: The response's contract model.
        :raises ValueError: If the request is not valid.
        :raises Extension.DoesNotExist: If the extension is not installed.
        :raises SmarterExtensionException: If the extension cannot be acted on.
        """
        raise NotImplementedError


class ExtensionListHandler(ExtensionApiHandler):
    """The installed extensions that the requesting user may see, and the state of the registry."""

    read_only = True

    def handle(self, request, body, **kwargs) -> ExtensionListResponse:
        """
        List the installed extensions that the requesting user may see, by display name.

        :param request: The request.
        :param body: None: the request has no body.
        :returns: The extensions, whether the registry is enabled, and how many updates are available.
        """
        extensions = []
        for extension in Extension.objects.select_related("installed_version").order_by("display_name"):
            if self.visible(request, extension):
                extensions.append(extension)
        updates_available = 0
        for extension in extensions:
            if extension.update_available:
                updates_available += 1
        return ExtensionListResponse(
            objects=[ExtensionSummary.from_model(extension, detail_url(extension.slug)) for extension in extensions],
            registry_enabled=registry.is_enabled(),
            updates_available=updates_available,
        )


class ExtensionRegistryHandler(ExtensionApiHandler):
    """The registry's extensions, with what each offers on this platform.

    Only a superuser may refresh it.
    """

    request_model = RegistryRequest
    read_only = True

    def handle(self, request, body: Optional[BaseModel], **kwargs) -> RegistryResponse:
        """
        Return the registry's extensions, from the cached index, or from the registry if a superuser asks to refresh it.

        :param request: The request.
        :param body: Whether to refresh the index.
        :returns: The registry's extensions, or an error if the registry is disabled or cannot be read.
        """
        if not isinstance(body, RegistryRequest):
            raise ValueError("The request is not a RegistryRequest.")
        if not registry.is_enabled():
            return RegistryResponse(
                enabled=False,
                error="The extension registry is disabled until SMARTER_EXTENSION_REGISTRY_PUBLIC_KEY is set.",
                objects=[],
            )
        try:
            user = request.user
            refresh = body.refresh and isinstance(user, User) and user.is_superuser
            index = registry.refresh_index() if refresh else registry.get_index()
        except SmarterExtensionException as e:
            return RegistryResponse(enabled=True, error=e.message, objects=[])
        return RegistryResponse(enabled=True, objects=registry_extensions(index))


class ExtensionCheckUpdatesHandler(ExtensionApiHandler):
    """Check the registry for updates now."""

    def handle(self, request, body, **kwargs) -> ActionResponse:
        """
        Check the registry for updates, refreshing its index, and record each extension's latest version.

        :param request: The request.
        :param body: None: the request has no body.
        :returns: A message that names the available updates.
        """
        updates = registry.check_for_updates(refresh=True)
        names = ", ".join(f"{extension.display_name} {extension.latest_version}" for extension in updates)
        return ActionResponse(
            message=f"Updates are available: {names}." if updates else "Every extension is up to date."
        )


class ExtensionInstallHandler(ExtensionApiHandler):
    """Install, or update, an extension from the registry."""

    request_model = InstallRequest

    def handle(self, request, body: Optional[BaseModel], **kwargs) -> ActionResponse:
        """
        Install, or update, an extension from the registry.

        :param request: The request.
        :param body: The extension's slug, and optionally its version.
        :returns: A message, and the installed extension.
        """
        if not isinstance(body, InstallRequest):
            raise ValueError("The request is not an InstallRequest.")
        extension = registry.install_from_registry(body.slug, body.version, user=request.user)  # type: ignore[arg-type]
        return ActionResponse(
            message=f"Installed {extension.display_name} {extension.installed_version.version}.",  # type: ignore[union-attr]
            extension=extension_detail(extension),
        )


class ExtensionUploadHandler(ExtensionApiHandler):
    """Install, or update, an extension from an uploaded archive: a multipart request with the file ``archive``."""

    def handle(self, request, body, **kwargs) -> ActionResponse:
        """
        Install an extension from the uploaded archive.

        :param request: The multipart request, with the file ``archive``.
        :param body: None: the archive is a file, not a JSON body.
        :returns: A message, and the installed extension.
        :raises ValueError: If no archive was uploaded, or it is larger than ``MAX_UPLOAD_BYTES``.
        """
        upload = request.FILES.get("archive")
        if upload is None:
            raise ValueError("Choose an extension's .zip archive to upload.")
        if upload.size and upload.size > MAX_UPLOAD_BYTES:
            raise ValueError(f"The archive is larger than {MAX_UPLOAD_BYTES} bytes.")
        extension = self.installer(request).install(upload.read())
        return ActionResponse(
            message=f"Installed {extension.display_name} {extension.installed_version.version}. Configure its settings, then enable it.",  # type: ignore[union-attr]
            extension=extension_detail(extension),
        )


class ExtensionDetailHandler(ExtensionApiHandler):
    """Everything that an extension's detail page shows, and less to a user who is not a superuser."""

    read_only = True

    def handle(self, request, body, slug: str = "", **kwargs) -> ExtensionDetailResponse:
        """
        Return an extension's detail, or its read-only detail to a user who is not a superuser.

        :param request: The request.
        :param body: None: the request has no body.
        :param slug: The extension's slug, from the url.
        :returns: The extension's detail.
        :raises Extension.DoesNotExist: If it is not installed, or the requesting user may not see it.
        """
        extension = self.extension(slug)
        if request.user.is_superuser:
            return ExtensionDetailResponse(extension=extension_detail(extension))
        if not self.visible(request, extension):
            raise Extension.DoesNotExist
        return ExtensionDetailResponse(extension=read_only_detail(extension_detail(extension)))


class ExtensionActionHandler(ExtensionApiHandler):
    """The base class of an action on one extension: :meth:`act` returns the message of its success."""

    def act(self, request, extension: Extension, body) -> str:
        """
        Carry out the action, and return what happened.

        :param request: The request.
        :param extension: The extension to act on.
        :param body: The request's body, validated by :attr:`request_model`, or None.
        :returns: The message of the action's success.
        """
        raise NotImplementedError

    def handle(self, request, body, slug: str = "", **kwargs) -> ActionResponse:
        """
        Act on an extension, then return the message and the extension as it now is.

        :param request: The request.
        :param body: The request's body, validated by :attr:`request_model`, or None.
        :param slug: The extension's slug, from the url.
        :returns: The message, and the extension's detail, or None if the action uninstalled it.
        """
        extension = self.extension(slug)
        message = self.act(request, extension, body)
        refreshed = Extension.objects.select_related("installed_version").filter(slug=slug).first()
        if refreshed:
            refreshed_detail = extension_detail(refreshed)
        else:
            refreshed_detail = None
        return ActionResponse(message=message, extension=refreshed_detail)


class ExtensionEnableHandler(ExtensionActionHandler):
    """Enable an extension."""

    def act(self, request, extension, body) -> str:
        """Enable the extension, after checking that it is compatible, loads, and has its required settings."""
        self.installer(request).enable(extension)
        return f"Enabled {extension.display_name}."


class ExtensionDisableHandler(ExtensionActionHandler):
    """Disable an extension."""

    def act(self, request, extension, body) -> str:
        """Disable the extension."""
        self.installer(request).disable(extension)
        return f"Disabled {extension.display_name}."


class ExtensionUpdateHandler(ExtensionActionHandler):
    """Update an extension to the registry's newest compatible version."""

    def act(self, request, extension, body) -> str:
        """Install the registry's newest compatible version of the extension."""
        updated = registry.install_from_registry(extension.slug, user=request.user)  # type: ignore[arg-type]
        return f"Updated {extension.display_name} to {updated.installed_version.version}."  # type: ignore[union-attr]


class ExtensionRollbackHandler(ExtensionActionHandler):
    """Make an earlier version of an extension the one that runs."""

    request_model = RollbackRequest

    def act(self, request, extension, body: RollbackRequest) -> str:
        """
        Make one of the extension's installed versions the one that runs.

        :raises ValueError: If the version is not one of the extension's.
        """
        version = ExtensionVersion.objects.filter(pk=body.version_id, extension=extension).first()
        if version is None:
            raise ValueError(f"{extension.display_name} has no version {body.version_id}.")
        self.installer(request).rollback(extension, version)
        return f"Rolled {extension.display_name} back to {version.version}."


class ExtensionConfigureHandler(ExtensionActionHandler):
    """Change some of an extension's settings."""

    request_model = ConfigureRequest

    def act(self, request, extension, body: ConfigureRequest) -> str:
        """
        Save the extension's settings.

        A secret setting is given a new value, which is saved, encrypted, in a Secret owned by
        the platform admin, or the id of one of the platform admin's Secrets, or neither, which
        clears it.

        :raises ValueError: If the extension has no installed version, a secret setting does not
            exist, or a Secret is not one of the platform admin's.
        """
        if extension.installed_version is None:
            raise ValueError(f"{extension.display_name} has no installed version.")
        manifest = extension.installed_version.parsed_manifest
        values: dict[str, SettingInput] = dict(body.values)
        owner = smarter_cached_objects.smarter_admin_user_profile
        for name, secret_input in body.secrets.items():
            spec = manifest.setting(name)
            if spec is None or spec.type != ExtensionSettingType.SECRET:
                raise ValueError(f"{extension.display_name} has no secret setting {name}.")
            if secret_input.value:
                name_of_secret = secret_name(extension.slug, name)
                secret = Secret.objects.filter(user_profile=owner, name=name_of_secret).first()
                if not secret:
                    secret = Secret(
                        user_profile=owner,
                        name=name_of_secret,
                        description=f"The {name} setting of the {extension.slug} extension.",
                    )
                secret.encrypted_value = Secret.encrypt(secret_input.value)
                secret.save()
                values[name] = secret
            elif secret_input.secret_id is not None:
                secret = Secret.objects.filter(user_profile=owner, pk=secret_input.secret_id).first()
                if secret is None:
                    raise ValueError(f"Secret {secret_input.secret_id} is not one of the platform admin's Secrets.")
                values[name] = secret
            else:
                values[name] = None
        self.installer(request).configure(extension, values)
        return f"Saved the settings of {extension.display_name}."


class ExtensionAvailabilityHandler(ExtensionActionHandler):
    """Change which accounts may use an extension."""

    request_model = AvailabilityRequest

    def act(self, request, extension, body: AvailabilityRequest) -> str:
        """
        Make the extension available to every account, or to the given accounts.

        :raises ValueError: If some of the accounts do not exist.
        """
        accounts = list(Account.objects.filter(pk__in=body.account_ids))
        if len(accounts) != len(set(body.account_ids)):
            raise ValueError("Some of the accounts do not exist.")
        extension.all_accounts = body.all_accounts
        extension.save(update_fields=["all_accounts", "updated_at"])
        extension.accounts.set(accounts)
        if body.all_accounts:
            return f"{extension.display_name} is available to every account."
        return f"{extension.display_name} is available to {len(accounts)} account(s)."


class ExtensionUninstallHandler(ExtensionActionHandler):
    """Uninstall an extension."""

    def act(self, request, extension, body) -> str:
        """Uninstall the extension."""
        self.installer(request).uninstall(extension)
        return f"Uninstalled {extension.display_name}."


class ExtensionAccountsHandler(ExtensionApiHandler):
    """Every account, for the availability picker."""

    def handle(self, request, body, **kwargs) -> AccountsResponse:
        """
        List every account, by account number.

        :param request: The request.
        :param body: None: the request has no body.
        :returns: The accounts.
        """
        return AccountsResponse(
            objects=[AccountRef.from_model(account) for account in Account.objects.order_by("account_number")]
        )


# ------------------------------------------------------------------------------
# the web console's api
# ------------------------------------------------------------------------------
# abstract: its concrete views get handle() from the handler that they mix in before it.
class ExtensionApiView(ExtensionApiHandler, SmarterAuthenticatedNeverCachedWebView):  # pylint: disable=abstract-method
    """
    The base class of the web console's Extensions api: POST only, JSON in and out, and a Django session.

    Its concrete views mix a handler in before it, e.g. ``ExtensionEnableApiView(ExtensionEnableHandler,
    ExtensionApiView)``. Errors are ``{"error": ...}``.
    """

    http_method_names = ["post"]

    @property
    def formatted_class_name(self) -> str:  # type: ignore[override]
        """The class name, for logging."""
        return f"{self.formatted_text(__name__)}.{self.__class__.__name__}"

    def error(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> JsonResponse:
        """
        Return an error response.

        :param message: What went wrong.
        :param status: The HTTP status.
        :returns: ``{"error": message}``, with the status.
        """
        return JsonResponse(ErrorResponse(error=message).to_json(), status=status)

    def post(self, request: ASGIRequest, *args, **kwargs) -> JsonResponse:
        """
        Carry out the request with :meth:`respond`.

        :param request: The request.
        :param kwargs: Keyword arguments from the url, e.g. ``slug``.
        :returns: The JSON of the model that :meth:`handle` returns, or an error.
        """
        status, result = self.respond(request, **kwargs)
        if isinstance(result, str):
            return self.error(result, status)
        return JsonResponse(result.to_json())


class ExtensionListApiView(ExtensionListHandler, ExtensionApiView):
    """The installed extensions that the requesting user may see, and the state of the registry."""


class ExtensionRegistryApiView(ExtensionRegistryHandler, ExtensionApiView):
    """The registry's extensions, with what each offers on this platform."""


class ExtensionCheckUpdatesApiView(ExtensionCheckUpdatesHandler, ExtensionApiView):
    """Check the registry for updates now."""


class ExtensionInstallApiView(ExtensionInstallHandler, ExtensionApiView):
    """Install, or update, an extension from the registry."""


class ExtensionUploadApiView(ExtensionUploadHandler, ExtensionApiView):
    """Install, or update, an extension from an uploaded archive."""


class ExtensionDetailApiView(ExtensionDetailHandler, ExtensionApiView):
    """An extension's detail page."""


class ExtensionEnableApiView(ExtensionEnableHandler, ExtensionApiView):
    """Enable an extension."""


class ExtensionDisableApiView(ExtensionDisableHandler, ExtensionApiView):
    """Disable an extension."""


class ExtensionUpdateApiView(ExtensionUpdateHandler, ExtensionApiView):
    """Update an extension to the registry's newest compatible version."""


class ExtensionRollbackApiView(ExtensionRollbackHandler, ExtensionApiView):
    """Make an earlier version of an extension the one that runs."""


class ExtensionConfigureApiView(ExtensionConfigureHandler, ExtensionApiView):
    """Change some of an extension's settings."""


class ExtensionAvailabilityApiView(ExtensionAvailabilityHandler, ExtensionApiView):
    """Change which accounts may use an extension."""


class ExtensionUninstallApiView(ExtensionUninstallHandler, ExtensionApiView):
    """Uninstall an extension."""


class ExtensionAccountsApiView(ExtensionAccountsHandler, ExtensionApiView):
    """Every account, for the availability picker."""


__all__ = [
    "ExtensionAccountsHandler",
    "ExtensionActionHandler",
    "ExtensionApiHandler",
    "ExtensionAvailabilityHandler",
    "ExtensionCheckUpdatesHandler",
    "ExtensionConfigureHandler",
    "ExtensionDetailHandler",
    "ExtensionDisableHandler",
    "ExtensionEnableHandler",
    "ExtensionInstallHandler",
    "ExtensionListHandler",
    "ExtensionRegistryHandler",
    "ExtensionRollbackHandler",
    "ExtensionUninstallHandler",
    "ExtensionUpdateHandler",
    "ExtensionUploadHandler",
    "ExtensionApiView",
    "FORBIDDEN",
    "MAX_UPLOAD_BYTES",
    "ExtensionAccountsApiView",
    "ExtensionAvailabilityApiView",
    "ExtensionCheckUpdatesApiView",
    "ExtensionConfigureApiView",
    "ExtensionDetailApiView",
    "ExtensionDetailView",
    "ExtensionDisableApiView",
    "ExtensionEnableApiView",
    "ExtensionInstallApiView",
    "ExtensionListApiView",
    "ExtensionListView",
    "ExtensionRegistryApiView",
    "ExtensionRollbackApiView",
    "ExtensionUninstallApiView",
    "ExtensionUpdateApiView",
    "ExtensionUploadApiView",
    "extension_detail",
    "read_only_detail",
    "registry_extensions",
]
