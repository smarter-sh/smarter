# pylint: disable=W0718,R0904
"""
Smarter API Proxy Manifest handler.

The broker implements the ``smarter`` CLI commands for Proxies:

- ``apply``: create or update the Proxy from its manifest. ``spec.provider`` and ``spec.apiKey``
  are resolved to the Provider and Secret of those names that the user may read.
- ``describe``: the manifest, with the Proxy's URL, and the URL and Secret it forwards with.
- ``get``: the Proxies that the user may read, including the built-in ones.
- ``delete``: delete the user's Proxy.

Proxies are not deployed: they work as soon as they are applied. So ``deploy``, ``undeploy``,
``logs`` and ``prompt`` are not implemented.
"""

import datetime
from typing import Any, List, Optional, Type
from urllib.parse import urljoin

from django.db import transaction
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.provider.models import Provider
from smarter.apps.proxy.caching import invalidate_all_cached_proxies_for_user_profile
from smarter.apps.proxy.exceptions import ProxyNotFound
from smarter.apps.proxy.manifest.models.proxy.const import MANIFEST_KIND
from smarter.apps.proxy.manifest.models.proxy.metadata import SAMProxyMetadata
from smarter.apps.proxy.manifest.models.proxy.model import SAMProxy
from smarter.apps.proxy.manifest.models.proxy.spec import (
    SAMProxySpec,
    SAMProxySpecAuth,
)
from smarter.apps.proxy.manifest.models.proxy.status import SAMProxyStatus
from smarter.apps.proxy.models import Proxy
from smarter.apps.proxy.serializers import ProxySerializer
from smarter.apps.proxy.services import resolve_proxy
from smarter.apps.proxy.signals import broker_ready
from smarter.apps.secret.models import Secret
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
    memoized_dependencies,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.PROXY_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000


def proxy_spec_to_django_orm(spec: SAMProxySpec) -> dict[str, Any]:
    """The Proxy fields of a spec, other than its Provider and Secret, which the broker resolves by name."""
    return {
        "base_url": spec.baseUrl or "",
        "auth_header": spec.auth.header,
        "auth_scheme": spec.auth.scheme,
        "headers": dict(spec.headers),
        "allowed_paths": list(spec.allowedPaths),
        "timeout": spec.timeout,
        "is_active": spec.isActive,
    }


def django_orm_to_proxy_spec(proxy: Proxy) -> SAMProxySpec:
    """The spec of a Proxy, as it would be applied: its Secret is named only if it is the Proxy's own."""
    return SAMProxySpec(
        provider=proxy.provider.name,
        apiKey=proxy.api_key_secret.name if proxy.api_key_secret else None,
        baseUrl=proxy.base_url or None,
        auth=SAMProxySpecAuth(header=proxy.auth_header, scheme=proxy.auth_scheme),
        headers=proxy.headers or {},
        allowedPaths=proxy.allowed_paths or [],
        timeout=proxy.timeout,
        isActive=proxy.is_active,
    )


