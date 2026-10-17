"""
The web console's Extensions pages, and their api.

Superusers manage extensions on two pages, which one React app, ``@smarter/extension-console``,
renders, depending on the root element that the page's template provides. Every other user sees
the same pages read-only: the extensions that their account may use, without their settings, their
availability or the platform admin's Secrets, and without any action.

- **Extensions** (``/extensions/``): the installed extensions, and the registry's, which can be
  installed, and an archive's upload.
- **An extension** (``/extensions/<slug>/``): its documentation, tools, settings, availability,
  versions and resources, and every action on it.

The api is a set of POST endpoints, under ``/extensions/react-integration/api/``. The actions are
for superusers only; the list, the registry and an extension's detail are read-only for everyone
else. Each validates its request and builds its response with the models of
:mod:`~smarter.apps.llmtool.extension.contract`, and carries out its action with the
:class:`~smarter.apps.llmtool.extension.installer.ExtensionInstaller` or the
:mod:`~smarter.apps.llmtool.extension.registry` client, as the admin console and the management
commands do. An action's failure is a 400 with ``{"error": "..."}``, whose message is meant for
the person who tried it.
"""

from http import HTTPStatus
from typing import Optional

from django.conf import settings
from django.core.handlers.asgi import ASGIRequest
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ValidationError
from waffle import get_waffle_switch_model

from smarter.apps.account.models import Account
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmtool.models import Extension, ExtensionVersion
from smarter.apps.secret.models import Secret
from smarter.lib import json, logging
from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active

