# pylint: disable=C0302,W0718
"""Smarter API User Manifest handler"""

import datetime
import logging
from typing import Optional, Type

from django.db import transaction
from django.http import HttpRequest
from langchain_community.vectorstores.utils import DistanceStrategy
from pinecone.db_control.enums import DeletionProtection, Metric, VectorType
from pinecone.db_control.models import ServerlessSpec

from smarter.apps.account.models import User
from smarter.apps.account.models.user_profile import UserProfile
from smarter.apps.connection.models import ApiConnection
from smarter.apps.vectorstore.manifest.models.vectorstore.const import MANIFEST_KIND
from smarter.apps.vectorstore.manifest.models.vectorstore.metadata import (
    SAMVectorstoreMetadata,
)
from smarter.apps.vectorstore.manifest.models.vectorstore.model import SAMVectorstore
from smarter.apps.vectorstore.manifest.models.vectorstore.spec import (
    SAMEmbeddingsInterface,
    SAMIndexModelInterface,
    SAMVectorstoreInterface,
    SAMVectorstoreSpec,
)
from smarter.apps.vectorstore.manifest.models.vectorstore.status import (
    SAMVectorstoreStatus,
)
from smarter.apps.vectorstore.models import (
    EmbeddingsInterface,
    IndexModelInterface,
    VectorestoreMeta,
    VectorstoreInterface,
)
from smarter.apps.vectorstore.serializers import VectorstoreSerializer
from smarter.common.conf.settings import smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
    SAMBrokerInternalError,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.VECTORSTORE_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

MAX_RESULTS = 1000
"""
Maximum number of results to return for list operations.
This limit helps prevent performance issues and excessive data retrieval.

TODO: Make this configurable via smarter_settings.
"""


