# pylint: disable=W0718,C0302
"""Smarter API Guardrail Manifest handler."""

import datetime
from typing import Optional, Type

from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer
from taggit.managers import TaggableManager

from smarter.apps.account.utils import (
    smarter_cached_objects,
    valid_resource_owners_for_user,
)
from smarter.apps.guardrail.manifest.models.guardrail.const import MANIFEST_KIND
from smarter.apps.guardrail.manifest.models.guardrail.metadata import (
    SAMGuardrailMetadata,
)
from smarter.apps.guardrail.manifest.models.guardrail.model import SAMGuardrail
from smarter.apps.guardrail.manifest.models.guardrail.spec import (
    SAMGuardrailSpec,
    SAMGuardrailSpecConfig,
)
from smarter.apps.guardrail.manifest.models.guardrail.status import SAMGuardrailStatus
from smarter.apps.guardrail.models import (
    Guardrail,
)
from smarter.apps.guardrail.models.guardail import (
    GuardrailAction,
    GuardrailCategory,
    GuardrailType,
    MatchStrategy,
)
from smarter.apps.plugin.signals import broker_ready
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
    __name__, any_switches=[SmarterWaffleSwitches.GUARDRAIL_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000


class SAMGuardrailBrokerError(SAMBrokerError):
    """Base exception for Smarter API Guardrail Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Guardrail Manifest Broker Error"


class GuardrailSerializer(ModelSerializer):
    """Django ORM model serializer for get()."""

    # pylint: disable=C0115
    class Meta:
        model = Guardrail
        fields = ["__all__"]


class SAMGuardrailBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` Guardrail manifests.

    This class provides a high-level abstraction for managing guardrail manifests
    within the Smarter platform. It acts as the central coordinator for the
    lifecycle of guardrail manifests, bridging the gap between declarative YAML
    files and persistent application state.

    The broker is responsible for:

    - Managing the lifecycle of guardrail manifests, including loading, validation,
      and parsing of YAML files.
    - Initializing Pydantic models from manifest data to ensure robust schema
      validation and serialization.
    - Integrating with Django ORM models that represent guardrail manifests,
      supporting creation, update, deletion, and querying of database records.
    - Transforming data between Django ORM models and Pydantic models to enable
      seamless conversion between database and API representations.
    - Coordinating composite models, such as Guardrail, GuardrailAPIKey,
      GuardrailPlugin, and GuardrailFunctions, to ensure all components of an guardrail
      are synchronized according to the manifest specification.
    - Ensuring atomic and consistent application of changes using Django's
      transaction management.
    - Providing detailed logging and error handling integrated with the Smarter
      platform's diagnostics systems.

    This broker is a key component in the deployment, configuration, and
    lifecycle management of guardrails in the Smarter Framework.
    """

    # override the base abstract manifest model with the Guardrail model
    _manifest: Optional[SAMGuardrail] = None
    _pydantic_model: Type[SAMGuardrail] = SAMGuardrail
    _guardrail: Optional[Guardrail] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        logger.info(msg)

    @property
    def SerializerClass(self) -> Type[GuardrailSerializer]:
        """
        The Django ORM model serializer class for the Guardrail.

        :returns: The Guardrail Django ORM model serializer class.
        :rtype: Type[ModelSerializer]
        """
        return GuardrailSerializer

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
    def guardrail(self) -> Optional[Guardrail]:
        """
        Provides access to the Django ORM model instance representing the current Smarter Guardrail.

        This property retrieves the Guardrail object associated with the broker's account and name.
        If a matching Guardrail record exists in the database, it is returned and cached for future access.
        If no such record exists, and a manifest is available, a new Guardrail instance is created using
        data extracted from the manifest and then persisted to the database.

        This property ensures that the broker always has access to a valid Guardrail model, either by
        fetching an existing record or by creating one from the manifest specification. The Guardrail
        model stores the configuration and runtime state of the guardrail, and is used for all database
        operations related to the guardrail's lifecycle.

        :returns: The Django ORM Guardrail instance if found or created, otherwise ``None`` if neither
                  a database record nor a manifest is available.
        :rtype: Optional[Guardrail]

        .. note::

            The returned Guardrail object is essential for linking related resources such as API keys,
            plugins, and functions, and for performing updates or queries on the guardrail's state.

        .. admonition:: FIX NOTE

            This should be refactored/removed in favor of orm_instance. There is no logic
            in this property that merits it overriding the parent orm_instance property.

        .. admonition:: FIX NOTE

            This is breaking an unwritten rule of Smarter resources in that it is
            lazily **creating** a database record on a property getter.
            Creating/updating database records should be handled in apply().
        """
        if self._guardrail:
            return self._guardrail

        try:
            self._guardrail = Guardrail.get_cached_object(
                invalidate=True, user_profile=self.user_profile, name=self.name
            )  # type: ignore
            logger.debug(
                "%s.guardrail() retrieved existing Guardrail instance %s owned by %s from database.",
                self.formatted_class_name,
                self._guardrail,
                self.user_profile,
            )
            return self._guardrail
        except Guardrail.DoesNotExist:
            self._guardrail = None

        logger.debug(
            "%s.guardrail() Guardrail instance not found for user_profile %s. Attempting to create a new instance.",
            self.formatted_class_name,
            self.user_profile,
        )
        if self.manifest:
            data = self.manifest_to_django_orm()
            data["user_profile"] = self.user_profile
            logger.debug("%s.guardrail() Creating new Guardrail with data: %s", self.formatted_class_name, data)
            tags = data.pop("tags", [])
            self._guardrail = Guardrail.objects.create(**data)
            if self._guardrail and tags:
                self._guardrail.tags.set(tags)
            self._created = True
            logger.warning(
                "%s.guardrail() lazily created new Guardrail instance %s owned by %s. This logic should be handled in apply().",
                self.formatted_class_name,
                self._guardrail,
                self.user_profile,
            )
        else:
            logger.warning(
                "%s.guardrail() %s not found for user_profile %s",
                self.formatted_class_name,
                self._guardrail,
                self.user_profile,
            )

        return self._guardrail

    def manifest_to_django_orm(self) -> dict:
        """
        Convert the Smarter API Guardrail manifest into a dictionary suitable for creating or updating a Django ORM Guardrail model.

        This method extracts all relevant configuration, metadata, and versioning information from the loaded manifest
        and transforms it into a dictionary format compatible with Django ORM operations. The manifest's configuration
        is first dumped and converted from camelCase to snake_case to match Django's field naming conventions.

        The resulting dictionary includes the account, name, description, and version fields from the manifest metadata,
        as well as all configuration fields from the manifest specification. This dictionary can be used to instantiate
        or update a Guardrail ORM model instance in the database.

        If the manifest is not loaded or is invalid, an exception is raised to indicate that the broker is not ready
        to perform the transformation.

        :returns: A dictionary containing all fields required to create or update a Django ORM Guardrail model.
        :rtype: dict

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded or cannot be found.
        :raises SAMGuardrailBrokerError: If the manifest configuration cannot be converted to a dictionary.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"Manifest not loaded for {self.kind} broker. Cannot convert to Django ORM.", thing=self.kind
            )
        metadata = super().manifest_to_django_orm()

        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.to_snake_case(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMGuardrailBrokerError(
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
        Transform the Django ORM Guardrail model instance into a dictionary compatible with the Smarter API Guardrail manifest format.

        This method converts the current Guardrail ORM model and its related resources (plugins, functions, API key)
        into a dictionary structure that matches the expected schema for a Pydantic manifest. The conversion includes
        renaming fields from snake_case to camelCase, removing internal-only fields, and assembling metadata, spec,
        and status sections as required by the manifest.

        The resulting dictionary contains all configuration, metadata, plugin, function, and status information
        necessary to reconstruct the manifest for the guardrail. This enables seamless round-trip conversion between
        database state and manifest representation.

        If the Guardrail model is not available, the method logs a warning and returns ``None``. If the conversion
        fails, an exception is raised to indicate the error.

        :returns: A dictionary representing the Smarter API Guardrail manifest, or ``None`` if the Guardrail model is not set.
        :rtype: Optional[dict]

        :raises SAMGuardrailBrokerError: If the ORM model cannot be converted to a manifest dictionary.

        See also:

        - :py:meth:`smarter.apps.guardrail.manifest.brokers.guardrail.SAMGuardrailBroker.manifest_to_django_orm`
        - :py:class:`smarter.apps.guardrail.manifest.models.guardrail.SAMGuardrail`
        - :py:class:`smarter.apps.guardrail.manifest.models.guardrail.metadata.SAMGuardrailMetadata`
        - :py:class:`smarter.apps.guardrail.manifest.models.guardrail.spec.SAMGuardrailSpec`
        - :py:class:`smarter.apps.guardrail.manifest.models.guardrail.status.SAMGuardrailStatus`
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
        if not self.guardrail:
            logger.warning(
                "%s.django_orm_to_manifest_dict() called without a Guardrail. This could affect broker operations.",
                self.formatted_class_name,
            )
            return None
        guardrail_dict = model_to_dict(self.guardrail)
        guardrail_dict = self.to_camel_case(guardrail_dict)
        if not isinstance(guardrail_dict, dict):
            raise SAMGuardrailBrokerError(
                f"Failed to convert {self.kind} {self.guardrail.name} to dict", thing=self.kind
            )
        guardrail_dict.pop("id")
        guardrail_dict.pop("name")
        guardrail_dict.pop("description")
        guardrail_dict.pop("version")

        meta = SAMGuardrailMetadata(
            name=self.guardrail.name,
            description=self.guardrail.description,
            version=self.guardrail.version,
            tags=self.guardrail.tags_list,
            annotations=self.guardrail.annotations if isinstance(self.guardrail.annotations, list) else [],
        )
        spec_config = SAMGuardrailSpecConfig(**guardrail_dict)
        spec = SAMGuardrailSpec(config=spec_config)
        status = SAMGuardrailStatus(
            accountNumber=self.account.account_number,
            username=self.user_profile.user.username,
            recordLocator=self.guardrail.record_locator,
            created=self.guardrail.created_at,
            modified=self.guardrail.updated_at,
        )
        model = SAMGuardrail(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta,
            spec=spec,
            status=status,
        )

        logger.debug(
            "%s.django_orm_to_manifest_dict() converted Guardrail %s to manifest dict: %s",
            self.formatted_class_name,
            self.guardrail.name,
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

        This property generates a human-readable class name that is used to improve the clarity
        and consistency of log messages throughout the broker. The formatted class name includes
        the parent class name and appends the specific broker class identifier, making it easier
        to trace log entries back to their source within the codebase.

        The formatted class name is especially useful in environments where multiple brokers or
        components are active, as it helps distinguish log messages and aids in debugging and
        monitoring application behavior.

        :returns: A string containing the formatted class name, suitable for use in log output.
        :rtype: str
        """
        class_name = f"{SAMGuardrailBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for the Smarter API Guardrail.

        This property provides the specific kind identifier used to classify the Smarter API Guardrail
        manifest within the Smarter platform. The kind is a key component of the manifest schema,
        allowing the system to recognize and process guardrail manifests appropriately. The kind value is defined as a constant in the guardrail manifest model
        and is used throughout the broker to ensure consistency when handling guardrail manifests.

        :returns: The manifest kind string for the Smarter API Guardrail.
        :rtype: str

        .. important::

            The kind property is essential for manifest validation, routing, and processing within
            the Smarter platform.
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMGuardrail]:
        """
        Returns the Smarter API Guardrail manifest as a Pydantic model.

        This method constructs and returns an instance of the ``SAMGuardrail`` Pydantic model,
        which represents the full manifest for a Smarter API Guardrail. The manifest contains
        all configuration, metadata, and specification details required to describe and deploy
        an guardrail within the Smarter platform.

        The manifest is initialized using data provided by the manifest loader. The loader
        supplies the manifest's API version, kind, metadata, and specification, which are
        passed to the respective fields of the ``SAMGuardrail`` model. The metadata and spec
        fields are themselves Pydantic models (``SAMGuardrailMetadata`` and ``SAMGuardrailSpec``),
        and are recursively initialized with their corresponding data.

        Unlike child models, which are automatically cascade-initialized by Pydantic when
        constructing the parent model, the top-level manifest model must be explicitly
        instantiated in this method. This ensures that all manifest data is validated and
        structured according to the schema defined by the ``SAMGuardrail`` model.

        If the manifest has already been initialized and cached, this method returns the
        cached instance. If the loader is present and its manifest kind matches the expected
        kind, a new manifest instance is created and cached before returning.

        :returns: An instance of ``SAMGuardrail`` representing the guardrail manifest, or ``None``
                if the manifest cannot be initialized.
        :rtype: Optional[SAMGuardrail]
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMGuardrail):
                raise SAMGuardrailBrokerError("Cached manifest is not a SAMGuardrail instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            logger.debug(
                "%s.manifest() initializing %s from SAMLoader with name %s",
                self.formatted_class_name,
                self.kind,
                self.loader.manifest_metadata.get(SAMMetadataKeys.NAME.value, "unknown"),
            )
            self._manifest = SAMGuardrail(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMGuardrailMetadata(**self.loader.manifest_metadata),
                spec=SAMGuardrailSpec(**self.loader.manifest_spec),
            )
            return self._manifest
        if self._guardrail:
            self._manifest = self.django_orm_to_manifest_dict()  # type: ignore
            if self._manifest:
                logger.debug(
                    "%s.manifest() initialized from loader for existing Guardrail %s with name %s",
                    self.formatted_class_name,
                    self._guardrail,
                    self._guardrail.name,
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

        We should invalidate
        any cached objects that are related to the Guardrail when any mutation
        occurs. In this case, we need to invalidate the Guardrail cache itself,
        but also any related objects such as the plugins, functions and
        api keys.

        .. returns: None
        .. rtype: None
        """
        logger.debug("%s.cache_invalidations() called.", self.formatted_class_name_cache_invalidations)

        # 1.) invalidate the Guardrail cache itself.
        # -----------------------------
        Guardrail.get_cached_object(pk=self.guardrail.id, invalidate=True)  # type: ignore

        # 2.) invalidate anything else in which the guardrail is part of. this could
        # include listviews, the plugins, functions and api keys.
        # -----------------------------
        Guardrail.get_cached_objects(user_profile=self.user_profile, invalidate=True)

        # 3.) invalidate all children of Guardrail
        # -----------------------------

        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[Guardrail]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[Guardrail]
        """
        return Guardrail

    @property
    def ORMModelClass(self) -> Type[Guardrail]:
        """
        The Django ORM model class for the Guardrail.

        :returns: The Guardrail Django ORM model class.
        :rtype: Type[Guardrail]
        """
        return Guardrail

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for the Smarter API Guardrail.

        :returns: A JSON response containing an example Smarter API Guardrail manifest.
        :rtype: SmarterJournaledJsonResponse

        See also:

        - :py:class:`smarter.apps.guardrail.manifest.models.guardrail.SAMGuardrail`
        - :py:class:`smarter.lib.manifest.enumSAMKeys`
        - :py:class:`smarter.apps.guardrail.manifest.enum.SAMMetadataKeys`
        - :py:class:`smarter.apps.guardrail.manifest.enum.SCLIResponseGet`
        - :py:class:`smarter.apps.guardrail.manifest.enum.SCLIResponseGetData`
        - :py:class:`from smarter.common.conf.settings_defaults`
        """

        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        meta_data = SAMGuardrailMetadata(
            name="example_guardrail",
            description="This is an example guardrail manifest generated by the SAMGuardrailBroker. It serves as a template for creating your own guardrail manifests.",
            version="1.0.0",
            tags=["example", "template", "school-project"],
            annotations=[
                {"color": "red"},
                {"size": "medium"},
                {"hash": "sha256:abc123def456"},
            ],
        )
        config = SAMGuardrailSpecConfig(
            guardrail_type=GuardrailType.OUTPUT,
            category=GuardrailCategory.JAILBREAK,
            match_strategy=MatchStrategy.REGEX,
            pattern="",
            config={},
            action=GuardrailAction.ESCALATE,
            severity=2,
            confidence_threshold=1,
            is_active=True,
            is_blocking=True,
            priority=100,
            fallback_message="help",
        )

        spec = SAMGuardrailSpec(
            config=config,
        )
        status = SAMGuardrailStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        model = SAMGuardrail(apiVersion=self.api_version, kind=self.kind, metadata=meta_data, spec=spec, status=status)

        return self.json_response_ok(command=command, data=model.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value, None)
        name = self.clean_cli_param(param=name, param_name="name", url=self.smarter_build_absolute_uri(request))

        # generate a QuerySet of PluginMeta objects that match our search criteria
        if name:
            guardrails = Guardrail.objects.filter(user_profile__account=self.account, name=name)
        else:
            guardrails = Guardrail.objects.filter(user_profile__account=self.account)
        valid_owners = valid_resource_owners_for_user(user_profile=self.user_profile)
        guardrails = guardrails.filter(user_profile__in=valid_owners).order_by("name")[:MAX_RESULTS]
        logger.debug(
            "%s.get() found %s Guardrails for account %s", self.formatted_class_name, guardrails.count(), self.account
        )

        # iterate over the QuerySet and use a serializer to create a model dump for each Guardrail
        for guardrail in guardrails:
            try:
                model_dump = GuardrailSerializer(guardrail).data
                if not model_dump:
                    raise SAMGuardrailBrokerError(
                        f"Model dump failed for {self.kind} {guardrail.name}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.to_camel_case(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                logger.error(
                    "%s.get() failed to serialize %s %s",
                    self.formatted_class_name,
                    self.kind,
                    guardrail.name,
                    exc_info=True,
                )
                raise SAMGuardrailBrokerError(
                    f"Failed to serialize {self.kind} {guardrail.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=GuardrailSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    # pylint: disable=too-many-branches
    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest.

        copy the manifest data to the Django ORM model and
        save the model to the database. Note that there are fields included in the
        manifest that are not editable
        and are therefore removed from the Django ORM model dict prior to attempting
        the save() command. These fields are defined in the readonly_fields list.

        Guardrail is a composite model that includes the Guardrail, GuardrailAPIKey,
        GuardrailPlugin and GuardrailFunctions models. All of these are represented
        in the manifest spec and are created or updated as needed.

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
        if not isinstance(self.guardrail, Guardrail):
            raise SAMGuardrailBrokerError(f"Guardrail {self.name} not found", thing=self.kind, command=command)
        with transaction.atomic():
            readonly_fields = ["id", "created_at", "updated_at", "tags"]
            try:
                data = self.manifest_to_django_orm()
                tags = data.get("tags", [])
                for field in readonly_fields:
                    data.pop(field, None)
                for key, value in data.items():
                    setattr(self.guardrail, key, value)
                if self.guardrail.user_profile != self.user_profile:
                    raise SAMGuardrailBrokerError(
                        f"User profile mismatch for {self.kind} {self.manifest.metadata.name}",
                        thing=self.kind,
                        command=command,
                    )
                self.guardrail.save()

                # Fix note: occasionally seeing AttributeError: \'list\' object has no attribute \'set\ in the logs,
                # which is why this is wrapped in a try/except block.
                try:
                    if not isinstance(self.guardrail.tags, TaggableManager):
                        logger.warning(
                            "%s.apply() guardrail.tags is a list instead of a TaggableManager for %s %s owned by %s. This is unexpected and may indicate an issue with the Guardrail model definition or the database state. Tags=%s",
                            self.formatted_class_name,
                            self.kind,
                            self.manifest.metadata.name,
                            self.user_profile,
                            tags,
                        )
                    else:
                        self.guardrail.tags.set(tags)
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
                self.guardrail.refresh_from_db()
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
                raise SAMGuardrailBrokerError(
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
        if self.guardrail:
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
                raise SAMGuardrailBrokerError(
                    f"Failed to describe {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if self.guardrail:
            try:
                self.guardrail.delete()
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
                raise SAMGuardrailBrokerError(
                    f"Failed to delete {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise NotImplementedError(
            f"{self.kind} {self.name} deploy() is not implemented.", thing=self.kind, command=command
        )

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise NotImplementedError(
            f"{self.kind} {self.name} undeploy() is not implemented.", thing=self.kind, command=command
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
