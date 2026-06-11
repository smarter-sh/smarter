# pylint: disable=W0718,C0302
"""Smarter API LLMClient Manifest handler."""

import datetime
from typing import List, Optional, Type

from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer
from taggit.managers import TaggableManager

from smarter.apps.account.utils import (
    smarter_cached_objects,
    valid_resource_owners_for_user,
)
from smarter.apps.llm_client.manifest.models.llm_client.const import MANIFEST_KIND
from smarter.apps.llm_client.manifest.models.llm_client.metadata import (
    SAMLLMClientMetadata,
)
from smarter.apps.llm_client.manifest.models.llm_client.model import SAMLLMClient
from smarter.apps.llm_client.manifest.models.llm_client.spec import (
    SAMLLMClientSpec,
    SAMLLMClientSpecConfig,
)
from smarter.apps.llm_client.manifest.models.llm_client.status import SAMLLMClientStatus
from smarter.apps.llm_client.models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientFunctions,
    LLMClientPlugin,
)
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.signals import broker_ready
from smarter.apps.plugin.utils import get_plugin_examples_by_name
from smarter.common.conf import settings_defaults
from smarter.common.utils.decorators import camel_case
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
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
    __name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

MAX_RESULTS = 1000


class SAMLLMClientBrokerError(SAMBrokerError):
    """Base exception for Smarter API LLMClient Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API LLMClient Manifest Broker Error"


class LLMClientSerializer(ModelSerializer):
    """Django ORM model serializer for get()."""

    # pylint: disable=C0115
    class Meta:
        model = LLMClient
        fields = ["name", "url", "dns_verification_status", "deployed", "created_at", "updated_at"]


class SAMLLMClientBroker(AbstractBroker):
    """
    Broker for :py:class:`SAM <smarter.lib.manifest.models.AbstractSAMMetadataBase>` LLMClient manifests.

    This class provides a high-level abstraction for managing llm_client manifests
    within the Smarter platform. It acts as the central coordinator for the
    lifecycle of llm_client manifests, bridging the gap between declarative YAML
    files and persistent application state.

    The broker is responsible for:

    - Managing the lifecycle of llm_client manifests, including loading, validation,
      and parsing of YAML files.
    - Initializing Pydantic models from manifest data to ensure robust schema
      validation and serialization.
    - Integrating with Django ORM models that represent llm_client manifests,
      supporting creation, update, deletion, and querying of database records.
    - Transforming data between Django ORM models and Pydantic models to enable
      seamless conversion between database and API representations.
    - Coordinating composite models, such as LLMClient, LLMClientAPIKey,
      LLMClientPlugin, and LLMClientFunctions, to ensure all components of an llm_client
      are synchronized according to the manifest specification.
    - Ensuring atomic and consistent application of changes using Django's
      transaction management.
    - Providing detailed logging and error handling integrated with the Smarter
      platform's diagnostics systems.

    This broker is a key component in the deployment, configuration, and
    lifecycle management of llm_clients in the Smarter Framework.
    """

    # override the base abstract manifest model with the LLMClient model
    _manifest: Optional[SAMLLMClient] = None
    _pydantic_model: Type[SAMLLMClient] = SAMLLMClient
    _llm_client: Optional[LLMClient] = None
    _functions: Optional[List[str]] = None
    _plugins: Optional[List[str]] = None
    _llm_client_api_key: Optional[LLMClientAPIKey] = None
    _name: Optional[str] = None
    _ready: bool = False

    def __init__(self, *args, **kwargs):
        """
        Initialize the SAMLLMClientBroker instance.

        This constructor initializes the broker by calling the parent class's
        constructor, which will attempt to bootstrap the class instance
        with any combination of raw manifest data (in JSON or YAML format),
        a manifest loader, or existing Django ORM models. If a manifest
        loader is provided and its kind matches the expected kind for this broker,
        the manifest is initialized using the loader's data.

        This class can bootstrap itself in any of the following ways:

        - request.body (yaml or json string)
        - name + account (determined via authentication of the request object)
        - SAMLoader instance
        - manifest instance
        - filepath to a manifest file

        If raw manifest data is provided, whether as a string or a dictionary,
        or a SAMLoader instance, the base class constructor will only goes as
        far as initializing the loader. The actual manifest model initialization
        is deferred to this constructor, which checks the loader's kind.

        :param args: Positional arguments passed to the parent constructor.
        :param kwargs: Keyword arguments passed to the parent constructor.

        **Example:**

        .. code-block:: python

            broker = SAMLLMClientBroker(loader=loader, plugin_meta=plugin_meta)
        .. seealso::
            - `SAMPluginBaseBroker.__init__`
        """
        super().__init__(*args, **kwargs)
        logger.debug(
            "%s.__init__() called with args=%s, kwargs=%s",
            self.formatted_class_name,
            args,
            kwargs,
        )
        self._llm_client = kwargs.get("llm_client")
        if self._llm_client:
            logger.debug(
                "%s.__init__() initialized with existing LLMClient instance: %s",
                self.formatted_class_name,
                self._llm_client,
            )
        if not self.ready:
            if not self.loader and not self.manifest and not self.llm_client:
                logger.warning(
                    "%s.__init__() No loader nor existing LLMClient provided for %s broker. Cannot initialize.",
                    self.formatted_class_name,
                    self.kind,
                )
                return
            if self.loader and self.loader.manifest_kind != self.kind:
                raise SAMBrokerErrorNotReady(
                    f"Loader manifest kind {self.loader.manifest_kind} does not match broker kind {self.kind}",
                    thing=self.kind,
                )

            if self.loader:
                self._manifest = SAMLLMClient(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMLLMClientMetadata(**self.loader.manifest_metadata),
                    spec=SAMLLMClientSpec(**self.loader.manifest_spec),
                )
            if self._manifest:
                logger.debug(
                    "%s.__init__() initialized manifest from loader for %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name if self.manifest and self.manifest.metadata else None,
                )
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        logger.info(msg)

    @property
    def SerializerClass(self) -> Type[LLMClientSerializer]:
        """
        The Django ORM model serializer class for the LLMClient.

        :returns: The LLMClient Django ORM model serializer class.
        :rtype: Type[ModelSerializer]
        """
        return LLMClientSerializer

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
    def llm_client(self) -> Optional[LLMClient]:
        """
        Provides access to the Django ORM model instance representing the current Smarter LLMClient.

        This property retrieves the LLMClient object associated with the broker's account and name.
        If a matching LLMClient record exists in the database, it is returned and cached for future access.
        If no such record exists, and a manifest is available, a new LLMClient instance is created using
        data extracted from the manifest and then persisted to the database.

        This property ensures that the broker always has access to a valid LLMClient model, either by
        fetching an existing record or by creating one from the manifest specification. The LLMClient
        model stores the configuration and runtime state of the llm_client, and is used for all database
        operations related to the llm_client's lifecycle.

        :returns: The Django ORM LLMClient instance if found or created, otherwise ``None`` if neither
                  a database record nor a manifest is available.
        :rtype: Optional[LLMClient]

        .. note::

            The returned LLMClient object is essential for linking related resources such as API keys,
            plugins, and functions, and for performing updates or queries on the llm_client's state.

        .. admonition:: FIX NOTE

            This should be refactored/removed in favor of orm_instance. There is no logic
            in this property that merits it overriding the parent orm_instance property.

        .. admonition:: FIX NOTE

            This is breaking an unwritten rule of Smarter resources in that it is
            lazily **creating** a database record on a property getter.
            Creating/updating database records should be handled in apply().
        """
        if self._llm_client:
            return self._llm_client

        try:
            self._llm_client = LLMClient.get_cached_object(
                invalidate=True, user_profile=self.user_profile, name=self.name
            )
            logger.debug(
                "%s.llm_client() retrieved existing LLMClient instance %s owned by %s from database.",
                self.formatted_class_name,
                self._llm_client,
                self.user_profile,
            )
            return self._llm_client
        except LLMClient.DoesNotExist:
            self._llm_client = None

        logger.debug(
            "%s.llm_client() LLMClient instance not found for user_profile %s. Attempting to create a new instance.",
            self.formatted_class_name,
            self.user_profile,
        )
        if self.manifest:
            data = self.manifest_to_django_orm()
            data["user_profile"] = self.user_profile
            logger.debug("%s.llm_client() Creating new LLMClient with data: %s", self.formatted_class_name, data)
            tags = data.pop("tags", [])
            self._llm_client = LLMClient.objects.create(**data)
            if self._llm_client and tags:
                self._llm_client.tags.set(tags)
            self._created = True
            logger.warning(
                "%s.llm_client() lazily created new LLMClient instance %s owned by %s. This logic should be handled in apply().",
                self.formatted_class_name,
                self._llm_client,
                self.user_profile,
            )
        else:
            logger.warning(
                "%s.llm_client() %s not found for user_profile %s",
                self.formatted_class_name,
                self._llm_client,
                self.user_profile,
            )

        return self._llm_client

    @property
    def functions(self) -> Optional[List[str]]:
        """
        Provides access to the Django ORM model class representing LLMClient functions.

        This property retrieves a list of the names of the ``LLMClientFunctions`` Django ORM model
        objects that are linked to the LLMClient managed by this broker.
        The functions define the capabilities and operations
        that the LLMClient can perform, as specified in the manifest.

        If the functions have already been retrieved and cached, they are returned immediately.
        Otherwise, the property attempts to fetch the functions from the database using the
        current LLMClient instance. If no functions are found, ``None`` is returned.

        :returns: A list of names of ``LLMClientFunctions`` instances associated with the LLMClient, or ``None`` if no functions exist.
        :rtype: Optional[List[str]]
        """
        if self._functions:
            return self._functions
        if not self.llm_client:
            return None

        queryset = LLMClientFunctions.objects.filter(llm_client=self.llm_client)
        self._functions = list(queryset.values_list("name", flat=True))

        return self._functions

    @property
    def plugins(self) -> Optional[List[str]]:
        """
        Provides access to the Django ORM model class representing LLMClient plugins.

        This property retrieves a list of the names of the ``LLMClientPlugin`` Django ORM model
        objects that are linked to the LLMClient managed by this broker.
        The plugins extend the functionality of the LLMClient,
        as specified in the manifest.

        If the plugins have already been retrieved and cached, they are returned immediately.
        Otherwise, the property attempts to fetch the plugins from the database using the
        current LLMClient instance. If no plugins are found, ``None`` is returned.

        :returns: A list of names of ``LLMClientPlugin`` instances associated with the LLMClient, or ``None`` if no plugins exist.
        :rtype: Optional[List[str]]
        """
        if self._plugins:
            return self._plugins
        if not self.llm_client:
            return None

        queryset = LLMClientPlugin.objects.filter(llm_client=self.llm_client)
        self._plugins = list(queryset.values_list("plugin_meta__name", flat=True))

        return self._plugins

    @property
    def llm_client_api_key(self) -> Optional[LLMClientAPIKey]:
        """
        Provides access to the API key associated with the current LLMClient instance.

        This property retrieves the ``LLMClientAPIKey`` Django ORM model object that is linked to
        the LLMClient managed by this broker. The API key is used for authenticating requests made
        by the LLMClient and is stored securely in the database.

        If the API key has already been retrieved and cached, it is returned immediately.
        Otherwise, the property attempts to fetch the API key from the database using the
        current LLMClient instance. If no API key is found, ``None`` is returned.

        This property is essential for operations that require authentication or authorization
        on behalf of the LLMClient, such as invoking external APIs or managing secure resources.

        :returns: The ``LLMClientAPIKey`` instance associated with the LLMClient, or ``None`` if no API key exists.
        :rtype: Optional[LLMClientAPIKey]

        .. important::

            If the LLMClientAPIKey is ``None``, it indicates that no API key has been set for the LLMClient,
            which in turn will enable anonymous unauthenticated access for the LLMClient.
        """
        if self._llm_client_api_key:
            return self._llm_client_api_key
        try:
            self._llm_client_api_key = LLMClientAPIKey.objects.get(llm_client=self.llm_client)
        except LLMClientAPIKey.DoesNotExist:
            return None
        return self._llm_client_api_key

    def manifest_to_django_orm(self) -> dict:
        """
        Convert the Smarter API LLMClient manifest into a dictionary suitable for creating or updating a Django ORM LLMClient model.

        This method extracts all relevant configuration, metadata, and versioning information from the loaded manifest
        and transforms it into a dictionary format compatible with Django ORM operations. The manifest's configuration
        is first dumped and converted from camelCase to snake_case to match Django's field naming conventions.

        The resulting dictionary includes the account, name, description, and version fields from the manifest metadata,
        as well as all configuration fields from the manifest specification. This dictionary can be used to instantiate
        or update a LLMClient ORM model instance in the database.

        If the manifest is not loaded or is invalid, an exception is raised to indicate that the broker is not ready
        to perform the transformation.

        :returns: A dictionary containing all fields required to create or update a Django ORM LLMClient model.
        :rtype: dict

        :raises SAMBrokerErrorNotReady: If the manifest is not loaded or cannot be found.
        :raises SAMLLMClientBrokerError: If the manifest configuration cannot be converted to a dictionary.
        """
        if not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"Manifest not loaded for {self.kind} broker. Cannot convert to Django ORM.", thing=self.kind
            )
        metadata = super().manifest_to_django_orm()

        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.to_snake_case(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMLLMClientBrokerError(
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
        Transform the Django ORM LLMClient model instance into a dictionary compatible with the Smarter API LLMClient manifest format.

        This method converts the current LLMClient ORM model and its related resources (plugins, functions, API key)
        into a dictionary structure that matches the expected schema for a Pydantic manifest. The conversion includes
        renaming fields from snake_case to camelCase, removing internal-only fields, and assembling metadata, spec,
        and status sections as required by the manifest.

        The resulting dictionary contains all configuration, metadata, plugin, function, and status information
        necessary to reconstruct the manifest for the llm_client. This enables seamless round-trip conversion between
        database state and manifest representation.

        If the LLMClient model is not available, the method logs a warning and returns ``None``. If the conversion
        fails, an exception is raised to indicate the error.

        :returns: A dictionary representing the Smarter API LLMClient manifest, or ``None`` if the LLMClient model is not set.
        :rtype: Optional[dict]

        :raises SAMLLMClientBrokerError: If the ORM model cannot be converted to a manifest dictionary.

        See also:

        - :py:meth:`smarter.apps.llm_client.manifest.brokers.llm_client.SAMLLMClientBroker.manifest_to_django_orm`
        - :py:class:`smarter.apps.llm_client.manifest.models.llm_client.SAMLLMClient`
        - :py:class:`smarter.apps.llm_client.manifest.models.llm_client.metadata.SAMLLMClientMetadata`
        - :py:class:`smarter.apps.llm_client.manifest.models.llm_client.spec.SAMLLMClientSpec`
        - :py:class:`smarter.apps.llm_client.manifest.models.llm_client.status.SAMLLMClientStatus`
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
        if not self.llm_client:
            logger.warning(
                "%s.django_orm_to_manifest_dict() called without a LLMClient. This could affect broker operations.",
                self.formatted_class_name,
            )
            return None
        llm_client_dict = model_to_dict(self.llm_client)
        llm_client_dict = self.to_camel_case(llm_client_dict)
        if not isinstance(llm_client_dict, dict):
            raise SAMLLMClientBrokerError(
                f"Failed to convert {self.kind} {self.llm_client.name} to dict", thing=self.kind
            )
        llm_client_dict.pop("id")
        llm_client_dict.pop("name")
        llm_client_dict.pop("description")
        llm_client_dict.pop("version")

        plugins = LLMClientPlugin.objects.filter(llm_client=self.llm_client)
        plugin_names = [plugin.plugin_meta.name for plugin in plugins]

        functions = LLMClientFunctions.objects.filter(llm_client=self.llm_client)
        function_names = [function.name for function in functions]

        api_key = self.llm_client_api_key.api_key if self.llm_client_api_key else None

        meta = SAMLLMClientMetadata(
            name=self.llm_client.name,
            description=self.llm_client.description,
            version=self.llm_client.version,
            tags=self.llm_client.tags_list,
            annotations=self.llm_client.annotations if isinstance(self.llm_client.annotations, list) else [],
        )
        spec_config = SAMLLMClientSpecConfig(**llm_client_dict)
        spec = SAMLLMClientSpec(config=spec_config, plugins=plugin_names, functions=function_names, apiKey=api_key)
        status = SAMLLMClientStatus(
            accountNumber=self.account.account_number,
            username=self.user_profile.user.username,
            recordLocator=self.llm_client.record_locator,
            created=self.llm_client.created_at,
            modified=self.llm_client.updated_at,
            deployed=self.llm_client.deployed,
            defaultHost=self.llm_client.default_host,
            sandboxHost=self.llm_client.sandbox_host,
            hostname=self.llm_client.hostname,
            dnsVerificationStatus=self.llm_client.dns_verification_status,
            customUrl=self.llm_client.custom_url,
            defaultUrl=self.llm_client.default_url,
            sandboxUrl=self.llm_client.sandbox_url,
            url=self.llm_client.url,
            urlLLMClient=self.llm_client.url_llm_client,
            urlChatConfig=self.llm_client.url_chat_config,
            urlChatapp=self.llm_client.url_chatapp,
        )
        model = SAMLLMClient(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=meta,
            spec=spec,
            status=status,
        )

        logger.debug(
            "%s.django_orm_to_manifest_dict() converted LLMClient %s to manifest dict: %s",
            self.formatted_class_name,
            self.llm_client.name,
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
        class_name = f"{SAMLLMClientBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for the Smarter API LLMClient.

        This property provides the specific kind identifier used to classify the Smarter API LLMClient
        manifest within the Smarter platform. The kind is a key component of the manifest schema,
        allowing the system to recognize and process llm_client manifests appropriately. The kind value is defined as a constant in the llm_client manifest model
        and is used throughout the broker to ensure consistency when handling llm_client manifests.

        :returns: The manifest kind string for the Smarter API LLMClient.
        :rtype: str

        .. important::

            The kind property is essential for manifest validation, routing, and processing within
            the Smarter platform.
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMLLMClient]:
        """
        Returns the Smarter API LLMClient manifest as a Pydantic model.

        This method constructs and returns an instance of the ``SAMLLMClient`` Pydantic model,
        which represents the full manifest for a Smarter API LLMClient. The manifest contains
        all configuration, metadata, and specification details required to describe and deploy
        an llm_client within the Smarter platform.

        The manifest is initialized using data provided by the manifest loader. The loader
        supplies the manifest's API version, kind, metadata, and specification, which are
        passed to the respective fields of the ``SAMLLMClient`` model. The metadata and spec
        fields are themselves Pydantic models (``SAMLLMClientMetadata`` and ``SAMLLMClientSpec``),
        and are recursively initialized with their corresponding data.

        Unlike child models, which are automatically cascade-initialized by Pydantic when
        constructing the parent model, the top-level manifest model must be explicitly
        instantiated in this method. This ensures that all manifest data is validated and
        structured according to the schema defined by the ``SAMLLMClient`` model.

        If the manifest has already been initialized and cached, this method returns the
        cached instance. If the loader is present and its manifest kind matches the expected
        kind, a new manifest instance is created and cached before returning.

        :returns: An instance of ``SAMLLMClient`` representing the llm_client manifest, or ``None``
                if the manifest cannot be initialized.
        :rtype: Optional[SAMLLMClient]
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMLLMClient):
                raise SAMLLMClientBrokerError("Cached manifest is not a SAMLLMClient instance", thing=self.kind)
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            logger.debug(
                "%s.manifest() initializing %s from SAMLoader with name %s",
                self.formatted_class_name,
                self.kind,
                self.loader.manifest_metadata.get(SAMMetadataKeys.NAME.value, "unknown"),
            )
            self._manifest = SAMLLMClient(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMLLMClientMetadata(**self.loader.manifest_metadata),
                spec=SAMLLMClientSpec(**self.loader.manifest_spec),
            )
            return self._manifest
        if self._llm_client:
            self._manifest = self.django_orm_to_manifest_dict()  # type: ignore
            if self._manifest:
                logger.debug(
                    "%s.manifest() initialized from loader for existing LLMClient %s with name %s",
                    self.formatted_class_name,
                    self._llm_client,
                    self._llm_client.name,
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
        any cached objects that are related to the LLMClient when any mutation
        occurs. In this case, we need to invalidate the LLMClient cache itself,
        but also any related objects such as the plugins, functions and
        api keys.

        .. returns: None
        .. rtype: None
        """
        logger.debug("%s.cache_invalidations() called.", self.formatted_class_name_cache_invalidations)

        # 1.) invalidate the LLMClient cache itself.
        # -----------------------------
        LLMClient.get_cached_object(pk=self.llm_client.id, invalidate=True)  # type: ignore

        # 2.) invalidate anything else in which the llm_client is part of. this could
        # include listviews, the plugins, functions and api keys.
        # -----------------------------
        LLMClient.get_cached_objects(user_profile=self.user_profile, invalidate=True)

        # 3.) invalidate all children of LLMClient
        # -----------------------------
        llm_client_functions = LLMClientFunctions.objects.filter(llm_client=self.llm_client)
        for llm_client_function in llm_client_functions:
            LLMClientFunctions.get_cached_object(pk=llm_client_function.id, invalidate=True)  # type: ignore

        llm_client_plugins = LLMClientPlugin.objects.filter(llm_client=self.llm_client)
        for llm_client_plugin in llm_client_plugins:
            LLMClientPlugin.get_cached_object(pk=llm_client_plugin.id, invalidate=True)  # type: ignore

        llm_client_api_keys = LLMClientAPIKey.objects.filter(llm_client=self.llm_client)
        for llm_client_api_key in llm_client_api_keys:
            LLMClientAPIKey.get_cached_object(pk=llm_client_api_key.id, invalidate=True)  # type: ignore

        return super().cache_invalidations()

    @property
    def ORMMetaModelClass(self) -> Type[LLMClient]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[LLMClient]
        """
        return LLMClient

    @property
    def ORMModelClass(self) -> Type[LLMClient]:
        """
        The Django ORM model class for the LLMClient.

        :returns: The LLMClient Django ORM model class.
        :rtype: Type[LLMClient]
        """
        return LLMClient

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for the Smarter API LLMClient.

        :returns: A JSON response containing an example Smarter API LLMClient manifest.
        :rtype: SmarterJournaledJsonResponse

        See also:

        - :py:class:`smarter.apps.llm_client.manifest.models.llm_client.SAMLLMClient`
        - :py:class:`smarter.lib.manifest.enumSAMKeys`
        - :py:class:`smarter.apps.llm_client.manifest.enum.SAMMetadataKeys`
        - :py:class:`smarter.apps.llm_client.manifest.enum.SCLIResponseGet`
        - :py:class:`smarter.apps.llm_client.manifest.enum.SCLIResponseGetData`
        - :py:class:`from smarter.common.conf.settings_defaults`
        """

        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        meta_data = SAMLLMClientMetadata(
            name="example_llm_client",
            description="This is an example llm_client manifest generated by the SAMLLMClientBroker. It serves as a template for creating your own llm_client manifests.",
            version="1.0.0",
            tags=["example", "template", "school-project"],
            annotations=[
                {"color": "red"},
                {"size": "medium"},
                {"hash": "sha256:abc123def456"},
            ],
        )
        config = SAMLLMClientSpecConfig(
            subdomain=None,
            customDomain=None,
            deployed=False,
            provider=settings_defaults.LLM_DEFAULT_PROVIDER,
            defaultModel=settings_defaults.LLM_DEFAULT_MODEL,
            defaultSystemRole=settings_defaults.LLM_DEFAULT_SYSTEM_ROLE,
            defaultTemperature=settings_defaults.LLM_DEFAULT_TEMPERATURE,
            defaultMaxTokens=settings_defaults.LLM_DEFAULT_MAX_TOKENS,
            appName="Example LLMClient",
            appAssistant="Example Assistant",
            appWelcomeMessage="Welcome to the Example LLMClient! How can I assist you today?",
            appExamplePrompts=[
                "What is the weather like today?",
                "Can you tell me a joke?",
                "How do I reset my password?",
            ],
            appPlaceholder="Type your message here...",
            appInfoUrl="https://example.com/info",
            appBackgroundImageUrl="https://cdn.smarter.sh/prompt-ui/background.png",
            appLogoUrl="https://cdn.smarter.sh/prompt-ui/logo.png",
            appFileAttachment=False,
        )

        spec = SAMLLMClientSpec(
            config=config,
            plugins=get_plugin_examples_by_name(),
            functions=["date_calculator", "get_current_weather"],
            apiKey="snake_case_api_key_name",
        )
        status = SAMLLMClientStatus(
            accountNumber=smarter_cached_objects.smarter_account.account_number,
            username=smarter_cached_objects.smarter_admin.username,
            recordLocator="abc123def456",
            created=datetime.datetime.now(),
            modified=datetime.datetime.now(),
            deployed=False,
            defaultHost="example-llm_client.smarterapi.com",
            defaultUrl="https://example-llm_client.smarterapi.com",
            customUrl=None,
            sandboxHost="https://example.com",
            sandboxUrl="https://example.com/api/v1/llm-clients/1/",
            hostname="example-llm_client.smarterapi.com",
            url="https://example.com/api/v1/llm-clients/1/",
            urlLLMClient="https://example-llm_client.smarterapi.com/llm_client",
            urlChatapp="https://example-llm_client.smarterapi.com/chatapp",
            urlChatConfig="https://example-llm_client.smarterapi.com/chatconfig",
            dnsVerificationStatus="verified",
        )
        model = SAMLLMClient(apiVersion=self.api_version, kind=self.kind, metadata=meta_data, spec=spec, status=status)

        return self.json_response_ok(command=command, data=model.model_dump())

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value, None)
        name = self.clean_cli_param(param=name, param_name="name", url=self.smarter_build_absolute_uri(request))

        # generate a QuerySet of PluginMeta objects that match our search criteria
        if name:
            llm_clients = LLMClient.objects.filter(user_profile__account=self.account, name=name)
        else:
            llm_clients = LLMClient.objects.filter(user_profile__account=self.account)
        valid_owners = valid_resource_owners_for_user(user_profile=self.user_profile)
        llm_clients = llm_clients.filter(user_profile__in=valid_owners).order_by("name")[:MAX_RESULTS]
        logger.debug(
            "%s.get() found %s LLMClients for account %s", self.formatted_class_name, llm_clients.count(), self.account
        )

        # iterate over the QuerySet and use a serializer to create a model dump for each LLMClient
        for llm_client in llm_clients:
            try:
                model_dump = LLMClientSerializer(llm_client).data
                if not model_dump:
                    raise SAMLLMClientBrokerError(
                        f"Model dump failed for {self.kind} {llm_client.name}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.to_camel_case(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                logger.error(
                    "%s.get() failed to serialize %s %s",
                    self.formatted_class_name,
                    self.kind,
                    llm_client.name,
                    exc_info=True,
                )
                raise SAMLLMClientBrokerError(
                    f"Failed to serialize {self.kind} {llm_client.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=LLMClientSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    # pylint: disable=too-many-branches
    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest.

        copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
        Note that there are fields included in the manifest that are not editable
        and are therefore removed from the Django ORM model dict prior to attempting
        the save() command. These fields are defined in the readonly_fields list.

        LLMClient is a composite model that includes the LLMClient, LLMClientAPIKey,
        LLMClientPlugin and LLMClientFunctions models. All of these are represented
        in the manifest spec and are created or updated as needed.

        .. note::

            tags are handled separately because they are of type TaggableManager and
            require a different method to set them.
        """
        super().apply(request, kwargs)
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
        if not isinstance(self.llm_client, LLMClient):
            raise SAMLLMClientBrokerError(f"LLMClient {self.name} not found", thing=self.kind, command=command)
        with transaction.atomic():
            readonly_fields = ["id", "created_at", "updated_at", "tags"]
            try:
                data = self.manifest_to_django_orm()
                tags = data.get("tags", [])
                for field in readonly_fields:
                    data.pop(field, None)
                for key, value in data.items():
                    setattr(self.llm_client, key, value)
                if self.llm_client.user_profile != self.user_profile:
                    raise SAMLLMClientBrokerError(
                        f"User profile mismatch for {self.kind} {self.manifest.metadata.name}",
                        thing=self.kind,
                        command=command,
                    )
                self.llm_client.save()

                # Fix note: occasionally seeing AttributeError: \'list\' object has no attribute \'set\ in the logs,
                # which is why this is wrapped in a try/except block.
                try:
                    if not isinstance(self.llm_client.tags, TaggableManager):
                        logger.warning(
                            "%s.apply() llm_client.tags is a list instead of a TaggableManager for %s %s owned by %s. This is unexpected and may indicate an issue with the LLMClient model definition or the database state. Tags=%s",
                            self.formatted_class_name,
                            self.kind,
                            self.manifest.metadata.name,
                            self.user_profile,
                            tags,
                        )
                    else:
                        self.llm_client.tags.set(tags)
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
                self.llm_client.refresh_from_db()
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
                raise SAMLLMClientBrokerError(
                    f"Failed to apply {self.kind} {self.manifest.metadata.name}", thing=self.kind, command=command
                ) from e

            # LLMClientAPIKey: create or update the API Key
            # -------------
            if self.manifest.spec.apiKey:
                try:
                    api_key = SmarterAuthToken.objects.get(name=self.manifest.spec.apiKey, user=self.user)
                except SmarterAuthToken.DoesNotExist as e:
                    logger.error(
                        "%s.apply() failed to find SmarterAuthToken %s",
                        self.formatted_class_name,
                        self.manifest.spec.apiKey,
                        exc_info=True,
                    )
                    raise SAMBrokerErrorNotFound(
                        f"API Key {self.manifest.spec.apiKey} not found", thing=self.kind, command=command
                    ) from e
                for key in LLMClientAPIKey.objects.filter(llm_client=self.llm_client):
                    if key.api_key != api_key:
                        key.delete()
                        logger.debug("%s.apply() Detached SmarterAuthToken %s from LLMClient %s", self.formatted_class_name, key.name, self.llm_client.name)  # type: ignore[union-attr]
                _, created = LLMClientAPIKey.objects.get_or_create(llm_client=self.llm_client, api_key=api_key)
                if created:
                    logger.debug(
                        "%s.apply() SmarterAuthToken %s attached to LLMClient %s",
                        self.formatted_class_name,
                        self.manifest.spec.apiKey,
                        self.llm_client.name,
                    )

            # LLMClientPlugin: add what's missing, remove what is in the model but is not in the manifest
            # -------------
            for plugin in LLMClientPlugin.objects.filter(llm_client=self.llm_client):
                if not self.manifest.spec.plugins or (
                    self.manifest.spec.plugins and plugin.plugin_meta.name not in self.manifest.spec.plugins
                ):
                    plugin.delete()
                    logger.debug(
                        "%s.apply() Detached Plugin %s from LLMClient %s",
                        self.formatted_class_name,
                        plugin.plugin_meta.name,
                        self.llm_client.name,
                    )
            if self.manifest.spec.plugins:
                for plugin_name in self.manifest.spec.plugins:
                    plugin_name = str(self.to_snake_case(plugin_name))
                    try:
                        plugin = PluginMeta.objects.get(name=plugin_name, user_profile=self.user_profile)
                    except PluginMeta.DoesNotExist as e:
                        logger.error(
                            "%s.apply() did not find a Plugin named %s",
                            self.formatted_class_name,
                            plugin_name,
                            exc_info=True,
                        )
                        raise SAMBrokerErrorNotFound(
                            f"Plugin {plugin_name} not found for account {self.account.account_number if self.account else 'unknown'}",
                            thing=self.kind,
                            command=command,
                        ) from e
                    _, created = LLMClientPlugin.objects.get_or_create(llm_client=self.llm_client, plugin_meta=plugin)
                    if created:
                        logger.debug(
                            "%s.apply() attached Plugin %s to LLMClient %s",
                            self.formatted_class_name,
                            plugin.name,
                            self.llm_client.name,
                        )

            # LLMClientFunctions: add what's missing, remove what's in the model but not in the manifest
            # -------------
            for function in LLMClientFunctions.objects.filter(llm_client=self.llm_client):
                if function.name not in self.manifest.spec.functions:
                    function.delete()
                    logger.debug(
                        "%s.apply() Detached Function %s from LLMClient %s",
                        self.formatted_class_name,
                        function.name,
                        self.llm_client.name,
                    )
            if self.manifest.spec.functions:
                for function in self.manifest.spec.functions:
                    if function not in LLMClientFunctions.choices_list():
                        return self.json_response_err_notfound(
                            command=command,
                            message=f"Function {function} not found. Valid functions are: {LLMClientFunctions.choices_list()}",
                        )
                    _, created = LLMClientFunctions.objects.get_or_create(llm_client=self.llm_client, name=function)
                    if created:
                        logger.debug(
                            "%s.apply() attached Function %s to LLMClient %s",
                            self.formatted_class_name,
                            function,
                            self.llm_client.name,
                        )

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
        if self.llm_client:
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
                raise SAMLLMClientBrokerError(
                    f"Failed to describe {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if self.llm_client:
            try:
                self.llm_client.delete()
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
                raise SAMLLMClientBrokerError(
                    f"Failed to delete {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if self.llm_client:
            try:
                self.llm_client.deployed = True
                self.llm_client.save()
                self.llm_client.refresh_from_db()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                logger.error(
                    "%s.deploy() failed to deploy %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.name,
                    exc_info=True,
                )
                raise SAMLLMClientBrokerError(
                    f"Failed to deploy {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        if self.name is None:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if self.llm_client:
            try:
                self.llm_client.deployed = False
                self.llm_client.save()
                self.llm_client.refresh_from_db()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                logger.error(
                    "%s.undeploy() failed to undeploy %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.name,
                    exc_info=True,
                )
                raise SAMLLMClientBrokerError(
                    f"Failed to undeploy {self.kind} {self.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} not found", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
