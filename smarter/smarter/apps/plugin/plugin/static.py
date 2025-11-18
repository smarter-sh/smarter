"""A PLugin that returns a static json object stored in the Plugin itself."""

import logging
from typing import Any, Optional, Type

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonMetadataKeys,
    SAMPluginCommonSpecPromptKeys,
    SAMPluginCommonSpecSelectorKeys,
    SAMPluginSpecKeys,
    SAMStaticPluginSpecDataKeys,
)
from smarter.apps.plugin.models import PluginDataStatic
from smarter.apps.plugin.serializers import PluginStaticSerializer
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults
from smarter.common.conf import settings as smarter_settings
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

from ..manifest.enum import SAMPluginCommonSpecSelectorKeyDirectiveValues
from ..manifest.models.static_plugin.const import MANIFEST_KIND
from ..manifest.models.static_plugin.model import SAMStaticPlugin
from ..signals import plugin_called, plugin_responded
from .base import PluginBase, SmarterPluginError


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class StaticPlugin(PluginBase):
    """A PLugin that returns a static json object stored in the Plugin itself."""

    SAMPluginType = SAMStaticPlugin

    _manifest: Optional[SAMStaticPlugin] = None
    _metadata_class: str = SAMPluginCommonMetadataClass.STATIC.value
    _plugin_data: Optional[PluginDataStatic] = None
    _plugin_data_serializer: Optional[PluginStaticSerializer] = None

    def __init__(
        self,
        *args,
        manifest: Optional[SAMStaticPlugin] = None,
        **kwargs,
    ):
        super().__init__(*args, manifest=manifest, **kwargs)

    @property
    def manifest(self) -> Optional[SAMStaticPlugin]:
        """Return the Pydandic model of the plugin."""
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = SAMStaticPlugin(**self.to_json())  # type: ignore[call-arg]
        return self._manifest

    @property
    def plugin_data(self) -> Optional[PluginDataStatic]:
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
            self._plugin_data = (
                PluginDataStatic(**self.plugin_data_django_model) if self.plugin_data_django_model else None
            )
        if self.plugin_meta:
            # we don't have a Pydantic model but we do have an existing
            # Django ORM model instance, so we can use that directly.
            self._plugin_data = PluginDataStatic.objects.get(
                plugin=self.plugin_meta,
            )
        # new Plugin scenario. there's nothing in the database yet.
        return self._plugin_data

    @property
    def plugin_data_class(self) -> type:
        """Return the plugin data class."""
        return PluginDataStatic

    @property
    def plugin_data_serializer(self) -> Optional[PluginStaticSerializer]:
        """Return the plugin data serializer."""
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginStaticSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> Type[PluginStaticSerializer]:
        """Return the plugin data serializer class."""
        return PluginStaticSerializer

    @property
    def plugin_data_django_model(self) -> Optional[dict[str, Any]]:
        """
        transform the Pydantic model into a Django ORM model.
        Return the plugin data definition as a json object.
        """
        # recast the Pydantic model the the PluginDataStatic Django ORM model
        if self._manifest:
            return {
                "plugin": self.plugin_meta,
                "description": (
                    self.manifest.spec.data.description
                    if self.manifest and self.manifest.spec and self.manifest.spec.data
                    else None
                ),
                "static_data": (
                    self.manifest.spec.data.staticData
                    if self.manifest and self.manifest.spec and self.manifest.spec.data
                    else None
                ),
            }

    @property
    def custom_tool(self) -> Optional[dict[str, Any]]:
        """Return the plugin tool."""
        if self.ready:
            return {
                "type": "function",
                "function": {
                    "name": self.function_calling_identifier,
                    "description": self.plugin_data.description if self.plugin_data else "Static Plugin",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "inquiry_type": {
                                "type": "string",
                                "enum": self.plugin_data.return_data_keys if self.plugin_data else None,
                            },
                        },
                        "required": ["inquiry_type"],
                    },
                },
            }
        return None

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        static_plugin = {
            SAMKeys.APIVERSION.value: SmarterApiVersions.V1,
            SAMKeys.KIND.value: MANIFEST_KIND,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "everlasting_gobstopper",
                SAMPluginCommonMetadataKeys.PLUGIN_CLASS.value: SAMPluginCommonMetadataClassValues.STATIC.value,
                SAMMetadataKeys.DESCRIPTION.value: "Get additional information about the Everlasting Gobstopper product created by Willy Wonka Chocolate Factory. Information includes sales promotions, coupon codes, company contact information and biographical background on the company founder.",
                SAMMetadataKeys.VERSION.value: "0.1.0",
                SAMMetadataKeys.TAGS.value: ["candy", "treats", "chocolate", "Gobstoppers", "Willy Wonka"],
            },
            SAMKeys.SPEC.value: {
                SAMPluginSpecKeys.SELECTOR.value: {
                    SAMPluginCommonSpecSelectorKeys.DIRECTIVE.value: SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
                    SAMPluginCommonSpecSelectorKeys.SEARCHTERMS.value: [
                        "Gobstopper",
                        "Gobstoppers",
                        "Gobbstopper",
                        "Gobbstoppers",
                    ],
                },
                SAMPluginSpecKeys.PROMPT.value: {
                    SAMPluginCommonSpecPromptKeys.PROVIDER.value: SettingsDefaults.LLM_DEFAULT_PROVIDER,
                    SAMPluginCommonSpecPromptKeys.SYSTEMROLE.value: "You are a helpful marketing agent for the [Willy Wonka Chocolate Factory](https://wwcf.com). Whenever possible you should defer to the tool calls provided for additional information about everlasting gobstoppers.",
                    SAMPluginCommonSpecPromptKeys.MODEL.value: SettingsDefaults.LLM_DEFAULT_MODEL,
                    SAMPluginCommonSpecPromptKeys.TEMPERATURE.value: SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
                    SAMPluginCommonSpecPromptKeys.MAXTOKENS.value: SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
                },
                SAMPluginSpecKeys.DATA.value: {
                    SAMStaticPluginSpecDataKeys.DESCRIPTION.value: "Get additional information about the Everlasting Gobstopper product created by Willy Wonka Chocolate Factory. Information includes sales promotions, coupon codes, company contact information and biographical background on the company founder.",
                    SAMStaticPluginSpecDataKeys.STATIC.value: {
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
                    },
                },
            },
        }

        # recast the Python dict to the Pydantic model
        # in order to validate our output
        pydantic_model = cls.SAMPluginType(**static_plugin)
        return json.loads(pydantic_model.model_dump_json())

    def tool_call_fetch_plugin_response(self, function_args: dict[str, Any]) -> str:
        """
        Fetch the inquiry_type from a StaticPlugin.
        """
        inquiry_type = function_args.get("inquiry_type")
        if not isinstance(inquiry_type, str):
            raise SmarterPluginError(
                f"Plugin {self.name} invalid inquiry_type. Expected a string, got {type(inquiry_type)}.",
            )

        if not self.ready:
            raise SmarterPluginError(
                f"Plugin {self.name} is not in a ready state.",
            )

        if not self.plugin_data:
            raise SmarterPluginError(
                f"Plugin {self.name} is not ready. Plugin data is not available.",
            )

        plugin_called.send(
            sender=self.tool_call_fetch_plugin_response,
            plugin=self,
            inquiry_type=inquiry_type,
        )

        try:
            return_data = self.plugin_data.sanitized_return_data(self.params)
            if not isinstance(return_data, dict):
                raise SmarterPluginError(
                    f"Plugin {self.name} return data is not a dictionary.",
                )

            try:
                retval = return_data[inquiry_type]
            except KeyError as e:
                raise SmarterPluginError(
                    f"Plugin {self.name} does not have a return value for inquiry_type: {inquiry_type}. Available keys are: {list(return_data.keys())} from return_data {json.dumps(return_data)}.",
                ) from e

            if retval is None:
                raise SmarterPluginError(
                    f"Plugin {self.name} return value for inquiry_type: {inquiry_type} is None.",
                )

            try:
                retval = json.dumps(retval)
            except (TypeError, ValueError) as e:
                raise SmarterPluginError(
                    f"Plugin {self.name} return value for inquiry_type: {inquiry_type} could not be serialized to JSON: {e}.",
                ) from e

            if not isinstance(retval, str):
                raise SmarterPluginError(
                    f"Plugin {self.name} return value for inquiry_type: {inquiry_type} is not a string. Expected a string, got {type(retval)}.",
                )
            plugin_responded.send(
                sender=self.tool_call_fetch_plugin_response,
                plugin=self,
                inquiry_type=inquiry_type,
                response=retval,
            )
            return retval
        except KeyError as e:
            raise SmarterPluginError(
                f"Plugin {self.name} does not have a return value for inquiry_type: {inquiry_type}.",
            ) from e
        except json.JSONDecodeError as e:
            raise SmarterPluginError(
                f"Plugin {self.name} contains Json data that could not be decoded: {e}.",
            ) from e
