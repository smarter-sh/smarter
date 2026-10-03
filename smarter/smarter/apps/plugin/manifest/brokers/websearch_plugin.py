# pylint: disable=W0718,C0302
"""
Smarter API WebsearchPlugin Manifest handler.

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Optional, Type

from django.http import HttpRequest

from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.websearch_plugin.model import (
    SAMWebsearchPlugin,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.spec import (
    SAMWebsearchPluginSpec,
    WebsearchData,
)
from smarter.apps.plugin.models import (
    PluginDataWebsearch,
    PluginMeta,
)
from smarter.apps.plugin.plugin.websearch import WebsearchPlugin
from smarter.apps.plugin.signals import broker_ready
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    SAMBrokerError,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)

from . import SAMPluginBrokerError
from .plugin_base import SAMPluginBaseBroker

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])


class SAMWebsearchPluginBroker(SAMPluginBaseBroker):
    """
    Broker for Smarter API WebsearchPlugin manifests.

    This class is responsible for loading, validating, and parsing Smarter API YAML WebsearchPlugin manifests,
    and initializing the corresponding Pydantic model. It provides generic services for WebsearchPlugins,
    such as instantiation, creation, update, and deletion.

    A WebsearchPlugin gives the LLM access to the open web: searching it via a web search API,
    and reading web pages by URL. ``spec.websearchData`` configures each operation, and the
    domains that may be accessed. The web search api key is referred to by the name of its
    Smarter Secret.

    **Responsibilities:**

      - Load and validate WebsearchPlugin manifests.
      - Parse manifest data and initialize the `SAMWebsearchPlugin` Pydantic model.
      - Manage plugin lifecycle: create, update, delete, and describe.
      - Interface with Django ORM models for plugin metadata, prompt, selector, and websearch data.

    **Parameters:**

      - `loader`: Manifest loader instance (must match expected manifest kind).
      - `plugin_meta`: Django ORM model for plugin metadata.
      - `plugin_data`: Django ORM model for websearch plugin data.
      - `user_profile`: User profile associated with the plugin.
      - `name`: Plugin name.

    **Example Manifest Response:**

    .. code-block:: json

        {
            "apiVersion": "smarter.sh/v1",
            "kind": "Plugin",
            "metadata": {
                "name": "cli_test_plugin",
                "description": "...",
                "version": "0.2.0",
                "tags": [],
                "annotations": null,
                "pluginClass": "websearch"
            },
            "spec": {
                "prompt": { },
                "selector": { },
                "websearchData": { }
            },
            "status": {
                "created": "2025-06-24T21:38:36.368058+00:00",
                "modified": "2025-06-24T21:38:36.434526+00:00"
            }
        }

    .. seealso::

        - `SAMPluginBaseBroker` for base broker functionality.
        - `SAMWebsearchPlugin` for the manifest model.
        - Django ORM models: `PluginMeta`, `PluginDataWebsearch`, `PluginPrompt`, `PluginSelector`.
    """

    # override the base abstract manifest model with the WebsearchPlugin model
    _manifest: Optional[SAMWebsearchPlugin] = None
    _pydantic_model: Type[SAMWebsearchPlugin] = SAMWebsearchPlugin
    _plugin_data: Optional[PluginDataWebsearch] = None
    _plugin: Optional[WebsearchPlugin] = None
    _plugin_websearch_spec_data: Optional[WebsearchData] = None
    _plugin_websearch_spec: Optional[SAMWebsearchPluginSpec] = None

    def __init__(self, *args, **kwargs):
        """
        Initialize the SAMWebsearchPluginBroker instance.

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

            broker = SAMWebsearchPluginBroker(loader=loader, plugin_meta=plugin_meta)
        .. seealso::
            - `SAMPluginBaseBroker.__init__`
        """
        super().__init__(*args, **kwargs)
        if not self.ready:
            if not self.loader and not self.manifest and not self.plugin:
                logger.error(
                    "%s.__init__() No loader nor existing Plugin provided for %s broker. Cannot initialize.",
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
                self._manifest = SAMWebsearchPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMWebsearchPluginSpec(**self.loader.manifest_spec),
                )
            if self._manifest:
                logger.debug(
                    "%s.__init__() initialized manifest from loader for %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self._manifest.metadata.name,
                )
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        logger.info(msg)

    def plugin_init(self):
        """
        Initialize the SAMWebsearchPluginBroker instance.

        This method initializes the broker by calling the parent class's `init` method.
        It sets up any necessary state or configurations required for handling WebsearchPlugin manifests.

        :return: None

        **Example:**

        .. code-block:: python

            broker = SAMWebsearchPluginBroker()
            broker.init()

        .. seealso::

            - `SAMPluginBaseBroker.init`
        """
        super().plugin_init()
        self._manifest = None
        self._plugin_data = None
        self._plugin = None
        self._plugin_websearch_spec_data = None
        self._plugin_websearch_spec = None

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns a formatted class name for logging.

        This property provides a human-readable class name string, combining the parent class name
        (from `super().formatted_class_name`) with the current class name. This is useful for
        log messages, debugging, and tracing execution in complex broker hierarchies.

        :return: Formatted class name string, e.g. ``BaseBroker.SAMWebsearchPluginBroker()``
        :rtype: str

        **Example:**

        .. code-block:: python

            broker = SAMWebsearchPluginBroker()
            print(broker.formatted_class_name)
            # Output: BaseBroker.SAMWebsearchPluginBroker()

        .. seealso::
            - `SAMPluginBaseBroker.formatted_class_name`
        """
        class_name = f"{SAMWebsearchPluginBroker.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for this broker.

        This property provides the manifest kind string, which is used to identify the type of plugin manifest
        handled by this broker. For websearch plugins, this is typically set to ``MANIFEST_KIND``.

        :return: Manifest kind string (e.g. ``"Plugin"``)
        :rtype: str

        **Example:**

        .. code-block:: python

            broker = SAMWebsearchPluginBroker()
            print(broker.kind)
            # Output: "Plugin"

        .. seealso::

            - `MANIFEST_KIND` constant in `smarter.apps.plugin.manifest.models.websearch_plugin.const`
            - `SAMWebsearchPluginBroker.manifest`
        """
        return MANIFEST_KIND

    @property
    def ORMModelClass(self) -> Type[PluginDataWebsearch]:
        """
        Returns the Django ORM model class for websearch plugin data.

        This property provides the Django ORM model class that represents the websearch plugin data
        associated with this broker. It is used for database operations related to websearch plugin data.

        :return: Django ORM model class for websearch plugin data.
        :rtype: Type[PluginDataWebsearch]

        **Example:**

        .. code-block:: python

            broker = SAMWebsearchPluginBroker()
            ORMModelClass = broker.ORMModelClass
            print(ORMModelClass.__name__)
            # Output: "PluginDataWebsearch"
        .. seealso::
            - `PluginDataWebsearch` Django ORM model.
            - `SAMWebsearchPluginBroker.plugin_data`
        """
        return PluginDataWebsearch

    @property
    def SAMModelClass(self) -> Type[SAMWebsearchPlugin]:
        """
        Return the Pydantic model class for the broker.

        :return: The Pydantic model class definition for the broker.
        :rtype: Type[SAMWebsearchPlugin]
        """
        return SAMWebsearchPlugin

    @property
    def manifest(self) -> Optional[SAMWebsearchPlugin]:
        """
        Returns the manifest for the websearch plugin as a Pydantic model instance.

        This can be initialized any of three ways:
        1. If already from the constructor, return the cached manifest.
        2. If the plugin metadata exists, build the manifest from the Django ORM models.
        3. If a manifest loader is provided, build the manifest from the loader data.

        This property initializes and returns a `SAMWebsearchPlugin` object, representing the full manifest for a websearch plugin.
        The manifest is built using data from the manifest loader, including API version, kind, metadata, and specification.
        Child models (such as metadata and spec) are automatically initialized by Pydantic using the provided data.

        :return: The initialized websearch plugin manifest as a Pydantic model, or None if not available.
        :rtype: Optional[SAMWebsearchPlugin]

        **Example:**

        .. code-block:: python

            broker = SAMWebsearchPluginBroker()
            manifest = broker.manifest
            if manifest:
                print(manifest.model_dump_json())

        .. seealso::

            - `SAMWebsearchPlugin`
            - `SAMPluginCommonMetadata`
            - `SAMWebsearchPluginSpec`
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMWebsearchPlugin):
                raise SAMPluginBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest

        # 1.) prioritize manifest loader data if available. if it was provided
        #     in the request body then this is the authoritative source.
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMWebsearchPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMWebsearchPluginSpec(**self.loader.manifest_spec),
            )
            logger.debug(
                "%s.manifest initialized from loader for %s %s", self.formatted_class_name, self.kind, self.name
            )
            return self._manifest

        # 2.) next, (and only if a loader is not available) try to initialize
        #     from existing ORM model if available
        elif self.plugin_meta:
            logger.debug(
                "%s.manifest building from ORM models for %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
            )
            metadata = self.plugin_metadata_orm2pydantic()
            data = self.plugin_websearch_spec_data_orm2pydantic()
            if not data:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} manifest() failed to build data for {self.kind} {self.plugin_meta.name}",
                    thing=self.kind,
                )
            spec = self.plugin_websearch_spec_orm2pydantic()
            if not spec:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} manifest() failed to build spec for {self.kind} {self.plugin_meta.name}",
                    thing=self.kind,
                )
            status = self.plugin_status_pydantic()

            # initialize the SAMWebsearchPlugin manifest with child models
            self._manifest = SAMWebsearchPlugin(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=metadata,
                spec=spec,
                status=status,
            )
            logger.debug(
                "%s.manifest initialized from ORM models for %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
            )
            return self._manifest
        else:
            logger.warning("%s.manifest could not be initialized", self.formatted_class_name)
        return self._manifest

    @property
    def plugin(self) -> Optional[WebsearchPlugin]:
        """
        Returns the `WebsearchPlugin` instance managed by this broker.

        This property lazily initializes and returns a `WebsearchPlugin` object, using the current plugin metadata,
        user profile, manifest, and name. If the plugin has already been initialized, the cached instance is returned.

        :return: The managed `WebsearchPlugin` instance, or None if initialization fails.
        :rtype: Optional[WebsearchPlugin]

        **Example:**

        .. code-block:: python

            broker = SAMWebsearchPluginBroker()
            plugin = broker.plugin
            if plugin:
                print(plugin.name)

        .. seealso::

            - `WebsearchPlugin`
            - `SAMWebsearchPluginBroker.manifest`
            - `SAMWebsearchPluginBroker.plugin_meta`
        """
        if self._plugin:
            return self._plugin
        self._plugin = WebsearchPlugin(
            plugin_meta=self.plugin_meta,
            user_profile=self.user_profile,
            manifest=self._manifest,
            name=self.name,
        )
        return self._plugin

    @property
    def plugin_data(self) -> Optional[PluginDataWebsearch]:
        """
        Returns the `PluginDataWebsearch` object for this broker.

        This property retrieves the websearch plugin data from the database, using the associated `plugin_meta`.
        If the data has already been loaded, the cached instance is returned. If `plugin_meta` is not set,
        this property returns None.

        :return: The `PluginDataWebsearch` instance for this plugin, or None if not available.
        :rtype: Optional[PluginDataWebsearch]

        **Example:**

        .. code-block:: python

            broker = SAMWebsearchPluginBroker()
            data = broker.plugin_data
            if data:
                print(data.search_provider)

        :raises SAMPluginBrokerError:
            If there is an error retrieving the plugin data from the database.

        .. seealso::

            - `PluginDataWebsearch`
            - `SAMWebsearchPluginBroker.plugin_meta`
        """
        if self._plugin_data:
            return self._plugin_data

        if self.plugin_meta is None:
            return None

        try:
            self._plugin_data = PluginDataWebsearch.get_cached_data_by_plugin(plugin=self.plugin_meta)
            logger.debug(
                "%s.plugin_data() PluginDataWebsearch object retrieved for %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
            )
        except PluginDataWebsearch.DoesNotExist:
            logger.warning(
                "%s.plugin_data() PluginDataWebsearch object does not exist for %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
            )
        return self._plugin_data

    @property
    def ready(self) -> bool:
        """
        Check if the broker is ready for operations.

        This property determines whether the broker has been properly initialized and is ready to perform operations such as applying manifests or querying connections. It checks the presence of the manifest and connection properties.

        :return: True if the broker is ready, False otherwise.
        :rtype: bool

        .. seealso::

            :meth:`SAMApiConnectionBroker.manifest`
            :meth:`SAMApiConnectionBroker.connection`

        **Example usage**::
            if broker.ready:
                print("Broker is ready for operations.")
        """
        if not super().ready:
            logger.debug("%s.ready returning False because SAMPluginBaseBroker is not ready", self.formatted_class_name)
            return False
        if self._manifest or self._plugin:
            logger.debug(
                "%s.ready returning True because manifest %s and/or plugin %s has been initialized",
                self.formatted_class_name,
                self._manifest,
                self._plugin,
            )
            broker_ready.send(sender=self.__class__, broker=self)
            return True
        logger.debug(
            "%s.ready returning False because neither manifest nor plugin could be initialized",
            self.formatted_class_name,
        )
        return False

    def plugin_websearch_spec_data_orm2pydantic(self) -> Optional[WebsearchData]:
        """
        Convert plugin websearch data from the Django ORM model format to the Pydantic manifest format.

        The web search api key is rendered as the name of its Secret, never its value.

        :return: The websearch plugin data as a Pydantic model, or None if not available.
        :rtype: Optional[WebsearchData]

        **Example:**

        .. code-block:: python

            broker = SAMWebsearchPluginBroker()
            websearch_data = broker.plugin_websearch_spec_data_orm2pydantic()
            print(websearch_data.model_dump_json())

        .. seealso::

            - `PluginDataWebsearch`
            - `PluginDataWebsearch.manifest_data`
            - `WebsearchData`
        """
        if self._plugin_websearch_spec_data:
            return self._plugin_websearch_spec_data
        if not self.plugin_meta:
            return None
        if not self.plugin_data:
            return None
        self._plugin_websearch_spec_data = WebsearchData(**self.plugin_data.manifest_data())
        return self._plugin_websearch_spec_data

    def plugin_websearch_spec_orm2pydantic(self) -> Optional[SAMWebsearchPluginSpec]:
        """
        Convert the websearch plugin specification from the Django ORM model format to the Pydantic manifest format.

        This method constructs a `SAMWebsearchPluginSpec` Pydantic model using the prompt, selector,
        and websearch data associated with the current `plugin_meta`. It retrieves each component
        using their respective ORM-to-Pydantic conversion methods.

        :return: The websearch plugin specification as a Pydantic model.
        :rtype: SAMWebsearchPluginSpec

        **Example:**

        .. code-block:: python

            broker = SAMWebsearchPluginBroker()
            websearch_spec = broker.plugin_websearch_spec_orm2pydantic()
            print(websearch_spec.model_dump_json())

        :raises SAMPluginBrokerError:
            If there is an error retrieving or converting any component of the plugin specification.

        .. seealso::

            - `SAMWebsearchPluginSpec`
            - `SAMPluginCommonSpecPrompt`
            - `SAMPluginCommonSpecSelector`
            - `WebsearchData`
        """
        if self._plugin_websearch_spec:
            return self._plugin_websearch_spec
        if not self.plugin_meta:
            return None
        prompt = self.plugin_prompt_orm2pydantic()
        selector = self.plugin_selector_orm2pydantic()
        data = self.plugin_websearch_spec_data_orm2pydantic()
        if not data:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} plugin_websearch_spec_orm2pydantic() failed to build data for {self.kind} {self.plugin_meta.name}",
                thing=self.kind,
            )
        self._plugin_websearch_spec = SAMWebsearchPluginSpec(
            prompt=prompt,
            selector=selector,
            websearchData=data,
        )
        return self._plugin_websearch_spec

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def cache_invalidations(self) -> None:
        """Invalidate any relevant caches when the manifest or plugin data changes."""
        logger.debug("%s.cache_invalidations() called.", self.formatted_class_name_cache_invalidations)
        PluginDataWebsearch.get_cached_object(invalidate=True, plugin=self.plugin_meta)  # type: ignore
        return super().cache_invalidations()

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for a websearch plugin.

        This method generates and returns a sample manifest structure for a websearch plugin, using
        `WebsearchPlugin.example_manifest`. The response is wrapped in a `SmarterJournaledJsonResponse`
        for consistent API output.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments passed to the manifest generator.
        :return: JSON response containing the example manifest.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.example_manifest(request, foo="bar")
            print(response.data)

        .. seealso::

            - `WebsearchPlugin.example_manifest`
            - `SmarterJournaledJsonResponse`
            - `SmarterJournalCliCommands`
        """
        logger.debug(
            "%s.example_manifest() called for %s %s %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
        )
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        example_manifest = SAMWebsearchPlugin(**WebsearchPlugin.example_manifest())  # type: ignore[arg-type]
        return self.json_response_ok(command=command, data=example_manifest.model_dump())

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Serialize and return the manifest for a websearch plugin as a JSON response.

        This method collects and validates all required components of a websearch plugin manifest, including metadata,
        prompt configuration, selector criteria, and websearch data. It ensures that all plugin objects are present and
        ready, and provides informative error responses if any required component is missing or invalid.

        The returned manifest contains the following top-level fields:

        - ``apiVersion``: Manifest API version string.
        - ``kind``: Manifest kind (usually "Plugin").
        - ``metadata``: Plugin metadata (name, description, version, tags, annotations, plugin class).
        - ``spec``: Specification details (prompt configuration, selector criteria, websearch plugin data).
        - ``status``: Creation and last modification timestamps.

        Example response:

        .. code-block:: json

           {
               "apiVersion": "smarter.sh/v1",
               "kind": "Plugin",
               "metadata": {
                   "name": "cli_test_plugin",
                   "description": "...",
                   "version": "0.2.0",
                   "tags": [],
                   "annotations": null,
                   "pluginClass": "websearch"
               },
               "spec": {
                   "prompt": {  },
                   "selector": {  },
                   "websearchData": {  }
               },
               "status": {
                   "created": "2025-06-24T21:38:36.368058+00:00",
                   "modified": "2025-06-24T21:38:36.434526+00:00"
               }
           }

        Error handling:
            - If manifest is not set, a ``SAMPluginBrokerError`` is raised.

        Returns
        -------
        SmarterJournaledJsonResponse
            JSON response containing the plugin manifest or error details.
        """
        logger.debug(
            "%s.describe() called for %s %s %s", self.formatted_class_name, self.kind, self.name, self.user_profile
        )
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)

        if not self.manifest:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} manifest not initialized. Cannot describe",
                thing=self.kind,
                command=command,
            )

        data = json.loads(self.manifest.model_dump_json())
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest to the database.

        This method copies the manifest data to the Django ORM model and saves it to the database.
        It first ensures the manifest is loaded and validated by calling the base class's `apply` method.
        If the plugin or its metadata is not properly initialized, an error is raised.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments for manifest application.
        :return: JSON response indicating success or error details.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.apply(request, name="cli_test_plugin")
            print(response.data)

        :raises SAMPluginBrokerError:
            If the plugin or plugin metadata is not initialized
        :raises SAMBrokerErrorNotReady:
            If the plugin is not ready after creation

        .. seealso::

            - `SAMPluginBaseBroker.apply`
            - `WebsearchPlugin.create`
            - `WebsearchPlugin.save`
            - `SmarterJournaledJsonResponse`
        """
        logger.debug(
            "%s.apply() called for %s %s %s", self.formatted_class_name, self.kind, self.name, self.user_profile
        )
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)

        if not self.user:
            raise SAMBrokerError(
                message="User not authenticated. Cannot apply websearch plugin.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        if not self.user.is_staff:
            raise SAMBrokerError(
                message="Only account admins can apply websearch plugins.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )

        if not self.plugin:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin not initialized. Cannot apply",
                thing=self.kind,
                command=command,
            )
        if self.plugin.ready:
            # the Plugin class was initialized with enough data to bring
            # itself to a ready state, meaning that no create/save is needed.
            return self.json_response_ok(command=command, data=self.to_json())

        if not isinstance(self.plugin, WebsearchPlugin):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin not initialized. Cannot apply",
                thing=self.kind,
                command=command,
            )
        if not isinstance(self.plugin_meta, PluginMeta):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin_meta not initialized. Cannot apply",
                thing=self.kind,
                command=command,
            )

        try:
            self.plugin.create()
        except Exception as e:
            logger.error(
                "%s.apply() failed to create %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
                exc_info=True,
            )
            return self.json_response_err(command=command, e=e)

        if self.plugin.ready:
            try:
                self.plugin.save()
            except Exception as e:
                return self.json_response_err(command=command, e=e)
            self.cache_invalidations()
            return self.json_response_ok(command=command, data=self.to_json())
        try:
            raise SAMBrokerErrorNotReady(
                f"{self.formatted_class_name} {self.plugin_meta.name} not ready", thing=self.kind, command=command
            )
        except SAMBrokerErrorNotReady as err:
            logger.error(
                "%s.apply() failed to save %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
                exc_info=True,
            )
            return self.json_response_err(command=command, e=err)

    def prompt(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Prompt with the websearch plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.prompt() called for %s %s %s", self.formatted_class_name, self.kind, self.name, self.user_profile
        )
        super().prompt(request, kwargs)
        command = self.prompt.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="prompt() not implemented", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the websearch plugin.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating success or error.
        :rtype: SmarterJournaledJsonResponse

        :raises SAMPluginBrokerError:
            If the plugin or plugin metadata is not initialized.
        :raises SAMBrokerErrorNotReady:
            If the plugin is not ready to be deleted.

        .. seealso::

            - `WebsearchPlugin.delete`
            - `SmarterJournaledJsonResponse`
            - :meth:`SAMPluginBaseBroker.set_and_verify_name_param`
        """
        logger.debug(
            "%s.delete() called for %s %s %s", self.formatted_class_name, self.kind, self.name, self.user_profile
        )
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)

        if not self.user:
            raise SAMBrokerError(
                message="User not authenticated. Cannot delete websearch plugin.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        if not self.user.is_staff:
            raise SAMBrokerError(
                message="Only account admins can delete websearch plugins.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )

        if not isinstance(self.plugin, WebsearchPlugin):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin not initialized. Cannot delete",
                thing=self.kind,
                command=command,
            )
        if not isinstance(self.plugin_meta, PluginMeta):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin_meta not initialized. Cannot delete",
                thing=self.kind,
                command=command,
            )
        self.verify_no_dependencies(command)
        if self.plugin.ready:
            try:
                self.plugin.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMBrokerError(
                    f"{self.formatted_class_name} {self.plugin_meta.name} delete failed",
                    thing=self.kind,
                    command=command,
                ) from e
        raise SAMBrokerErrorNotReady(
            f"{self.formatted_class_name} {self.plugin_meta.name} not ready", thing=self.kind, command=command
        )

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Deploy the websearch plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.deploy() called for %s %s %s", self.formatted_class_name, self.kind, self.name, self.user_profile
        )
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("deploy() not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Undeploy the websearch plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.undeploy() called for %s %s %s", self.formatted_class_name, self.kind, self.name, self.user_profile
        )
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("undeploy() not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs for the websearch plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.logs() called for %s %s %s", self.formatted_class_name, self.kind, self.name, self.user_profile
        )
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("logs() not implemented", thing=self.kind, command=command)
