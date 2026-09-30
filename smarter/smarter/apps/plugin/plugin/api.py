"""
A Plugin that uses a remote REST API server to retrieve its return data.

.. note::

    This is a complex AI resource that exists within the following class hierarchy

    1. Smarter Secret: The authentication credential for the remote API connection.
    2. Smarter API Connection: The complete connection configuration to the remote REST API server (base url, authentication method, api key, timeout, proxy, etc.).
    3. Smarter API Plugin: The plugin that defines the API endpoint, HTTP method, headers, body and parameters to send to the remote REST API server.
    4. Smarter LLMClient: The prompting resource (LLMClient, Agent, Workflow unit, etcetera) that includes the API Plugin:

.. sphinx note: these are relative to the rst doc that calls automodule on this file.

.. literalinclude:: ../../../../../smarter/smarter/apps/account/data/example-manifests/secret-smarter-test-api.yaml
    :language: yaml
    :caption: 1.) Example Smarter Secret Manifest

.. literalinclude:: ../../../../../smarter/smarter/apps/connection/data/sample-connections/smarter-test-api.yaml
    :language: yaml
    :caption: 2.) Example Smarter API Connection Manifest

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/stackademy/stackademy-plugin-api.yaml
    :language: yaml
    :caption: 3.) Example Stackademy API Plugin Manifest

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/stackademy/stackademy-llmclient-api.yaml
    :language: yaml
    :caption: 4.) Example Stackademy LLMClient Manifest
"""

import re
from datetime import datetime
from typing import Any, Optional, Type, Union
from urllib.parse import quote

from django.core.exceptions import MultipleObjectsReturned

