# pylint: disable=W0718,C0302,R0904
"""
Smarter API LLMHost Manifest handler.

The broker implements the ``smarter`` CLI commands for LLMHosts:

- ``apply``: create or update the LLMHost from its manifest. It does not launch it.
- ``deploy``: launch the LLMHost on Kubernetes.
- ``undeploy``: destroy its Kubernetes resources. The model volume is kept, unless
  ``storage.retain`` is false.
- ``describe``: the manifest, with the status of the last status check.
- ``get``: the user's LLMHosts.
- ``logs``: the inference server's recent logs.
- ``delete``: destroy its Kubernetes resources, including the model volume, then delete it.
"""

import datetime
from typing import Any, List, Optional, Type

from django.db import transaction
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmhost.caching import invalidate_all_cached_llmhosts_for_user_profile
from smarter.apps.llmhost.manifest.models.llmhost.const import MANIFEST_KIND
from smarter.apps.llmhost.manifest.models.llmhost.metadata import (
    SAMLLMHostMetadata,
)
from smarter.apps.llmhost.manifest.models.llmhost.model import SAMLLMHost
from smarter.apps.llmhost.manifest.models.llmhost.spec import (
    SAMLLMHostEngineConfig,
    SAMLLMHostModel,
    SAMLLMHostModelCapabilities,
    SAMLLMHostResources,
    SAMLLMHostSpec,
)
from smarter.apps.llmhost.manifest.models.llmhost.status import SAMLLMHostStatus
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute
from smarter.apps.llmhost.serializers import LLMHostSerializer
from smarter.apps.llmhost.services import LLMHostService, LLMHostServiceError
from smarter.apps.llmhost.services.compute import (
    cost_per_hour,
    pod_requests,
    resolve_compute,
)
from smarter.apps.llmhost.services.engines import get_engine
from smarter.apps.llmhost.services.exceptions import LLMHostComputeError
from smarter.apps.plugin.signals import broker_ready
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
    __name__, any_switches=[SmarterWaffleSwitches.LLM_HOST_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000


def spec_to_django_orm(spec: SAMLLMHostSpec, name: str, compute: Optional[LLMHostCompute] = None) -> dict[str, Any]:
    """
    The LLMHost fields of a spec: the spec itself, and copies of the parts that are queried.

    and reported on.

    :param compute: The LLMHost's compute, from
        :func:`~smarter.apps.llmhost.services.compute.resolve_compute`. Its name is stored in the
        spec, so that an LLMHost whose spec did not choose one keeps the one chosen for it.
    """
    model = spec.model
    engine = get_engine(spec.engine.name)
    if compute is not None:
        spec = spec.model_copy(update={"compute": compute.name})
    return {
        "spec": spec.model_dump(mode="json", exclude_none=True),
        "compute": compute,
        "model_source": model.source,
        "model_repository": model.repository,
        "model_revision": model.revision or "",
        "model_task": model.task,
        "served_model_name": engine.served_name(spec, name),
        "license": model.license or "",
        "model_architecture": model.architecture or "",
        "parameter_count": model.parameterCount,
        "context_window": model.contextWindow,
        "embedding_dimensions": model.embeddingDimensions,
        "quantization": model.quantization,
        "supports_streaming": model.capabilities.streaming,
        "supports_function_calling": model.capabilities.functionCalling,
        "supports_vision": model.capabilities.vision,
        "supports_reasoning": model.capabilities.reasoning,
        "inference_engine": spec.engine.name,
        "api_format": spec.engine.apiFormat,
        "gpu_type": compute.gpu_type if compute is not None and spec.resources.gpuCount else "",
        "gpu_count": spec.resources.gpuCount,
        "vram_required_gb": spec.resources.vramRequiredGb,
        "replicas": spec.scaling.replicas,
        "cost_per_hour": cost_per_hour(pod_requests(spec), compute),
    }


class SAMLLMHostBrokerError(SAMBrokerError):
    """Base exception for Smarter API LLMHost Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API LLMHost Manifest Broker Error"


class SAMLLMHostBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` LLMHost manifests.

    It converts between LLMHost manifests and the :class:`~smarter.apps.llmhost.models.LLMHost`
    Django ORM model, and delegates the LLMHost's lifecycle to
    :class:`~smarter.apps.llmhost.services.LLMHostService`.
    """

    _manifest: Optional[SAMLLMHost] = None
    _pydantic_model: Type[SAMLLMHost] = SAMLLMHost
    _llmhost: Optional[LLMHost] = None
    _service: Optional[LLMHostService] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        logger.info(
            "%s.__init__() broker for %s %s is %s.", self.formatted_class_name, self.kind, self.name, self.ready_state
        )

    @property
    def SerializerClass(self) -> Type[ModelSerializer]:
        """The Django ORM model serializer class for the LLMHost."""
        return LLMHostSerializer

    @property
    def service(self) -> LLMHostService:
        """The LLMHost service."""
        if self._service is None:
            self._service = LLMHostService()
        return self._service

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
    def llmhost(self) -> Optional[LLMHost]:
        """The user's LLMHost with the broker's name, if it exists.

        It is never created here: :meth:`apply` does that.
        """
        if self._llmhost:
            return self._llmhost
        if not self.user_profile or not self.name:
            return None
        self._llmhost = LLMHost.objects.filter(user_profile=self.user_profile, name=self.name).first()
        return self._llmhost

    def manifest_to_django_orm(self) -> dict[str, Any]:
        """Convert the manifest into a dict of Django ORM LLMHost fields."""
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"Manifest not loaded for {self.kind} broker.", thing=self.kind)
        try:
            if self.user_profile is None:
                raise LLMHostComputeError("a user is required to choose a compute.")
            compute = resolve_compute(self.manifest.spec, self.user_profile)
        except LLMHostComputeError as e:
            raise SAMLLMHostBrokerError(f"{self.kind} {self.manifest.metadata.name}: {e}", thing=self.kind) from e
        return {
            **super().manifest_to_django_orm(),
            **spec_to_django_orm(self.manifest.spec, self.manifest.metadata.name, compute),
        }

    def status_for(self, llmhost: LLMHost) -> dict[str, Any]:
        """The LLMHost's state, as of its last status check."""
        return {
            "hostStatus": llmhost.status,
            "message": llmhost.status_message or None,
            "replicas": llmhost.replicas,
            "readyReplicas": llmhost.ready_replicas,
            "healthy": llmhost.last_health_ok,
            "endpoint": llmhost.endpoint_url or None,
            "publicUrl": llmhost.public_url or None,
            "apiKeySecret": llmhost.api_key_secret.name if llmhost.api_key_secret else None,
            "deployedAt": llmhost.deployed_at,
            "lastCheckedAt": llmhost.last_health_check_at,
            "uptimeHours": llmhost.uptime_hours,
            "estimatedCost": llmhost.estimated_cost,
        }

    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """Convert the LLMHost into a manifest dict, with its status."""
        if not self.account or not self.user_profile:
            raise SAMBrokerErrorNotReady(
                f"Account and user profile are required to describe a {self.kind}.", thing=self.kind
            )
        llmhost = self.llmhost
        if not llmhost:
            return None
        meta = SAMLLMHostMetadata(
            name=llmhost.name,
            description=llmhost.description,
            version=llmhost.version,
            tags=llmhost.tags_list,
            annotations=llmhost.annotations if isinstance(llmhost.annotations, list) else [],
        )
        status = SAMLLMHostStatus(
            accountNumber=self.account.account_number,
            username=self.user_profile.user.username,
            recordLocator=llmhost.record_locator,
            created=llmhost.created_at,
            modified=llmhost.updated_at,
            **self.status_for(llmhost),
        )
        model = SAMLLMHost(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta,
            spec=self.service.spec_of(llmhost),
            status=status,
        )
        return model.model_dump(mode="json", exclude_none=True)

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return self.formatted_text(f"{SAMLLMHostBroker.__name__}[{id(self)}]")

    @property
    def kind(self) -> str:
        """The manifest kind: LLMHost."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMLLMHost]:
        """The LLMHost manifest, as a Pydantic model, from the manifest loader."""
        if self._manifest:
            if not isinstance(self._manifest, SAMLLMHost):
                raise SAMLLMHostBrokerError("Cached manifest is not a SAMLLMHost instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMLLMHost(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMLLMHostMetadata(**self.loader.manifest_metadata),
                spec=SAMLLMHostSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def cache_invalidations(self) -> None:
        """Invalidate the cached LLMHost, and the user's cached LLMHost lists."""
        if self.llmhost:
            LLMHost.get_cached_object(pk=self.llmhost.pk, invalidate=True)
        if self.user_profile:
            LLMHost.get_cached_objects(user_profile=self.user_profile, invalidate=True)
            invalidate_all_cached_llmhosts_for_user_profile(self.user_profile)
        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[LLMHost]:
        return LLMHost

    @property
    def ORMModelClass(self) -> Type[LLMHost]:
        return LLMHost

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return an example LLMHost manifest: Llama 3.1 8B Instruct, served by vLLM on one A10G GPU."""
        command = SmarterJournalCliCommands(self.example_manifest.__name__)
        meta_data = SAMLLMHostMetadata(
            name="example_llmhost",
            description="Meta Llama 3.1 8B Instruct, served by vLLM on one NVIDIA A10G GPU, with tool calling.",
            version="1.0.0",
            tags=["example", "llama", "vllm"],
            annotations=[{"smarter.sh/llmhost/purpose": "example"}],
        )
        spec = SAMLLMHostSpec(
            model=SAMLLMHostModel(
                source="huggingface",
                repository="meta-llama/Llama-3.1-8B-Instruct",
                revision="main",
                servedName="llama-3.1-8b-instruct",
                tokenSecret="huggingface_token",
                license="llama3.1",
                architecture="llama",
                parameterCount=8_030_261_248,
                contextWindow=131072,
                quantization="bf16",
                capabilities=SAMLLMHostModelCapabilities(functionCalling=True),
            ),
            compute="gpu_a10g_1x",
            engine=SAMLLMHostEngineConfig(
                name="vllm",
                contextLength=16384,
                gpuMemoryUtilization=0.9,
                args=["--enable-auto-tool-choice", "--tool-call-parser", "llama3_json"],
            ),
            resources=SAMLLMHostResources(gpuCount=1, vramRequiredGb=21, cpu="4", memory="24Gi"),
        )
        status = SAMLLMHostStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        model = SAMLLMHost(apiVersion=self.api_version, kind=self.kind, metadata=meta_data, spec=spec, status=status)
        return self.json_response_ok(command=command, data=model.model_dump(mode="json", exclude_none=True))

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the LLMHosts that the user may read, optionally filtered by name."""
        command = SmarterJournalCliCommands(self.get.__name__)
        name = self.clean_cli_param(
            param=kwargs.get(SAMMetadataKeys.NAME.value, None),
            param_name="name",
            url=self.smarter_build_absolute_uri(request),
        )
        if self.user_profile is None:
            raise SAMBrokerErrorNotReady("user_profile is not set.")
        llmhosts = LLMHost.objects.with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
        if name:
            llmhosts = llmhosts.filter(name=name)
        data = [
            self.to_camel_case(LLMHostSerializer(llmhost).data) for llmhost in llmhosts.order_by("name")[:MAX_RESULTS]
        ]
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=LLMHostSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Create or update the LLMHost from the manifest.

        Applying does not launch, nor relaunch, the LLMHost: ``deploy`` does.

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
            llmhost = self.llmhost
            if llmhost is None:
                llmhost = LLMHost(**data)
            else:
                for key, value in data.items():
                    setattr(llmhost, key, value)
            try:
                llmhost.save()
                llmhost.tags.set(tags)
            except Exception as e:
                raise SAMLLMHostBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}: {e}", thing=self.kind, command=command
                ) from e
        self._llmhost = llmhost
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.to_json())

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.prompt.__name__)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the LLMHost as a manifest, with the status of its last status check."""
        command = SmarterJournalCliCommands(self.describe.__name__)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} name property is not set.", thing=self.kind, command=command)
        if not self.llmhost:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        try:
            data = self.django_orm_to_manifest_dict()
        except Exception as e:
            raise SAMLLMHostBrokerError(
                f"Failed to describe {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data=data)

    @memoized_dependencies
    def dependencies(self) -> List[AbstractBroker]:
        """Return brokers for the resources that depend on this LLMHost.

        No other resource refers to an LLMHost.

        :return: An empty list.
        :rtype: List[AbstractBroker]
        """
        return []

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Destroy the LLMHost's Kubernetes resources, including its model volume, then delete it."""
        command = SmarterJournalCliCommands(self.delete.__name__)
        llmhost = self.llmhost
        if self.name is None or not llmhost:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        self.verify_no_dependencies(command)
        # pylint: disable=import-outside-toplevel
        from smarter.apps.llmhost.tasks import destroy_dns_record

        try:
            self.cache_invalidations()
            destroy_dns_record(llmhost)
            self.service.delete(llmhost)
            self._llmhost = None
        except Exception as e:
            raise SAMLLMHostBrokerError(
                f"Failed to delete {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data={})

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Launch the LLMHost on Kubernetes.

        It returns when the cluster accepts the resources. Use ``describe`` to follow the status,
        which Celery Beat refreshes every few minutes.
        """
        command = SmarterJournalCliCommands(self.deploy.__name__)
        llmhost = self.llmhost
        if self.name is None or not llmhost:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        # pylint: disable=import-outside-toplevel
        from smarter.apps.llmhost.tasks import create_dns_record

        try:
            observation = self.service.launch(llmhost)
        except LLMHostServiceError as e:
            raise SAMLLMHostBrokerError(
                f"Failed to deploy {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        create_dns_record(llmhost)
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=observation.to_dict())

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Destroy the LLMHost's Kubernetes resources.

        Its model volume is kept, unless storage.retain is false.
        """
        command = SmarterJournalCliCommands(self.undeploy.__name__)
        llmhost = self.llmhost
        if self.name is None or not llmhost:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        # pylint: disable=import-outside-toplevel
        from smarter.apps.llmhost.tasks import destroy_dns_record

        try:
            self.service.destroy(llmhost)
        except LLMHostServiceError as e:
            raise SAMLLMHostBrokerError(
                f"Failed to undeploy {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        destroy_dns_record(llmhost)
        self.cache_invalidations()
        return self.json_response_ok(
            command=command, data={"status": llmhost.status, "message": llmhost.status_message}
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the most recent log lines of the LLMHost's inference server."""
        command = SmarterJournalCliCommands(self.logs.__name__)
        llmhost = self.llmhost
        if self.name is None or not llmhost:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        try:
            logs = self.service.logs(llmhost)
        except LLMHostServiceError as e:
            raise SAMLLMHostBrokerError(
                f"Failed to get the logs of {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data={"logs": logs})


__all__ = ["SAMLLMHostBroker", "SAMLLMHostBrokerError", "spec_to_django_orm"]
