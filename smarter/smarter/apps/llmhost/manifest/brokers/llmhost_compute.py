# pylint: disable=W0718,R0904
"""
Smarter API LLMHostCompute Manifest handler.

The broker implements the ``smarter`` CLI commands for LLMHostComputes:

- ``apply``: create or update the LLMHostCompute from its manifest. It does not create the
  node group: an LLMHost's launch does, when it first needs one of its nodes. While the node group
  exists, only ``nodeGroup.maxNodes`` and ``cost`` can change, because a node group's nodes
  cannot be changed in place.
- ``deploy``: reconcile the node group with its LLMHosts: create it, if they need nodes, add the
  nodes that they need, and remove those that they do not.
- ``describe``: the manifest, with the node group's status as of its last reconcile.
- ``get``: the LLMHostComputes that the user may read, including the built-in ones.
- ``delete``: delete the LLMHostCompute and its node group. Refused while LLMHosts use it.
"""

import datetime
from typing import Any, List, Optional, Type

from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmhost.manifest.models.llmhost_compute.const import MANIFEST_KIND
from smarter.apps.llmhost.manifest.models.llmhost_compute.metadata import (
    SAMLLMHostComputeMetadata,
)
from smarter.apps.llmhost.manifest.models.llmhost_compute.model import (
    SAMLLMHostCompute,
)
from smarter.apps.llmhost.manifest.models.llmhost_compute.spec import (
    SAMLLMHostComputeCost,
    SAMLLMHostComputeGpu,
    SAMLLMHostComputeNode,
    SAMLLMHostComputeNodeGroup,
    SAMLLMHostComputeSpec,
)
from smarter.apps.llmhost.manifest.models.llmhost_compute.status import (
    SAMLLMHostComputeStatus,
)
from smarter.apps.llmhost.models import LLMHostCompute
from smarter.apps.llmhost.models.compute import LLMHostComputeNodeGroupStatus
from smarter.apps.llmhost.serializers import LLMHostComputeSerializer
from smarter.apps.llmhost.services.compute import ComputeProvisioner
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


def compute_spec_to_django_orm(spec: SAMLLMHostComputeSpec) -> dict[str, Any]:
    """The LLMHostCompute fields of a spec: the spec itself, and copies of the parts that sizing and node groups use."""
    node = spec.node
    gpu = node.gpu
    return {
        "spec": spec.model_dump(mode="json", exclude_none=True),
        "instance_type": node.instanceType,
        "cpu": node.cpu,
        "memory_gb": node.memoryGb,
        "gpu_type": gpu.type if gpu else "",
        "gpu_count": gpu.count if gpu else 0,
        "gpu_memory_gb": gpu.memoryGb if gpu else 0,
        "max_nodes": spec.nodeGroup.maxNodes,
        "price_per_hour": spec.cost.perHour,
    }


def immutable_changes(compute: LLMHostCompute, spec: SAMLLMHostComputeSpec) -> list[str]:
    """The parts of the spec that changed, and that an existing node group cannot change: its nodes, and subnets."""
    old = compute.spec or {}
    new = spec.model_dump(mode="json", exclude_none=True)
    changes = []
    if old.get("node") != new.get("node"):
        changes.append("node")
    if (old.get("nodeGroup", {}) or {}).get("subnetIds", []) != new["nodeGroup"].get("subnetIds", []):
        changes.append("nodeGroup.subnetIds")
    return changes