class SAMVectorstoreBrokerError(SAMBrokerError):
    """Base exception for Smarter API Vectorstore Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Vectorstore Manifest Broker Error"


class SAMVectorstoreBroker(AbstractBroker):
    """
    Smarter API Vectorstore Manifest Broker

    This class manages the lifecycle of Smarter API Vectorstore manifests, including loading, validating, parsing, and mapping them to Django ORM models and Pydantic models for serialization and deserialization.
    **Responsibilities:**
      - Load and validate Smarter API YAML Vectorstore manifests.
      - Parse manifests and initialize the corresponding Pydantic model (`SAMVectorstore`).
      - Interact with Django ORM models representing vectorstore manifests.
      - Create, update, delete, and query Django ORM models.
      - Transform Django ORM models into Pydantic models for serialization/deserialization.

    **Example Usage:**

      .. code-block:: python

         broker = SAMVectorstoreBroker()
         manifest = broker.manifest
         if manifest:
             print(manifest.apiVersion, manifest.kind)

    .. warning::

       If the manifest loader or manifest metadata is missing, the manifest may not be initialized and `None` may be returned.

    .. seealso::

       - `SAMVectorstore` (Pydantic model)
       - Django ORM models: `smarter.apps.vectorstore.models.Vectorstore`

    .. todo::

       Make the maximum results for list operations configurable via `smarter_settings`.

    """

    # override the base abstract manifest model with the Vectorstore model
    _manifest: Optional[SAMVectorstore] = None
    _pydantic_model: Type[SAMVectorstore] = SAMVectorstore

    # our ORM models.
    _vectorstore_meta: Optional[VectorestoreMeta] = None
    _index_model_interface: Optional[IndexModelInterface] = None
    _vectorstore_interface: Optional[VectorstoreInterface] = None
    _embeddings_interface: Optional[EmbeddingsInterface] = None

    @property
    def vectorstore_meta(self) -> Optional[VectorestoreMeta]:
        """
        Return the VectorestoreMeta associated with this broker, if available.

        :returns: The `VectorestoreMeta` instance, or `None` if not set.

        **Example usage:**

        .. code-block:: python

           vectorstore_meta = broker.vectorstore_meta
           if vectorstore_meta:
               print(f"VectorestoreMeta name: {vectorstore_meta.name}")

        See Also:

           - :class:`smarter.apps.vectorstore.models.VectorestoreMeta`
        """
        name = self._manifest.metadata.name if self._manifest else self._name
        if not self._vectorstore_meta and (isinstance(name, str) and isinstance(self.user_profile, UserProfile)):
            with transaction.atomic():
                try:
                    self._vectorstore_meta = VectorestoreMeta.objects.get(user_profile=self.user_profile, name=name)
                except VectorestoreMeta.DoesNotExist:
                    # It's possible the manifest exists but the corresponding database entry does not, so we return None in that case
                    return self._vectorstore_meta

                try:
                    self._index_model_interface = IndexModelInterface.objects.get(vectorstore=self._vectorstore_meta)
                except IndexModelInterface.DoesNotExist as e:
                    raise SAMBrokerInternalError(
                        f"Failed to describe {self.kind} {name}. IndexModelInterface not found",
                        thing=self.kind,
                        command=None,
                    ) from e

                try:
                    self._vectorstore_interface = VectorstoreInterface.objects.get(vectorstore=self._vectorstore_meta)
                except VectorstoreInterface.DoesNotExist as e:
                    raise SAMBrokerInternalError(
                        f"Failed to describe {self.kind} {name}. VectorstoreInterface not found",
                        thing=self.kind,
                        command=None,
                    ) from e

                try:
                    self._embeddings_interface = EmbeddingsInterface.objects.get(vectorstore=self._vectorstore_meta)
                except EmbeddingsInterface.DoesNotExist as e:
                    raise SAMBrokerInternalError(
                        f"Failed to describe {self.kind} {name}. EmbeddingsInterface not found",
                        thing=self.kind,
                        command=None,
                    ) from e

                logger.debug(
                    "%s.vectorstore_meta() initialized ORM objects: %s",
                    self.formatted_class_name,
                    self._vectorstore_meta,
                )

        return self._vectorstore_meta

    @property
    def index_model_interface(self) -> Optional[IndexModelInterface]:
        """
        Return the IndexModelInterface associated with this broker, if available.

        :returns: The `IndexModelInterface` instance, or `None` if not set.

        **Example usage:**

        .. code-block:: python

           index_model_interface = broker.index_model_interface()
           if index_model_interface:
               print(f"IndexModelInterface dimension: {index_model_interface.dimension}")

        See Also:

           - :class:`smarter.apps.vectorstore.models.IndexModelInterface`
        """
        return self._index_model_interface

    @property
    def vectorstore_interface(self) -> Optional[VectorstoreInterface]:
        """
        Return the VectorstoreInterface associated with this broker, if available.

        :returns: The `VectorstoreInterface` instance, or `None` if not set.

        **Example usage:**

        .. code-block:: python

           vectorstore_interface = broker.vectorstore_interface()
           if vectorstore_interface:
               print(f"VectorstoreInterface namespace: {vectorstore_interface.namespace}")

        See Also:

           - :class:`smarter.apps.vectorstore.models.VectorstoreInterface`
        """
        return self._vectorstore_interface

    @property
    def embeddings_interface(self) -> Optional[EmbeddingsInterface]:
        """
        Return the EmbeddingsInterface associated with this broker, if available.

        :returns: The `EmbeddingsInterface` instance, or `None` if not set.

        **Example usage:**

        .. code-block:: python

           embeddings_interface = broker.embeddings_interface()
           if embeddings_interface:
               print(f"EmbeddingsInterface provider: {embeddings_interface.provider}")

        See Also:

           - :class:`smarter.apps.vectorstore.models.EmbeddingsInterface`
        """
        return self._embeddings_interface

    def manifest_to_django_orm(self) -> dict:
        raise NotImplementedError(
            "manifest_to_django_orm is not implemented for SAMVectorstoreBroker. Use django_meta_orm_to_manifest.model_dump() instead."
        )

    def django_meta_orm_to_manifest(self) -> SAMVectorstoreMetadata:
        """
        Convert the Django ORM `VectorestoreMeta` model instance into a
        `SAMVectorstoreMetadata` Pydantic model for manifest serialization.

        :raises: :class:`SAMVectorstoreBrokerError`
              If `self.vectorstore_meta` is not set or is not an instance of `VectorestoreMeta`.

        :returns: A `SAMVectorstoreMetadata` instance representing the manifest metadata.

        **Example usage:**

        .. code-block:: python

            metadata = broker.django_meta_orm_to_manifest()
            print(metadata.name, metadata.description)
        """

        if not isinstance(self.vectorstore_meta, VectorestoreMeta):
            raise SAMVectorstoreBrokerError(
                f"Expected type VectorestoreMeta but got {type(self.vectorstore_meta)}", thing=self.kind
            )

        return SAMVectorstoreMetadata(
            name=self.vectorstore_meta.name,
            description=self.vectorstore_meta.description,
            version=self.vectorstore_meta.version,
            tags=self.vectorstore_meta.tags_list,
            annotations=self.vectorstore_meta.annotations,
        )

    def django_vector_interface_to_manifest(self) -> SAMVectorstoreInterface:
        """
        Convert the Django ORM `VectorstoreInterface` model instance into a
        `SAMVectorstoreInterface` Pydantic model for manifest serialization.

        :raises: :class:`SAMVectorstoreBrokerError`
              If `self.vectorstore_interface` is not set or is not an instance of `VectorstoreInterface`.

        :returns: A `SAMVectorstoreInterface` instance representing the manifest interface.

        **Example usage:**

        .. code-block:: python

            interface = broker.django_vector_interface_to_manifest()
            print(interface.textKey, interface.namespace)
        """

        if not isinstance(self.vectorstore_interface, VectorstoreInterface):
            raise SAMVectorstoreBrokerError(
                f"Expected type VectorstoreInterface for vectorstore_interface but got {type(self._vectorstore_interface)}",
                thing=self.kind,
            )

        # see langchain_core.vectorstores.base.VectorStoreRetriever and
        # langchain_core.embeddings.openai.OpenAIEmbeddings for
        # inspiration on how to structure these interfaces
        return SAMVectorstoreInterface(
            textKey=self.vectorstore_interface.text_key,
            namespace=self.vectorstore_interface.namespace,
            distanceStrategy=self.vectorstore_interface.distance_strategy,
        )

    def django_embeddings_interface_to_manifest(self) -> SAMEmbeddingsInterface:
        """
        Convert the Django ORM `EmbeddingsInterface` model instance into a
        `SAMEmbeddingsInterface` Pydantic model for manifest serialization.

        :raises: :class:`SAMVectorstoreBrokerError`
              If `self.embeddings_interface` is not set or is not an instance of `EmbeddingsInterface`.

        :returns: A `SAMEmbeddingsInterface` instance representing the manifest interface.

        **Example usage:**

        .. code-block:: python

            embeddings = broker.django_embeddings_interface_to_manifest()
            print(embeddings.provider, embeddings.providerModel)
        """
        if not isinstance(self.embeddings_interface, EmbeddingsInterface):
            raise SAMVectorstoreBrokerError(
                f"Expected type EmbeddingsInterface for embeddings_interface but got {type(self._embeddings_interface)}",
                thing=self.kind,
            )

        # see langchain_core.vectorstores.base.VectorStoreRetriever and
        # langchain_core.embeddings.openai.OpenAIEmbeddings for
        # inspiration on how to structure these interfaces
        return SAMEmbeddingsInterface(
            provider=self.embeddings_interface.provider,
            providerModel=self.embeddings_interface.provider_model,
            dimensions=self.embeddings_interface.dimensions,
            deployment=self.embeddings_interface.deployment,
            apiVersion=self.embeddings_interface.api_version,
            baseUrl=self.embeddings_interface.base_url,
            openaiApiType=self.embeddings_interface.openai_api_type,
            openaiProxy=self.embeddings_interface.openai_api_proxy,
            embeddingCtxLength=self.embeddings_interface.embedding_ctx_length,
            apiKey=self.embeddings_interface.api_key,
            organization=self.embeddings_interface.organization,
            allowedSpecial=self.embeddings_interface.allowed_special,
            disallowedSpecial=self.embeddings_interface.disallowed_special,
            chunkSize=self.embeddings_interface.chunk_size,
            maxRetries=self.embeddings_interface.max_retries,
            timeout=self.embeddings_interface.timeout,
            headers=self.embeddings_interface.headers,
            tiktokenEnabled=self.embeddings_interface.tiktoken_enabled,
            tiktokenModelName=self.embeddings_interface.tiktoken_model_name,
            showProgressBar=self.embeddings_interface.show_progress_bar,
            modelKwargs=self.embeddings_interface.model_kwargs,
            skipEmpty=self.embeddings_interface.skip_empty,
            defaultHeaders=self.embeddings_interface.default_headers,
            defaultQuery=self.embeddings_interface.default_query,
            retryMinSeconds=self.embeddings_interface.retry_min_seconds,
            retryMaxSeconds=self.embeddings_interface.retry_max_seconds,
            checkEmbeddingCtxLength=self.embeddings_interface.check_ctx_length,
        )

    def django_index_model_to_manifest(self) -> SAMIndexModelInterface:
        """
        Convert the Django ORM `IndexModelInterface` model instance into a
        `SAMIndexModelInterface` Pydantic model for manifest serialization.

        :raises: :class:`SAMVectorstoreBrokerError`
              If `self.index_model_interface` is not set or is not an instance of `IndexModelInterface`.

        :returns: A `SAMIndexModelInterface` instance representing the manifest interface.

        **Example usage:**

        .. code-block:: python

            index_model = broker.django_index_model_to_manifest()
            print(index_model.spec, index_model.dimension)
        """
        if not isinstance(self.index_model_interface, IndexModelInterface):
            raise SAMVectorstoreBrokerError(
                f"Expected type IndexModelInterface for index_model_interface but got {type(self._index_model_interface)}",
                thing=self.kind,
            )

        # see pinecone.db_control.models.IndexModel
        return SAMIndexModelInterface(
            spec=self.index_model_interface.spec,
            dimension=self.index_model_interface.dimension,
            metric=self.index_model_interface.metric,
            timeout=self.index_model_interface.timeout,
            deletionProtection=self.index_model_interface.deletion_protection,
            vectorType=self.index_model_interface.vector_type,
        )

    def django_orm_to_manifest(self) -> SAMVectorstore:
        """
        Convert a Django ORM `Vectorstore` model instance into a dictionary formatted for Pydantic manifest consumption.

        :returns: A `SAMVectorstore` instance representing the Smarter API Vectorstore manifest.

        .. note::

           Field names are automatically converted from snake_case to camelCase for compatibility with Pydantic models.

        :raises: :class:`SAMVectorstoreBrokerError` if `self.user` is not set.

        **Example usage:**

        .. code-block:: python

           manifest_dict = broker.django_orm_to_manifest()
           if manifest_dict:
               print(manifest_dict.model_dump())

        See Also:

           - :class:`SAMVectorstore`
           - :class:`smarter.apps.account.models.Vectorstore`
           - :class:`smarter.lib.manifest.enum.SamKeys`
           - :class:`smarter.lib.manifest.enumSAMMetadataKeys`
           - :class:`smarter.lib.manifest.enumSAMVectorstoreSpecKeys`

        """
        logger.debug(
            "%s.django_orm_to_manifest() called for %s %s", self.formatted_class_name, self.name, self.user_profile
        )

        if not isinstance(self.vectorstore_meta, VectorestoreMeta):
            raise SAMVectorstoreBrokerError(
                f"Expected type VectorestoreMeta but got {type(self.vectorstore_meta)}", thing=self.kind
            )

        if not isinstance(self.vectorstore_meta.connection, ApiConnection):
            raise SAMVectorstoreBrokerError(
                f"Expected type ApiConnection for connection but got {type(self.vectorstore_meta.connection)}",
                thing=self.kind,
            )
        if not isinstance(self.vectorstore_meta.connection.name, str):
            raise SAMVectorstoreBrokerError(
                f"Expected type str for connection.name but got {type(self.vectorstore_meta.connection.name)}",
                thing=self.kind,
            )

        metadata = self.django_meta_orm_to_manifest()

        spec = SAMVectorstoreSpec(
            connection=self.vectorstore_meta.connection.name,
            backend=self.vectorstore_meta.backend,
            vectorstore=self.django_vector_interface_to_manifest(),
            embeddings=self.django_embeddings_interface_to_manifest(),
            indexModel=self.django_index_model_to_manifest(),
        )
        status = SAMVectorstoreStatus(
            recordLocator=self.vectorstore_meta.record_locator,
            created=self.vectorstore_meta.created_at,
            modified=self.vectorstore_meta.updated_at,
            vectorstore_status=self.vectorstore_meta.status,
        )

        model = SAMVectorstore(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=metadata,
            spec=spec,
            status=status,
        )

        return model

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def SerializerClass(self) -> Type[VectorstoreSerializer]:
        """
        Get the Django REST Framework serializer class for the Smarter API Vectorstore.

        :returns: The `VectorstoreSerializer` class.
        :rtype: Type[ModelSerializer]
        """
        return VectorstoreSerializer

    @property
    def formatted_class_name(self) -> str:
        """
        Return a formatted class name string for logging and diagnostics.

        :returns: A string representing the fully qualified class name, including the parent class.

        **Example usage:**

        .. code-block:: python

           logger.debug(broker.formatted_class_name)

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{SAMVectorstoreBroker.__name__}[{id(self)}]"

    @property
    def kind(self) -> str:
        """
        Return the manifest kind string for the Smarter API Vectorstore.

        :returns: The manifest kind as a string (e.g., ``"Vectorstore"``).

        **Example usage:**

        .. code-block:: python

           if broker.kind == "Vectorstore":
               print("This broker handles Vectorstore manifests.")

        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMVectorstore]:
        """
        Get the manifest for the Smarter API Vectorstore as a Pydantic model.

        :returns: A `SAMVectorstore` Pydantic model instance representing the Smarter API Vectorstore manifest, or None if not initialized.

        .. note::

           The top-level manifest model (`SAMVectorstore`) must be explicitly initialized with manifest data, typically using ``**data`` from the manifest loader.

        .. warning::

           If the manifest loader or manifest metadata is missing, the manifest will not be initialized and None may be returned.

        **Example usage**::

            # Access the manifest property
            manifest = broker.manifest
            if manifest:
                print(manifest.apiVersion, manifest.kind)
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMVectorstore):
                raise SAMVectorstoreBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMVectorstore(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMVectorstoreMetadata(**self.loader.manifest_metadata),
                spec=SAMVectorstoreSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def ORMMetaModelClass(self) -> Type[VectorestoreMeta]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[VectorestoreMeta]
        """
        return VectorestoreMeta

    @property
    def ORMModelClass(self) -> Type[VectorestoreMeta]:
        """
        Return the model class associated with the Smarter API Vectorstore.

        :returns: The `VectorestoreMeta` model class.

        **Example usage:**

        .. code-block:: python

           model_cls = broker.ORMModelClass
           provider_instance = model_cls.objects.get(name="example_provider")

        .. seealso::

           - :class:`smarter.apps.vectorstore.models.VectorestoreMeta`
        """
        return VectorestoreMeta

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return the Django model class associated with the Smarter API Vectorstore manifest.

        :returns: The Django `VectorestoreMeta` model class.

        **Example usage:**

        .. code-block:: python

           user_cls = broker.ORMModelClass
           user = user_cls.objects.get(username="example_user")

        .. seealso::

           - :class:`smarter.apps.account.models.VectorestoreMeta`
           - :meth:`django_orm_to_manifest`
           - :class:`smarter.apps.SamKeys`
           - :class:`SAMMetadataKeys`
           - :class:`SAMVectorstoreSpecKeys`

        """
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        metadata = SAMVectorstoreMetadata(
            name="acme_llm_company",
            description="an example vectorstore manifest for the Smarter API Vectorstore",
            version="1.0.0",
            tags=["example", "vectorstore", "smarter-api"],
            annotations=[
                {f"{smarter_settings.root_domain}/vectorstore": "example_provider"},
                {f"{smarter_settings.root_domain}/created_by": "smarter_provider_broker"},
            ],
        )
        spec_vectorstore_interface = SAMVectorstoreInterface(
            textKey="example_key_id",
            namespace="example_namespace",
            distanceStrategy=DistanceStrategy.COSINE.value,
        )
        spec_embeddings_interface = SAMEmbeddingsInterface(
            provider="openai",
            providerModel="text-embedding-ada-002",
            dimensions=1536,
            deployment="example_deployment",
            apiVersion="2024-01-01",
            baseUrl="https://api.example-embeddings.com",
            openaiApiType="example_api_type",
            openaiProxy="https://proxy.example.com",
            embeddingCtxLength=8191,
            apiKey="example_api_key",
            organization="example_org",
            allowedSpecial={"<special1>", "<special2>"},
            disallowedSpecial={"<disallowed1>", "<disallowed2>"},
            chunkSize=1000,
            maxRetries=2,
            timeout=30,
            headers={"Custom-Header": "Value"},
            tiktokenEnabled=True,
            tiktokenModelName="example-tiktoken-model",
            showProgressBar=False,
            modelKwargs={"param1": "value1", "param2": "value2"},
            skipEmpty=False,
            defaultHeaders={"Default-Header": "DefaultValue"},
            defaultQuery={"default_param": "default_value"},
            retryMinSeconds=4,
            retryMaxSeconds=20,
            checkEmbeddingCtxLength=True,
        )
        spec = ServerlessSpec(
            cloud="AWS",
            region="us-east-1",
        ).asdict()
        spec_index_model = SAMIndexModelInterface(
            spec=spec.get("serverless"),
            dimension=1536,
            metric=Metric.COSINE.value,
            timeout=30,
            deletionProtection=DeletionProtection.DISABLED.value,
            vectorType=VectorType.SPARSE.value,
        )
        spec = SAMVectorstoreSpec(
            connection="example_api_connection",
            backend="pinecone",
            isActive=True,
            vectorstore=spec_vectorstore_interface,
            embeddings=spec_embeddings_interface,
            indexModel=spec_index_model,
        )
        status = SAMVectorstoreStatus(
            recordLocator="example_record_locator",
            created=datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
            modified=datetime.datetime(2024, 1, 15, 12, 0, 0, tzinfo=datetime.timezone.utc),
        )

        model = SAMVectorstore(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=metadata,
            spec=spec,
            status=status,
        )

        return self.json_response_ok(command=command, data=model.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve Smarter API Vectorstore manifests as a list of serialized Pydantic models.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments, including optional filter parameters.

        :returns: A `SmarterJournaledJsonResponse` containing a list of user manifests and metadata.

        .. note::

           If a vectorstore name is provided in `kwargs`, only manifests for that vectorstore are returned; otherwise, all manifests for the account are listed.

        :raises: :class:`SAMVectorstoreBrokerError`
           If serialization fails for any vectorstore

        **Example usage:**

        .. code-block:: python

           response = broker.get(request, name="openai")
           print(response.data["spec"]["items"])

        See Also:

           - :class:`smarter.apps.vectorstore.serializers.VectorstoreSerializer`
           - :meth:`django_orm_to_manifest`
           - :class:`smarter.lib.manifest.response.SmarterJournaledJsonResponse`
           - :class:`smarter.lib.manifest.enum.SamKeys`
           - :class:`smarter.lib.manifest.enum.SAMMetadataKeys`
           - :class:`smarter.lib.manifest.enum.SCLIResponseGet`
           - :class:`smarter.lib.manifest.enum.SCLIResponseGetData`

        """
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        name: Optional[str] = kwargs.get(SAMMetadataKeys.NAME.value, None)
        data = []
        if not isinstance(self.user_profile, UserProfile):
            raise SAMVectorstoreBrokerError("User profile is not set or invalid", thing=self.kind, command=command)

        if name:
            vectorstores = VectorestoreMeta.objects.filter(name=name).with_read_permission_for(self.user_profile.user)[
                :MAX_RESULTS
            ]
        else:
            vectorstores = VectorestoreMeta.objects.with_read_permission_for(self.user_profile.user)[:MAX_RESULTS]

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for vectorstore in vectorstores:
            try:
                self._vectorstore_meta = vectorstore
                model = self.django_meta_orm_to_manifest()
                model_dump = model.model_dump()
                if not model_dump:
                    raise SAMVectorstoreBrokerError(
                        f"Model dump failed for {self.kind} {vectorstore.name}", thing=self.kind, command=command
                    )
                data.append(model_dump)
            except Exception as e:
                raise SAMVectorstoreBrokerError(
                    f"Model dump failed for {self.kind} {vectorstore.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: self.params,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=VectorstoreSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest data to the Django ORM `Vectorstore` model and persist changes to the database.


        .. note::

            tags are handled separately because they are of type TaggableManager and
            require a different method to set them.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A `SmarterJournaledJsonResponse` containing the updated user manifest.

        .. note::

           This method first calls ``super().apply()`` to ensure the manifest is loaded and validated before applying changes.

        .. attention::

           Fields in the manifest that are not editable (e.g., ``id``, ``date_joined``, ``last_login``, ``username``, ``is_superuser``) are removed before saving to the ORM model.

        :raises: :class:`SAMVectorstoreBrokerError`
           If the user instance is not set or is invalid


        **Example usage:**

        .. code-block:: python

           response = broker.apply(request)
           print(response.data)

        See Also:

           - :class:`smarter.apps.vectorstore.models.Vectorstore`
           - :class:`SAMVectorstoreBrokerError`

        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)

        if not isinstance(self._manifest, SAMVectorstore):
            raise SAMVectorstoreBrokerError(
                f"Invalid manifest type or manifest is not set: {type(self._manifest)}",
                thing=self.kind,
                command=command,
            )
        if not isinstance(self.user, User):
            raise SAMVectorstoreBrokerError("User is not set or invalid", thing=self.kind, command=command)
        if not isinstance(self.user_profile, UserProfile):
            raise SAMVectorstoreBrokerError("User profile is not set or invalid", thing=self.kind, command=command)

        if not self.user.is_staff:
            raise SAMVectorstoreBrokerError(
                message="Only account admins can apply vectorstore manifests.",
                thing=self.kind,
                command=command,
            )

        name = self._manifest.metadata.name
        logger.debug("%s.apply() called with manifest: %s %s", self.formatted_class_name, name, self.user_profile)

        def map_fields(data: dict, instance: VectorestoreMeta) -> TimestampedModel:
            for field in readonly_fields:
                data.pop(field, None)
            for key, value in data.items():
                setattr(instance, key, value)
            return instance

        readonly_fields = [
            "id",
            "user_profile",
        ]

        with transaction.atomic():
            try:
                self._vectorstore_meta, created = VectorestoreMeta.objects.get_or_create(
                    user_profile=self.user_profile, name=self._manifest.metadata.name
                )
                if created:
                    logger.debug(
                        "%s.apply() created new %s '%s'", self.formatted_class_name, self.kind, self._vectorstore_meta
                    )

                # unpack the manifest into a snake_case dictionary and map it to the ORM model
                metadata = super().manifest_to_django_orm()
                dump = self.manifest.spec.vectorstore.model_dump()  # type: ignore[return-value]
                dump = self.camel_to_snake(dump)
                if not isinstance(metadata, dict) or not isinstance(dump, dict):
                    raise SAMVectorstoreBrokerError(
                        f"Expected metadata and dump to be dictionaries for {self.kind} {name}",
                        thing=self.kind,
                        command=command,
                    )
                data = {**metadata, **dump}

                tags = data.get("tags", [])
                self._vectorstore_meta = map_fields(data, self._vectorstore_meta)  # type: ignore
                if not isinstance(self.vectorstore_meta, VectorestoreMeta):
                    raise SAMVectorstoreBrokerError(
                        f"Vectorstore is not set for {self.kind} {name}", thing=self.kind, command=command
                    )
                self.vectorstore_meta.save()
                self.vectorstore_meta.tags.set(tags)
            except Exception as e:
                raise SAMVectorstoreBrokerError(
                    f"Failed to apply {self.kind} {name}",
                    thing=self.kind,
                    command=command,
                ) from e

            try:
                self._index_model_interface, _ = IndexModelInterface.objects.get_or_create(
                    vectorstore=self._vectorstore_meta
                )
                dump = self.manifest.spec.indexModel.model_dump()  # type: ignore[return-value]
                dump = self.camel_to_snake(dump)
                if not isinstance(dump, dict):
                    raise SAMBrokerInternalError(
                        f"Expected dump to be a dictionary for {self.kind} {name}", thing=self.kind, command=command
                    )
                data = {**dump}
                self._index_model_interface = map_fields(data, self._index_model_interface)  # type: ignore
                if not isinstance(self._index_model_interface, IndexModelInterface):
                    raise SAMBrokerInternalError(
                        f"IndexModelInterface is not set for {self.kind} {name}", thing=self.kind, command=command
                    )
                self._index_model_interface.save()
            except Exception as e:
                raise SAMBrokerInternalError(
                    f"Failed to apply {IndexModelInterface.__class__.__name__} for {self.kind} {name}",
                    thing=self.kind,
                    command=command,
                ) from e

            try:
                self._vectorstore_interface, _ = VectorstoreInterface.objects.get_or_create(
                    vectorstore=self._vectorstore_meta
                )
                dump = self._manifest.spec.vectorstore.model_dump()  # type: ignore[return-value]
                dump = self.camel_to_snake(dump)
                if not isinstance(dump, dict):
                    raise SAMBrokerInternalError(
                        f"Expected dump to be a dictionary for {self.kind} {name}", thing=self.kind, command=command
                    )
                data = {**dump}
                self._vectorstore_interface = map_fields(data, self._vectorstore_interface)  # type: ignore
                if not isinstance(self._vectorstore_interface, VectorstoreInterface):
                    raise SAMBrokerInternalError(
                        f"VectorstoreInterface is not set for {self.kind} {name}", thing=self.kind, command=command
                    )
                self._vectorstore_interface.save()
            except Exception as e:
                raise SAMBrokerInternalError(
                    f"Failed to apply {VectorstoreInterface.__class__.__name__} for {self.kind} {name}",
                    thing=self.kind,
                    command=command,
                ) from e

            try:
                self._embeddings_interface, _ = EmbeddingsInterface.objects.get_or_create(
                    vectorstore=self._vectorstore_meta
                )
                dump = self._manifest.spec.embeddings.model_dump()  # type: ignore[return-value]
                dump = self.camel_to_snake(dump)
                if not isinstance(dump, dict):
                    raise SAMBrokerInternalError(
                        f"Expected dump to be a dictionary for {self.kind} {name}", thing=self.kind, command=command
                    )
                data = {**dump}
                self._embeddings_interface = map_fields(data, self._embeddings_interface)  # type: ignore
                if not isinstance(self._embeddings_interface, EmbeddingsInterface):
                    raise SAMBrokerInternalError(
                        f"EmbeddingsInterface is not set for {self.kind} {name}", thing=self.kind, command=command
                    )
                self._embeddings_interface.save()
            except Exception as e:
                raise SAMBrokerInternalError(
                    f"Failed to apply {EmbeddingsInterface.__class__.__name__} for {self.kind} {name}",
                    thing=self.kind,
                    command=command,
                ) from e

        logger.debug("%s.apply() successfully applied manifest for %s '%s'", self.formatted_class_name, self.kind, name)

        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.to_json())

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            this is not implemented for the Smarter API Vectorstore manifest.

        :raises: :class:`SAMBrokerErrorNotImplemented`
            Always raised to indicate that the chat operation is not implemented for this manifest type.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: Never returns; always raises an exception.
        """
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Describe the Smarter API Vectorstore manifest by retrieving the corresponding Django ORM `Vectorstore` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments, including the username to describe.

        :returns: A `SmarterJournaledJsonResponse` containing the user manifest data.

        :raises: :class:`SAMBrokerErrorNotFound`
           If the vectorstore with the specified name does not exist or is not associated with the account.
        :raises: :class:`SAMVectorstoreBrokerError`
           If serialization fails for the vectorstore.

        _index_model_interface: Optional[IndexModelInterface]
        _vectorstore_interface: Optional[VectorstoreInterface]
        _embeddings_interface: Optional[EmbeddingsInterface]
        """
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if not isinstance(self.user_profile, UserProfile):
            raise SAMVectorstoreBrokerError("User profile is not set or invalid", thing=self.kind, command=command)

        self._name = kwargs.get("name")

        if not isinstance(self.vectorstore_meta, VectorestoreMeta) or self.vectorstore_meta.name != self.name:
            raise SAMBrokerErrorNotFound(
                f"Failed to describe {self.kind} {self.name}. Not found or not associated with account",
                thing=self.kind,
                command=command,
            )

        if self.vectorstore_meta:
            try:
                model = self.django_orm_to_manifest()
                data = model.model_dump()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMVectorstoreBrokerError(
                    f"Failed to describe {self.kind} {self.vectorstore_meta.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the Smarter API Vectorstore manifest by removing the corresponding Django ORM `Vectorstore` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments, including the username to delete.

        :returns: A `SmarterJournaledJsonResponse` indicating the result of the delete operation.

        :raises: :class:`SAMBrokerErrorNotFound`
           If the vectorstore with the specified name does not exist.
        :raises: :class:`SAMVectorstoreBrokerError`
           If deletion fails for the vectorstore.

        """
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)

        if not isinstance(self.user_profile, UserProfile):
            raise SAMVectorstoreBrokerError("User profile is not set or invalid", thing=self.kind, command=command)

        if not self.user_profile.user.is_staff or self.user_profile.user.is_superuser:
            raise SAMVectorstoreBrokerError(
                message="Only account admins can delete providers.",
                thing=self.kind,
                command=command,
            )

        if not isinstance(self.params, dict):
            raise SAMBrokerErrorNotImplemented(message="Params must be a dictionary", thing=self.kind, command=command)

        self._name = self.params.get("name")
        self._vectorstore_meta = None
        self._index_model_interface = None
        self._vectorstore_interface = None
        self._embeddings_interface = None

        if not isinstance(self.vectorstore_meta, VectorestoreMeta):
            raise SAMBrokerErrorNotFound(
                f"Failed to delete {self.kind} {self.name}. Not found or not associated with account",
                thing=self.kind,
                command=command,
            )
        try:
            with transaction.atomic():
                if self.index_model_interface:
                    self.index_model_interface.delete()
                if self.vectorstore_interface:
                    self.vectorstore_interface.delete()
                if self.embeddings_interface:
                    self.embeddings_interface.delete()
                self.vectorstore_meta.delete()
            return self.json_response_ok(command=command, data={})
        except Exception as e:
            raise SAMVectorstoreBrokerError(
                f"Failed to delete {self.kind} {self.name}", thing=self.kind, command=command
            ) from e

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Deploy the Smarter API Vectorstore manifest by activating the corresponding Django ORM `Vectorstore` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises: :class:`SAMVectorstoreBrokerError`
           If deployment fails for the user.

        :returns: A `SmarterJournaledJsonResponse` indicating the result of the deploy operation.
        """
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)

        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Undeploy the Smarter API Vectorstore manifest by deactivating the corresponding Django ORM `Vectorstore` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises: :class:`SAMVectorstoreBrokerError`
           If undeployment fails for the user.
        """
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)

        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs related to the Smarter API Vectorstore manifest.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A `SmarterJournaledJsonResponse` containing log data.
        """
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)


__all__ = ["SAMVectorstoreBroker", "SAMVectorstoreBrokerError"]
