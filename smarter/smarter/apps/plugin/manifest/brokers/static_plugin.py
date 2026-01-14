# pylint: disable=W0718
"""Smarter API StaticPlugin Manifest handler"""

import logging
from datetime import datetime, timezone
from typing import Optional, Type

from django.http import HttpRequest

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
)
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.spec import (
    SAMPluginCommonSpecPrompt,
    SAMPluginCommonSpecSelector,
)
from smarter.apps.plugin.manifest.models.common.plugin.status import (
    SAMPluginCommonStatus,
)
from smarter.apps.plugin.manifest.models.static_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.apps.plugin.manifest.models.static_plugin.spec import (
    SAMPluginStaticSpec,
    SAMPluginStaticSpecData,
)
from smarter.apps.plugin.models import (
    PluginDataStatic,
    PluginMeta,
)
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.apps.plugin.signals import broker_ready
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import (
    SAMBrokerError,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)

from . import SAMPluginBrokerError
from .plugin_base import SAMPluginBaseBroker


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.MANIFEST_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMStaticPluginBroker(SAMPluginBaseBroker):
    """
    Broker for Smarter API StaticPlugin manifests.

    This class is responsible for loading, validating, and parsing Smarter API YAML StaticPlugin manifests,
    and initializing the corresponding Pydantic model. It provides generic services for StaticPlugins,
    such as instantiation, creation, update, and deletion.

    **Responsibilities:**

      - Load and validate StaticPlugin manifests.
      - Parse manifest data and initialize the `SAMStaticPlugin` Pydantic model.
      - Manage plugin lifecycle: create, update, delete, and describe.
      - Interface with Django ORM models for plugin metadata, prompt, selector, and static data.

    **Parameters:**

      - `loader`: Manifest loader instance (must match expected manifest kind).
      - `plugin_meta`: Django ORM model for plugin metadata.
      - `plugin_data`: Django ORM model for static plugin data.
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
                "pluginClass": "static"
            },
            "spec": {
                "prompt": { },
                "selector": { },
                "data": { }
            },
            "status": {
                "created": "2025-06-24T21:38:36.368058+00:00",
                "modified": "2025-06-24T21:38:36.434526+00:00"
            }
        }

    .. seealso::

        - `SAMPluginBaseBroker` for base broker functionality.
        - `SAMStaticPlugin` for the manifest model.
        - Django ORM models: `PluginMeta`, `PluginDataStatic`, `PluginPrompt`, `PluginSelector`.

    """

    # override the base abstract manifest model with the StaticPlugin model
    _manifest: Optional[SAMStaticPlugin] = None
    _pydantic_model: Type[SAMStaticPlugin] = SAMStaticPlugin
    _plugin_data: Optional[PluginDataStatic] = None
    _plugin: Optional[StaticPlugin] = None
    _plugin_static_spec_data: Optional[SAMPluginStaticSpecData] = None
    _plugin_static_spec: Optional[SAMPluginStaticSpec] = None

    def __init__(self, *args, **kwargs):
        """
        Initialize the SAMStaticPluginBroker instance.

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

            broker = SAMStaticPluginBroker(loader=loader, plugin_meta=plugin_meta)
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
                self._manifest = SAMStaticPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMPluginStaticSpec(**self.loader.manifest_spec),
                )
            if self._manifest:
                logger.debug(
                    "%s.__init__() initialized manifest from loader for %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                )
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        if self.ready:
            logger.info(msg)
        else:
            logger.warning(msg)

    def plugin_init(self):
        """
        Initialize the SAMStaticPluginBroker instance.

        This method initializes the broker by calling the parent class's `init` method.
        It sets up any necessary state or configurations required for handling StaticPlugin manifests.

        :return: None

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            broker.init()

        .. seealso::

            - `SAMPluginBaseBroker.init`

        """
        super().plugin_init()
        self._manifest = None
        self._plugin_data = None
        self._plugin = None
        self._plugin_static_spec_data = None
        self._plugin_static_spec = None

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

        :return: Formatted class name string, e.g. ``BaseBroker.SAMStaticPluginBroker()``
        :rtype: str

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            print(broker.formatted_class_name)
            # Output: BaseBroker.SAMStaticPluginBroker()

        .. seealso::
            - `SAMPluginBaseBroker.formatted_class_name`

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{self.__class__.__name__}[{id(self)}]"

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for this broker.

        This property provides the manifest kind string, which is used to identify the type of plugin manifest
        handled by this broker. For static plugins, this is typically set to ``MANIFEST_KIND``.

        :return: Manifest kind string (e.g. ``"Plugin"``)
        :rtype: str

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            print(broker.kind)
            # Output: "Plugin"


        .. seealso::

            - `MANIFEST_KIND` constant in `smarter.apps.plugin.manifest.models.static_plugin.const`
            - `SAMStaticPluginBroker.manifest`

        """
        return MANIFEST_KIND

    @property
    def ORMModelClass(self) -> Type[PluginDataStatic]:
        """
        Returns the Django ORM model class for static plugin data.

        This property provides the Django ORM model class that represents the static plugin data
        associated with this broker. It is used for database operations related to static plugin data.

        :return: Django ORM model class for static plugin data.
        :rtype: Type[PluginDataStatic]

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            ORMModelClass = broker.ORMModelClass
            print(ORMModelClass.__name__)
            # Output: "PluginDataStatic"
        .. seealso::
            - `PluginDataStatic` Django ORM model.
            - `SAMStaticPluginBroker.plugin_data`
        """
        return PluginDataStatic

    @property
    def SAMModelClass(self) -> Type[SAMStaticPlugin]:
        """
        Return the Pydantic model class for the broker.

        :return: The Pydantic model class definition for the broker.
        :rtype: Type[SAMStaticPlugin]
        """
        return SAMStaticPlugin

    @property
    def manifest(self) -> Optional[SAMStaticPlugin]:
        """
        Returns the manifest for the static plugin as a Pydantic model instance.
        This can be initialized any of three ways:
        1. If already from the constructor, return the cached manifest.
        2. If the plugin metadata exists, build the manifest from the Django ORM models.
        3. If a manifest loader is provided, build the manifest from the loader data.

        This property initializes and returns a `SAMStaticPlugin` object, representing the full manifest for a static plugin.
        The manifest is built using data from the manifest loader, including API version, kind, metadata, and specification.
        Child models (such as metadata and spec) are automatically initialized by Pydantic using the provided data.

        :return: The initialized static plugin manifest as a Pydantic model, or None if not available.
        :rtype: Optional[SAMStaticPlugin]

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            manifest = broker.manifest
            if manifest:
                print(manifest.model_dump_json())

        .. seealso::

            - `SAMStaticPlugin`
            - `SAMPluginCommonMetadata`
            - `SAMPluginStaticSpec`

        """
        if self._manifest:
            if not isinstance(self._manifest, SAMStaticPlugin):
                raise SAMPluginBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest

        # 1.) prioritize manifest loader data if available. if it was provided
        #     in the request body then this is the authoritative source.
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMStaticPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMPluginStaticSpec(**self.loader.manifest_spec),
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
            data = self.plugin_static_spec_data_orm2pydantic()
            if not data:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} manifest() failed to build data for {self.kind} {self.plugin_meta.name}",
                    thing=self.kind,
                )
            spec = self.plugin_static_spec_orm2pydantic()
            if not spec:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} manifest() failed to build spec for {self.kind} {self.plugin_meta.name}",
                    thing=self.kind,
                )
            status = self.plugin_status_pydantic()

            # initialize the SAMStaticPlugin manifest with child models
            self._manifest = SAMStaticPlugin(
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
    def plugin(self) -> Optional[StaticPlugin]:
        """
        Returns the `StaticPlugin` instance managed by this broker.

        This property lazily initializes and returns a `StaticPlugin` object, using the current plugin metadata,
        user profile, manifest, and name. If the plugin has already been initialized, the cached instance is returned.

        :return: The managed `StaticPlugin` instance, or None if initialization fails.
        :rtype: Optional[StaticPlugin]

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            plugin = broker.plugin
            if plugin:
                print(plugin.name)

        .. seealso::

            - `StaticPlugin`
            - `SAMStaticPluginBroker.manifest`
            - `SAMStaticPluginBroker.plugin_meta`
        """
        if self._plugin:
            return self._plugin
        self._plugin = StaticPlugin(
            plugin_meta=self.plugin_meta,
            user_profile=self.user_profile,
            manifest=self._manifest,
            name=self.name,
        )
        return self._plugin

    @property
    def plugin_data(self) -> Optional[PluginDataStatic]:
        """
        Returns the `PluginDataStatic` object for this broker.

        This property retrieves the static plugin data from the database, using the associated `plugin_meta`.
        If the data has already been loaded, the cached instance is returned. If `plugin_meta` is not set,
        this property returns None.

        :return: The `PluginDataStatic` instance for this plugin, or None if not available.
        :rtype: Optional[PluginDataStatic]

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            data = broker.plugin_data
            if data:
                print(data.some_field)

        :raises SAMPluginBrokerError:
            If there is an error retrieving the plugin data from the database.


        .. seealso::

            - `PluginDataStatic`
            - `SAMStaticPluginBroker.plugin_meta`
        """
        if self._plugin_data:
            return self._plugin_data

        if self.plugin_meta is None:
            return None

        try:
            data = PluginDataStatic.get_cached_data_by_plugin(plugin=self.plugin_meta)
            if not data:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} plugin_data() failed to get cached data for {self.kind} {self.plugin_meta.name}",
                    thing=self.kind,
                )
            self._plugin_data = data
        except PluginDataStatic.DoesNotExist:
            logger.warning(
                "%s.plugin_data() PluginDataStatic object does not exist for %s %s",
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
            logger.debug(
                "%s.ready retturning False because SAMPluginBaseBroker is not ready", self.formatted_class_name
            )
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

    def plugin_static_spec_data_orm2pydantic(self) -> Optional[SAMPluginStaticSpecData]:
        """
        Convert plugin static data from the Django ORM model format to the Pydantic manifest format.

        This method retrieves the static plugin data associated with the current `plugin_meta` and
        converts it into a `SAMPluginStaticSpecData` Pydantic model. If no data is found, an empty
        `SAMPluginStaticSpecData` model is returned.

        :return: The static plugin data as a Pydantic model.
        :rtype: SAMPluginStaticSpecData

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            static_data = broker.plugin_static_spec_data_orm2pydantic()
            print(static_data.model_dump_json())

        :raises SAMPluginBrokerError:
            If there is an error retrieving or converting the plugin data.


        .. seealso::

            - `PluginDataStatic`
            - `SAMPluginStaticSpecData`
        """
        if self._plugin_static_spec_data:
            return self._plugin_static_spec_data
        if not self.plugin_meta:
            return None
        self._plugin_static_spec_data = SAMPluginStaticSpecData(
            staticData=self.plugin_data.static_data if self.plugin_data else {},
        )
        return self._plugin_static_spec_data

    def plugin_static_spec_orm2pydantic(self) -> Optional[SAMPluginStaticSpec]:
        """
        Convert the static plugin specification from the Django ORM model format to the Pydantic manifest format.

        This method constructs a `SAMPluginStaticSpec` Pydantic model using the prompt, selector,
        and static data associated with the current `plugin_meta`. It retrieves each component
        using their respective ORM-to-Pydantic conversion methods.

        :return: The static plugin specification as a Pydantic model.
        :rtype: SAMPluginStaticSpec

        **Example:**

        .. code-block:: python

            broker = SAMStaticPluginBroker()
            static_spec = broker.plugin_static_spec_orm2pydantic()
            print(static_spec.model_dump_json())

        :raises SAMPluginBrokerError:
            If there is an error retrieving or converting any component of the plugin specification.


        .. seealso::

            - `SAMPluginStaticSpec`
            - `SAMPluginCommonSpecPrompt`
            - `SAMPluginCommonSpecSelector`
            - `SAMPluginStaticSpecData`
        """
        if self._plugin_static_spec:
            return self._plugin_static_spec
        if not self.plugin_meta:
            return None
        prompt = self.plugin_prompt_orm2pydantic()
        selector = self.plugin_selector_orm2pydantic()
        data = self.plugin_static_spec_data_orm2pydantic()
        if not data:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} plugin_static_spec_orm2pydantic() failed to build data for {self.kind} {self.plugin_meta.name}",
                thing=self.kind,
            )
        self._plugin_static_spec = SAMPluginStaticSpec(
            prompt=prompt,
            selector=selector,
            data=data,
        )
        return self._plugin_static_spec

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for a static plugin.

        This method generates and returns a sample manifest structure for a static plugin, using
        `StaticPlugin.example_manifest`. The response is wrapped in a `SmarterJournaledJsonResponse`
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

            - `StaticPlugin.example_manifest`
            - `SmarterJournaledJsonResponse`
            - `SmarterJournalCliCommands`


        """
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)

        manifest_meta = SAMPluginCommonMetadata(
            name="everlasting_gobstopper",
            description="Get additional information about the Everlasting Gobstopper product created by Willy Wonka Chocolate Factory. Information includes sales promotions, coupon codes, company contact information and biographical background on the company founder.",
            version="0.1.0",
            tags=["candy", "treats", "chocolate", "Gobstoppers", "Willy Wonka"],
            annotations=[
                {"smarter.sh/created_by": "smarter_static_plugin_broker"},
                {"smarter.sh/plugin": "everlasting_gobstopper"},
            ],
            pluginClass=SAMPluginCommonMetadataClassValues.STATIC.value,
        )
        manifest_spec = SAMPluginStaticSpec(
            selector=SAMPluginCommonSpecSelector(
                directive=SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
                searchTerms=[
                    "Gobstopper",
                    "Gobstoppers",
                    "Gobbstopper",
                    "Gobbstoppers",
                ],
            ),
            prompt=SAMPluginCommonSpecPrompt(
                provider=SettingsDefaults.LLM_DEFAULT_PROVIDER,
                systemRole="You are a helpful marketing agent for the [Willy Wonka Chocolate Factory](https://wwcf.com). Whenever possible you should defer to the tool calls provided for additional information about everlasting gobstoppers.",
                model=SettingsDefaults.LLM_DEFAULT_MODEL,
                temperature=SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
                maxTokens=SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
            ),
            data=SAMPluginStaticSpecData(
                staticData={
                    "contact": [
                        {"name": "Willy Wonka"},
                        {"title": "Founder and CEO"},
                        {"location": "1234 Chocolate Factory Way, Chocolate City, Chocolate State, USA"},
                        {"phone": "+1 123-456-7890"},
                        {"website_url": "https://wwcf.com"},
                        {"whatsapp": 11234567890},
                        {"email": "ww@wwcf.com"},
                    ],
                    "biographical": "Willy Wonka is a fictional character appearing in British author Roald Dahl's 1964 children's novel Charlie and the Chocolate Factory, its 1972 sequel Charlie and the Great Glass Elevator and several films based on those books. He is the eccentric founder and proprietor of the Wonka Chocolate Factory\n",
                    "sales_promotions": [
                        {
                            "name": "Everlasting Gobstopper",
                            "description": 'The Everlasting Gobstopper is a candy that, according to Willy Wonka, "Never Gets Smaller Or Ever Gets Eaten". It is the main focus of Charlie and the Chocolate Factory, both the 1971 film and the 2005 film, and Willy Wonka and the Chocolate Factory, the 1971 film adaptation of the novel.\n',
                            "price": "$1.00",
                            "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Everlasting_Gobstopper.jpg/220px-Everlasting_Gobstopper.jpg",
                        },
                        {
                            "name": "Wonka Bar",
                            "description": "Wonka Bars are a fictional brand of chocolate made by Willy Wonka, and also a chocolate bar inspired by the Willy Wonka Bar from the novel and the films Willy Wonka & the Chocolate Factory and Charlie and the Chocolate Factory.\n",
                            "price": "$1.00",
                            "image": "https://m.media-amazon.com/images/I/81E-734cMzL._AC_UF894,1000_QL80_.jpg",
                        },
                    ],
                    "coupon_codes": [
                        {"name": "10% off", "code": "10OFF", "description": "10% off your next purchase\n"},
                        {"name": "20% off", "code": "20OFF", "description": "20% off your next purchase\n"},
                    ],
                }
            ),
        )
        manifest_status = SAMPluginCommonStatus(
            accountNumber="1234-5678-9012",
            username="example_user",
            created=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            modified=datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
        )
        example_manifest = SAMStaticPlugin(
            apiVersion=SmarterApiVersions.V1,
            kind=SAMKinds.STATIC_PLUGIN.value,
            metadata=manifest_meta,
            spec=manifest_spec,
            status=manifest_status,
        )
        return self.json_response_ok(command=command, data=example_manifest.model_dump())

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Serialize and return the manifest for a static plugin as a JSON response.

        This method collects and validates all required components of a static plugin manifest, including metadata,
        prompt configuration, selector criteria, and static data. It ensures that all plugin objects are present and
        ready, and provides informative error responses if any required component is missing or invalid.

        The returned manifest contains the following top-level fields:

        - ``apiVersion``: Manifest API version string.
        - ``kind``: Manifest kind (usually "Plugin").
        - ``metadata``: Plugin metadata (name, description, version, tags, annotations, plugin class).
        - ``spec``: Specification details (prompt configuration, selector criteria, static plugin data).
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
                   "pluginClass": "static"
               },
               "spec": {
                   "prompt": {  },
                   "selector": {  },
                   "data": {  }
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
            - `StaticPlugin.create`
            - `StaticPlugin.save`
            - `SmarterJournaledJsonResponse`
        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        if self.plugin.ready:
            # the Plugin class was initialized with enough data to bring
            # itself to a ready state, meaning that no create/save is needed.
            return self.json_response_ok(command=command, data=self.to_json())

        if not isinstance(self.plugin, StaticPlugin):
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

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Chat with the static plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        super().chat(request, kwargs)
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="chat() not implemented", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the static plugin.

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

            - `StaticPlugin.delete`
            - `SmarterJournaledJsonResponse`
            - :meth:`SAMPluginBaseBroker.set_and_verify_name_param`

        """
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)
        if not isinstance(self.plugin, StaticPlugin):
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
        Deploy the static plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("deploy() not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Undeploy the static plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("undeploy() not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs for the static plugin (not implemented).

        :raises SAMBrokerErrorNotImplemented:
            Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating error.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("logs() not implemented", thing=self.kind, command=command)