from . import registry
from .contract import (
    TRUST_BADGE_LABELS,
    AccountRef,
    AccountsResponse,
    ActionResponse,
    AvailabilityRequest,
    ConfigureRequest,
    ErrorResponse,
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
from .manifest import ExtensionSettingType
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
    """Return the name of the Secret that holds a secret setting's typed value."""
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
    """Return whether a version is newer than another; an unparsable version is never newer."""
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
class ExtensionPageView(SmarterAuthenticatedNeverCachedWebView):
    """
    The base class of the Extensions pages, and the React app's root element's attributes.

    A superuser manages extensions on them; every other user sees them read-only.
    """

    template_path: str
    context_key: str
    root_id: str

    def page_context(self, **extra: str) -> dict:
        """The template's context: the React app's root element's attributes."""
        # pylint: disable=import-outside-toplevel
        from .urls import ExtensionReverseNames

        return {
            self.context_key: {
                "root_id": self.root_id,
                "django_csrf_cookie_name": settings.CSRF_COOKIE_NAME,
                "django_session_cookie_name": settings.SESSION_COOKIE_NAME,
                "cookie_domain": settings.SESSION_COOKIE_DOMAIN,
                "extension_api_url": reverse(ExtensionReverseNames.namespace, ExtensionReverseNames.api_root),
                "extension_list_url": reverse(ExtensionReverseNames.namespace, ExtensionReverseNames.listview),
                "can_edit": "true" if self.request.user.is_superuser else "false",  # type: ignore[union-attr]
                "react_debug_mode": switch_is_active(SmarterWaffleSwitches.ENABLE_REACTAPP_DEBUG_MODE),
                "smarter_request_id": self.generate_smarter_request_id(),
                **extra,
            }
        }


class ExtensionListView(ExtensionPageView):
    """Render the Extensions list of the Smarter web console."""

    template_path = "react/extension-list.html"
    context_key = "extension_list"
    root_id = "smarter-extension-list-root"

    def get(self, request: ASGIRequest, *args, **kwargs) -> HttpResponse:
        return render(request, template_name=self.template_path, context=self.page_context())


class ExtensionDetailView(ExtensionPageView):
    """Render an extension's detail page in the Smarter web console."""

    template_path = "react/extension-detail.html"
    context_key = "extension_detail"
    root_id = "smarter-extension-detail-root"

    def get(self, request: ASGIRequest, *args, slug: str = "", **kwargs) -> HttpResponse:
        extension = Extension.objects.filter(slug=slug).first()
        if extension is None or not (
            request.user.is_superuser or extension.is_available_to(self.account)  # type: ignore[union-attr]
        ):
            return SmarterHttpResponseNotFound(request=request, error_message=f"No extension {slug} is installed.")
        return render(request, template_name=self.template_path, context=self.page_context(extension_slug=slug))


# ------------------------------------------------------------------------------
# the api
# ------------------------------------------------------------------------------
class ExtensionApiView(SmarterAuthenticatedNeverCachedWebView):
    """
    The base class of the Extensions api: POST only, JSON in and out, and superusers only unless.

    :attr:`read_only` is set.

    Subclasses implement :meth:`handle`, which returns a contract model, and set
    :attr:`request_model` if the request has a body.
    """

    request_model: Optional[type[BaseModel]] = None
    read_only: bool = False
    """Whether every user may call it.

    It then shows a user who is not a superuser only what they may see.
    """
    http_method_names = ["post"]

    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return self.formatted_text(f"{__name__}.{self.__class__.__name__}")

    def error(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> JsonResponse:
        """Return an error response."""
        return JsonResponse(ErrorResponse(error=message).to_json(), status=status)

    def installer(self, request: ASGIRequest) -> ExtensionInstaller:
        """Return an installer that acts as the requesting superuser."""
        return ExtensionInstaller(user=request.user)  # type: ignore[arg-type]

    def extension(self, slug: str) -> Extension:
        """Return an installed extension, or raise Extension.DoesNotExist."""
        return Extension.objects.select_related("installed_version").get(slug=slug)

    def parse(self, request: ASGIRequest) -> Optional[BaseModel]:
        """Validate the request's JSON body with :attr:`request_model`."""
        if self.request_model is None:
            return None
        try:
            body = json.loads(request.body or b"{}")
        except json.JSONDecodeError as e:
            raise ValueError(f"The request is not JSON: {e}") from e
        try:
            return self.request_model.model_validate(body if isinstance(body, dict) else {})
        except ValidationError as e:
            problems = "; ".join(
                f"{'.'.join(str(part) for part in error['loc']) or 'request'}: {error['msg']}" for error in e.errors()
            )
            raise ValueError(f"The request is not valid: {problems}") from e

    def visible(self, request: ASGIRequest, extension: Extension) -> bool:
        """Return whether the requesting user may see an extension: a superuser sees every one."""
        return request.user.is_superuser or extension.is_available_to(self.account)  # type: ignore[union-attr]

    def post(self, request: ASGIRequest, *args, **kwargs) -> JsonResponse:
        if not (self.read_only or request.user.is_superuser):  # type: ignore[union-attr]
            return self.error(FORBIDDEN, HTTPStatus.FORBIDDEN)
        try:
            body = self.parse(request)
            result = self.handle(request, body, **kwargs)
        except ValueError as e:
            return self.error(str(e))
        except Extension.DoesNotExist:
            return self.error(f"No extension {kwargs.get('slug')} is installed.", HTTPStatus.NOT_FOUND)
        except SmarterExtensionException as e:
            return self.error(e.message)
        # a lifecycle hook is an extension's code, which can fail in any way at all.
        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.exception("%s.post() failed", self.formatted_class_name)
            return self.error(f"{type(e).__name__}: {e}", HTTPStatus.INTERNAL_SERVER_ERROR)
        return JsonResponse(result.to_json())

    def handle(self, request: ASGIRequest, body: Optional[BaseModel], **kwargs):
        """Carry out the request, and return its response's model."""
        raise NotImplementedError


class ExtensionListApiView(ExtensionApiView):
    """The installed extensions that the requesting user may see, and the state of the registry."""

    read_only = True

    def handle(self, request, body, **kwargs) -> ExtensionListResponse:
        extensions = [
            extension
            for extension in Extension.objects.select_related("installed_version").order_by("display_name")
            if self.visible(request, extension)
        ]
        return ExtensionListResponse(
            objects=[ExtensionSummary.from_model(extension, detail_url(extension.slug)) for extension in extensions],
            registry_enabled=registry.is_enabled(),
            updates_available=sum(1 for extension in extensions if extension.update_available),
        )


class ExtensionRegistryApiView(ExtensionApiView):
    """The registry's extensions, with what each offers on this platform.

    Only a superuser may refresh it.
    """

    request_model = RegistryRequest
    read_only = True

    def handle(self, request, body: RegistryRequest, **kwargs) -> RegistryResponse:
        if not registry.is_enabled():
            return RegistryResponse(
                enabled=False,
                error="The extension registry is disabled until SMARTER_EXTENSION_REGISTRY_PUBLIC_KEY is set.",
                objects=[],
            )
        try:
            refresh = body.refresh and request.user.is_superuser
            index = registry.refresh_index() if refresh else registry.get_index()
        except SmarterExtensionException as e:
            return RegistryResponse(enabled=True, error=e.message, objects=[])
        return RegistryResponse(enabled=True, objects=registry_extensions(index))


class ExtensionCheckUpdatesApiView(ExtensionApiView):
    """Check the registry for updates now."""

    def handle(self, request, body, **kwargs) -> ActionResponse:
        updates = registry.check_for_updates(refresh=True)
        names = ", ".join(f"{extension.display_name} {extension.latest_version}" for extension in updates)
        return ActionResponse(
            message=f"Updates are available: {names}." if updates else "Every extension is up to date."
        )


class ExtensionInstallApiView(ExtensionApiView):
    """Install, or update, an extension from the registry."""

    request_model = InstallRequest

    def handle(self, request, body: InstallRequest, **kwargs) -> ActionResponse:
        extension = registry.install_from_registry(body.slug, body.version, user=request.user)  # type: ignore[arg-type]
        return ActionResponse(
            message=f"Installed {extension.display_name} {extension.installed_version.version}.",  # type: ignore[union-attr]
            extension=extension_detail(extension),
        )


class ExtensionUploadApiView(ExtensionApiView):
    """Install, or update, an extension from an uploaded archive: a multipart request with the file ``archive``."""

    def handle(self, request, body, **kwargs) -> ActionResponse:
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


class ExtensionDetailApiView(ExtensionApiView):
    """Everything that an extension's detail page shows, and less to a user who is not a superuser."""

    read_only = True

    def handle(self, request, body, slug: str = "", **kwargs) -> ExtensionDetailResponse:
        extension = self.extension(slug)
        if request.user.is_superuser:
            return ExtensionDetailResponse(extension=extension_detail(extension))
        if not self.visible(request, extension):
            raise Extension.DoesNotExist
        return ExtensionDetailResponse(extension=read_only_detail(extension_detail(extension)))


class ExtensionActionApiView(ExtensionApiView):
    """The base class of an action on one extension: :meth:`act` returns the message of its success."""

    def act(self, request: ASGIRequest, extension: Extension, body) -> str:
        """Carry out the action, and return what happened."""
        raise NotImplementedError

    def handle(self, request, body, slug: str = "", **kwargs) -> ActionResponse:
        extension = self.extension(slug)
        message = self.act(request, extension, body)
        refreshed = Extension.objects.select_related("installed_version").filter(slug=slug).first()
        return ActionResponse(message=message, extension=extension_detail(refreshed) if refreshed else None)


class ExtensionEnableApiView(ExtensionActionApiView):
    """Enable an extension."""

    def act(self, request, extension, body) -> str:
        self.installer(request).enable(extension)
        return f"Enabled {extension.display_name}."


class ExtensionDisableApiView(ExtensionActionApiView):
    """Disable an extension."""

    def act(self, request, extension, body) -> str:
        self.installer(request).disable(extension)
        return f"Disabled {extension.display_name}."


class ExtensionUpdateApiView(ExtensionActionApiView):
    """Update an extension to the registry's newest compatible version."""

    def act(self, request, extension, body) -> str:
        updated = registry.install_from_registry(extension.slug, user=request.user)  # type: ignore[arg-type]
        return f"Updated {extension.display_name} to {updated.installed_version.version}."  # type: ignore[union-attr]


class ExtensionRollbackApiView(ExtensionActionApiView):
    """Make an earlier version of an extension the one that runs."""

    request_model = RollbackRequest

    def act(self, request, extension, body: RollbackRequest) -> str:
        version = ExtensionVersion.objects.filter(pk=body.version_id, extension=extension).first()
        if version is None:
            raise ValueError(f"{extension.display_name} has no version {body.version_id}.")
        self.installer(request).rollback(extension, version)
        return f"Rolled {extension.display_name} back to {version.version}."


class ExtensionConfigureApiView(ExtensionActionApiView):
    """Change some of an extension's settings."""

    request_model = ConfigureRequest

    def act(self, request, extension, body: ConfigureRequest) -> str:
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
                secret = Secret.objects.filter(
                    user_profile=owner, name=secret_name(extension.slug, name)
                ).first() or Secret(
                    user_profile=owner,
                    name=secret_name(extension.slug, name),
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


class ExtensionAvailabilityApiView(ExtensionActionApiView):
    """Change which accounts may use an extension."""

    request_model = AvailabilityRequest

    def act(self, request, extension, body: AvailabilityRequest) -> str:
        accounts = list(Account.objects.filter(pk__in=body.account_ids))
        if len(accounts) != len(set(body.account_ids)):
            raise ValueError("Some of the accounts do not exist.")
        extension.all_accounts = body.all_accounts
        extension.save(update_fields=["all_accounts", "updated_at"])
        extension.accounts.set(accounts)
        if body.all_accounts:
            return f"{extension.display_name} is available to every account."
        return f"{extension.display_name} is available to {len(accounts)} account(s)."


class ExtensionUninstallApiView(ExtensionActionApiView):
    """Uninstall an extension."""

    def act(self, request, extension, body) -> str:
        self.installer(request).uninstall(extension)
        return f"Uninstalled {extension.display_name}."


class ExtensionAccountsApiView(ExtensionApiView):
    """Every account, for the availability picker."""

    def handle(self, request, body, **kwargs) -> AccountsResponse:
        return AccountsResponse(
            objects=[AccountRef.from_model(account) for account in Account.objects.order_by("account_number")]
        )


__all__ = [
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
