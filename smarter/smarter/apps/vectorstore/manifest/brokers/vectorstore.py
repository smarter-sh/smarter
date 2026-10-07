# pylint: disable=W0718,R0904
"""
Smarter API Vectorstore Manifest handler.

The broker converts between Vectorstore manifests and the
:class:`~smarter.apps.vectorstore.models.VectorstoreMeta` model, and implements the ``smarter``
CLI commands for Vectorstores:

- ``apply``: create or update the Vectorstore. It does not create the database.
- ``deploy``: create the database: a self-hosted Qdrant server, or a managed index.
- ``undeploy``: stop serving. A self-hosted server's data is kept.
- ``delete``: destroy the database and all of its data, unless deletionProtection is enabled,
  then delete the Vectorstore.
- ``describe``, ``get``, ``logs`` and ``example_manifest``.

Account admins, i.e. staff, may apply, deploy, undeploy and delete their own Vectorstores.
Anyone may describe and get the Vectorstores that are shared with them.
"""

import datetime
from typing import Any, List, Optional, Type

from django.db import transaction
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.connection.models import ApiConnection
from smarter.apps.plugin.signals import broker_ready
from smarter.apps.provider.models import Provider
from smarter.apps.vectorstore.caching import (
    invalidate_all_cached_vectorstores_for_user_profile,
)
from smarter.apps.vectorstore.manifest.models.vectorstore.const import MANIFEST_KIND
from smarter.apps.vectorstore.manifest.models.vectorstore.metadata import (
    SAMVectorstoreMetadata,
)
from smarter.apps.vectorstore.manifest.models.vectorstore.model import SAMVectorstore
from smarter.apps.vectorstore.manifest.models.vectorstore.spec import (
    SAMVectorstoreEmbeddings,
    SAMVectorstoreIndex,
    SAMVectorstoreMaintenance,
    SAMVectorstoreSelfHosted,
    SAMVectorstoreSpec,
)
from smarter.apps.vectorstore.manifest.models.vectorstore.status import (
    SAMVectorstoreStatus,
)
from smarter.apps.vectorstore.models import (
    VectorstoreDocumentStatus,
    VectorstoreMeta,
    VectorstoreStatus,
)
from smarter.apps.vectorstore.serializers import VectorstoreSerializer
from smarter.apps.vectorstore.service import VectorstoreService
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
    __name__, any_switches=[SmarterWaffleSwitches.VECTORSTORE_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000
IMMUTABLE_WHILE_DEPLOYED = {
    # what cannot change once the database exists, because it would no longer match it.
    "backend": lambda spec: spec.backend,
    "hosting": lambda spec: spec.hosting,
    "index.name": lambda spec: spec.index.name,
    "index.dimension": lambda spec: spec.index.dimension,
    "index.metric": lambda spec: spec.index.metric,
    "selfHosted.storage": lambda spec: spec.selfHosted.storage if spec.selfHosted else None,
    "pinecone": lambda spec: spec.pinecone.model_dump() if spec.pinecone else None,
}


class SAMVectorstoreBrokerError(SAMBrokerError):
    """Base exception for Smarter API Vectorstore Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Vectorstore Manifest Broker Error"


class SAMVectorstoreBroker(AbstractBroker):
    """Broker for Vectorstore manifests.

    See the module's documentation.
    """

    _manifest: Optional[SAMVectorstore] = None
    _pydantic_model: Type[SAMVectorstore] = SAMVectorstore
    _vectorstore: Optional[VectorstoreMeta] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        logger.info(
            "%s.__init__() broker for %s %s is %s.", self.formatted_class_name, self.kind, self.name, self.ready_state
        )

    @property
    def SerializerClass(self) -> Type[ModelSerializer]:
        return VectorstoreSerializer

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
    def vectorstore(self) -> Optional[VectorstoreMeta]:
        """The user's own Vectorstore with the broker's name, else one shared with them.

        It is never created here.
        """
        if self._vectorstore:
            return self._vectorstore
        if not self.user_profile or not self.name:
            return None
        self._vectorstore = (
            VectorstoreMeta.objects.filter(user_profile=self.user_profile, name=self.name).first()
            or VectorstoreMeta.objects.filter(name=self.name)
            .with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
            .order_by("-updated_at")
            .first()
        )
        return self._vectorstore

    def owned_vectorstore(self, command: SmarterJournalCliCommands) -> VectorstoreMeta:
        """The Vectorstore, if the user is staff and owns it."""
        if not self.user_profile:
            raise SAMBrokerErrorNotReady("user_profile is not set.", thing=self.kind, command=command)
        if not (self.user_profile.user.is_staff or self.user_profile.user.is_superuser):
            raise SAMVectorstoreBrokerError(
                f"Only account admins may {command.value} a {self.kind}.", thing=self.kind, command=command
            )
        vectorstore = self.vectorstore
        if vectorstore is None or (
            vectorstore.user_profile_id != self.user_profile.pk  # type: ignore[attr-defined]
            and not self.user_profile.user.is_superuser
        ):
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        return vectorstore

    # -------------------------------------------------------------------------
    # resolving names
    # -------------------------------------------------------------------------
    def resolve_provider(self, name: str) -> Provider:
        """Spec.embeddings.provider: the user's own Provider, else the most recently updated one shared with them."""
        assert self.user_profile is not None
        provider = Provider.objects.filter(name=name, user_profile=self.user_profile).first() or (
            Provider.objects.filter(name=name)
            .with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
            .order_by("-updated_at")
            .first()
        )
        if provider is None:
            raise SAMBrokerErrorNotFound(
                f"spec.embeddings.provider: Provider {name} not found, or not shared with you.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        return provider

    def resolve_connection(self, name: Optional[str]) -> Optional[ApiConnection]:
        """Spec.connection: the user's own ApiConnection, else one shared with them."""
        if not name:
            return None
        assert self.user_profile is not None
        connection = ApiConnection.objects.filter(name=name, user_profile=self.user_profile).first() or (
            ApiConnection.objects.filter(name=name)
            .with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
            .order_by("-updated_at")
            .first()
        )
        if connection is None:
            raise SAMBrokerErrorNotFound(
                f"spec.connection: ApiConnection {name} not found, or not shared with you.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        return connection

    # -------------------------------------------------------------------------
    # conversions
    # -------------------------------------------------------------------------
    def manifest_to_django_orm(self) -> dict[str, Any]:
        """The VectorstoreMeta fields of the manifest."""
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"Manifest not loaded for {self.kind} broker.", thing=self.kind)
        spec = self.manifest.spec
        retval = {**super().manifest_to_django_orm()}
        retval.update(
            {
                "spec": spec.model_dump(mode="json"),
                "backend": spec.backend,
                "hosting": spec.hosting,
                "is_active": spec.isActive,
                "dimension": spec.index.dimension,
                "metric": spec.index.metric,
                "deletion_protection": spec.index.deletionProtection,
                "embeddings_model": spec.embeddings.model,
            }
        )
        return retval

    def spec_of(self, vectorstore: VectorstoreMeta) -> SAMVectorstoreSpec:
        """The Vectorstore's spec, as it was applied."""
        data = dict(vectorstore.spec or {})
        if not data:
            data = {
                "backend": vectorstore.backend,
                "hosting": vectorstore.hosting,
                "connection": vectorstore.connection.name if vectorstore.connection else None,
                "index": {"dimension": vectorstore.dimension, "metric": vectorstore.metric},
                "embeddings": {
                    "provider": vectorstore.embeddings_provider.name if vectorstore.embeddings_provider else "",
                    "model": vectorstore.embeddings_model,
                },
            }
        return SAMVectorstoreSpec(**data)

    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """The Vectorstore as a manifest, with its status."""
        vectorstore = self.vectorstore
        if not vectorstore:
            return None
        meta = SAMVectorstoreMetadata(
            name=vectorstore.name,
            description=vectorstore.description,
            version=vectorstore.version,
            tags=vectorstore.tags_list,
            annotations=vectorstore.annotations if isinstance(vectorstore.annotations, list) else [],
        )
        status = SAMVectorstoreStatus(
            accountNumber=vectorstore.user_profile.account.account_number,
            username=vectorstore.user_profile.user.username,
            recordLocator=vectorstore.record_locator,
            created=vectorstore.created_at,
            modified=vectorstore.updated_at,
            vectorstoreStatus=vectorstore.status,
            message=vectorstore.status_message or None,
            indexName=vectorstore.index_name or None,
            endpoint=vectorstore.endpoint_url or None,
            apiKeySecret=vectorstore.api_key_secret.name if vectorstore.api_key_secret else None,
            vectorCount=vectorstore.vector_count,
            documentCount=vectorstore.documents.count(),  # type: ignore[attr-defined]
            snapshotCount=vectorstore.snapshots.count(),  # type: ignore[attr-defined]
            deployedAt=vectorstore.deployed_at,
            lastCheckedAt=vectorstore.last_checked_at,
            lastSnapshotAt=vectorstore.last_snapshot_at,
            lastMaintenanceAt=vectorstore.last_maintenance_at,
        )
        model = SAMVectorstore(
            apiVersion=self.api_version, kind=self.kind, metadata=meta, spec=self.spec_of(vectorstore), status=status
        )
        return model.model_dump(mode="json")

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        return self.formatted_text(f"{SAMVectorstoreBroker.__name__}[{id(self)}]")

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMVectorstore]:
        """The Vectorstore manifest, as a Pydantic model, from the manifest loader."""
        if self._manifest:
            if not isinstance(self._manifest, SAMVectorstore):
                raise SAMVectorstoreBrokerError("Cached manifest is not a SAMVectorstore instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMVectorstore(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMVectorstoreMetadata(**self.loader.manifest_metadata),
                spec=SAMVectorstoreSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    @property
    def ORMMetaModelClass(self) -> Type[VectorstoreMeta]:
        return VectorstoreMeta

    @property
    def ORMModelClass(self) -> Type[VectorstoreMeta]:
        return VectorstoreMeta

    @property
    def orm_meta_instance(self) -> Optional[VectorstoreMeta]:  # type: ignore[override]
        return self.vectorstore

    @property
    def orm_instance(self) -> Optional[VectorstoreMeta]:  # type: ignore[override]
        return self.vectorstore

    def cache_invalidations(self) -> None:
        if self.user_profile:
            invalidate_all_cached_vectorstores_for_user_profile(self.user_profile)
        if self._vectorstore:
            VectorstoreMeta.get_cached_object(pk=self._vectorstore.pk, invalidate=True)
        return super().cache_invalidations()

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """An example Vectorstore manifest: a self-hosted Qdrant database for a knowledge base."""
        command = SmarterJournalCliCommands(self.example_manifest.__name__)
        model = SAMVectorstore(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=SAMVectorstoreMetadata(
                name="example_knowledge_base",
                description="A self-hosted Qdrant vector database of a company's product documentation.",
                version="1.0.0",
                tags=["example", "rag", "qdrant"],
                annotations=[{"smarter.sh/vectorstore/purpose": "example"}],
            ),
            spec=SAMVectorstoreSpec(
                backend="qdrant",
                hosting="self_hosted",
                index=SAMVectorstoreIndex(dimension=1536, metric="cosine"),
                embeddings=SAMVectorstoreEmbeddings(provider="openai", model="text-embedding-3-small"),
                selfHosted=SAMVectorstoreSelfHosted(storage="10Gi"),
                maintenance=SAMVectorstoreMaintenance(snapshotIntervalHours=24, snapshotRetention=7),
            ),
            status=SAMVectorstoreStatus(
                accountNumber=smarter_cached_objects.smarter_account.account_number,
                username=smarter_cached_objects.smarter_admin.username,
                recordLocator="vectorstoremeta-abc123",
                created=datetime.datetime.now(),
                modified=datetime.datetime.now(),
                vectorstoreStatus=VectorstoreStatus.PENDING.value,
            ),
        )
        return self.json_response_ok(command=command, data=model.model_dump(mode="json"))

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """The Vectorstores that the user may read, optionally filtered by name."""
        command = SmarterJournalCliCommands(self.get.__name__)
        name = self.clean_cli_param(
            param=kwargs.get(SAMMetadataKeys.NAME.value, None),
            param_name="name",
            url=self.smarter_build_absolute_uri(request),
        )
        if self.user_profile is None:
            raise SAMBrokerErrorNotReady("user_profile is not set.")
        vectorstores = VectorstoreMeta.objects.with_read_permission_for(self.user_profile.user)  # type: ignore[attr-defined]
        if name:
            vectorstores = vectorstores.filter(name=name)
        items = [
            self.to_camel_case(VectorstoreSerializer(vectorstore).data)
            for vectorstore in vectorstores.order_by("name")[:MAX_RESULTS]
        ]
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(items)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=VectorstoreSerializer()),
                SCLIResponseGetData.ITEMS.value: items,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(  # pylint: disable=too-many-locals
        self, request: HttpRequest, *args, **kwargs
    ) -> SmarterJournaledJsonResponse:
        """
        Create or update the Vectorstore.

        It does not create its database: deploy does.

        Once it is deployed, its backend, hosting, index, and self-hosted storage cannot change,
        because the database would no longer match. If its embeddings model changes, its loaded
        documents are loaded again.
        """
        command = SmarterJournalCliCommands(self.apply.__name__)
        if not self.ready or not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"{self.kind} {self.name} broker is not ready", thing=self.kind, command=command
            )
        if not self.user_profile:
            raise SAMBrokerErrorNotReady("user_profile is not set.", thing=self.kind, command=command)
        if not (self.user_profile.user.is_staff or self.user_profile.user.is_superuser):
            raise SAMVectorstoreBrokerError(
                f"Only account admins may apply a {self.kind}.", thing=self.kind, command=command
            )
        spec = self.manifest.spec
        provider = self.resolve_provider(spec.embeddings.provider)
        connection = self.resolve_connection(spec.connection)
        data = self.manifest_to_django_orm()
        tags = data.pop("tags", None) or []
        for field in ("id", "created_at", "updated_at"):
            data.pop(field, None)

        existing = VectorstoreMeta.objects.filter(
            user_profile=self.user_profile, name=self.manifest.metadata.name
        ).first()
        reload_documents = False
        if existing and existing.status != VectorstoreStatus.PENDING:
            previous = self.spec_of(existing)
            changed = [field for field, value in IMMUTABLE_WHILE_DEPLOYED.items() if value(previous) != value(spec)]
            if changed:
                raise SAMVectorstoreBrokerError(
                    f"{self.kind} {existing.name} is deployed, so {', '.join(changed)} cannot change. "
                    "Delete it, and apply it again, to change them.",
                    thing=self.kind,
                    command=command,
                )
            reload_documents = (
                previous.embeddings.provider,
                previous.embeddings.model,
                previous.embeddings.chunkSize,
            ) != (
                spec.embeddings.provider,
                spec.embeddings.model,
                spec.embeddings.chunkSize,
            )

        with transaction.atomic():
            vectorstore = existing or VectorstoreMeta(user_profile=self.user_profile)
            for key, value in data.items():
                setattr(vectorstore, key, value)
            vectorstore.embeddings_provider = provider
            vectorstore.connection = connection
            if not vectorstore.index_name or vectorstore.status == VectorstoreStatus.PENDING:
                vectorstore.index_name = spec.index.name or vectorstore.default_index_name()
            try:
                vectorstore.save()
                vectorstore.tags.set(tags)
            except Exception as e:
                raise SAMVectorstoreBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}: {e}", thing=self.kind, command=command
                ) from e
        self._vectorstore = vectorstore

        if (
            existing
            and existing.is_self_hosted
            and existing.status in (VectorstoreStatus.PROVISIONING, VectorstoreStatus.READY)
        ):
            # e.g. its cpu or memory changed.
            VectorstoreService(vectorstore).backend.provision()
        if reload_documents:
            self.reload_documents(vectorstore)
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.to_json())

    @staticmethod
    def reload_documents(vectorstore: VectorstoreMeta) -> int:
        """Load the loaded documents again, e.g. with a new embeddings model."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.vectorstore.tasks import load_vectorstore_document

        documents = list(vectorstore.documents.filter(status=VectorstoreDocumentStatus.LOADED))  # type: ignore[attr-defined]
        for document in documents:
            document.status = VectorstoreDocumentStatus.PENDING
            document.save(update_fields=["status", "updated_at"])
            if vectorstore.status == VectorstoreStatus.READY:
                load_vectorstore_document.delay(document.pk)
        return len(documents)

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = SmarterJournalCliCommands(self.prompt.__name__)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """The Vectorstore as a manifest, with its status."""
        command = SmarterJournalCliCommands(self.describe.__name__)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} name property is not set.", thing=self.kind, command=command)
        if not self.vectorstore:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        try:
            data = self.django_orm_to_manifest_dict()
        except Exception as e:
            raise SAMVectorstoreBrokerError(
                f"Failed to describe {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data=data)

    @memoized_dependencies
    def dependencies(self) -> List[AbstractBroker]:
        """Return brokers for the Vectorsearches that search this Vectorstore.

        :return: A broker for each Vectorsearch whose ``spec.vectorstore`` is this Vectorstore.
        :rtype: List[AbstractBroker]
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.manifests.enum import SAMKinds
        from smarter.apps.vectorsearch.models import Vectorsearch

        vectorstore = self.vectorstore
        if not vectorstore:
            return []
        return self.dependency_brokers(
            SAMKinds.VECTORSEARCH.value, Vectorsearch.objects.filter(vectorstore=vectorstore)
        )

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Destroy the database and its data, unless deletionProtection is enabled, then delete the Vectorstore."""
        command = SmarterJournalCliCommands(self.delete.__name__)
        vectorstore = self.owned_vectorstore(command)
        self.verify_no_dependencies(command)
        service = VectorstoreService(vectorstore)
        try:
            if vectorstore.deployed_at:
                service.destroy()
            elif vectorstore.deletion_protection:
                service.destroy()  # raises
            secret = vectorstore.api_key_secret
            vectorstore.delete()
            if secret is not None:
                secret.delete()
        except Exception as e:
            raise SAMVectorstoreBrokerError(
                f"Failed to delete {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        self._vectorstore = None
        self.cache_invalidations()
        return self.json_response_ok(command=command, data={})

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Create the database.

        A self-hosted server takes a minute or two to become ready: follow it with describe.
        """
        command = SmarterJournalCliCommands(self.deploy.__name__)
        vectorstore = self.owned_vectorstore(command)
        try:
            VectorstoreService(vectorstore).deploy()
        except Exception as e:
            raise SAMVectorstoreBrokerError(
                f"Failed to deploy {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.django_orm_to_manifest_dict() or {})

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Stop serving.

        A self-hosted server's data is kept, and a managed index is left as it is.
        """
        command = SmarterJournalCliCommands(self.undeploy.__name__)
        vectorstore = self.owned_vectorstore(command)
        try:
            VectorstoreService(vectorstore).undeploy()
        except Exception as e:
            raise SAMVectorstoreBrokerError(
                f"Failed to undeploy {self.kind} {self.name}: {e}", thing=self.kind, command=command
            ) from e
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.django_orm_to_manifest_dict() or {})

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """A self-hosted Qdrant server's recent logs."""
        command = SmarterJournalCliCommands(self.logs.__name__)
        vectorstore = self.owned_vectorstore(command)
        logs = VectorstoreService(vectorstore).backend.logs() if vectorstore.is_self_hosted else None
        return self.json_response_ok(command=command, data={"logs": logs or ""})


__all__ = ["SAMVectorstoreBroker", "SAMVectorstoreBrokerError"]
