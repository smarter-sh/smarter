# pylint: disable=W0718,C0302
"""Smarter API Vectorsearch Manifest handler."""

import datetime
from typing import Optional, Type

from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer
from taggit.managers import TaggableManager

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.plugin.signals import broker_ready
from smarter.apps.secret.models import Secret
from smarter.apps.vectorsearch.manifest.models.vectorsearch.const import MANIFEST_KIND
from smarter.apps.vectorsearch.manifest.models.vectorsearch.metadata import (
    SAMVectorsearchMetadata,
)
from smarter.apps.vectorsearch.manifest.models.vectorsearch.model import SAMVectorsearch
from smarter.apps.vectorsearch.manifest.models.vectorsearch.spec import (
    SAMVectorsearchSpec,
    SAMVectorsearchSpecConfig,
)
from smarter.apps.vectorsearch.manifest.models.vectorsearch.status import (
    SAMVectorsearchStatus,
)
from smarter.apps.vectorsearch.models import (
    Vectorsearch,
    VectorsearchSearchType,
)
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.common.utils.decorators import camel_case
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.VECTORSEARCH_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000


class SAMVectorsearchBrokerError(SAMBrokerError):
    """Base exception for Smarter API Vectorsearch Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Vectorsearch Manifest Broker Error"


class VectorsearchSerializer(ModelSerializer):
    """Django ORM model serializer for get()."""

    # pylint: disable=C0115
    class Meta:
        model = Vectorsearch
        fields = ["__all__"]


class SAMVectorsearchBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` Vectorsearch manifests.

    This class provides a high-level abstraction for managing vectorsearch manifests
    within the Smarter platform. It acts as the central coordinator for the
    lifecycle of vectorsearch manifests, bridging the gap between declarative YAML
    files and persistent application state.

    The broker is responsible for:

    - Managing the lifecycle of vectorsearch manifests, including loading, validation,
      and parsing of YAML files.
    - Initializing Pydantic models from manifest data to ensure robust schema
      validation and serialization.
    - Integrating with Django ORM models that represent vectorsearch manifests,
      supporting creation, update, deletion, and querying of database records.
    - Transforming data between Django ORM models and Pydantic models to enable
      seamless conversion between database and API representations.
    - Resolving the manifest's declarative `vectorstoreName` and `authSecretName`
      references against this account's VectorstoreMeta and Secret records, since
      those are FKs on Vectorsearch but name references in the manifest spec.
    - Ensuring atomic and consistent application of changes using Django's
      transaction management.
    - Providing detailed logging and error handling integrated with the Smarter
      platform's diagnostics systems.

    This broker is a key component in the deployment, configuration, and
    lifecycle management of vectorsearches in the Smarter Framework.
    """

    # override the base abstract manifest model with the Vectorsearch model
    _manifest: Optional[SAMVectorsearch] = None
    _pydantic_model: Type[SAMVectorsearch] = SAMVectorsearch
    _vectorsearch: Optional[Vectorsearch] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        logger.info(msg)

    @property
    def SerializerClass(self) -> Type[VectorsearchSerializer]:
        """
        The Django ORM model serializer class for the Vectorsearch.

        :returns: The Vectorsearch Django ORM model serializer class.
        :rtype: Type[ModelSerializer]
        """
        return VectorsearchSerializer

    @property
    def ready(self) -> bool:
        """
        Check if the broker is ready for operations.

        This property determines whether the broker has been properly initialized
        and is ready to perform its functions. A broker is considered ready if
        it has a valid manifest loaded, either from raw data, a loader, or
        existing Django ORM models.

        :returns: ``True`` if the broker is ready, ``False`` otherwise.
        :rtype: bool
        """
        if self._ready:
            return self._ready
        retval = super().ready
        if not retval:
            logger.debug("%s.ready() AbstractBroker is not ready for %s", self.formatted_class_name, self.kind)
            return False
        retval = self.manifest is not None or self.account is not None
        logger.debug(
            "%s.ready() manifest presence indicates ready=%s for %s",
            self.formatted_class_name,
            retval,
            self.kind,
        )
        if retval:
            self._ready = True
            broker_ready.send(sender=self.__class__, broker=self)
        return self._ready

    @property
    def vectorsearch(self) -> Optional[Vectorsearch]:
        """
        Provides access to the Django ORM model instance representing the current Smarter Vectorsearch.

        This property retrieves the Vectorsearch object associated with the broker's account and name.
        If a matching Vectorsearch record exists in the database, it is returned and cached for future
        access. If no such record exists, and a manifest is available, a new Vectorsearch instance is
        created using data extracted from the manifest -- with `vectorstoreName`/`authSecretName`
        resolved to their corresponding VectorstoreMeta/Secret FKs -- and then persisted to the database.

        :returns: The Django ORM Vectorsearch instance if found or created, otherwise ``None`` if
                  neither a database record nor a manifest is available.
        :rtype: Optional[Vectorsearch]

        .. admonition:: FIX NOTE

            This should be refactored/removed in favor of orm_instance. There is no logic
            in this property that merits it overriding the parent orm_instance property.

        .. admonition:: FIX NOTE

            This is breaking an unwritten rule of Smarter resources in that it is
            lazily **creating** a database record on a property getter.
            Creating/updating database records should be handled in apply().
        """
        if self._vectorsearch:
            return self._vectorsearch

        try:
            self._vectorsearch = Vectorsearch.get_cached_object(
                invalidate=True, user_profile=self.user_profile, name=self.name
            )  # type: ignore
            logger.debug(
                "%s.vectorsearch() retrieved existing Vectorsearch instance %s owned by %s from database.",
                self.formatted_class_name,
                self._vectorsearch,
                self.user_profile,
            )
            return self._vectorsearch
        except Vectorsearch.DoesNotExist:
            self._vectorsearch = None

        logger.debug(
            "%s.vectorsearch() Vectorsearch instance not found for user_profile %s. Attempting to create a new instance.",
            self.formatted_class_name,
            self.user_profile,
        )
        if self.manifest:
            data = self.manifest_to_django_orm()
            data["user_profile"] = self.user_profile
            vectorstore_name = data.pop("vectorstore_name", None)
            auth_secret_name = data.pop("auth_secret_name", None)
            data["vectorstore"] = self.resolve_vectorstore(vectorstore_name)
            data["auth_secret"] = self.resolve_auth_secret(auth_secret_name)
            logger.debug("%s.vectorsearch() Creating new Vectorsearch with data: %s", self.formatted_class_name, data)
            tags = data.pop("tags", [])
            self._vectorsearch = Vectorsearch.objects.create(**data)
            if self._vectorsearch and tags:
                self._vectorsearch.tags.set(tags)
            self._created = True
            logger.warning(
                "%s.vectorsearch() lazily created new Vectorsearch instance %s owned by %s. This logic should be handled in apply().",
                self.formatted_class_name,
                self._vectorsearch,
                self.user_profile,
            )
        else:
            logger.warning(
                "%s.vectorsearch() %s not found for user_profile %s",
                self.formatted_class_name,
                self._vectorsearch,
                self.user_profile,
            )

        return self._vectorsearch

    def resolve_vectorstore(self, vectorstore_name: str) -> VectorstoreMeta:
        """
        Resolve a manifest `vectorstoreName` reference to a VectorstoreMeta instance owned by this account.

        :param vectorstore_name: The name of the VectorstoreMeta to resolve.
        :type vectorstore_name: str
        :returns: The resolved VectorstoreMeta instance.
        :rtype: VectorstoreMeta
        :raises SAMVectorsearchBrokerError: If no matching VectorstoreMeta is found for this account.
        """
        vectorstore = VectorstoreMeta.objects.filter(user_profile=self.user_profile, name=vectorstore_name).first()
        if vectorstore is None:
            raise SAMVectorsearchBrokerError(
                f"VectorstoreMeta '{vectorstore_name}' not found for this account.", thing=self.kind
            )
        return vectorstore

    def resolve_auth_secret(self, auth_secret_name: Optional[str]) -> Optional[Secret]:
        """
        Resolve a manifest `authSecretName` reference to a Secret instance owned by this account, if provided.

        :param auth_secret_name: The name of the Secret to resolve, or ``None``.
        :type auth_secret_name: Optional[str]
        :returns: The resolved Secret instance, or ``None`` if no name was given.
        :rtype: Optional[Secret]
        :raises SAMVectorsearchBrokerError: If a name was given but no matching Secret is found.
        """
        if not auth_secret_name:
            return None
        secret = Secret.objects.filter(user_profile=self.user_profile, name=auth_secret_name).first()
        if secret is None:
            raise SAMVectorsearchBrokerError(
                f"Secret '{auth_secret_name}' not found for this account.", thing=self.kind
            )
        return secret

    def manifest_to_django_orm(self) -> dict:
        """
        Convert the Smarter API Vectorsearch manifest into a dictionary suitable for creating or updating.

        a Django ORM Vectorsearch model.

        This method extracts all relevant configuration, metadata, and versioning information from the
        loaded manifest and transforms it into a dictionary format compatible with Django ORM operations.
        The manifest's configuration is first dumped and converted from camelCase to snake_case to match
        Django's field naming conventions.

        `vectorstore_name` and `auth_secret_name` are left in the returned dict as plain strings rather
        than resolved here, since resolution requires a database lookup scoped to `self.user_profile`;
        callers (`vectorsearch` property, `apply()`) are responsible for popping and resolving them to
        the `vectorstore`/`auth_secret` FKs before assignment.

        :returns: A dictionary containing all fields required to create or update a Django ORM Vectorsearch model.
        :rtype: dict

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded or cannot be found.
        :raises SAMVectorsearchBrokerError: If the manifest configuration cannot be converted to a dictionary.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"Manifest not loaded for {self.kind} broker. Cannot convert to Django ORM.", thing=self.kind
            )
        metadata = super().manifest_to_django_orm()

        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.to_snake_case(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMVectorsearchBrokerError(
                f"Failed to convert {self.kind} {self.manifest.metadata.name} to dict. Got {type(config_dump)}",
                thing=self.kind,
            )
        retval = {
            **metadata,
            **config_dump,
        }
        logger.debug(
            "%s.manifest_to_django_orm() converted manifest to Django ORM dict: %s",
            self.formatted_class_name,
            retval,
        )

        return retval

    @camel_case()
    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """
        Transform the Django ORM Vectorsearch model instance into a dictionary compatible with the.

        Smarter API Vectorsearch manifest format.

        This method converts the current Vectorsearch ORM model into a dictionary structure that
        matches the expected schema for a Pydantic manifest. The conversion includes renaming fields
        from snake_case to camelCase, removing internal-only fields, resolving the `vectorstore`/
        `auth_secret` FKs back to `vectorstoreName`/`authSecretName` string references, and assembling
        metadata, spec, and status sections as required by the manifest.

        If the Vectorsearch model is not available, the method logs a warning and returns ``None``.
        If the conversion fails, an exception is raised to indicate the error.

        :returns: A dictionary representing the Smarter API Vectorsearch manifest, or ``None`` if the
                  Vectorsearch model is not set.
        :rtype: Optional[dict]

        :raises SAMVectorsearchBrokerError: If the ORM model cannot be converted to a manifest dictionary.

        See also:

        - :py:meth:`smarter.apps.vectorsearch.manifest.brokers.vectorsearch.SAMVectorsearchBroker.manifest_to_django_orm`
        - :py:class:`smarter.apps.vectorsearch.manifest.models.vectorsearch.SAMVectorsearch`
        - :py:class:`smarter.apps.vectorsearch.manifest.models.vectorsearch.metadata.SAMVectorsearchMetadata`
        - :py:class:`smarter.apps.vectorsearch.manifest.models.vectorsearch.spec.SAMVectorsearchSpec`
        - :py:class:`smarter.apps.vectorsearch.manifest.models.vectorsearch.status.SAMVectorsearchStatus`
        """
        if not self.account:
            raise SAMBrokerErrorNotReady(
                f"Account not loaded for {self.kind} broker. Cannot convert Django ORM to manifest dict.",
                thing=self.kind,
            )
        if not self.user_profile:
            raise SAMBrokerErrorNotReady(
                f"User profile not loaded for {self.kind} broker. Cannot convert Django ORM to manifest dict.",
                thing=self.kind,
            )
        if not self.vectorsearch:
            logger.warning(
                "%s.django_orm_to_manifest_dict() called without a Vectorsearch. This could affect broker operations.",
                self.formatted_class_name,
            )
            return None
        vectorsearch_dict = model_to_dict(self.vectorsearch)
        vectorsearch_dict.pop("id")
        vectorsearch_dict.pop("name")
        vectorsearch_dict.pop("description")
        vectorsearch_dict.pop("version", None)
        vectorsearch_dict.pop("vectorstore", None)
        vectorsearch_dict.pop("auth_secret", None)
        vectorsearch_dict["vectorstore_name"] = self.vectorsearch.vectorstore.name
        vectorsearch_dict["auth_secret_name"] = (
            self.vectorsearch.auth_secret.name if self.vectorsearch.auth_secret else None
        )
        vectorsearch_dict = self.to_camel_case(vectorsearch_dict)
        if not isinstance(vectorsearch_dict, dict):
            raise SAMVectorsearchBrokerError(
                f"Failed to convert {self.kind} {self.vectorsearch.name} to dict", thing=self.kind
            )

        meta = SAMVectorsearchMetadata(
            name=self.vectorsearch.name,
            description=self.vectorsearch.description,
            version=self.vectorsearch.version,
            tags=self.vectorsearch.tags_list,
            annotations=self.vectorsearch.annotations if isinstance(self.vectorsearch.annotations, list) else [],
        )
        spec_config = SAMVectorsearchSpecConfig(**vectorsearch_dict)
        spec = SAMVectorsearchSpec(config=spec_config)
        status = SAMVectorsearchStatus(
            accountNumber=self.account.account_number,
            username=self.user_profile.user.username,
            recordLocator=self.vectorsearch.record_locator,
            created=self.vectorsearch.created_at,
            modified=self.vectorsearch.updated_at,
        )
        model = SAMVectorsearch(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta,
            spec=spec,
            status=status,
        )

        logger.debug(
            "%s.django_orm_to_manifest_dict() converted Vectorsearch %s to manifest dict: %s",
            self.formatted_class_name,
            self.vectorsearch.name,
            model.model_dump(),
        )
        return model.model_dump()

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns a formatted string representing the class name for logging purposes.

        :returns: A string containing the formatted class name, suitable for use in log output.
        :rtype: str
        """
        class_name = f"{SAMVectorsearchBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for the Smarter API Vectorsearch.

        :returns: The manifest kind string for the Smarter API Vectorsearch.
        :rtype: str
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMVectorsearch]:
        """
        Returns the Smarter API Vectorsearch manifest as a Pydantic model.

        The manifest is initialized using data provided by the manifest loader, or, failing that,
        reconstructed from an existing Vectorsearch ORM record via `django_orm_to_manifest_dict()`.
        If the manifest has already been initialized and cached, this method returns the cached
        instance.

        :returns: An instance of ``SAMVectorsearch`` representing the vectorsearch manifest, or
                  ``None`` if the manifest cannot be initialized.
        :rtype: Optional[SAMVectorsearch]
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMVectorsearch):
                raise SAMVectorsearchBrokerError("Cached manifest is not a SAMVectorsearch instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            logger.debug(
                "%s.manifest() initializing %s from SAMLoader with name %s",
                self.formatted_class_name,
                self.kind,
                self.loader.manifest_metadata.get(SAMMetadataKeys.NAME.value, "unknown"),
            )
            self._manifest = SAMVectorsearch(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMVectorsearchMetadata(**self.loader.manifest_metadata),
                spec=SAMVectorsearchSpec(**self.loader.manifest_spec),
            )
            return self._manifest
        if self._vectorsearch:
            self._manifest = self.django_orm_to_manifest_dict()  # type: ignore
            if self._manifest:
                logger.debug(
                    "%s.manifest() initialized from loader for existing Vectorsearch %s with name %s",
                    self.formatted_class_name,
                    self._vectorsearch,
                    self._vectorsearch.name,
                )
                return self._manifest
        else:
            logger.warning(
                "%s.manifest() could not initialize",
                self.formatted_class_name,
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def cache_invalidations(self) -> None:
        """
        Handle broker specific cache invalidation logic.

        We should invalidate any cached objects that are related to the Vectorsearch when any
        mutation occurs. Unlike composite resources such as MCPClient, Vectorsearch has no child
        models of its own, so invalidation here is limited to the Vectorsearch record itself and
        any cached listviews for the owning account.

        :returns: None
        :rtype: None
        """
        logger.debug("%s.cache_invalidations() called.", self.formatted_class_name)

        # 1.) invalidate the Vectorsearch cache itself.
        # -----------------------------
        Vectorsearch.get_cached_object(pk=self.vectorsearch.id, invalidate=True)  # type: ignore

        # 2.) invalidate anything else in which the vectorsearch is part of, e.g. listviews.
        # -----------------------------
        Vectorsearch.get_cached_objects(user_profile=self.user_profile, invalidate=True)

        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[Vectorsearch]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[Vectorsearch]
        """
        return Vectorsearch

    @property
    def ORMModelClass(self) -> Type[Vectorsearch]:
        """
        The Django ORM model class for the Vectorsearch.

        :returns: The Vectorsearch Django ORM model class.
        :rtype: Type[Vectorsearch]
        """
        return Vectorsearch

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for the Smarter API Vectorsearch.

        :returns: A JSON response containing an example Smarter API Vectorsearch manifest.
        :rtype: SmarterJournaledJsonResponse

        See also:

        - :py:class:`smarter.apps.vectorsearch.manifest.models.vectorsearch.SAMVectorsearch`
        - :py:class:`smarter.lib.manifest.enum.SAMKeys`
        - :py:class:`smarter.apps.vectorsearch.manifest.enum.SAMMetadataKeys`
        - :py:class:`smarter.apps.vectorsearch.manifest.enum.SCLIResponseGet`
        - :py:class:`smarter.apps.vectorsearch.manifest.enum.SCLIResponseGetData`
        - :py:class:`from smarter.common.conf.settings_defaults`
        """
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        meta_data = SAMVectorsearchMetadata(
            name="example_vectorsearch",
            description=(
                "This is an example vectorsearch manifest generated by the SAMVectorsearchBroker. "
                "It serves as a template for creating your own vectorsearch manifests."
            ),
            version="1.0.0",
            tags=["example", "template", "rag"],
            annotations=[
                {"color": "blue"},
                {"purpose": "rag-retrieval"},
            ],
        )
        config = SAMVectorsearchSpecConfig(
            vectorstore_name="netflix_writers_embeddings",
            auth_secret_name=None,
            search_type=VectorsearchSearchType.SIMILARITY,
            k=4,
            score_threshold=None,
            fetch_k=None,
            lambda_mult=None,
            metadata_filter={"source": "netflix_writers"},
            is_enabled=True,
        )

        spec = SAMVectorsearchSpec(
            config=config,
        )
        status = SAMVectorsearchStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        model = SAMVectorsearch(
            apiVersion=self.api_version, kind=self.kind, metadata=meta_data, spec=spec, status=status
        )

        return self.json_response_ok(command=command, data=model.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value, None)
        name = self.clean_cli_param(param=name, param_name="name", url=self.smarter_build_absolute_uri(request))

        if self.user_profile is None:
            raise SAMBrokerErrorNotReady("user_profile is not set.")

        # generate a QuerySet of Vectorsearch objects that match our search criteria
        if name:
            vectorsearches = Vectorsearch.objects.filter(user_profile__account=self.account, name=name)
        else:
            vectorsearches = Vectorsearch.objects.filter(user_profile__account=self.account)
        vectorsearches = vectorsearches.with_ownership_permission_for(self.user_profile.user).order_by("name")[
            :MAX_RESULTS
        ]
        logger.debug(
            "%s.get() found %s Vectorsearches for account %s",
            self.formatted_class_name,
            vectorsearches.count(),
            self.account,
        )

        # iterate over the QuerySet and use a serializer to create a model dump for each Vectorsearch
        for vectorsearch in vectorsearches:
            try:
                model_dump = VectorsearchSerializer(vectorsearch).data
                if not model_dump:
                    raise SAMVectorsearchBrokerError(
                        f"Model dump failed for {self.kind} {vectorsearch.name}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.to_camel_case(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                logger.error(
                    "%s.get() failed to serialize %s %s",
                    self.formatted_class_name,
                    self.kind,
                    vectorsearch.name,
                    exc_info=True,
                )
                raise SAMVectorsearchBrokerError(
                    f"Failed to serialize {self.kind} {vectorsearch.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=VectorsearchSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    # pylint: disable=too-many-branches
    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest.

        Copy the manifest data to the Django ORM model and save the model to the database. Note
        that there are fields included in the manifest that are not editable and are therefore
        removed from the Django ORM model dict prior to attempting the save() command. These
        fields are defined in the readonly_fields list.

        `vectorstoreName` and `authSecretName` are resolved to their `vectorstore`/`auth_secret`
        FKs here -- after the flat setattr loop, since neither is a direct column on Vectorsearch
        under those manifest field names -- rather than in `manifest_to_django_orm()`, since
        resolution requires a database lookup scoped to `self.user_profile`.

        .. note::

            tags are handled separately because they are of type TaggableManager and
            require a different method to set them.
        """
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        if not self.ready:
            raise SAMBrokerErrorNotReady(
                f"{self.kind} {self.name} broker is not ready", thing=self.kind, command=command
            )
        if not self.manifest:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if not self.manifest.spec:
            raise SAMBrokerErrorNotReady(
                f"{self.kind} {self.name} manifest spec not found", thing=self.kind, command=command
            )
        if not isinstance(self.vectorsearch, Vectorsearch):
            raise SAMVectorsearchBrokerError(f"Vectorsearch {self.name} not found", thing=self.kind, command=command)
        with transaction.atomic():
            readonly_fields = ["id", "created_at", "updated_at", "tags"]
            try:
                data = self.manifest_to_django_orm()
                tags = data.get("tags", [])
                vectorstore_name = data.pop("vectorstore_name", None)
                auth_secret_name = data.pop("auth_secret_name", None)
                for field in readonly_fields:
                    data.pop(field, None)
                for key, value in data.items():
                    setattr(self.vectorsearch, key, value)
                self.vectorsearch.vectorstore = self.resolve_vectorstore(vectorstore_name)
                self.vectorsearch.auth_secret = self.resolve_auth_secret(auth_secret_name)
                if self.vectorsearch.user_profile != self.user_profile:
                    raise SAMVectorsearchBrokerError(
                        f"User profile mismatch for {self.kind} {self.manifest.metadata.name}",
                        thing=self.kind,
                        command=command,
                    )
                self.vectorsearch.full_clean()
                self.vectorsearch.save()

                # Fix note: occasionally seeing AttributeError: 'list' object has no attribute 'set'
                # in the logs, which is why this is wrapped in a try/except block.
                try:
                    if not isinstance(self.vectorsearch.tags, TaggableManager):
                        logger.warning(
                            "%s.apply() vectorsearch.tags is a list instead of a TaggableManager for %s %s "
                            "owned by %s. This is unexpected and may indicate an issue with the Vectorsearch "
                            "model definition or the database state. Tags=%s",
                            self.formatted_class_name,
                            self.kind,
                            self.manifest.metadata.name,
                            self.user_profile,
                            tags,
                        )
                    else:
                        self.vectorsearch.tags.set(tags)
                # pylint: disable=broad-except
                except Exception as e:
                    logger.error(
                        "%s.apply() failed to set tags for %s %s owned by %s. Tags=%s. Error: %s",
                        self.formatted_class_name,
                        self.kind,
                        self.manifest.metadata.name,
                        self.user_profile,
                        tags,
                        e,
                        exc_info=True,
                    )
                self.vectorsearch.refresh_from_db()
            except Exception as e:
                logger.error(
                    "%s.apply() failed to save %s %s owned by %s. Error: %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                    self.user_profile,
                    e,
                    exc_info=True,
                )
                raise SAMVectorsearchBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}", thing=self.kind, command=command
                ) from e

            # done! return the response. Django will take care of committing the transaction
            self.cache_invalidations()
            return self.json_response_ok(command=command, data=self.to_json())

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.prompt.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} name property is not set.", thing=self.kind, command=command)
        if self.vectorsearch:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                logger.error(
                    "%s.describe() failed to describe %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.name,
                    exc_info=True,
                )
                raise SAMVectorsearchBrokerError(
                    f"Failed to describe {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if self.vectorsearch:
            try:
                self.vectorsearch.delete()
                self.cache_invalidations()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                logger.error(
                    "%s.delete() failed to delete %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.name,
                    exc_info=True,
                )
                raise SAMVectorsearchBrokerError(
                    f"Failed to delete {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerError(f"{self.kind} {self.name} deploy() is not implemented.", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerError(
            f"{self.kind} {self.name} undeploy() is not implemented.", thing=self.kind, command=command
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
