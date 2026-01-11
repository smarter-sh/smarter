"""
A Plugin that uses a REST API to retrieve its return data

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

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/sample-connections/smarter-test-api.yaml
    :language: yaml
    :caption: 2.) Example Smarter API Connection Manifest

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/stackademy/stackademy-api.yaml
    :language: yaml
    :caption: 3.) Example Stackademy API Plugin Manifest

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/stackademy/chatbot-stackademy-api.yaml
    :language: yaml
    :caption: 4.) Example Stackademy Chatbot Manifest


"""

# python stuff
import logging
from datetime import datetime
from typing import Any, Optional, Type

# smarter stuff
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
from smarter.apps.plugin.models import ApiConnection, PluginDataApi, PluginMeta
from smarter.apps.plugin.serializers import PluginApiSerializer
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults, smarter_settings
from smarter.common.const import SMARTER_ADMIN_USERNAME
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils import camel_to_snake
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys

from .base import PluginBase, SmarterPluginError


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SmarterApiPluginError(SmarterPluginError):
    """Base class for all API plugin errors."""


class ApiPlugin(PluginBase):
    """
    Implements a plugin that interacts with external REST APIs via HTTP requests.

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
    _plugin_data: Optional[PluginDataApi] = None
    _plugin_data_serializer: Optional[PluginApiSerializer] = None

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
        Return the kind of the plugin.

        :return: The kind of the plugin.
        :rtype: str

        .. seealso::

            - :const:`smarter.apps.plugin.manifest.models.api_plugin.const.MANIFEST_KIND`

        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMApiPlugin]:
        """
        Return the Pydandic model of the plugin.

        :return: The Pydantic model of the plugin.
        :rtype: Optional[SAMApiPlugin]
        """
        if self._manifest:
            if not isinstance(self._manifest, SAMApiPlugin):
                raise SmarterApiPluginError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                )
            return self._manifest
        if self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = self.SAMPluginType(**self.to_json())  # type: ignore[call-arg]
        return self._manifest if isinstance(self._manifest, self.SAMPluginType) else None

    @property
    def plugin_data(self) -> Optional[PluginDataApi]:
        """
        Return the plugin data as a Django ORM instance.

        :return: The plugin data as a Django ORM instance.
        :rtype: Optional[PluginDataApi]
        """
        if self._plugin_data:
            return self._plugin_data

        # we only want a preexisting manifest ostensibly sourced
        # from the cli, not a lazy-loaded
        if self._manifest and self.plugin_meta:
            # this is an update scenario. the Plugin exists in the database,
            # AND we've received manifest data from the cli.
            self._plugin_data = PluginDataApi(**self.plugin_data_django_model)  # type: ignore[call-arg]
        if self.plugin_meta:
            # we don't have a Pydantic model but we do have an existing
            # Django ORM model instance, so we can use that directly.
            self._plugin_data = PluginDataApi.get_cached_data_by_plugin(
                plugin=self.plugin_meta,
            )
        # new Plugin scenario. there's nothing in the database yet.
        return self._plugin_data if isinstance(self._plugin_data, PluginDataApi) else None

    @property
    def plugin_data_class(self) -> Type[PluginDataApi]:
        """
        Return the plugin data class.

        :return: The plugin data class.
        :rtype: Type[PluginDataApi]
        """
        return PluginDataApi

    @property
    def plugin_data_serializer(self) -> Optional[PluginApiSerializer]:
        """
        Return the plugin data serializer.

        :return: The plugin data serializer.
        :rtype: Optional[PluginApiSerializer]
        """
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginApiSerializer(self.plugin_data)
        return self._plugin_data_serializer if isinstance(self._plugin_data_serializer, PluginApiSerializer) else None

    @property
    def plugin_data_serializer_class(self) -> Type[PluginApiSerializer]:
        """
        Return the plugin data serializer class.

        :return: The plugin data serializer class.
        :rtype: Type[PluginApiSerializer]
        """
        return PluginApiSerializer

    @property
    def plugin_data_django_model(self) -> Optional[dict[str, Any]]:
        """
        Return the plugin data definition as a json object.

        :return: The plugin data definition as a json object.
        :rtype: Optional[dict[str, Any]]

        :raises SmarterApiPluginError: If the plugin data is invalid.

        """
        if not self._manifest:
            return None

        api_data = self.manifest.spec.apiData.model_dump() if self.manifest else None
        if not api_data:
            raise SmarterApiPluginError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} missing required API data."
            )
        api_data = {camel_to_snake(key): value for key, value in api_data.items()}

        connection_name = self._manifest.spec.connection if self._manifest and self._manifest.spec else None
        if connection_name:
            # recast the Pydantic model to the PluginDataApi Django ORM model
            try:
                account = self.user_profile.account if self.user_profile else None
                plugin_data_apiconnection = ApiConnection.objects.get(
                    account=account,
                    name=connection_name,
                )
                api_data["connection"] = plugin_data_apiconnection
            except ApiConnection.DoesNotExist as e:
                raise SmarterApiPluginError(
                    f"{self.formatted_class_name}.plugin_data_django_model() error: ApiConnection {connection_name} does not exist for Plugin {self.plugin_meta.name if self.plugin_meta else "(Missing name)"} in account {account}. Error: {e}"
                ) from e

        # recast the Pydantic model's parameters field
        # to conform to openai's function calling schema.
        recasted_parameters = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
        parameters = self.manifest.spec.apiData.parameters if self.manifest and self.manifest.spec else None
        logger.info("%s.plugin_data_django_model() recasting parameters: %s", self.formatted_class_name, parameters)
        if isinstance(parameters, list):
            for parameter in parameters:
                if isinstance(parameter, Parameter):
                    # if the parameter is a Pydantic model, we need to convert it to a
                    # standard json dict.
                    parameter = parameter.model_dump()
                logger.info(
                    "%s.plugin_data_django_model() processing parameter: %s %s",
                    self.formatted_class_name,
                    type(parameter),
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

            api_data["parameters"] = recasted_parameters
        else:
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} parameters must be a list of dictionaries. Received: {parameters} {type(parameters)}"
            )

        if not isinstance(self.plugin_meta, PluginMeta):
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} missing required plugin_meta."
            )
        if not isinstance(self.manifest, SAMApiPlugin):
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} missing required manifest."
            )
        if not isinstance(api_data, dict):
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} missing required api_data."
            )

        return {
            "plugin": self.plugin_meta,
            "description": (
                self.manifest.metadata.description
                if self.manifest and self.manifest.metadata
                else self.plugin_meta.description if self.plugin_meta else None
            ),
            **api_data,
        }  # type: ignore[return-value]

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict[str, Any]] = None) -> dict:
        """
        Return an example manifest for the ApiPlugin.

        :param kwargs: Optional dictionary of keyword arguments to customize the example manifest.
        :type kwargs: Optional[dict[str, Any]]

        :return: An example manifest for the ApiPlugin.
        :rtype: dict

        """
        metadata = SAMPluginCommonMetadata(
            name="api_example",
            pluginClass=SAMPluginCommonMetadataClass.API.value,
            description="Get additional information about the admin account of the Smarter platform.",
            version="0.1.0",
            tags=["example.com", "api", "rest-api"],
            annotations=[{"smarter.sh/created_by": "smarter_api_plugin_broker"}, {"smarter.sh/plugin": "api_example"}],
        )
        selector = SAMPluginCommonSpecSelector(
            directive=SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
            searchTerms=[
                SMARTER_ADMIN_USERNAME,
                "Smarter",
                "account",
            ],
        )
        prompt = SAMPluginCommonSpecPrompt(
            provider=SettingsDefaults.LLM_DEFAULT_PROVIDER,
            systemRole="You are a helpful agent for Stackademy. You provide information on available courses by leveraging the Api.\n",
            model=SettingsDefaults.LLM_DEFAULT_MODEL,
            temperature=SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
            maxTokens=SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
        )
        connection = "smarter_test_api"
        api_data = ApiData(
            endpoint="/stackademy/course-catalogue/",
            method="GET",
            url_params=[
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
            test_values=[
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
            account_number="0123456789",
            username=SMARTER_ADMIN_USERNAME,
            created=datetime(2024, 1, 1, 0, 0, 0),
            modified=datetime(2024, 1, 1, 0, 0, 0),
        )
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
        Create the PluginDataApi instance in the database.

        .. note::

            This method only calls the superclass create method and logs the creation event.

        """
        super().create()

        logger.info("%s.create() called.", self.formatted_class_name)

    def tool_call_fetch_plugin_response(self, function_args: dict[str, Any]) -> Optional[str]:
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
        if not self.ready:
            raise SmarterConfigurationError(f"{self.name} PluginDataApi.apply() error: Plugin is not ready.")

        raise NotImplementedError("apply() must be implemented in a subclass of PluginBase.")

    def to_json(self, version: str = "v1") -> Optional[dict[str, Any]]:
        """
        Serialize a SqlPlugin in JSON format that is importable by Pydantic. This
        is used to create a Pydantic model from a Django ORM model
        for purposes of rendering a Plugin manifest for the Smarter API.

        :param version: The version of the API to serialize to. Defaults to "v1".
        :type version: str
        :return: The serialized JSON representation of the SqlPlugin.
        :rtype: Optional[dict[str, Any]]
        :raises SmarterConfigurationError: If the plugin is not ready or if there is an error during serialization.
        :raises SmarterPluginError: If the version is invalid.
        """
        if self.ready:
            if version == "v1":
                retval = super().to_json(version=version)
                if not isinstance(retval, dict):
                    raise SmarterConfigurationError(f"{self.formatted_class_name}.to_json() error: {self.name}.")
                if not isinstance(self.plugin_data_serializer, PluginApiSerializer):
                    raise SmarterConfigurationError(
                        f"{self.formatted_class_name}.to_json() error: {self.name} plugin_data_serializer expected PluginApiSerializer but got {type(self.plugin_data_serializer)}."
                    )
                retval[SAMKeys.SPEC.value][SAMPluginSpecKeys.API_DATA.value] = (
                    self.plugin_data_serializer.data if self.plugin_data_serializer else None
                )
                return json.loads(json.dumps(retval))
            raise SmarterPluginError(f"Invalid version: {version}")
        return None
