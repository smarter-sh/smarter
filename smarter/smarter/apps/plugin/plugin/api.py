"""A Plugin that uses a REST API to retrieve its return data"""

# python stuff
import logging
from typing import Any, Optional, Type

# smarter stuff
from smarter.apps.plugin.manifest.models.common import Parameter
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils import camel_to_snake
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.openai.enum import OpenAIToolCall

# smarter plugin stuff
from ..manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonMetadataKeys,
    SAMPluginCommonSpecPromptKeys,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
    SAMPluginCommonSpecSelectorKeys,
    SAMPluginSpecKeys,
)
from ..manifest.models.api_plugin.const import MANIFEST_KIND
from ..manifest.models.api_plugin.enum import SAMApiPluginSpecApiData
from ..manifest.models.api_plugin.model import SAMApiPlugin
from ..manifest.models.common.plugin.enum import SAMPluginCommonSpecTestValues
from ..models import ApiConnection, PluginDataApi, PluginMeta
from ..serializers import PluginApiSerializer
from .base import PluginBase, SmarterPluginError


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SmarterApiPluginError(SmarterPluginError):
    """Base class for all SQL plugin errors."""


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
        if not self._manifest and self.ready:
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
            self._plugin_data = PluginDataApi.objects.get(
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
                f"{self.formatted_class_name}.plugin_data_django_model() error: {self.name} missing required SQL data."
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
        logger.info("plugin_data_django_model() recasting parameters: %s", parameters)
        if isinstance(parameters, list):
            for parameter in parameters:
                if isinstance(parameter, Parameter):
                    # if the parameter is a Pydantic model, we need to convert it to a
                    # standard json dict.
                    parameter = parameter.model_dump()
                logger.info("plugin_data_django_model() processing parameter: %s %s", type(parameter), parameter)
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

        .. seealso::

            - :const:`smarter.apps.plugin.manifest.models.api_plugin.const.MANIFEST_KIND`
            - :class:`smarter.lib.manifest.enum.SAMKeys`
            - :class:`smarter.lib.manifest.enum.SAMMetadataKeys`
            - :class:`smarter.apps.plugin.manifest.enum.SAMPluginCommonMetadataKeys`
            - :class:`smarter.apps.plugin.manifest.enum.SAMPluginCommonMetadataClassValues`
            - :class:`smarter.apps.plugin.manifest.enum.SAMPluginSpecKeys`
            - :class:`smarter.apps.plugin.manifest.enum.SAMPluginCommonSpecSelectorKeys`
            - :class:`smarter.apps.plugin.manifest.enum.SAMPluginCommonSpecSelectorKeyDirectiveValues`
            - :class:`smarter.apps.plugin.manifest.enum.SAMPluginCommonSpecPromptKeys`
            - :class:`smarter.apps.plugin.manifest.models.api_plugin.enumSAMApiPluginSpecApiData`
            - :class:`smarter.apps.plugin.manifest.models.common.plugin.enum.SAMPluginCommonSpecTestValues`

        """
        api_plugin = {
            SAMKeys.APIVERSION.value: SmarterApiVersions.V1,
            SAMKeys.KIND.value: MANIFEST_KIND,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "api_example",
                SAMPluginCommonMetadataKeys.PLUGIN_CLASS.value: SAMPluginCommonMetadataClassValues.API.value,
                SAMMetadataKeys.DESCRIPTION.value: "Get additional information about the admin account of the Smarter platform.",
                SAMMetadataKeys.VERSION.value: "0.1.0",
                SAMMetadataKeys.TAGS.value: ["example.com", "api", "rest-api"],
            },
            SAMKeys.SPEC.value: {
                SAMPluginSpecKeys.SELECTOR.value: {
                    SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value: SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
                    SAMPluginCommonSpecSelectorKeys.SEARCHTERMS.value: [
                        "admin",
                        "Smarter",
                        "account",
                    ],
                },
                SAMPluginSpecKeys.PROMPT.value: {
                    SAMPluginCommonSpecPromptKeys.PROVIDER.value: SettingsDefaults.LLM_DEFAULT_PROVIDER,
                    SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value: "You are a helpful assistant for Smarter platform. You can provide information about the admin account of the Smarter platform.\n",
                    SAMPluginCommonSpecPromptKeys.MODEL.value: SettingsDefaults.LLM_DEFAULT_MODEL,
                    SAMPluginCommonSpecPromptKeys.TEMPERATURE.value: SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
                    SAMPluginCommonSpecPromptKeys.MAXTOKENS.value: SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
                },
                SAMPluginSpecKeys.CONNECTION.value: "smarter_test_api",
                SAMPluginSpecKeys.API_DATA.value: {
                    "description": "Query the Django User model to retrieve detailed account information about the admin account for the Smarter platform .",
                    SAMApiPluginSpecApiData.ENDPOINT.value: "/stackademy/course-catalogue/",
                    SAMApiPluginSpecApiData.PARAMETERS.value: [
                        cls.parameter_factory(
                            name="max_cost",
                            data_type="string",
                            description="A ceiling on the maximum cost of the course.",
                            required=False,
                            default="500.00",
                        ),
                        cls.parameter_factory(
                            name="description",
                            data_type="string",
                            description="A keyword to search for in the course description.",
                            required=False,
                            default="Python",
                        ),
                    ],
                    SAMApiPluginSpecApiData.HEADERS.value: [
                        {"name": "X-Debug-Request", "value": "true"},
                        {"name": "X-API-Key", "value": "your_api_key_here"},
                        {"name": "Content-Type", "value": "application/json"},
                        {"name": "Accept", "value": "application/json"},
                        {"name": "X-Request-ID", "value": "12345"},
                    ],
                    SAMApiPluginSpecApiData.BODY.value: [
                        {
                            OpenAIToolCall.NAME.value: "test",
                            OpenAIToolCall.TYPE.value: "string",
                            OpenAIToolCall.DESCRIPTION.value: "The test to run.",
                            OpenAIToolCall.REQUIRED.value: True,
                            OpenAIToolCall.DEFAULT.value: "test",
                        },
                        {
                            OpenAIToolCall.NAME.value: "test2",
                            OpenAIToolCall.TYPE.value: "string",
                            OpenAIToolCall.DESCRIPTION.value: "The second test to run.",
                            OpenAIToolCall.REQUIRED.value: False,
                            OpenAIToolCall.DEFAULT.value: "test2",
                        },
                    ],
                    SAMApiPluginSpecApiData.TEST_VALUES.value: [
                        {
                            SAMPluginCommonSpecTestValues.NAME.value: "username",
                            SAMPluginCommonSpecTestValues.VALUE.value: "admin",
                        },
                        {
                            SAMPluginCommonSpecTestValues.NAME.value: "limit",
                            SAMPluginCommonSpecTestValues.VALUE.value: "1",
                        },
                    ],
                    SAMApiPluginSpecApiData.LIMIT.value: 10,
                },
            },
        }
        # recast the Python dict to the Pydantic model
        # in order to validate our output
        try:
            pydantic_model = cls.SAMPluginType(**api_plugin)
        except Exception as e:
            raise SmarterConfigurationError(f"{cls.__name__} example_manifest() error: {e}") from e
        try:
            # validate the manifest against the schema
            return json.loads(pydantic_model.model_dump_json())
        except json.JSONDecodeError as e:
            raise SmarterConfigurationError(f"{cls.__name__} example_manifest() error: {e}") from e

    def create(self):
        """
        Create the PluginDataApi instance in the database.

        .. note::

            This method only calls the superclass create method and logs the creation event.

        """
        super().create()

        logger.info("PluginDataApi.create() called.")

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
