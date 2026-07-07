# pylint: disable=W0718,C0302
"""Smarter API MCPClient Manifest handler."""

import datetime
from typing import Optional, Type

from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer
from taggit.managers import TaggableManager

from smarter.apps.account.utils import smarter_cached_objects
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
from smarter.apps.mcpclient.models import (
    MCPAuthType,
    MCPClient,
    MCPTransport,
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
    __name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000


class SAMMCPClientBrokerError(SAMBrokerError):
    """Base exception for Smarter API MCPClient Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API MCPClient Manifest Broker Error"


class MCPClientSerializer(ModelSerializer):
    """Django ORM model serializer for get()."""

    # pylint: disable=C0115
    class Meta:
        model = MCPClient
        fields = ["__all__"]


class SAMMCPClientBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` MCPClient manifests.

    This class provides a high-level abstraction for managing mcpclient manifests
    within the Smarter platform. It acts as the central coordinator for the
    lifecycle of mcpclient manifests, bridging the gap between declarative YAML
    files and persistent application state.

    The broker is responsible for:

    - Managing the lifecycle of mcpclient manifests, including loading, validation,
      and parsing of YAML files.
    - Initializing Pydantic models from manifest data to ensure robust schema
      validation and serialization.
    - Integrating with Django ORM models that represent mcpclient manifests,
      supporting creation, update, deletion, and querying of database records.
    - Transforming data between Django ORM models and Pydantic models to enable
      seamless conversion between database and API representations.
    - Coordinating composite models, such as MCPClient, MCPClientAPIKey,
      MCPClientPlugin, and MCPClientFunctions, to ensure all components of an mcpclient
      are synchronized according to the manifest specification.
    - Ensuring atomic and consistent application of changes using Django's
      transaction management.
    - Providing detailed logging and error handling integrated with the Smarter
      platform's diagnostics systems.

    This broker is a key component in the deployment, configuration, and
    lifecycle management of mcpclients in the Smarter Framework.
    """

    # override the base abstract manifest model with the MCPClient model
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
    def SerializerClass(self) -> Type[MCPClientSerializer]:
        """
        The Django ORM model serializer class for the MCPClient.

        :returns: The MCPClient Django ORM model serializer class.
        :rtype: Type[ModelSerializer]
        """
        return MCPClientSerializer

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
    def mcpclient(self) -> Optional[MCPClient]:
        """
        Provides access to the Django ORM model instance representing the current Smarter MCPClient.

        This property retrieves the MCPClient object associated with the broker's account and name.
        If a matching MCPClient record exists in the database, it is returned and cached for future access.
        If no such record exists, and a manifest is available, a new MCPClient instance is created using
        data extracted from the manifest and then persisted to the database.

        This property ensures that the broker always has access to a valid MCPClient model, either by
        fetching an existing record or by creating one from the manifest specification. The MCPClient
        model stores the configuration and runtime state of the mcpclient, and is used for all database
        operations related to the mcpclient's lifecycle.

        :returns: The Django ORM MCPClient instance if found or created, otherwise ``None`` if neither
                  a database record nor a manifest is available.
        :rtype: Optional[MCPClient]

        .. note::

            The returned MCPClient object is essential for linking related resources such as API keys,
            plugins, and functions, and for performing updates or queries on the mcpclient's state.

        .. admonition:: FIX NOTE

            This should be refactored/removed in favor of orm_instance. There is no logic
            in this property that merits it overriding the parent orm_instance property.

        .. admonition:: FIX NOTE

            This is breaking an unwritten rule of Smarter resources in that it is
            lazily **creating** a database record on a property getter.
            Creating/updating database records should be handled in apply().
        """
        if self._mcpclient:
            return self._mcpclient

        try:
            self._mcpclient = MCPClient.get_cached_object(
                invalidate=True, user_profile=self.user_profile, name=self.name
            )  # type: ignore
            logger.debug(
                "%s.mcpclient() retrieved existing MCPClient instance %s owned by %s from database.",
                self.formatted_class_name,
                self._mcpclient,
                self.user_profile,
            )
            return self._mcpclient
        except MCPClient.DoesNotExist:
            self._mcpclient = None

        logger.debug(
            "%s.mcpclient() MCPClient instance not found for user_profile %s. Attempting to create a new instance.",
            self.formatted_class_name,
            self.user_profile,
        )
        if self.manifest:
            data = self.manifest_to_django_orm()
            data["user_profile"] = self.user_profile
            logger.debug("%s.mcpclient() Creating new MCPClient with data: %s", self.formatted_class_name, data)
            tags = data.pop("tags", [])
            self._mcpclient = MCPClient.objects.create(**data)
            if self._mcpclient and tags:
                self._mcpclient.tags.set(tags)
            self._created = True
            logger.warning(
                "%s.mcpclient() lazily created new MCPClient instance %s owned by %s. This logic should be handled in apply().",
                self.formatted_class_name,
                self._mcpclient,
                self.user_profile,
            )
        else:
            logger.warning(
                "%s.mcpclient() %s not found for user_profile %s",
                self.formatted_class_name,
                self._mcpclient,
                self.user_profile,
            )

        return self._mcpclient

    def manifest_to_django_orm(self) -> dict:
        """
        Convert the Smarter API MCPClient manifest into a dictionary suitable for creating or updating a Django ORM MCPClient model.

        This method extracts all relevant configuration, metadata, and versioning information from the loaded manifest
        and transforms it into a dictionary format compatible with Django ORM operations. The manifest's configuration
        is first dumped and converted from camelCase to snake_case to match Django's field naming conventions.

        The resulting dictionary includes the account, name, description, and version fields from the manifest metadata,
        as well as all configuration fields from the manifest specification. This dictionary can be used to instantiate
        or update a MCPClient ORM model instance in the database.

        If the manifest is not loaded or is invalid, an exception is raised to indicate that the broker is not ready
        to perform the transformation.

        :returns: A dictionary containing all fields required to create or update a Django ORM MCPClient model.
        :rtype: dict

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded or cannot be found.
        :raises SAMMCPClientBrokerError: If the manifest configuration cannot be converted to a dictionary.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"Manifest not loaded for {self.kind} broker. Cannot convert to Django ORM.", thing=self.kind
            )
        metadata = super().manifest_to_django_orm()

        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.to_snake_case(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMMCPClientBrokerError(
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
        Transform the Django ORM MCPClient model instance into a dictionary compatible with the Smarter API MCPClient manifest format.

        This method converts the current MCPClient ORM model and its related resources (plugins, functions, API key)
        into a dictionary structure that matches the expected schema for a Pydantic manifest. The conversion includes
        renaming fields from snake_case to camelCase, removing internal-only fields, and assembling metadata, spec,
        and status sections as required by the manifest.

        The resulting dictionary contains all configuration, metadata, plugin, function, and status information
        necessary to reconstruct the manifest for the mcpclient. This enables seamless round-trip conversion between
        database state and manifest representation.

        If the MCPClient model is not available, the method logs a warning and returns ``None``. If the conversion
        fails, an exception is raised to indicate the error.

        :returns: A dictionary representing the Smarter API MCPClient manifest, or ``None`` if the MCPClient model is not set.
        :rtype: Optional[dict]

        :raises SAMMCPClientBrokerError: If the ORM model cannot be converted to a manifest dictionary.

        See also:

        - :py:meth:`smarter.apps.mcpclient.manifest.brokers.mcpclient.SAMMCPClientBroker.manifest_to_django_orm`
        - :py:class:`smarter.apps.mcpclient.manifest.models.mcpclient.SAMMCPClient`
        - :py:class:`smarter.apps.mcpclient.manifest.models.mcpclient.metadata.SAMMCPClientMetadata`
        - :py:class:`smarter.apps.mcpclient.manifest.models.mcpclient.spec.SAMMCPClientSpec`
        - :py:class:`smarter.apps.mcpclient.manifest.models.mcpclient.status.SAMMCPClientStatus`
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
        if not self.mcpclient:
            logger.warning(
                "%s.django_orm_to_manifest_dict() called without a MCPClient. This could affect broker operations.",
                self.formatted_class_name,
            )
            return None
        mcpclient_dict = model_to_dict(self.mcpclient)
        mcpclient_dict = self.to_camel_case(mcpclient_dict)
        if not isinstance(mcpclient_dict, dict):
            raise SAMMCPClientBrokerError(
                f"Failed to convert {self.kind} {self.mcpclient.name} to dict", thing=self.kind
            )
        mcpclient_dict.pop("id")
        mcpclient_dict.pop("name")
        mcpclient_dict.pop("description")
        mcpclient_dict.pop("version")

        meta = SAMMCPClientMetadata(
            name=self.mcpclient.name,
            description=self.mcpclient.description,
            version=self.mcpclient.version,
            tags=self.mcpclient.tags_list,
            annotations=self.mcpclient.annotations if isinstance(self.mcpclient.annotations, list) else [],
        )
        spec_config = SAMMCPClientSpecConfig(**mcpclient_dict)
        spec = SAMMCPClientSpec(config=spec_config)
        status = SAMMCPClientStatus(
            accountNumber=self.account.account_number,
            username=self.user_profile.user.username,
            recordLocator=self.mcpclient.record_locator,
            created=self.mcpclient.created_at,
            modified=self.mcpclient.updated_at,
        )
        model = SAMMCPClient(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta,
            spec=spec,
            status=status,
        )

        logger.debug(
            "%s.django_orm_to_manifest_dict() converted MCPClient %s to manifest dict: %s",
            self.formatted_class_name,
            self.mcpclient.name,
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
        class_name = f"{SAMMCPClientBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for the Smarter API MCPClient.

        This property provides the specific kind identifier used to classify the Smarter API MCPClient
        manifest within the Smarter platform. The kind is a key component of the manifest schema,
        allowing the system to recognize and process mcpclient manifests appropriately. The kind value is defined as a constant in the mcpclient manifest model
        and is used throughout the broker to ensure consistency when handling mcpclient manifests.

        :returns: The manifest kind string for the Smarter API MCPClient.
        :rtype: str

        .. important::

            The kind property is essential for manifest validation, routing, and processing within
            the Smarter platform.
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMMCPClient]:
        """
        Returns the Smarter API MCPClient manifest as a Pydantic model.

        This method constructs and returns an instance of the ``SAMMCPClient`` Pydantic model,
        which represents the full manifest for a Smarter API MCPClient. The manifest contains
        all configuration, metadata, and specification details required to describe and deploy
        an mcpclient within the Smarter platform.

        The manifest is initialized using data provided by the manifest loader. The loader
        supplies the manifest's API version, kind, metadata, and specification, which are
        passed to the respective fields of the ``SAMMCPClient`` model. The metadata and spec
        fields are themselves Pydantic models (``SAMMCPClientMetadata`` and ``SAMMCPClientSpec``),
        and are recursively initialized with their corresponding data.

        Unlike child models, which are automatically cascade-initialized by Pydantic when
        constructing the parent model, the top-level manifest model must be explicitly
        instantiated in this method. This ensures that all manifest data is validated and
        structured according to the schema defined by the ``SAMMCPClient`` model.

        If the manifest has already been initialized and cached, this method returns the
        cached instance. If the loader is present and its manifest kind matches the expected
        kind, a new manifest instance is created and cached before returning.

        :returns: An instance of ``SAMMCPClient`` representing the mcpclient manifest, or ``None``
                if the manifest cannot be initialized.
        :rtype: Optional[SAMMCPClient]
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMMCPClient):
                raise SAMMCPClientBrokerError("Cached manifest is not a SAMMCPClient instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            logger.debug(
                "%s.manifest() initializing %s from SAMLoader with name %s",
                self.formatted_class_name,
                self.kind,
                self.loader.manifest_metadata.get(SAMMetadataKeys.NAME.value, "unknown"),
            )
            self._manifest = SAMMCPClient(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMMCPClientMetadata(**self.loader.manifest_metadata),
                spec=SAMMCPClientSpec(**self.loader.manifest_spec),
            )
            return self._manifest
        if self._mcpclient:
            self._manifest = self.django_orm_to_manifest_dict()  # type: ignore
            if self._manifest:
                logger.debug(
                    "%s.manifest() initialized from loader for existing MCPClient %s with name %s",
                    self.formatted_class_name,
                    self._mcpclient,
                    self._mcpclient.name,
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
        any cached objects that are related to the MCPClient when any mutation
        occurs. In this case, we need to invalidate the MCPClient cache itself,
        but also any related objects such as the plugins, functions and
        api keys.

        .. returns: None
        .. rtype: None
        """
        logger.debug("%s.cache_invalidations() called.", self.formatted_class_name_cache_invalidations)

        # 1.) invalidate the MCPClient cache itself.
        # -----------------------------
        MCPClient.get_cached_object(pk=self.mcpclient.id, invalidate=True)  # type: ignore

        # 2.) invalidate anything else in which the mcpclient is part of. this could
        # include listviews, the plugins, functions and api keys.
        # -----------------------------
        MCPClient.get_cached_objects(user_profile=self.user_profile, invalidate=True)

        # 3.) invalidate all children of MCPClient
        # -----------------------------

        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[MCPClient]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[MCPClient]
        """
        return MCPClient

    @property
    def ORMModelClass(self) -> Type[MCPClient]:
        """
        The Django ORM model class for the MCPClient.

        :returns: The MCPClient Django ORM model class.
        :rtype: Type[MCPClient]
        """
        return MCPClient

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for the Smarter API MCPClient.

        :returns: A JSON response containing an example Smarter API MCPClient manifest.
        :rtype: SmarterJournaledJsonResponse

        See also:

        - :py:class:`smarter.apps.mcpclient.manifest.models.mcpclient.SAMMCPClient`
        - :py:class:`smarter.lib.manifest.enumSAMKeys`
        - :py:class:`smarter.apps.mcpclient.manifest.enum.SAMMetadataKeys`
        - :py:class:`smarter.apps.mcpclient.manifest.enum.SCLIResponseGet`
        - :py:class:`smarter.apps.mcpclient.manifest.enum.SCLIResponseGetData`
        - :py:class:`from smarter.common.conf.settings_defaults`
        """

        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        meta_data = SAMMCPClientMetadata(
            name="example_mcpclient",
            description="This is an example mcpclient manifest generated by the SAMMCPClientBroker. It serves as a template for creating your own mcpclient manifests.",
            version="1.0.0",
            tags=["example", "template", "school-project"],
            annotations=[
                {"color": "red"},
                {"size": "medium"},
                {"hash": "sha256:abc123def456"},
            ],
        )
        config = SAMMCPClientSpecConfig(
            transport=MCPTransport.HTTP,
            endpoint_url="https://mcp.example.com/v1",
            command="",
            config={
                "headers": {"X-Client-Id": "smarter-harness"},
                "timeout_s": 30,
                "retry_policy": {"max_attempts": 3, "backoff_s": 2},
            },
            auth_type=MCPAuthType.API_KEY,
            credentials="mcp-example-api-key",
            allowed_tools=["search_docs", "create_ticket"],
            allowed_resources=["docs://example.com/*"],
            is_active=True,
            priority=100,
        )

        spec = SAMMCPClientSpec(
            config=config,
        )
        status = SAMMCPClientStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
        )
        model = SAMMCPClient(apiVersion=self.api_version, kind=self.kind, metadata=meta_data, spec=spec, status=status)

        return self.json_response_ok(command=command, data=model.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value, None)
        name = self.clean_cli_param(param=name, param_name="name", url=self.smarter_build_absolute_uri(request))

        if self.user_profile is None:
            raise SAMBrokerErrorNotReady("user_profile is not set.")

        # generate a QuerySet of PluginMeta objects that match our search criteria
        if name:
            mcpclients = MCPClient.objects.filter(user_profile__account=self.account, name=name)
        else:
            mcpclients = MCPClient.objects.filter(user_profile__account=self.account)
        mcpclients = mcpclients.with_ownership_permission_for(self.user_profile.user).order_by("name")[:MAX_RESULTS]
        logger.debug(
            "%s.get() found %s MCPClients for account %s", self.formatted_class_name, mcpclients.count(), self.account
        )

        # iterate over the QuerySet and use a serializer to create a model dump for each MCPClient
        for mcpclient in mcpclients:
            try:
                model_dump = MCPClientSerializer(mcpclient).data
                if not model_dump:
                    raise SAMMCPClientBrokerError(
                        f"Model dump failed for {self.kind} {mcpclient.name}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.to_camel_case(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                logger.error(
                    "%s.get() failed to serialize %s %s",
                    self.formatted_class_name,
                    self.kind,
                    mcpclient.name,
                    exc_info=True,
                )
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

    # pylint: disable=too-many-branches
    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest.

        copy the manifest data to the Django ORM model and
        save the model to the database. Note that there are fields included in the
        manifest that are not editable
        and are therefore removed from the Django ORM model dict prior to attempting
        the save() command. These fields are defined in the readonly_fields list.

        MCPClient is a composite model that includes the MCPClient, MCPClientAPIKey,
        MCPClientPlugin and MCPClientFunctions models. All of these are represented
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
        if not isinstance(self.mcpclient, MCPClient):
            raise SAMMCPClientBrokerError(f"MCPClient {self.name} not found", thing=self.kind, command=command)
        with transaction.atomic():
            readonly_fields = ["id", "created_at", "updated_at", "tags"]
            try:
                data = self.manifest_to_django_orm()
                tags = data.get("tags", [])
                for field in readonly_fields:
                    data.pop(field, None)
                for key, value in data.items():
                    setattr(self.mcpclient, key, value)
                if self.mcpclient.user_profile != self.user_profile:
                    raise SAMMCPClientBrokerError(
                        f"User profile mismatch for {self.kind} {self.manifest.metadata.name}",
                        thing=self.kind,
                        command=command,
                    )
                self.mcpclient.save()

                # Fix note: occasionally seeing AttributeError: \'list\' object has no attribute \'set\ in the logs,
                # which is why this is wrapped in a try/except block.
                try:
                    if not isinstance(self.mcpclient.tags, TaggableManager):
                        logger.warning(
                            "%s.apply() mcpclient.tags is a list instead of a TaggableManager for %s %s owned by %s. This is unexpected and may indicate an issue with the MCPClient model definition or the database state. Tags=%s",
                            self.formatted_class_name,
                            self.kind,
                            self.manifest.metadata.name,
                            self.user_profile,
                            tags,
                        )
                    else:
                        self.mcpclient.tags.set(tags)
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
                self.mcpclient.refresh_from_db()
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
                raise SAMMCPClientBrokerError(
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
        if self.mcpclient:
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
                raise SAMMCPClientBrokerError(
                    f"Failed to describe {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if self.mcpclient:
            try:
                self.mcpclient.delete()
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
                raise SAMMCPClientBrokerError(
                    f"Failed to delete {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerError(f"{self.kind} {self.name} deploy() is not implemented.", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerError(
            f"{self.kind} {self.name} undeploy() is not implemented.", thing=self.kind, command=command
        )

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
