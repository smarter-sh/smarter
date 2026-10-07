# pylint: disable=W0718,C0302,R0904
"""
Smarter API MCPClient Manifest handler.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import datetime
from typing import Any, List, Optional, Type

from django.db import transaction
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.mcpclient.caching import (
    invalidate_all_cached_mcpclients_for_user_profile,
    invalidate_cached_catalog,
)
from smarter.apps.mcpclient.manifest.enum import (
    SAMMCPClientAuthType,
    SAMMCPClientTransport,
)
from smarter.apps.mcpclient.manifest.models.mcpclient.const import MANIFEST_KIND
from smarter.apps.mcpclient.manifest.models.mcpclient.metadata import (
    SAMMCPClientMetadata,
)
from smarter.apps.mcpclient.manifest.models.mcpclient.model import SAMMCPClient
from smarter.apps.mcpclient.manifest.models.mcpclient.spec import (
    SAMMCPClientSpec,
    SAMMCPClientSpecConfig,
)
from smarter.apps.mcpclient.manifest.models.mcpclient.status import SAMMCPClientStatus
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.mcpclient.serializers import MCPClientSerializer
from smarter.apps.plugin.signals import broker_ready
from smarter.apps.secret.models import Secret
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
    __name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000

CONFIG_FIELDS = {
    # manifest spec.config field: Django ORM MCPClient field
    "transport": "transport",
    "endpointUrl": "endpoint_url",
    "headers": "headers",
    "timeout": "timeout",
    "authType": "auth_type",
    "apiKeyHeader": "api_key_header",
    "allowedTools": "allowed_tools",
    "allowedResources": "allowed_resources",
    "includeInstructions": "include_instructions",
    "cacheTtl": "cache_ttl",
    "isActive": "is_active",
    "priority": "priority",
}
"""The spec.config fields, other than credentials, and their Django ORM fields."""


class SAMMCPClientBrokerError(SAMBrokerError):
    """Base exception for Smarter API MCPClient Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API MCPClient Manifest Broker Error"


class SAMMCPClientBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` MCPClient manifests.

    The broker converts between MCPClient manifests and the
    :class:`~smarter.apps.mcpclient.models.MCPClient` Django ORM model, and implements the
    ``smarter`` CLI commands for MCPClients: ``apply``, ``describe``, ``get``, ``delete``
    and ``example_manifest``. MCPClients are not deployed, so ``deploy`` and ``undeploy``
    are not implemented.

    ``spec.config.credentials`` is the name of a Smarter Secret, which must belong to, or
    be shared with, the manifest's owner. It is stored as a foreign key, and rendered as
    the Secret's name, never its value.
    """

    _manifest: Optional[SAMMCPClient] = None
    _pydantic_model: Type[SAMMCPClient] = SAMMCPClient
    _mcpclient: Optional[MCPClient] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        logger.info(msg)

    @property
    def SerializerClass(self) -> Type[ModelSerializer]:
        """The Django ORM model serializer class for the MCPClient."""
        return MCPClientSerializer

    @property
    def ready(self) -> bool:
        """
        Check if the broker is ready for operations.

        A broker is ready if it has a manifest, or an account.

        :returns: ``True`` if the broker is ready, ``False`` otherwise.
        :rtype: bool
        """
        if self._ready:
            return self._ready
        if not super().ready:
            logger.debug("%s.ready() AbstractBroker is not ready for %s", self.formatted_class_name, self.kind)
            return False
        if self.manifest is not None or self.account is not None:
            self._ready = True
            broker_ready.send(sender=self.__class__, broker=self)
        return self._ready

    @property
    def mcpclient(self) -> Optional[MCPClient]:
        """
        The user's MCPClient with the broker's name, if it exists.

        Unlike the scaffolded version of this property, it never creates an MCPClient.
        :meth:`apply` does that.

        :returns: The MCPClient, or ``None``.
        :rtype: Optional[MCPClient]
        """
        if self._mcpclient:
            return self._mcpclient
        if not self.user_profile or not self.name:
            return None
        self._mcpclient = (
            MCPClient.objects.select_related("credentials", "user_profile__user", "user_profile__account")
            .filter(user_profile=self.user_profile, name=self.name)
            .first()
        )
        return self._mcpclient

    def resolve_secret(self, name: Optional[str]) -> Optional[Secret]:
        """
        Return the Secret named ``name`` that the broker's user may read.

        The user's own Secret takes precedence over one that is shared with them.

        :param name: The name of the Secret, or ``None``.
        :returns: The Secret, or ``None`` if ``name`` is ``None``.
        :raises SAMBrokerErrorNotFound: If the user has no Secret by that name.
        """
        if not name:
            return None
        if not self.user_profile:
            raise SAMBrokerErrorNotReady("user_profile is not set.", thing=self.kind)
        secret = Secret.objects.filter(name=name, user_profile=self.user_profile).first()
        if secret is None:
            secret = (
                Secret.objects.filter(name=name)
                .with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
                .order_by("-updated_at")
                .first()
            )
        if secret is None:
            raise SAMBrokerErrorNotFound(
                f"Secret {name} not found, or not shared with {self.user_profile}.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        return secret

    def manifest_to_django_orm(self) -> dict[str, Any]:
        """
        Convert the manifest into a dict of Django ORM MCPClient fields.

        The ``credentials`` Secret name is resolved to the Secret. The fields are mapped
        explicitly, rather than by converting camelCase to snake_case, so that the keys of
        ``headers`` are preserved.

        :returns: A dict of MCPClient fields, including the metadata fields.
        :rtype: dict
        :raises SAMBrokerErrorNotReady: If the manifest is not loaded.
        :raises SAMBrokerErrorNotFound: If the credentials Secret is not found.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"Manifest not loaded for {self.kind} broker. Cannot convert to Django ORM.", thing=self.kind
            )
        metadata = super().manifest_to_django_orm()
        config = self.manifest.spec.config
        retval = {**metadata}
        for manifest_field, orm_field in CONFIG_FIELDS.items():
            retval[orm_field] = getattr(config, manifest_field)
        retval["credentials"] = self.resolve_secret(config.credentials)
        return retval

    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """
        Convert the MCPClient into a manifest dict.

        ``credentials`` is rendered as the Secret's name, never its value. The status
        reports the result of the last connection to the MCP server.

        :returns: The manifest, as a dict, or ``None`` if the MCPClient does not exist.
        :rtype: Optional[dict]
        """
        if not self.account or not self.user_profile:
            raise SAMBrokerErrorNotReady(
                f"Account and user profile are required to describe a {self.kind}.",
                thing=self.kind,
            )
        mcpclient = self.mcpclient
        if not mcpclient:
            return None
        config_data = {
            manifest_field: getattr(mcpclient, orm_field) for manifest_field, orm_field in CONFIG_FIELDS.items()
        }
        config_data["transport"] = config_data["transport"] or SAMMCPClientTransport.HTTP.value
        config_data["headers"] = config_data["headers"] or {}
        config_data["allowedTools"] = config_data["allowedTools"] or []
        config_data["allowedResources"] = config_data["allowedResources"] or []
        config_data["authType"] = config_data["authType"] or SAMMCPClientAuthType.NONE.value
        config_data["credentials"] = mcpclient.credential_name
        meta = SAMMCPClientMetadata(
            name=mcpclient.name,
            description=mcpclient.description,
            version=mcpclient.version,
            tags=mcpclient.tags_list,
            annotations=mcpclient.annotations if isinstance(mcpclient.annotations, list) else [],
        )
        spec = SAMMCPClientSpec(config=SAMMCPClientSpecConfig(**config_data))
        status = SAMMCPClientStatus(
            accountNumber=self.account.account_number,
            username=self.user_profile.user.username,
            recordLocator=mcpclient.record_locator,
            created=mcpclient.created_at,
            modified=mcpclient.updated_at,
            connectionStatus=mcpclient.status,
            protocolVersion=mcpclient.protocol_version,
            serverName=mcpclient.server_name,
            serverVersion=mcpclient.server_version,
            lastConnected=mcpclient.last_connected_at,
            lastError=mcpclient.last_error,
            tools=mcpclient.tools or [],
        )
        model = SAMMCPClient(apiVersion=self.api_version, kind=self.kind, metadata=meta, spec=spec, status=status)
        return model.model_dump()

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        class_name = f"{SAMMCPClientBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def kind(self) -> str:
        """The manifest kind: MCPClient."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMMCPClient]:
        """
        The MCPClient manifest, as a Pydantic model, from the manifest loader.

        :returns: The manifest, or ``None`` if the broker has no loader for an MCPClient manifest.
        :rtype: Optional[SAMMCPClient]
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMMCPClient):
                raise SAMMCPClientBrokerError("Cached manifest is not a SAMMCPClient instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMMCPClient(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMMCPClientMetadata(**self.loader.manifest_metadata),
                spec=SAMMCPClientSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def cache_invalidations(self) -> None:
        """Invalidate the cached MCPClient, the user's cached MCPClient lists, and the MCPClient's catalog."""
        if self.mcpclient:
            MCPClient.get_cached_object(pk=self.mcpclient.id, invalidate=True)  # type: ignore[attr-defined]
            invalidate_cached_catalog(self.mcpclient)
        if self.user_profile:
            MCPClient.get_cached_objects(user_profile=self.user_profile, invalidate=True)
            invalidate_all_cached_mcpclients_for_user_profile(self.user_profile)
        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[MCPClient]:
        """The Django ORM meta model class: MCPClient."""
        return MCPClient

    @property
    def ORMModelClass(self) -> Type[MCPClient]:
        """The Django ORM model class: MCPClient."""
        return MCPClient

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return an example MCPClient manifest."""
        command = SmarterJournalCliCommands(self.example_manifest.__name__)
        meta_data = SAMMCPClientMetadata(
            name="example_mcpclient",
            description="An example MCPClient, for GitHub's MCP server. It offers the LLM the server's read-only tools.",
            version="1.0.0",
            tags=["example", "github"],
            annotations=[{"smarter.sh/mcpclient/documentation": "https://github.com/github/github-mcp-server"}],
        )
        config = SAMMCPClientSpecConfig(
            transport=SAMMCPClientTransport.HTTP.value,
            endpointUrl="https://api.githubcopilot.com/mcp/",
            headers={"X-MCP-Toolsets": "repos,issues,pull_requests"},
            timeout=30,
            authType=SAMMCPClientAuthType.BEARER_TOKEN.value,
            credentials="github_personal_access_token",
            allowedTools=["get_*", "list_*", "search_*"],
            allowedResources=[],
            includeInstructions=True,
            cacheTtl=300,
            isActive=True,
            priority=100,
        )
        status = SAMMCPClientStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        model = SAMMCPClient(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta_data,
            spec=SAMMCPClientSpec(config=config),
            status=status,
        )
        return self.json_response_ok(command=command, data=model.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the MCPClients that the user may read, optionally filtered by name."""
        command = SmarterJournalCliCommands(self.get.__name__)
        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value, None)
        name = self.clean_cli_param(param=name, param_name="name", url=self.smarter_build_absolute_uri(request))

        if self.user_profile is None:
            raise SAMBrokerErrorNotReady("user_profile is not set.")

        mcpclients = MCPClient.objects.with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
        if name:
            mcpclients = mcpclients.filter(name=name)
        mcpclients = mcpclients.order_by("name")[:MAX_RESULTS]

        for mcpclient in mcpclients:
            try:
                data.append(self.to_camel_case(MCPClientSerializer(mcpclient).data))
            except Exception as e:
                raise SAMMCPClientBrokerError(
                    f"Failed to serialize {self.kind} {mcpclient.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=MCPClientSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Create or update the MCPClient from the manifest.

        Saving the MCPClient queues :func:`~smarter.apps.mcpclient.tasks.refresh_mcpclient`,
        which connects to the MCP server and records the result in the MCPClient's status.

        .. note::

            tags are handled separately because they are of type TaggableManager and
            require a different method to set them.
        """
        command = SmarterJournalCliCommands(self.apply.__name__)
        if not self.ready:
            raise SAMBrokerErrorNotReady(
                f"{self.kind} {self.name} broker is not ready", thing=self.kind, command=command
            )
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

        data = self.manifest_to_django_orm()
        tags = data.pop("tags", None) or []
        for field in ("id", "created_at", "updated_at"):
            data.pop(field, None)
        with transaction.atomic():
            mcpclient = self.mcpclient
            if mcpclient is None:
                mcpclient = MCPClient(**data)
            else:
                if mcpclient.user_profile != self.user_profile:
                    raise SAMMCPClientBrokerError(
                        f"User profile mismatch for {self.kind} {self.manifest.metadata.name}",
                        thing=self.kind,
                        command=command,
                    )
                for key, value in data.items():
                    setattr(mcpclient, key, value)
            try:
                mcpclient.save()
                mcpclient.tags.set(tags)
            except Exception as e:
                logger.error(
                    "%s.apply() failed to save %s %s: %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                    e,
                    exc_info=True,
                )
                raise SAMMCPClientBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}: {e}", thing=self.kind, command=command
                ) from e
        self._mcpclient = mcpclient
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.to_json())

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.prompt.__name__)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the MCPClient as a manifest, with its status."""
        command = SmarterJournalCliCommands(self.describe.__name__)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} name property is not set.", thing=self.kind, command=command)
        if not self.mcpclient:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        try:
            data = self.django_orm_to_manifest_dict()
        except Exception as e:
            raise SAMMCPClientBrokerError(
                f"Failed to describe {self.kind} {self.name}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data=data)

    @memoized_dependencies
    def dependencies(self) -> List[AbstractBroker]:
        """Return brokers for the LLMClients that use this MCPClient.

        :return: A broker for each LLMClient that lists this MCPClient in its ``spec.mcpClients``.
        :rtype: List[AbstractBroker]
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.manifests.enum import SAMKinds
        from smarter.apps.llmclient.models import LLMClient, LLMClientMCPClients

        mcpclient = self.mcpclient
        if not mcpclient:
            return []
        llmclients = LLMClient.objects.filter(
            id__in=LLMClientMCPClients.objects.filter(mcpclient=mcpclient).values("llmclient_id")
        )
        return self.dependency_brokers(SAMKinds.LLM_CLIENT.value, llmclients)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Delete the MCPClient.

        Refused while LLMClients use it.
        """
        command = SmarterJournalCliCommands(self.delete.__name__)
        if self.name is None or not self.mcpclient:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        self.verify_no_dependencies(command)
        try:
            self.cache_invalidations()
            self.mcpclient.delete()
            self._mcpclient = None
        except Exception as e:
            raise SAMMCPClientBrokerError(
                f"Failed to delete {self.kind} {self.name}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data={})

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.deploy.__name__)
        raise SAMBrokerErrorNotImplemented(
            message=f"{self.kind} {self.name} deploy() is not implemented.", thing=self.kind, command=command
        )

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.undeploy.__name__)
        raise SAMBrokerErrorNotImplemented(
            message=f"{self.kind} {self.name} undeploy() is not implemented.", thing=self.kind, command=command
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.logs.__name__)
        return self.json_response_ok(command=command, data={})
