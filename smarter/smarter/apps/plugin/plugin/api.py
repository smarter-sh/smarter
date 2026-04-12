"""
A PLugin that uses a remote REST API server to retrieve its return data


.. note::

    This is a complex AI resource that exists within the following class hierarchy

    1. Smarter Secret: The authentication credential for the remote API connection.
    2. Smarter API Connection: The complete connection configuration to the remote API database server (host, port, secret, ssh key, username, etc.).
    3. Smarter API Plugin: The plugin that defines the API query and it's parameters to run against the remote API database server.
    4. Smarter Chatbot: The prompting resource (Chatbot, Agent, Workflow unit, etcetera) that includes the API Plugin:

.. sphinx note: these are relative to the rst doc that calls automodule on this file.

.. literalinclude:: ../../../../../smarter/smarter/apps/account/data/example-manifests/secret-smarter-test-db.yaml
    :language: yaml
    :caption: 1.) Example Smarter Secret Manifest

.. literalinclude:: ../../../../../smarter/smarter/apps/connection/data/sample-connections/smarter-test-api.yaml
    :language: yaml
    :caption: 2.) Example Smarter API Connection Manifest

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/stackademy/stackademy-plugin-api.yaml
    :language: yaml
    :caption: 3.) Example Stackademy API Plugin Manifest

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/stackademy/stackademy-chatbot-api.yaml
    :language: yaml
    :caption: 4.) Example Stackademy Chatbot Manifest

"""

import logging
from datetime import datetime
from typing import Any, Optional, Type, Union

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
from smarter.common.const import SMARTER_ADMIN_USERNAME
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils import camel_to_snake
from smarter.lib import json
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
MAX_API_RESULTS = 1000  # Maximum length of API query to prevent excessive load on the database


class SmarterApiPluginError(SmarterPluginError):
    """Base class for all API plugin errors."""


class ApiPlugin(PluginBase):
    """
    Implements a plugin that executes API queries on a remote API database server to retrieve data.

    This class provides mechanisms to:

    - Retrieve and serialize plugin data using Django ORM and Pydantic models.
    - Validate and recast API parameters to conform to OpenAI's function calling schema.
    - Integrate with Smarter's plugin manifest and metadata system.
    - Handle plugin instantiation from both manifest and database sources.
    - Manage connections to external APIs using account-specific credentials.
    - Provide example manifest generation for API plugins.
    - Enforce configuration and data integrity through custom error handling.

    The plugin expects a manifest describing the API endpoint, parameters, headers, and other metadata.
    It supports lazy loading and validation of plugin data, and ensures compatibility with Smarter's plugin infrastructure.

    Subclasses must implement the ``tool_call_fetch_plugin_response`` and ``apply`` methods to define custom API interaction logic.
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
            >>> print(manifest.spec.apiData.api_query)
            SELECT * FROM auth_user WHERE username = '{username}';
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
            >>> print(data.api_query)
            SELECT * FROM auth_user WHERE username = '{username}';
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
            {'api_query': "SELECT * FROM auth_user WHERE username = '{username}';", ...}
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
        https://platform.openai.com/docs/guides/function-calling?api-mode=chat

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
                    apiQuery: >
                    SELECT * FROM auth_user WHERE username = '{username}';
                    parameters:
                    - name: username
                        type: string
                        description: The username to query.
                        required: true
                        default: admin
                    - name: unit
                        type: string
                        enum:
                        - Celsius
                        - Fahrenheit
                        description: The temperature unit to use.
                        required: false
                        default: Celsius
                    testValues:
                    - name: username
                        value: admin
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
        api_data = {camel_to_snake(key): value for key, value in api_data.items()}

        connection_name = self._manifest.spec.connection if self._manifest else None
        if connection_name:
            # recast the Pydantic model to the PluginDataApi Django ORM model
            try:
                account = self.user_profile.cached_account if self.user_profile else None
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
            tags=["db", "api", "database"],
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
                    name="username",
                    value=SMARTER_ADMIN_USERNAME,
                ),
                TestValue(
                    name="limit",
                    value="1",
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

    def tool_call_fetch_plugin_response(
        self, function_args: Union[dict[str, Any], list]
    ) -> Optional[Union[dict, list, str]]:
        """
        Fetch information from a Plugin object.

        :param function_args: The function arguments to pass to the plugin.
        :type function_args: dict[str, Any]
        :return: The response from the plugin.
        :rtype: Optional[str]
        :raises NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError("tool_call_fetch_plugin_response() must be implemented in a subclass of PluginBase.")

    # pylint: disable=W0613
    def apply(self, function_args: dict[str, Any]) -> Optional[str]:
        """
        Apply the plugin to the function arguments.

        :param function_args: The function arguments to pass to the plugin.
        :type function_args: dict[str, Any]
        :return: The response from the plugin.
        :rtype: Optional[str]
        :raises SmarterConfigurationError: If the plugin is not ready.
        :raises NotImplementedError: If the method is not implemented in a subclass.
        """
        if not self.user or not self.user.is_staff:
            raise SmarterApiPluginError("Only account admins can apply static plugins.")

        if not self.ready:
            raise SmarterConfigurationError(f"{self.name} PluginDataApi.apply() error: Plugin is not ready.")

        raise NotImplementedError("apply() must be implemented in a subclass of PluginBase.")

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
            >>> print(manifest_json["spec"]["apiData"]["api_query"])
            SELECT * FROM auth_user WHERE username = '{username}';
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
                return json.loads(json.dumps(retval))
            raise SmarterPluginError(f"Invalid version: {version}")
        return None