class SAMProxyBrokerError(SAMBrokerError):
    """Base exception for Smarter API Proxy Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Proxy Manifest Broker Error"


class SAMProxyBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` Proxy manifests.

    It converts between Proxy manifests and the :class:`~smarter.apps.proxy.models.Proxy`
    Django ORM model.

    ``spec.provider`` is the name of a Provider that the manifest's owner may read, e.g. a
    built-in one. ``spec.apiKey`` is the name of a Secret of the owner's account. The user's own
    takes precedence. They are stored as foreign keys, and rendered as names, never the API key
    itself.
    """

    _manifest: Optional[SAMProxy] = None
    _pydantic_model: Type[SAMProxy] = SAMProxy
    _proxy: Optional[Proxy] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        logger.info(
            "%s.__init__() broker for %s %s is %s.", self.formatted_class_name, self.kind, self.name, self.ready_state
        )

    @property
    def SerializerClass(self) -> Type[ModelSerializer]:
        """The Django ORM model serializer class for the Proxy."""
        return ProxySerializer

    @property
    def ready(self) -> bool:
        """A broker is ready if it has a manifest, or an account."""
        if self._ready:
            return self._ready
        if not super().ready:
            return False
        if self.manifest is not None or self.account is not None:
            self._ready = True
            broker_ready.send(sender=self.__class__, broker=self)
        return self._ready

    @property
    def proxy(self) -> Optional[Proxy]:
        """
        The user's own Proxy with the broker's name, if it exists.

        It is never created here: :meth:`apply` does that.
        """
        if self._proxy:
            return self._proxy
        if not self.user_profile or not self.name:
            return None
        self._proxy = (
            Proxy.objects.select_related("provider", "api_key_secret", "user_profile__user", "user_profile__account")
            .filter(user_profile=self.user_profile, name=self.name)
            .first()
        )
        return self._proxy

    def readable_proxy(self) -> Optional[Proxy]:
        """
        The Proxy that the user means by the broker's name: their own, else their account's, else the built-in one.

        ``describe`` uses it, so that users can read the built-in Proxies' manifests.
        """
        if self.proxy:
            return self.proxy
        if not self.user_profile or not self.name:
            return None
        try:
            return resolve_proxy(self.name, self.user_profile)
        except ProxyNotFound:
            return None

    def resolve_provider(self, name: str) -> Provider:
        """The Provider named by spec.provider: the user's own, else the most recently updated one that they may read."""
        if not self.user_profile:
            raise SAMBrokerErrorNotReady("user_profile is not set.", thing=self.kind)
        provider = Provider.objects.filter(name=name, user_profile=self.user_profile).first()
        if provider is None:
            provider = (
                Provider.objects.filter(name=name)
                .with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
                .order_by("-updated_at")
                .first()
            )
        if provider is None:
            raise SAMBrokerErrorNotFound(
                f"spec.provider: Provider {name} not found, or not shared with {self.user_profile}.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        return provider

    def resolve_secret(self, name: Optional[str]) -> Optional[Secret]:
        """
        The Secret named by spec.apiKey, or ``None`` if it is not set: the user's own, else their account's.

        Unlike the Provider, the Secret must belong to the user's account, so that a Proxy cannot
        send another account's API key, e.g. the platform's, to a base URL of its owner's choosing.
        See :meth:`~smarter.apps.proxy.models.Proxy.may_use_secret`.
        """
        if not name:
            return None
        if not self.user_profile:
            raise SAMBrokerErrorNotReady("user_profile is not set.", thing=self.kind)
        secret = Secret.objects.filter(name=name, user_profile=self.user_profile).first()
        if secret is None:
            secret = (
                Secret.objects.filter(name=name, user_profile__account=self.user_profile.account)
                .order_by("-updated_at")
                .first()
            )
        if secret is None:
            raise SAMBrokerErrorNotFound(
                f"spec.apiKey: Secret {name} not found in the account of {self.user_profile}. A Proxy may only use "
                "its own account's Secrets.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        return secret

    def manifest_to_django_orm(self) -> dict[str, Any]:
        """
        Convert the manifest into a dict of Django ORM Proxy fields.

        :raises SAMBrokerErrorNotFound: if the Provider or Secret is not found.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"Manifest not loaded for {self.kind} broker.", thing=self.kind)
        spec = self.manifest.spec
        return {
            **super().manifest_to_django_orm(),
            **proxy_spec_to_django_orm(spec),
            "provider": self.resolve_provider(spec.provider),
            "api_key_secret": self.resolve_secret(spec.apiKey),
        }

    def django_orm_to_manifest_dict(self, proxy: Optional[Proxy] = None) -> Optional[dict]:
        """Convert a Proxy, by default the user's, into a manifest dict, with its status."""
        if not self.account or not self.user_profile:
            raise SAMBrokerErrorNotReady(
                f"Account and user profile are required to describe a {self.kind}.", thing=self.kind
            )
        proxy = proxy or self.proxy
        if not proxy:
            return None
        meta = SAMProxyMetadata(
            name=proxy.name,
            description=proxy.description,
            version=proxy.version,
            tags=proxy.tags_list,
            annotations=proxy.annotations if isinstance(proxy.annotations, list) else [],
        )
        status = SAMProxyStatus(
            accountNumber=proxy.user_profile.account.account_number,
            username=proxy.user_profile.user.username,
            recordLocator=proxy.record_locator,
            created=proxy.created_at,
            modified=proxy.updated_at,
            url=urljoin(smarter_settings.environment_url, proxy.url) if proxy.url else None,
            upstreamUrl=proxy.upstream_base_url or None,
            apiKeySecret=proxy.secret_name,
        )
        model = SAMProxy(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta,
            spec=django_orm_to_proxy_spec(proxy),
            status=status,
        )
        return model.model_dump(mode="json", exclude_none=True)

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return self.formatted_text(f"{SAMProxyBroker.__name__}[{id(self)}]")

    @property
    def kind(self) -> str:
        """The manifest kind: Proxy."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMProxy]:
        """The Proxy manifest, as a Pydantic model, from the manifest loader."""
        if self._manifest:
            if not isinstance(self._manifest, SAMProxy):
                raise SAMProxyBrokerError("Cached manifest is not a SAMProxy instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMProxy(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMProxyMetadata(**self.loader.manifest_metadata),
                spec=SAMProxySpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def cache_invalidations(self) -> None:
        """Invalidate the cached Proxy, and the user's cached Proxy lists."""
        if self.proxy:
            Proxy.get_cached_object(pk=self.proxy.pk, invalidate=True)
        if self.user_profile:
            Proxy.get_cached_objects(user_profile=self.user_profile, invalidate=True)
            invalidate_all_cached_proxies_for_user_profile(self.user_profile)
        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[Proxy]:
        return Proxy

    @property
    def ORMModelClass(self) -> Type[Proxy]:
        return Proxy

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return an example Proxy manifest, for Anthropic's Messages API."""
        command = SmarterJournalCliCommands(self.example_manifest.__name__)
        meta_data = SAMProxyMetadata(
            name="example_anthropic",
            description="Passthrough access to Anthropic's Messages API, with an API key that Smarter keeps.",
            version="1.0.0",
            tags=["example", "anthropic"],
            annotations=[{"smarter.sh/proxy/documentation": "https://docs.claude.com/en/api/messages"}],
        )
        spec = SAMProxySpec(
            provider="anthropic",
            apiKey="anthropic_api_key",
            baseUrl="https://api.anthropic.com/v1/",
            auth=SAMProxySpecAuth(header="x-api-key", scheme=""),
            headers={"anthropic-version": "2023-06-01"},
            allowedPaths=["messages", "messages/count_tokens", "models", "models/*"],
            timeout=120,
            isActive=True,
        )
        status = SAMProxyStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
            url=urljoin(smarter_settings.environment_url, "/api/v1/proxy/example_anthropic/"),
            upstreamUrl="https://api.anthropic.com/v1/",
            apiKeySecret="anthropic_api_key",
        )
        model = SAMProxy(apiVersion=self.api_version, kind=self.kind, metadata=meta_data, spec=spec, status=status)
        return self.json_response_ok(command=command, data=model.model_dump(mode="json", exclude_none=True))

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the Proxies that the user may read, optionally filtered by name."""
        command = SmarterJournalCliCommands(self.get.__name__)
        name = self.clean_cli_param(
            param=kwargs.get(SAMMetadataKeys.NAME.value, None),
            param_name="name",
            url=self.smarter_build_absolute_uri(request),
        )
        if self.user_profile is None:
            raise SAMBrokerErrorNotReady("user_profile is not set.")
        proxies = Proxy.objects.with_read_permission_for(self.user_profile.user).select_related(  # type: ignore[attr-defined]
            "provider", "api_key_secret", "user_profile__user", "user_profile__account"
        )
        if name:
            proxies = proxies.filter(name=name)
        data = []
        for proxy in proxies.order_by("name")[:MAX_RESULTS]:
            try:
                data.append(self.to_camel_case(ProxySerializer(proxy).data))
            except Exception as e:
                raise SAMProxyBrokerError(
                    f"Failed to serialize {self.kind} {proxy.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=ProxySerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Create or update the user's Proxy from the manifest.

        .. note::

            tags are handled separately because they are of type TaggableManager and
            require a different method to set them.
        """
        command = SmarterJournalCliCommands(self.apply.__name__)
        if not self.ready or not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"{self.kind} {self.name} broker is not ready", thing=self.kind, command=command
            )
        data = self.manifest_to_django_orm()
        tags = data.pop("tags", None) or []
        for field in ("id", "created_at", "updated_at"):
            data.pop(field, None)
        with transaction.atomic():
            proxy = self.proxy
            if proxy is None:
                proxy = Proxy(**data)
            else:
                for key, value in data.items():
                    setattr(proxy, key, value)
            try:
                proxy.save()
                proxy.tags.set(tags)
            except Exception as e:
                raise SAMProxyBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}: {e}", thing=self.kind, command=command
                ) from e
        self._proxy = proxy
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.to_json())

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.prompt.__name__)
        raise SAMBrokerErrorNotImplemented(
            message=f"Prompt not implemented: call the {self.kind}'s URL with the provider's SDK.",
            thing=self.kind,
            command=command,
        )

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the Proxy as a manifest: the user's own, else their account's, else the built-in one."""
        command = SmarterJournalCliCommands(self.describe.__name__)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} name property is not set.", thing=self.kind, command=command)
        proxy = self.readable_proxy()
        if not proxy:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        try:
            data = self.django_orm_to_manifest_dict(proxy)
        except Exception as e:
            raise SAMProxyBrokerError(
                f"Failed to describe {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data=data)

    @memoized_dependencies
    def dependencies(self) -> List[AbstractBroker]:
        """Return brokers for the resources that depend on this Proxy.

        No other resource refers to a Proxy.

        :return: An empty list.
        :rtype: List[AbstractBroker]
        """
        return []

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Delete the user's Proxy.

        Its Provider and Secret are not deleted.
        """
        command = SmarterJournalCliCommands(self.delete.__name__)
        proxy = self.proxy
        if self.name is None or not proxy:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        self.verify_no_dependencies(command)
        try:
            self.cache_invalidations()
            proxy.delete()
            self._proxy = None
        except Exception as e:
            raise SAMProxyBrokerError(
                f"Failed to delete {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data={})

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.deploy.__name__)
        raise SAMBrokerErrorNotImplemented(
            message=f"Deploy not implemented: a {self.kind} works as soon as it is applied.",
            thing=self.kind,
            command=command,
        )

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.undeploy.__name__)
        raise SAMBrokerErrorNotImplemented(
            message=f"Undeploy not implemented: set the {self.kind}'s spec.isActive to false.",
            thing=self.kind,
            command=command,
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.logs.__name__)
        raise SAMBrokerErrorNotImplemented(message="Logs not implemented", thing=self.kind, command=command)


__all__ = [
    "SAMProxyBroker",
    "SAMProxyBrokerError",
    "django_orm_to_proxy_spec",
    "proxy_spec_to_django_orm",
]