class SAMLLMHostComputeBrokerError(SAMBrokerError):
    """Base exception for Smarter API LLMHostCompute Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API LLMHostCompute Manifest Broker Error"


class SAMLLMHostComputeBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` LLMHostCompute manifests.

    It converts between LLMHostCompute manifests and the
    :class:`~smarter.apps.llmhost.models.LLMHostCompute` Django ORM model, and delegates the node
    group to :class:`~smarter.apps.llmhost.services.compute.ComputeProvisioner`.
    """

    _manifest: Optional[SAMLLMHostCompute] = None
    _pydantic_model: Type[SAMLLMHostCompute] = SAMLLMHostCompute
    _compute: Optional[LLMHostCompute] = None
    _provisioner: Optional[ComputeProvisioner] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        logger.info(
            "%s.__init__() broker for %s %s is %s.", self.formatted_class_name, self.kind, self.name, self.ready_state
        )

    @property
    def SerializerClass(self) -> Type[ModelSerializer]:
        """The Django ORM model serializer class for the LLMHostCompute."""
        return LLMHostComputeSerializer

    @property
    def provisioner(self) -> ComputeProvisioner:
        if self._provisioner is None:
            self._provisioner = ComputeProvisioner()
        return self._provisioner

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
    def compute(self) -> Optional[LLMHostCompute]:
        """The user's LLMHostCompute with the broker's name, if it exists.

        It is never created here: :meth:`apply` does that.
        """
        if self._compute:
            return self._compute
        if not self.user_profile or not self.name:
            return None
        self._compute = LLMHostCompute.objects.filter(user_profile=self.user_profile, name=self.name).first()
        return self._compute

    def manifest_to_django_orm(self) -> dict[str, Any]:
        """Convert the manifest into a dict of Django ORM LLMHostCompute fields."""
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"Manifest not loaded for {self.kind} broker.", thing=self.kind)
        return {**super().manifest_to_django_orm(), **compute_spec_to_django_orm(self.manifest.spec)}

    @staticmethod
    def status_for(compute: LLMHostCompute) -> dict[str, Any]:
        """The node group's state, as of its last reconcile."""
        return {
            "nodeGroupName": compute.nodegroup_name,
            "nodeGroupStatus": compute.nodegroup_status,
            "desiredNodes": compute.desired_nodes,
            "readyNodes": compute.ready_nodes,
            "llmhosts": compute.llmhosts.count(),  # type: ignore[attr-defined]
            "message": compute.status_message or None,
            "lastReconciledAt": compute.last_reconciled_at,
        }

    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """Convert the LLMHostCompute into a manifest dict, with its status."""
        if not self.account or not self.user_profile:
            raise SAMBrokerErrorNotReady(
                f"Account and user profile are required to describe a {self.kind}.", thing=self.kind
            )
        compute = self.compute
        if not compute:
            return None
        meta = SAMLLMHostComputeMetadata(
            name=compute.name,
            description=compute.description,
            version=compute.version,
            tags=compute.tags_list,
            annotations=compute.annotations if isinstance(compute.annotations, list) else [],
        )
        status = SAMLLMHostComputeStatus(
            accountNumber=self.account.account_number,
            username=self.user_profile.user.username,
            recordLocator=compute.record_locator,
            created=compute.created_at,
            modified=compute.updated_at,
            **self.status_for(compute),
        )
        model = SAMLLMHostCompute(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta,
            spec=SAMLLMHostComputeSpec(**(compute.spec or {})),
            status=status,
        )
        return model.model_dump(mode="json", exclude_none=True)

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return self.formatted_text(f"{SAMLLMHostComputeBroker.__name__}[{id(self)}]")

    @property
    def kind(self) -> str:
        """The manifest kind: LLMHostCompute."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMLLMHostCompute]:
        """The LLMHostCompute manifest, as a Pydantic model, from the manifest loader."""
        if self._manifest:
            if not isinstance(self._manifest, SAMLLMHostCompute):
                raise SAMLLMHostComputeBrokerError(
                    "Cached manifest is not a SAMLLMHostCompute instance", thing=self.kind
                )
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMLLMHostCompute(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMLLMHostComputeMetadata(**self.loader.manifest_metadata),
                spec=SAMLLMHostComputeSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def cache_invalidations(self) -> None:
        """Invalidate the cached LLMHostCompute, and the user's cached LLMHostCompute lists."""
        if self.compute:
            LLMHostCompute.get_cached_object(pk=self.compute.pk, invalidate=True)
        if self.user_profile:
            LLMHostCompute.get_cached_objects(user_profile=self.user_profile, invalidate=True)
        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[LLMHostCompute]:
        return LLMHostCompute

    @property
    def ORMModelClass(self) -> Type[LLMHostCompute]:
        return LLMHostCompute

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return an example LLMHostCompute manifest: g6.2xlarge nodes with one NVIDIA L4."""
        command = SmarterJournalCliCommands(self.example_manifest.__name__)
        meta_data = SAMLLMHostComputeMetadata(
            name="example_gpu_l4_1x",
            description="One NVIDIA L4 with 24 GB, 8 vCPUs and 32 GiB.",
            version="1.0.0",
            tags=["example", "gpu", "l4"],
            annotations=[{"smarter.sh/llmhostcompute/purpose": "example"}],
        )
        spec = SAMLLMHostComputeSpec(
            node=SAMLLMHostComputeNode(
                instanceType="g6.2xlarge",
                cpu=8,
                memoryGb=32,
                gpu=SAMLLMHostComputeGpu(type="L4", count=1, memoryGb=24),
                diskSizeGb=100,
            ),
            nodeGroup=SAMLLMHostComputeNodeGroup(maxNodes=4),
            cost=SAMLLMHostComputeCost(perHour="0.9776"),  # type: ignore[arg-type]
        )
        status = SAMLLMHostComputeStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        model = SAMLLMHostCompute(
            apiVersion=self.api_version, kind=self.kind, metadata=meta_data, spec=spec, status=status
        )
        return self.json_response_ok(command=command, data=model.model_dump(mode="json", exclude_none=True))

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the LLMHostComputes that the user may read, optionally filtered by name."""
        command = SmarterJournalCliCommands(self.get.__name__)
        name = self.clean_cli_param(
            param=kwargs.get(SAMMetadataKeys.NAME.value, None),
            param_name="name",
            url=self.smarter_build_absolute_uri(request),
        )
        if self.user_profile is None:
            raise SAMBrokerErrorNotReady("user_profile is not set.")
        computes = LLMHostCompute.objects.with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
        if name:
            computes = computes.filter(name=name)
        data = [
            self.to_camel_case(LLMHostComputeSerializer(compute).data)
            for compute in computes.order_by("name")[:MAX_RESULTS]
        ]
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=LLMHostComputeSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Create or update the LLMHostCompute from the manifest.

        It does not create the node group.

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
            compute = self.compute
            if compute is None:
                compute = LLMHostCompute(**data)
            else:
                changes = immutable_changes(compute, self.manifest.spec)
                if changes and compute.nodegroup_status != LLMHostComputeNodeGroupStatus.ABSENT:
                    raise SAMLLMHostComputeBrokerError(
                        f"Failed to apply {self.kind} {self.name}: its node group {compute.nodegroup_name} exists, "
                        f"so {', '.join(changes)} cannot change. Apply a new {self.kind} instead.",
                        thing=self.kind,
                        command=command,
                    )
                for key, value in data.items():
                    setattr(compute, key, value)
            try:
                compute.save()
                compute.tags.set(tags)
            except Exception as e:
                raise SAMLLMHostComputeBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}: {e}", thing=self.kind, command=command
                ) from e
        self._compute = compute
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.to_json())

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.prompt.__name__)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return the LLMHostCompute as a manifest, with the node group's status as of its last reconcile."""
        command = SmarterJournalCliCommands(self.describe.__name__)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} name property is not set.", thing=self.kind, command=command)
        if not self.compute:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        try:
            data = self.django_orm_to_manifest_dict()
        except Exception as e:
            raise SAMLLMHostComputeBrokerError(
                f"Failed to describe {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data=data)

    @memoized_dependencies
    def dependencies(self) -> List[AbstractBroker]:
        """Return brokers for the LLMHosts that run on this LLMHostCompute.

        :return: A broker for each LLMHost whose ``spec.compute`` is this LLMHostCompute.
        :rtype: List[AbstractBroker]
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.manifests.enum import SAMKinds

        compute = self.compute
        if not compute:
            return []
        return self.dependency_brokers(SAMKinds.LLM_HOST.value, compute.llmhosts.all())  # type: ignore[attr-defined]

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Delete the LLMHostCompute, and its node group.

        Refused while LLMHosts use it.
        """
        command = SmarterJournalCliCommands(self.delete.__name__)
        compute = self.compute
        if self.name is None or not compute:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        self.verify_no_dependencies(command)
        try:
            self.cache_invalidations()
            # the pre_delete receiver deletes the node group.
            compute.delete()
            self._compute = None
        except (ProtectedError, Exception) as e:
            raise SAMLLMHostComputeBrokerError(
                f"Failed to delete {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data={})

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Reconcile the node group with its LLMHosts: create it, and add or remove nodes, as they need."""
        command = SmarterJournalCliCommands(self.deploy.__name__)
        compute = self.compute
        if self.name is None or not compute:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        try:
            state = self.provisioner.reconcile(compute)
        except LLMHostComputeError as e:
            raise SAMLLMHostComputeBrokerError(
                f"Failed to reconcile {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=state.__dict__)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.undeploy.__name__)
        raise SAMBrokerErrorNotImplemented(
            message=f"Undeploy not implemented: undeploy the {self.kind}'s LLMHosts, and its idle nodes are removed.",
            thing=self.kind,
            command=command,
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.logs.__name__)
        raise SAMBrokerErrorNotImplemented(message="Logs not implemented", thing=self.kind, command=command)


__all__ = [
    "SAMLLMHostComputeBroker",
    "SAMLLMHostComputeBrokerError",
    "compute_spec_to_django_orm",
    "immutable_changes",
]