from smarter.apps.connection.models import ApiConnection
from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
    SAMPluginSpecKeys,
)
from smarter.apps.plugin.manifest.models.api_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.api_plugin.model import SAMApiPlugin
from smarter.apps.plugin.manifest.models.api_plugin.spec import (
    ApiData,
    SAMApiPluginSpec,
)
from smarter.apps.plugin.manifest.models.common import (
    Parameter,
    ParameterType,
    RequestHeader,
    TestValue,
    UrlParam,
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
from smarter.apps.plugin.models import PluginDataApi, PluginMeta
from smarter.apps.plugin.serializers import PluginApiSerializer
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import settings_defaults
from smarter.common.const import SMARTER_ADMIN_USERNAME, SmarterHttpMethods
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils import to_snake_case
from smarter.lib import json, logging
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys

from .base import PluginBase, SmarterPluginError


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
MAX_API_RESULTS = 1000  # Maximum number of API response rows to return, to prevent excessive load on the remote API


class SmarterApiPluginError(SmarterPluginError):
    """Base class for all API plugin errors."""


class ApiPlugin(PluginBase):
    """
    Implements a plugin that sends HTTP requests to a remote REST API server to retrieve data.

    This class provides the logic for integrating REST API-based plugins into the Smarter platform. It supports
    manifest-driven configuration, parameter validation, and authenticated request execution. The plugin can be
    instantiated from either a manifest (Pydantic model) or an existing Django ORM instance.

    Key Features:

        - Accepts plugin configuration via manifest or ORM model.
        - Validates and recasts parameter definitions to conform to OpenAI function calling schema.
        - Interpolates user-provided arguments into ``{placeholder}`` path segments of the endpoint, with URL encoding.
        - Sends remaining arguments as URL query string parameters (``GET``, ``DELETE``) or as JSON body fields (``POST``, ``PUT``, ``PATCH``).
        - Executes requests using a remote API connection, which supplies the base url, authentication and timeout.
        - Handles errors related to configuration, connection, and request execution.
        - Provides example manifest generation for testing and documentation.

    Usage:

        - Instantiate with a manifest or ORM model.
        - Use `tool_call_fetch_plugin_response()` to execute API requests with arguments from OpenAI tool calls.
        - Use `plugin_data_django_model` to convert manifest data to a Django ORM-compatible dictionary.
        - Use `example_manifest()` to generate a sample manifest for this plugin type.

    .. note::

        - Static ``urlParams``, ``headers`` and ``body`` from the manifest are sent with every request. Arguments
          from the LLM tool call take precedence over static values of the same name.
        - The maximum number of returned rows is limited to prevent excessive load on the remote API.
        - Only ``GET`` responses are cached. Failed requests are never cached.
        - Logging is controlled via feature switches and log level settings.

    .. seealso::

        - OpenAI Function Calling: https://platform.openai.com/docs/guides/function-calling?api-mode=prompt
        - Smarter Plugin Manifest Documentation
    """

    SAMPluginType = SAMApiPlugin

    _manifest: Optional[SAMApiPlugin] = None
    _metadata_class = SAMPluginCommonMetadataClass.API.value
    _plugin_data: PluginDataApi | None = None
    _plugin_data_serializer: PluginApiSerializer | None = None

    def __init__(
        self,
        *args,
        manifest: Optional[SAMApiPlugin] = None,
        **kwargs,
    ):
        super().__init__(*args, manifest=manifest, **kwargs)

    @property
    def kind(self) -> str:
        """
        Returns the kind identifier for this plugin.

        This property provides the canonical string used to distinguish the plugin type within the Smarter platform.
        The value is derived from the plugin manifest constant and is used for registration, serialization, and
        manifest validation.

        The kind is typically referenced in plugin manifests and API payloads to ensure the correct plugin logic
        is invoked for API-based plugins.

        :returns: The string identifier representing the plugin kind.
        :rtype: str

        :example:

            >>> plugin = ApiPlugin()
            >>> plugin.kind
            'api'
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMApiPlugin]:
        """
        Retrieve the manifest for this plugin as a Pydantic model.

        This property returns the plugin's manifest, which contains the configuration and specification
        for the API plugin in the form of a validated Pydantic model. If the manifest is not already set
        and the plugin is ready, it will be constructed from the current plugin data using the appropriate
        Pydantic model class.

        The manifest is essential for validating plugin configuration, generating OpenAI-compatible schemas,
        and ensuring the plugin operates with the correct parameters and metadata.

        :returns: The manifest as a ``SAMApiPlugin`` Pydantic model instance, or ``None`` if unavailable.
        :rtype: Optional[SAMApiPlugin]

        .. note::

            If the manifest is not present but the plugin is ready, this property will attempt to reconstruct
            the manifest from the plugin's JSON representation.

        :example:

            >>> plugin = ApiPlugin()
            >>> manifest = plugin.manifest
            >>> print(manifest.spec.apiData.endpoint)
            /stackademy/course-catalogue/
        """
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = self.SAMPluginType(**self.to_json())  # type: ignore[call-arg]
        return self._manifest

    @property
    def plugin_data(self) -> Optional[PluginDataApi]:
        """
        Return the plugin data as a Django ORM instance.

        This property provides access to the plugin's data in the form of a Django ORM model instance.
        It handles multiple scenarios for retrieving or constructing the plugin data:

        - If the plugin data has already been set, it is returned directly.
        - If both a manifest and plugin metadata are present, the plugin data is constructed from the manifest and metadata.
        - If only plugin metadata is present, the plugin data is retrieved from the database using the metadata.
        - If neither is available, the property returns ``None``.

        This logic ensures that the plugin data is always consistent with the current manifest and database state,
        supporting both creation and update workflows.

        :returns: The plugin data as a ``PluginDataApi`` Django ORM instance, or ``None`` if unavailable.
        :rtype: Optional[PluginDataApi]

        :raises PluginDataApi.DoesNotExist: If the plugin metadata is present but no corresponding database entry exists.

        .. note::

            This property does not create new database entries; it only retrieves or constructs plugin data
            based on existing manifest and metadata.

        :example:

            >>> plugin = ApiPlugin()
            >>> data = plugin.plugin_data
            >>> print(data.endpoint)
            /stackademy/course-catalogue/
        """
        if self._plugin_data:
            return self._plugin_data

        try:
            self._plugin_data = PluginDataApi.get_cached_object(plugin=self.plugin_meta)  # type: ignore[call-arg]
            logger.debug(
                "%s.plugin_data() retrieved existing PluginDataApi from database.",
                self.formatted_class_name,
            )
            return self._plugin_data
        except PluginDataApi.DoesNotExist:
            logger.debug(
                "%s.plugin_data() no existing PluginDataApi found in database for plugin_meta: %s",
                self.formatted_class_name,
                self.plugin_meta,
            )

        # we only want a preexisting manifest ostensibly sourced
        # from the cli, not a lazy-loaded
        if self._manifest and self.plugin_meta:
            # this is an update scenario. the Plugin exists in the database,
            # AND we've received manifest data from the cli.
            self._plugin_data = PluginDataApi(**self.plugin_data_django_model)  # type: ignore[call-arg]
            self._plugin_data.save()
            logger.debug(
                "%s.plugin_data() created new instance of %s from manifest and plugin metadata.",
                self.formatted_class_name,
                self.plugin_data_class.__name__,
            )
        if self.plugin_meta:
            # we don't have a Pydantic model but we do have an existing
            # Django ORM model instance, so we can use that directly.
            logger.debug(
                "%s.plugin_data() retrieving PluginDataApi from database using plugin metadata.",
                self.formatted_class_name,
            )
            self._plugin_data = PluginDataApi.get_cached_data_by_plugin(
                plugin=self.plugin_meta,
            )
        # new Plugin scenario. there's nothing in the database yet.
        return self._plugin_data

    @property
    def plugin_data_class(self) -> Type[PluginDataApi]:
        """
        Return the Django ORM model class used for plugin data.

        This property provides the class reference for the Django model that stores
        API plugin data in the Smarter platform. It is useful for type checking,
        serialization, and for constructing new instances of plugin data objects.

        The returned class can be used to create, query, or update plugin data
        records in the database. This is especially relevant when integrating
        with Django's ORM or when performing migrations and schema validation.

        :returns: The Django ORM model class for API plugin data.
        :rtype: Type[PluginDataApi]

        :example:

            >>> plugin = ApiPlugin()
            >>> model_cls = plugin.plugin_data_class
            >>> isinstance(model_cls(), PluginDataApi)
            True
        """
        return PluginDataApi

    @property
    def plugin_data_serializer(self) -> Optional[PluginApiSerializer]:
        """
        Return the serializer instance for plugin data.

        This property provides a serializer object for the API plugin's data, allowing
        conversion between Django ORM model instances and JSON-compatible representations.
        The serializer is used for validating, serializing, and deserializing plugin data,
        especially when preparing data for API responses or manifest generation.

        If the serializer has not yet been instantiated, it will be created using the
        current plugin data. This ensures that the serializer always reflects the latest
        state of the plugin's data.

        :returns: An instance of ``PluginApiSerializer`` for the plugin data, or ``None`` if plugin data is unavailable.
        :rtype: Optional[PluginApiSerializer]

        :example:

            >>> plugin = ApiPlugin()
            >>> serializer = plugin.plugin_data_serializer
            >>> print(serializer.data)
            {'endpoint': '/stackademy/course-catalogue/', 'method': 'GET', ...}
        """
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginApiSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> Type[PluginApiSerializer]:
        """
        Return the serializer class used for API plugin data.

        This property provides the class reference for the serializer that is responsible
        for converting API plugin data between Django ORM model instances and JSON-compatible
        representations. The serializer class is essential for validation, serialization,
        and deserialization of plugin data, especially when integrating with APIs or
        generating manifests.

        Use this property when you need to instantiate a new serializer for API plugin data,
        perform type checks, or access serializer-specific methods and attributes.

        :returns: The serializer class for API plugin data.
        :rtype: Type[PluginApiSerializer]

        :example:

            >>> plugin = ApiPlugin()
            >>> serializer_cls = plugin.plugin_data_serializer_class
            >>> serializer = serializer_cls(plugin.plugin_data)
            >>> isinstance(serializer, PluginApiSerializer)
            True
        """
        return PluginApiSerializer

    @property
    def plugin_data_django_model(self) -> Optional[dict[str, Any]]:
        """
        Transform the Pydantic model to the PluginDataApi Django ORM model and return the plugin data definition as a JSON object.

        See the OpenAI documentation:
        https://platform.openai.com/docs/guides/function-calling?api-mode=prompt

        The Pydantic 'Parameters' model is not directly compatible with OpenAI's function calling schema,
        and our Django ORM model expects a dictionary format for the parameters. This method converts
        the Pydantic model to a dictionary suitable for creating a Django ORM model instance.

        :raises SmarterApiPluginError: If the plugin manifest or API data is missing or invalid.
        :raises SmarterConfigurationError: If the parameters are not in the expected format.
        :returns: A dictionary representing the PluginDataApi Django ORM model.
        :rtype: Optional[dict[str, Any]]

        **Example of a correctly formatted dictionary:**

        .. code-block:: python

            {
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g., San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["Celsius", "Fahrenheit"],
                        "description": "The temperature unit to use. Infer this from the user's location."
                    }
                },
                "required": ["location", "unit"]
            }

        **Example of a Pydantic model:**

        .. code-block:: python

            [
                {
                    "name": "max_cost",
                    "type": "float",
                    "description": "the maximum cost that a student is willing to pay for a course.",
                    "required": False,
                    "enum": None,
                    "default": None
                },
                {
                    "name": "description",
                    "type": "string",
                    "description": "areas of specialization for courses in the catalogue.",
                    "required": False,
                    "enum": ["AI", "mobile", "web", "database", "network", "neural networks"],
                    "default": None
                }
            ]

        .. code-block:: yaml

            spec:
                selector:
                    directive: search_terms
                    searchTerms:
                    - admin
                    - Smarter platform
                    - admin account
                prompt:
                    provider: openai
                    systemRole: >
                    You are a helpful assistant for Smarter platform. You can provide information about the admin account of the Smarter platform.
                    model: gpt-4o-mini
                    temperature: 0.0
                    maxTokens: 256
                connection: test_api_connection
                apiData:
                    endpoint: /v1/weather/{location}/
                    method: GET
                    headers:
                    - name: Accept
                      value: application/json
                    parameters:
                    - name: location
                      type: string
                      description: The city and state, e.g., San Francisco, CA
                      required: true
                    - name: unit
                      type: string
                      enum:
                      - Celsius
                      - Fahrenheit
                      description: The temperature unit to use.
                      required: false
                      default: Celsius
                    testValues:
                    - name: location
                      value: San Francisco, CA
                    - name: unit
                      value: Celsius
                    limit: 10
        """
        if not self._manifest:
            return None

        if not isinstance(self.plugin_meta, PluginMeta):
            logger.debug(
                "%s.plugin_data_django_model() plugin_meta is not set. plugin_meta: %s",
                self.formatted_class_name,
                self.plugin_meta,
            )

        if not isinstance(self.manifest, SAMApiPlugin):
            raise SmarterApiPluginError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} plugin manifest is not available."
            )

        api_data = self.manifest.spec.apiData.model_dump() if self.manifest else None
        if not api_data:
            raise SmarterApiPluginError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} missing required API data."
            )
        api_data = {to_snake_case(key): value for key, value in api_data.items()}

        connection_name = self._manifest.spec.connection if self._manifest else None
        if connection_name:
            # recast the Pydantic model to the PluginDataApi Django ORM model
            plugin_data_apiconnection: Optional[ApiConnection] = None
            account = self.user_profile.cached_account if self.user_profile else None
            try:
                plugin_data_apiconnection = ApiConnection.objects.get(
                    user_profile__account=account,
                    name=connection_name,
                )
            except ApiConnection.DoesNotExist:
                pass
            except MultipleObjectsReturned:
                try:
                    # narrow the search to exactly the user_profile
                    # that authenticated the request.
                    plugin_data_apiconnection = ApiConnection.objects.get(
                        user_profile=self.user_profile,
                        name=connection_name,
                    )
                except ApiConnection.DoesNotExist:
                    pass
            if not plugin_data_apiconnection:
                raise SmarterApiPluginError(
                    f"{self.formatted_class_name}.plugin_data_django_model() error: ApiConnection {connection_name} does not exist for account {account}."
                )

            plugin_data_apiconnection.authorize()
            api_data["connection"] = plugin_data_apiconnection

        # recast the Pydantic model's parameters field
        # to conform to openai's function calling schema.
        recasted_parameters = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
        parameters = self.manifest.spec.apiData.parameters if self.manifest and self.manifest.spec else None
        if parameters and not isinstance(parameters, list):
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} parameters must be a list of dictionaries. Received: {parameters} {type(parameters)}"
            )
        if parameters:
            logger.debug("%s.plugin_data_django_model() recasting parameters", self.formatted_class_name)
            for parameter in parameters:
                if not isinstance(parameter, Parameter):
                    raise SmarterConfigurationError(
                        f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} each parameter must be a Pydantic Parameter model. Received: {parameter} {type(parameter)}"
                    )
                # if the parameter is a Pydantic model, we need to convert it to a
                # standard json dict.
                parameter = parameter.model_dump()
                logger.debug(
                    "%s.plugin_data_django_model() processing parameter: %s",
                    self.formatted_class_name,
                    parameter,
                )
                if not isinstance(parameter, dict):
                    raise SmarterConfigurationError(
                        f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} each parameter must be a valid json dict. Received: {parameter} {type(parameter)}"
                    )
                if "name" not in parameter or "type" not in parameter:
                    raise SmarterConfigurationError(
                        f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} each parameter must have a 'name' and 'type' field. Received: {parameter}"
                    )
                recasted_parameters["properties"][parameter["name"]] = {
                    "type": parameter["type"],
                    "description": parameter.get("description", ""),
                }
                if "enum" in parameter and parameter["enum"]:
                    if not isinstance(parameter["enum"], list):
                        raise SmarterConfigurationError(
                            f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} parameter 'enum' must be a list. Received: {parameter['enum']} {type(parameter['enum'])}"
                        )
                    recasted_parameters["properties"][parameter["name"]]["enum"] = parameter["enum"]
                if parameter.get("required", False):
                    recasted_parameters["required"].append(parameter["name"])
                if "default" in parameter and parameter["default"] is not None:
                    recasted_parameters["properties"][parameter["name"]]["default"] = parameter["default"]

            api_data["parameters"] = recasted_parameters

        return {
            "plugin": self.plugin_meta,
            "description": (
                self.manifest.metadata.description
                if self.manifest and self.manifest.metadata
                else self.plugin_meta.description if self.plugin_meta else "no description"
            ),
            **api_data,
        }  # type: ignore[call-arg]

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict] = None) -> dict:
        """
        Use Pydantic models to generate an example manifest for ApiPlugin.

        This class method creates a sample manifest dictionary for the ApiPlugin,
        illustrating the required structure and fields. The example manifest includes
        metadata, specification, and API query details, demonstrating how to configure
        the plugin for use within the Smarter platform.

        :param kwargs: Optional dictionary of additional fields to include in the manifest.
        :returns: A dictionary representing the example manifest for the ApiPlugin.
        :rtype: dict

        See Also:

        - :py:class:`smarter.lib.manifest.enum.SAMKeys`
        - :py:class:`smarter.lib.manifest.enum.SAMMetadataKeys`
        - :py:class:`smarter.apps.plugin.manifest.models.api_plugin.model.SAMApiPlugin`
        - :py:class:`smarter.apps.plugin.manifest.models.common.plugin.enum.SAMPluginCommonMetadataClassValues`
        - :py:class:`smarter.apps.plugin.manifest.models.common.plugin.enum.SAMPluginCommonSpecSelectorKeyDirectiveValues`
        - :py:class:`smarter.apps.plugin.manifest.models.common.plugin.enum.SAMPluginCommonSpecPromptKeys`
        """
        # build out the sub-models first
        metadata = SAMPluginCommonMetadata(
            name="api_example",
            pluginClass=SAMPluginCommonMetadataClass.API.value,
            description="Get additional information about courses available at Stackademy.",
            version="0.1.0",
            tags=["api", "rest"],
            annotations=[
                {"smarter.sh/created_by": "smarter_api_plugin_broker"},
                {"smarter.sh/plugin": "api_example"},
            ],
        )
        selector = SAMPluginCommonSpecSelector(
            directive=SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
            searchTerms=[
                "smarter",
                "users",
                SMARTER_ADMIN_USERNAME,
            ],
        )
        prompt = SAMPluginCommonSpecPrompt(
            provider=settings_defaults.LLM_DEFAULT_PROVIDER,
            systemRole="You are a helpful sales agent for Stackademy. You can provide information about courses available at Stackademy.\n",
            model=settings_defaults.LLM_DEFAULT_MODEL,
            temperature=settings_defaults.LLM_DEFAULT_TEMPERATURE,
            maxTokens=settings_defaults.LLM_DEFAULT_MAX_TOKENS,
        )
        connection = "example_connection"
        api_data = ApiData(
            endpoint="/stackademy/course-catalogue/",
            method="GET",
            urlParams=[
                UrlParam(
                    key="max_cost",
                    value="500.00",
                ),
                UrlParam(
                    key="description",
                    value="Python",
                ),
            ],
            headers=[
                RequestHeader(name="X-Debug-Request", value="true"),
                RequestHeader(name="X-API-Key", value="your_api_key_here"),
                RequestHeader(name="Content-Type", value="application/json"),
                RequestHeader(name="Accept", value="application/json"),
                RequestHeader(name="X-Request-ID", value="12345"),
            ],
            body={},
            parameters=[
                Parameter(
                    name="max_cost",
                    type=ParameterType.STRING,
                    description="A ceiling on the maximum cost of the course.",
                    required=False,
                    default="500.00",
                ),
                Parameter(
                    name="description",
                    type=ParameterType.STRING,
                    description="A keyword to search for in the course description.",
                    required=False,
                    default="Python",
                ),
            ],
            testValues=[
                TestValue(
                    name="max_cost",
                    value="500.00",
                ),
                TestValue(
                    name="description",
                    value="Python",
                ),
            ],
            limit=100,
        )

        spec = SAMApiPluginSpec(
            selector=selector,
            prompt=prompt,
            connection=connection,
            apiData=api_data,
        )
        status = SAMPluginCommonStatus(
            accountNumber="0123456789",
            username=SMARTER_ADMIN_USERNAME,
            recordLocator="abc123def456",
            created=datetime(2024, 1, 1, 0, 0, 0),
            modified=datetime(2024, 1, 1, 0, 0, 0),
        )

        # build the full Pydantic model from the sub-models
        sam_api_plugin = SAMApiPlugin(
            apiVersion=SmarterApiVersions.V1,
            kind=MANIFEST_KIND,
            metadata=metadata,
            spec=spec,
            status=status,
        )

        return json.loads(sam_api_plugin.model_dump_json())

    def create(self):
        """
        Create the plugin in the database.

        This method handles the creation of the API plugin in the database by invoking
        the superclass's create method. It ensures that all necessary data is properly
        initialized and stored according to the plugin's configuration.

        .. note::

            This method currently does not implement any additional logic beyond calling
            the superclass's create method.

        :returns: None
        :rtype: None
        """
        logger.debug("%s.create() called.", self.formatted_class_name)
        super().create()

    # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    def tool_call_fetch_plugin_response(
        self, function_args: Union[dict[str, Any], list]
    ) -> Optional[Union[dict, list, str]]:
        """
        Fetch information from a Plugin object in response to an OpenAI API tool call.

        This method processes the arguments received from an OpenAI function call,
        builds an HTTP request from the plugin's API data, sends it to the remote
        REST API server via the plugin's :py:class:`smarter.apps.connection.models.ApiConnection`,
        and returns the JSON response.

        Arguments are mapped onto the request as follows:

        1. Arguments whose names match a ``{placeholder}`` in the endpoint are URL encoded and
           interpolated into the endpoint path, e.g. ``/v1/weather/{location}/``.
        2. For ``GET`` and ``DELETE`` requests, all remaining arguments are appended to the static
           ``urlParams`` as URL query string parameters.
        3. For ``POST``, ``PUT`` and ``PATCH`` requests, all remaining arguments are merged into the
           static JSON ``body``, provided that the body is a JSON object. Otherwise they are sent
           as URL query string parameters.

        Arguments with a ``null`` value are omitted, since these are optional parameters for
        which the LLM did not provide a value. Static ``headers`` from the manifest are sent
        with every request, and authentication headers are added by the connection.

        See the OpenAI documentation:
        https://platform.openai.com/docs/assistants/tools/function-calling/quickstart

        **Example tool call payload:**

        .. code-block:: python

            "tool_calls": [
                {
                    "id": "call_1Ucn2R5WmBh7TtoE197SsP3p",
                    "function": {
                        "arguments": "{\"description\":\"Python\",\"max_cost\":\"500.00\"}",  # these are the function_args
                        "name": "smarter_plugin_0000004468"
                    },
                    "type": "function"
                }
            ]

        **Resulting HTTP request, for the example manifest:**

        .. code-block:: text

            GET {base_url}/stackademy/course-catalogue/?max_cost=500.00&description=Python

        :param function_args: Arguments for the function call, as a dict, list, or JSON string.
        :return: The JSON response of the API request as a dict or list, or an empty string if the request failed or returned no results.
        :raises SmarterApiPluginError: If plugin data or API connection is invalid, arguments are malformed, or a required endpoint placeholder is missing.
        """
        logger.debug("%s.tool_call_fetch_plugin_response() called.", self.formatted_class_name)

        if not self.plugin_data:
            raise SmarterApiPluginError(
                f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} plugin data is not available."
            )
        api_connection = self.plugin_data.connection
        if not isinstance(api_connection, ApiConnection):
            raise SmarterApiPluginError(
                f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} plugin data ApiConnection is not a valid ApiConnection instance."
            )

        function_args = function_args or []
        if isinstance(function_args, str):
            try:
                function_args = json.loads(function_args)
            except json.JSONDecodeError as e:
                raise SmarterApiPluginError(
                    f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} function_args is not a valid JSON string. Error: {e}"
                ) from e
        if isinstance(function_args, dict):
            function_args = [function_args]

        if not isinstance(function_args, list):
            raise SmarterApiPluginError(
                f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} function_args must be a dict or a JSON string."
            )

        # combine the list of dictionaries into a single dictionary, omitting
        # optional parameters for which the LLM did not provide a value.
        params: dict[str, Any] = {}
        for d in function_args:
            if not isinstance(d, dict):
                raise SmarterApiPluginError(
                    f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} function_args must be a list of dictionaries."
                )
            params.update(d)
        params = {key: value for key, value in params.items() if value is not None}

        endpoint = self.plugin_data.endpoint
        if not isinstance(endpoint, str):
            raise SmarterApiPluginError(
                f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} endpoint must be a string."
            )

        # interpolate path placeholders, e.g. /v1/weather/{location}/
        path_params: set[str] = set()

        def repl(match):
            key = match.group(1)
            if key not in params:
                raise SmarterApiPluginError(
                    f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} missing a value for endpoint placeholder '{key}'."
                )
            path_params.add(key)
            return quote(str(params[key]), safe="")

        endpoint = re.sub(r"\{(\w+)\}", repl, endpoint)
        params = {key: value for key, value in params.items() if key not in path_params}

        method = (self.plugin_data.method or SmarterHttpMethods.GET).upper()
        headers = {str(header["name"]): str(header["value"]) for header in self.plugin_data.headers or []}
        url_params = {str(url_param["key"]): url_param["value"] for url_param in self.plugin_data.url_params or []}
        body = self.plugin_data.body

        if method in (SmarterHttpMethods.POST, SmarterHttpMethods.PUT, SmarterHttpMethods.PATCH) and isinstance(
            body, (dict, type(None))
        ):
            body = {**(body or {}), **params}
        else:
            url_params.update(params)

        limit = (
            self.plugin_data.limit
            if self.plugin_data.limit and self.plugin_data.limit < MAX_API_RESULTS
            else MAX_API_RESULTS
        )

        logger.debug(
            "%s.tool_call_fetch_plugin_response() sending remote API request: %s %s params=%s",
            self.formatted_class_name,
            method,
            endpoint,
            url_params,
        )

        def execute_request() -> Union[dict[str, Any], list[Any]]:
            retval = api_connection.execute_query(
                endpoint=endpoint,
                params=url_params,
                limit=limit,
                method=method,
                headers=headers,
                body=body,
            )
            if not isinstance(retval, (dict, list)):
                # raise rather than return so that failed requests are never cached.
                raise SmarterApiPluginError(
                    f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} API request failed: {method} {endpoint}"
                )
            return retval

        @cache_results()
        def get_cached_api_response(connection_id: int, method: str, endpoint: str, request: str) -> Any:
            retval = execute_request()
            logger.debug(
                "%s.tool_call_fetch_plugin_response() fetched and cached API response for request: %s %s",
                self.formatted_class_name,
                method,
                endpoint,
            )
            return retval

        try:
            if method == SmarterHttpMethods.GET:
                # the cache key must include everything that can alter the response.
                request = json.dumps({"params": url_params, "headers": headers, "limit": limit}, sort_keys=True)
                retval = get_cached_api_response(api_connection.pk, method, endpoint, request)
            else:
                retval = execute_request()
        except SmarterApiPluginError as e:
            logger.warning("%s. Returning empty string.", e)
            return ""

        if not retval:
            logger.warning(
                "%s.tool_call_fetch_plugin_response() API request returned no results. Returning empty string.",
                self.formatted_class_name,
            )
            return ""
        if not isinstance(retval, (str, list, dict)):
            raise SmarterApiPluginError(
                f"{self.formatted_class_name}.tool_call_fetch_plugin_response() error: {self.name} API request returned an unexpected type: {type(retval)}. Expected str, list, or dict."
            )
        return retval

    def to_json(self, version: str = "v1") -> Optional[dict[str, Any]]:
        """
        Serialize the ApiPlugin instance to a JSON-compatible dictionary suitable for Pydantic import.

        This method transforms the plugin's internal state, including its manifest and data,
        into a dictionary format that can be used to instantiate a Pydantic model. This is
        primarily used for rendering a plugin manifest for the Smarter API, enabling
        interoperability between Django ORM models and Pydantic schemas.

        The output includes all relevant plugin fields, with the API data section populated
        from the plugin's serializer. This ensures that the manifest is complete and
        conforms to the expected schema for API consumption or further validation.

        :param version: The API version to use for serialization. Only "v1" is supported.
        :type version: str

        :returns: A dictionary representing the plugin in JSON format, or ``None`` if the plugin is not ready.
        :rtype: Optional[dict[str, Any]]

        :raises SmarterPluginError: If the plugin is not ready, the data is not a valid JSON object, or an unsupported version is specified.

        :note:
            The returned dictionary is structured for compatibility with Pydantic models and
            the Smarter API manifest specification. The API data is injected from the plugin's
            serializer to ensure accurate representation.

        :example:

            >>> plugin = ApiPlugin()
            >>> manifest_json = plugin.to_json()
            >>> print(manifest_json["spec"]["apiData"]["endpoint"])
            /stackademy/course-catalogue/
        """
        if self.ready:
            if version == "v1":
                retval = super().to_json(version=version)
                if not retval:
                    raise SmarterPluginError(
                        f"{self.formatted_class_name}.to_json() error: {self.name} plugin is not ready."
                    )
                if not isinstance(retval, dict):
                    raise SmarterPluginError(
                        f"{self.formatted_class_name}.to_json() error: {self.name} plugin data is not a valid JSON object. Received: {type(retval)}"
                    )
                retval[SAMKeys.SPEC.value][SAMPluginSpecKeys.API_DATA.value] = (
                    self.plugin_data_serializer.data if self.plugin_data_serializer else None
                )
                # parameters are stored in OpenAI function calling schema. convert them back to manifest format.
                retval[SAMKeys.SPEC.value][SAMPluginSpecKeys.API_DATA.value]["parameters"] = (
                    self.parameters_to_manifest(self.plugin_data.parameters if self.plugin_data else None)
                )
                # the api serializer does not include parameters nor test values.
                retval[SAMKeys.SPEC.value][SAMPluginSpecKeys.API_DATA.value]["testValues"] = (
                    self.plugin_data.test_values if self.plugin_data else None
                )
                # the connection is a top-level spec field in the manifest, not a field of the data section.
                retval[SAMKeys.SPEC.value]["connection"] = (
                    self.plugin_data.connection.name if self.plugin_data and self.plugin_data.connection else None
                )
                return json.loads(json.dumps(retval))
            raise SmarterPluginError(f"Invalid version: {version}")
        return None
