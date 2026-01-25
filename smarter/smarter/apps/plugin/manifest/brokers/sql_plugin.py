# pylint: disable=W0718
"""Smarter API SqlPlugin Manifest handler"""

import logging
from typing import TYPE_CHECKING, Optional, Type

from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.status import (
    SAMPluginCommonStatus,
)
from smarter.apps.plugin.manifest.models.sql_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.sql_plugin.model import SAMSqlPlugin
from smarter.apps.plugin.manifest.models.sql_plugin.spec import (
    Parameter,
    SAMSqlPluginSpec,
    SqlData,
    TestValue,
)
from smarter.apps.plugin.models import PluginDataSql, PluginMeta
from smarter.apps.plugin.plugin.sql import SqlPlugin
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

if TYPE_CHECKING:
    from django.http import HttpRequest


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.MANIFEST_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMSqlPluginBroker(SAMPluginBaseBroker):
    """
    Broker for Smarter SQL Plugin Manifests.

    This class is responsible for loading, validating, and parsing Smarter SQL YAML plugin manifests,
    and for initializing the corresponding Pydantic model. It provides generic services for SQL plugins,
    such as instantiation, creation, update, and deletion.

    **Responsibilities:**

      - Load and validate SQL plugin manifests.
      - Parse manifest data into a structured Pydantic model (`SAMSqlPlugin`).
      - Provide access to plugin metadata, status, and specification.
      - Manage plugin lifecycle operations (create, update, delete, etc.).

    **Example Usage:**

    .. code-block:: python

        broker = SAMSqlPluginBroker(manifest=my_manifest)
        plugin = broker.plugin
        if plugin.ready:
            plugin.create()
            plugin.save()

    **Parameters:**

    :param manifest: Optional; a `SAMSqlPlugin` Pydantic model instance representing the plugin manifest.
    :type manifest: Optional[SAMSqlPlugin]

    .. note::
        If the manifest kind does not match the expected plugin kind, or if required fields are missing,
        the broker may raise a `SAMPluginBrokerError` or related exception.

    """

    # override the base abstract manifest model with the Plugin model
    _manifest: Optional[SAMSqlPlugin] = None
    _pydantic_model: Type[SAMSqlPlugin] = SAMSqlPlugin
    _plugin: Optional[SqlPlugin] = None
    _plugin_meta: Optional[PluginMeta] = None
    _plugin_data: Optional[PluginDataSql] = None
    _sql_plugin_spec: Optional[SAMSqlPluginSpec] = None
    _sql_data: Optional[SqlData] = None

    def __init__(self, *args, **kwargs):
        """
        Initialize the SAMSqlPluginBroker instance.

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

            broker = SAMSqlPluginBroker(loader=loader, plugin_meta=plugin_meta)

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
                self._manifest = SAMSqlPlugin(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMSqlPluginSpec(**self.loader.manifest_spec),
                    status=(
                        SAMPluginCommonStatus(**self.loader.manifest_status)
                        if self.loader and self.loader.manifest_status
                        else None
                    ),
                )
            if self._manifest:
                logger.info(
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

    def plugin_init(self) -> None:
        """
        Initialize the SQL plugin for this broker.

        This method creates an instance of the `SqlPlugin` class using the current broker's
        metadata, user profile, manifest, and name. It assigns the created plugin to the
        broker's internal `_plugin` attribute for future access.

        :return: None

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=my_manifest)
            broker.plugin_init()
            plugin = broker.plugin
            if plugin.ready:
                plugin.create()
                plugin.save()
        """
        super().plugin_init()
        self._manifest = None
        self._plugin = None
        self._plugin_meta = None
        self._plugin_data = None
        self._sql_plugin_spec = None
        self._sql_data = None

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns a formatted class name for logging.

        This property provides a human-readable, fully qualified class name, which is especially useful for log messages
        and debugging output. The format includes the parent class's formatted name, followed by the current class name.

        :return: A string representing the formatted class name, e.g., ``ParentClass.SAMSqlPluginBroker()``.
        :rtype: str

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=my_manifest)
            print(broker.formatted_class_name)
            # Output: ParentClass.SAMSqlPluginBroker()

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{SAMSqlPluginBroker.__name__}[{id(self)}]"

    @property
    def ORMModelClass(self) -> Type[PluginDataSql]:
        """
        Return the Django ORM model class for the broker.

        :return: The Django ORM model class definition for the broker.
        :rtype: Type[PluginDataSql]
        """
        return PluginDataSql

    @property
    def SAMModelClass(self) -> Type[SAMSqlPlugin]:
        """
        Return the Pydantic model class for the broker.

        :return: The Pydantic model class definition for the broker.
        :rtype: Type[SAMSqlPlugin]
        """
        return SAMSqlPlugin

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind for this plugin broker.

        This property provides the canonical string identifier for the SQL plugin manifest type,
        as defined by the constant ``MANIFEST_KIND``. It is used to distinguish this broker's
        manifest type from others in the Smarter API system.

        :return: The manifest kind string for SQL plugins.
        :rtype: str

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=my_manifest)
            print(broker.kind)
            # Output: "SqlPlugin"  # (or the value of MANIFEST_KIND)

        .. seealso::
            :data:`MANIFEST_KIND`
            :attr:`SAMSqlPluginBroker.manifest`

        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMSqlPlugin]:
        """
        Returns the SQL plugin manifest as a validated Pydantic model instance.

        This property constructs and caches a `SAMSqlPlugin` object using data from the manifest loader,
        including API version, kind, metadata, specification, and status. Child models (such as metadata,
        spec, and status) are automatically initialized by Pydantic.

        If the manifest loader's kind matches the expected plugin kind, the manifest is created and cached
        for future access. If the manifest has already been initialized, the cached instance is returned.

        :return: The initialized SQL plugin manifest as a Pydantic model, or ``None`` if not available.
        :rtype: Optional[SAMSqlPlugin]

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=None)
            manifest = broker.manifest
            if manifest:
                print(manifest.apiVersion)

        .. seealso::

            :class:`SAMSqlPlugin`
            :attr:`SAMSqlPluginBroker.kind`
            :class:`SAMPluginCommonMetadata`
            :class:`SAMSqlPluginSpec`
            :class:`SAMPluginCommonStatus`

        """

        if self._manifest:
            if not isinstance(self._manifest, SAMSqlPlugin):
                raise SAMPluginBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest
        # 1.) prioritize manifest loader data if available. if it was provided
        #     in the request body then this is the authoritative source.
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMSqlPlugin(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMPluginCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlPluginSpec(**self.loader.manifest_spec),
                status=(
                    SAMPluginCommonStatus(**self.loader.manifest_status)
                    if self.loader and self.loader.manifest_status
                    else None
                ),
            )
        # 2.) next, (and only if a loader is not available) try to initialize
        #     from existing Account model if available
        elif self._plugin_meta:
            metadata = self.plugin_metadata_orm2pydantic()
            sql_data = self.plugin_data_orm2pydantic()
            if not sql_data:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} manifest() failed to build sql_data for {self.kind} {self.plugin_meta.name}",
                    thing=self.kind,
                )
            spec = self.plugin_sql_spec_orm2pydantic()
            if not spec:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} manifest() failed to build spec for {self.kind} {self.plugin_meta.name}",
                    thing=self.kind,
                )
            status = self.plugin_status_pydantic()

            # build the manifest from the
            self._manifest = SAMSqlPlugin(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=metadata,
                spec=spec,
                status=status,
            )
            return self._manifest
        else:
            logger.warning("%s.manifest could not be initialized", self.formatted_class_name)
        return self._manifest

    @property
    def plugin(self) -> Optional[SqlPlugin]:
        """
        Returns the initialized `SqlPlugin` instance for this broker.

        This property creates and caches a `SqlPlugin` object using the current broker's metadata, user profile,
        manifest, and name. If the plugin has already been initialized, the cached instance is returned.

        :return: The initialized `SqlPlugin` instance, or ``None`` if not available.
        :rtype: Optional[SqlPlugin]

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=my_manifest)
            plugin = broker.plugin
            if plugin and plugin.ready:
                plugin.create()
                plugin.save()

        .. seealso::

            :class:`SqlPlugin`
            :attr:`SAMSqlPluginBroker.manifest`
            :attr:`SAMSqlPluginBroker.plugin_meta`

        """
        if self._plugin:
            return self._plugin
        self._plugin = SqlPlugin(
            plugin_meta=self.plugin_meta,
            user_profile=self.user_profile,
            manifest=self._manifest,
            name=self.name,
        )
        return self._plugin

    @property
    def plugin_data(self) -> Optional[PluginDataSql]:
        """
        Returns the `PluginDataSql` ORM object associated with this broker.

        This property retrieves and caches the `PluginDataSql` instance for the current plugin, which is used
        to store and manage plugin-specific data in the database. If the object does not exist, a warning is logged
        and ``None`` is returned.

        :return: The `PluginDataSql` object for this broker, or ``None`` if not available.
        :rtype: Optional[PluginDataSql]

        :raises: :class:`PluginDataSql.DoesNotExist` if the object is not found in the database.

        **Example:**

        .. code-block:: python

            broker = SAMSqlPluginBroker(manifest=my_manifest)
            data = broker.plugin_data
            if data:
                print(data.connection)


        .. seealso::

            :class:`PluginDataSql`
            :attr:`SAMSqlPluginBroker.plugin_meta`

        """
        if self._plugin_data:
            return self._plugin_data

        if self.plugin_meta is None:
            logger.warning(
                "%s.plugin_data could not be retrieved because plugin_meta is None",
                self.formatted_class_name,
            )
            return None

        self._plugin_data = PluginDataSql.get_cached_data_by_plugin(plugin=self.plugin_meta)
        if not self._plugin_data:
            logger.warning(
                "%s.plugin_data could not be found for %s %s",
                self.formatted_class_name,
                self.kind,
                self.plugin_meta.name,
            )
        return self._plugin_data

    def plugin_sql_spec_orm2pydantic(self) -> Optional[SAMSqlPluginSpec]:
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
        if self._sql_plugin_spec:
            return self._sql_plugin_spec
        if not self.plugin_meta:
            logger.warning(
                "%s.plugin_sql_spec_orm2pydantic could not be built for %s %s because plugin_meta is None",
                self.formatted_class_name,
                self.kind,
                self.manifest.metadata.name if self.manifest and self.manifest.metadata else "<-- Missing Name -->",
            )
            return None
        selector = self.plugin_selector_orm2pydantic()
        prompt = self.plugin_prompt_orm2pydantic()
        data = self.plugin_data_orm2pydantic()
        if not data:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} plugin_static_spec_orm2pydantic() failed to build data for {self.kind} {self.plugin_meta.name}",
                thing=self.kind,
            )
        self._sql_plugin_spec = SAMSqlPluginSpec(
            selector=selector,
            prompt=prompt,
            connection=(
                self.plugin_data.connection.name
                if self.plugin_data and self.plugin_data.connection
                else "missing connection"
            ),
            sqlData=data,
        )
        return self._sql_plugin_spec

    def plugin_data_orm2pydantic(self) -> Optional[SqlData]:
        """
        Overrides the parent method to map SQL plugin data from ORM to Pydantic.
        Converts the plugin data from the Django ORM model format to the Pydantic manifest format.

        This method constructs a `SqlData` Pydantic model using the data associated with the current
        `plugin_meta`. It retrieves the data using the ORM-to-Pydantic conversion method.

        Parameters:
            parameters (dict): An OpenAI API-compliant dictionary of parameters to pass to the API call, e.g.::

                {
                    'type': 'object',
                    'required': ['username'],
                    'properties': {
                        'unit': {
                            'enum': ['Celsius', 'Fahrenheit'],
                            'type': 'string',
                            'default': 'Celsius',
                            'description': 'The temperature unit to use.'
                        },
                        'username': {
                            'type': 'string',
                            'default': 'admin',
                            'description': 'The username to query.'
                        }
                    },
                    'additionalProperties': False
                }

        Returns:
            SqlData: The plugin data as a Pydantic model.

        Example:

            .. code-block:: python

                broker = SAMSqlPluginBroker()
                sql_data = broker.plugin_data_orm2pydantic()
                print(sql_data.model_dump_json())

        Raises:
            SAMPluginBrokerError: If there is an error retrieving or converting the plugin data.

        See Also:
            - SqlData
        """
        if not self.plugin_meta:
            return None

        parameters: list[Parameter] = []
        orm_parameters: dict = self.plugin_data.parameters if self.plugin_data else {}
        if not isinstance(orm_parameters, dict):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} plugin_data_orm2pydantic() expected parameters to be a dict for {self.kind} {self.plugin_meta.name} but got {type(orm_parameters)}: {orm_parameters}",
                thing=self.kind,
            )

        # Handle OpenAPI-style parameter schema
        # Example: {
        #   'type': 'object',
        #   'required': ['username'],
        #   'properties': { ... }
        # }
        required_fields = orm_parameters.get("required", [])
        properties = orm_parameters.get("properties", {})
        for name, prop in properties.items():
            parameters.append(
                Parameter(
                    name=name,
                    type=prop.get("type", "string"),
                    description=prop.get("description"),
                    required=name in required_fields,
                    enum=prop.get("enum"),
                    default=prop.get("default"),
                )
            )
        test_values: list[TestValue] = []
        orm_test_values: list = self.plugin_data.test_values if self.plugin_data else []
        if not isinstance(orm_test_values, list):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} plugin_data_orm2pydantic() expected test_values to be a list for {self.kind} {self.plugin_meta.name} but got {type(orm_test_values)}: {orm_test_values}",
                thing=self.kind,
            )
        for test_value in orm_test_values:
            logger.info(
                "%s.plugin_data_orm2pydantic() processing test_value: %s", self.formatted_class_name, test_value
            )
            # example:  {'name': 'username', 'value': 'admin'}
            if not isinstance(test_value, dict):
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} plugin_data_orm2pydantic() expected each test_value to be a dict for {self.kind} {self.plugin_meta.name} but got {type(test_value)}: {test_value}",
                    thing=self.kind,
                )
            if not "name" in test_value or not "value" in test_value:
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} plugin_data_orm2pydantic() expected each test_value to have 'name' and 'value' keys for {self.kind} {self.plugin_meta.name} but got: {test_value}",
                    thing=self.kind,
                )
            test_values.append(
                TestValue(
                    name=test_value.get("name"),  # type: ignore
                    value=test_value.get("value"),  # type: ignore
                )
            )
        self._sql_data = SqlData(
            sqlQuery=self.plugin_data.sql_query if self.plugin_data else "",
            parameters=parameters,
            testValues=test_values,
            limit=self.plugin_data.limit if self.plugin_data else 0,
        )
        return self._sql_data

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def example_manifest(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Returns an example SQL plugin manifest as a JSON response.

        This method generates a sample manifest for the SQL plugin using the static
        ``example_manifest`` method of the `SqlPlugin` class. The response is wrapped in a
        `SmarterJournaledJsonResponse` for consistency with the Smarter API's journaling and
        response conventions.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments passed to the example manifest generator.
        :return: A JSON response containing the example SQL plugin manifest.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.example_manifest(request)
            print(response.data)

        .. seealso::

            :meth:`SqlPlugin.example_manifest`
            :class:`SmarterJournaledJsonResponse`

        """
        logger.debug(
            "%s.example_manifest() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = SqlPlugin.example_manifest(kwargs=kwargs)
        return self.json_response_ok(command=command, data=data)

    def describe(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response with the manifest data for this SQL plugin.

        This method serializes the current SQL plugin's manifest, metadata, specification, and status
        into a structured JSON response, suitable for API clients or UI inspection. It validates the
        manifest by round-tripping the data through the Pydantic model to ensure schema compliance.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments for customization.
        :return: A `SmarterJournaledJsonResponse` containing the manifest data.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.describe(request)
            print(response.data)

        :raises SAMPluginBrokerError: If required plugin components are not initialized.
        :raises SAMBrokerErrorNotReady: If the broker is not ready to describe the plugin.

        .. seealso::

            :meth:`SAMSqlPluginBroker.manifest`
            :class:`SmarterJournaledJsonResponse`
            :class:`SAMPluginBrokerError`
            :class:`SAMBrokerErrorNotReady`
            :class:`SqlPlugin`
            :class:`SmarterJournalCliCommands`
            :class:`SAMSqlPlugin`
            :class:`SAMKeys`
            :class:`SqlData`
            :class:`SAMPluginSpecKeys`
            :class:`SAMPluginMeta`

        """
        logger.debug(
            "%s.describe() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)

        if not self.manifest:
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.kind} plugin_meta not initialized. Cannot describe",
                thing=self.kind,
                command=command,
            )
        data = json.loads(self.manifest.model_dump_json())
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest: copy manifest data to the Django ORM model and save it to the database.

        This method loads and validates the manifest, then applies its data to the corresponding
        Django ORM model. The plugin is created and, if ready, saved to the database. The response
        includes the serialized plugin data or an error message if the operation fails.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments for customization.
        :return: A `SmarterJournaledJsonResponse` indicating success or failure.
        :rtype: SmarterJournaledJsonResponse

        **Example:**

        .. code-block:: python

            response = broker.apply(request)
            print(response.data)

        :raises SAMPluginBrokerError:
            If the manifest is not set or is not a valid `SAMSqlPlugin`
        :raises SAMBrokerErrorNotReady:
            If the plugin is not ready

        .. seealso::
            :meth:`SAMSqlPluginBroker.manifest`
            :class:`SAMSqlPlugin`
            :class:`SqlPlugin`
            :class:`SmarterJournaledJsonResponse`
            :class:`SAMPluginBrokerError`
            :class:`SAMBrokerErrorNotReady`
        """
        logger.debug(
            "%s.apply() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)

        if not self.user.is_staff:
            raise SAMBrokerError(
                message="Only account admins can apply sql plugin manifests.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )

        if not isinstance(self.manifest, SAMSqlPlugin):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.plugin_meta.name if self.plugin_meta else '<-- Missing Name -->'} manifest is not set",
                thing=self.kind,
                command=command,
            )
        try:
            self._plugin = SqlPlugin(
                user_profile=self.user_profile,
                manifest=self.manifest,
            )
            if not isinstance(self.plugin, SqlPlugin):
                raise SAMPluginBrokerError(
                    f"{self.formatted_class_name} {self.plugin_meta.name if self.plugin_meta else '<-- Missing Name -->'} is not a SqlPlugin",
                    thing=self.kind,
                    command=command,
                )
            self.plugin.create()
        except Exception as e:
            return self.json_response_err(command=command, e=e)

        if self.plugin.ready:
            try:
                self.plugin.save()
            except Exception as e:
                return self.json_response_err(command=command, e=e)
            return self.json_response_ok(command=command, data=self.to_json())
        try:
            raise SAMBrokerErrorNotReady(
                f"{self.formatted_class_name} {self.plugin_meta.name if self.plugin_meta else self.kind or "SqlPlugin"} not ready",
                thing=self.kind,
                command=command,
            )
        except SAMBrokerErrorNotReady as err:
            return self.json_response_err(command=command, e=err)

    def chat(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Chat with the SQL plugin (not implemented).
        This is not implemented for SQL plugins.

        :raises: SAMBrokerErrorNotImplemented: Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :return: A `SmarterJournaledJsonResponse` indicating that the method is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.chat() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="chat() not implemented", thing=self.kind, command=command)

    def delete(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the SQL plugin.
        This method deletes the SQL plugin associated with this broker. It verifies that the plugin
        is of the correct type and is ready before attempting deletion. If successful, it returns a
        JSON response indicating success; otherwise, it raises appropriate errors.

        :raises: SAMPluginBrokerError: If the plugin or plugin metadata is not properly initialized.
        :raises: SAMBrokerErrorNotReady: If the plugin is not ready for deletion.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :return: A `SmarterJournaledJsonResponse` indicating success or failure of the deletion.
        :rtype: SmarterJournaledJsonResponse

        .. seealso::

            :class:`SqlPlugin`
            :class:`SmarterJournaledJsonResponse`
            :class:`SAMPluginBrokerError`
            :class:`SAMBrokerErrorNotReady`
            :class:`SmarterJournalCliCommands`

        """
        logger.debug(
            "%s.delete() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)

        if not self.user.is_staff:
            raise SAMBrokerError(
                message="Only account admins can delete sql plugins.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )

        self.set_and_verify_name_param(command=command)
        if not isinstance(self.plugin, SqlPlugin):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} {self.plugin_meta.name if self.plugin_meta else '<-- Missing Name -->'} delete() not implemented for {self.kind}",
                thing=self.kind,
                command=command,
            )
        if not isinstance(self.plugin_meta, PluginMeta):
            raise SAMPluginBrokerError(
                f"{self.formatted_class_name} <-- Missing Name --> delete() not implemented for {self.kind}",
                thing=self.kind,
                command=command,
            )
        if not self.plugin.ready:
            raise SAMBrokerErrorNotReady(
                f"{self.formatted_class_name} {self.plugin_meta.name} not ready", thing=self.kind, command=command
            )
        try:
            self.plugin.delete()
            return self.json_response_ok(command=command, data={})
        except Exception as e:
            raise SAMBrokerError(
                f"{self.formatted_class_name} {self.plugin_meta.name} delete failed {e}",
                thing=self.kind,
                command=command,
            ) from e

    def deploy(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Deploy the SQL plugin (not implemented).
        This is not implemented for SQL plugins.

        :raises: SAMBrokerErrorNotImplemented: Always raised to indicate that this method is not implemented.
        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :return: A `SmarterJournaledJsonResponse` indicating that the method is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.deploy() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("deploy() not implemented", thing=self.kind, command=command)

    def undeploy(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Undeploy the SQL plugin (not implemented).
        This is not implemented for SQL plugins.

        :raises: SAMBrokerErrorNotImplemented: Always raised to indicate that this method is not implemented.

        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :return: A `SmarterJournaledJsonResponse` indicating that the method is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.undeploy() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("undeploy() not implemented", thing=self.kind, command=command)

    def logs(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs for the SQL plugin (not implemented).
        This is not implemented for SQL plugins.

        :raises: SAMBrokerErrorNotImplemented: Always raised to indicate that this method is not implemented.
        :param request: The HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :return: A `SmarterJournaledJsonResponse` indicating that the method is not implemented.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.logs() called for %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            args,
            kwargs,
        )
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented("logs() not implemented", thing=self.kind, command=command)
