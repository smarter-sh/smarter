"""A Plugin that uses a REST API to retrieve its return data"""

# python stuff
import json
import logging
from typing import Any, Optional, Type

# smarter stuff
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils import camel_to_snake
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
from ..models import ApiConnection, PluginDataApi
from ..serializers import PluginApiSerializer
from .base import PluginBase, SmarterPluginError


logger = logging.getLogger(__name__)


class SmarterApiPluginError(SmarterPluginError):
    """Base class for all SQL plugin errors."""


class ApiPlugin(PluginBase):
    """A Plugin that uses an http request to a REST API to retrieve its return data"""

    _metadata_class = SAMPluginCommonMetadataClass.API.value
    _plugin_data: Optional[PluginDataApi] = None
    _plugin_data_serializer: Optional[PluginApiSerializer] = None

    @property
    def kind(self) -> str:
        """Return the kind of the plugin."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMApiPlugin]:
        """Return the Pydandic model of the plugin."""
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = SAMApiPlugin(**self.to_json())  # type: ignore[call-arg]
        return self._manifest if isinstance(self._manifest, SAMApiPlugin) else None

    @property
    def plugin_data(self) -> Optional[PluginDataApi]:
        """
        Return the plugin data as a Django ORM instance.
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
        """Return the plugin data class."""
        return PluginDataApi

    @property
    def plugin_data_serializer(self) -> Optional[PluginApiSerializer]:
        """Return the plugin data serializer."""
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginApiSerializer(self.plugin_data)
        return self._plugin_data_serializer if isinstance(self._plugin_data_serializer, PluginApiSerializer) else None

    @property
    def plugin_data_serializer_class(self) -> Type[PluginApiSerializer]:
        """Return the plugin data serializer class."""
        return PluginApiSerializer

    @property
    def plugin_data_django_model(self) -> Optional[dict[str, Any]]:
        """Return the plugin data definition as a json object."""
        if self._manifest:
            # recast the Pydantic model to the PluginDataApi Django ORM model
            api_connection = ApiConnection.objects.get(
                account=self.user_profile.account if self.user_profile else None,
                name=self.manifest.spec.connection if self.manifest else None,
            )
            api_data = self.manifest.spec.apiData.model_dump() if self.manifest and self.manifest.spec.apiData else None
            if not api_data:
                raise SmarterConfigurationError(
                    f"{self.name} PluginDataApi plugin_data_django_model() error: missing required apiData in manifest spec."
                )
            api_data = {camel_to_snake(key): value for key, value in api_data.items()}
            api_data["connection"] = api_connection
            return {
                "plugin": self.plugin_meta,
                "description": self.plugin_meta.description if self.plugin_meta else None,
                **api_data,
            }

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict[str, Any]] = None) -> dict:

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
                        {"X-Debug-Request": "true"},
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
            pydantic_model = SAMApiPlugin(**api_plugin)
        except Exception as e:
            raise SmarterConfigurationError(f"{cls.__name__} example_manifest() error: {e}") from e
        try:
            # validate the manifest against the schema
            return json.loads(pydantic_model.model_dump_json())
        except json.JSONDecodeError as e:
            raise SmarterConfigurationError(f"{cls.__name__} example_manifest() error: {e}") from e

    def create(self):
        super().create()

        logger.info("PluginDataApi.create() called.")

    def tool_call_fetch_plugin_response(self, function_args: dict[str, Any]) -> Optional[str]:
        """
        Fetch information from a Plugin object.
        """
        raise NotImplementedError("tool_call_fetch_plugin_response() must be implemented in a subclass of PluginBase.")

    def apply(self, function_args: dict[str, Any]) -> Optional[str]:
        """
        Apply the plugin to the function arguments.
        """
        if not self.ready:
            raise SmarterConfigurationError(f"{self.name} PluginDataApi.apply() error: Plugin is not ready.")

        raise NotImplementedError("apply() must be implemented in a subclass of PluginBase.")

    def to_json(self, version: str = "v1") -> Optional[dict[str, Any]]:
        """
        Serialize a SqlPlugin in JSON format that is importable by Pydantic. This
        is used to create a Pydantic model from a Django ORM model
        for purposes of rendering a Plugin manifest for the Smarter API.
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
