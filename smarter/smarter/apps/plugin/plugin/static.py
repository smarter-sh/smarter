"""A PLugin that returns a static json object stored in the Plugin itself."""

import logging

from smarter.apps.plugin.manifest.enum import (
    SAMPluginMetadataClass,
    SAMPluginMetadataClassValues,
    SAMPluginMetadataKeys,
    SAMPluginSpecKeys,
    SAMPluginSpecPromptKeys,
    SAMPluginSpecSelectorKeys,
    SmartApiPluginSpecDataKeys,
)
from smarter.apps.plugin.models import PluginDataStatic
from smarter.apps.plugin.serializers import PluginDataStaticSerializer
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import SettingsDefaults
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

from ..manifest.models.plugin.const import MANIFEST_KIND
from .base import PluginBase


logger = logging.getLogger(__name__)


class PluginStatic(PluginBase):
    """A PLugin that returns a static json object stored in the Plugin itself."""

    _metadata_class = SAMPluginMetadataClass.STATIC_DATA.value
    _plugin_data: PluginDataStatic = None
    _plugin_data_serializer: PluginDataStaticSerializer = None

    @property
    def plugin_data(self) -> PluginDataStatic:
        """Return the plugin data."""
        return self._plugin_data

    @property
    def plugin_data_class(self) -> type:
        """Return the plugin data class."""
        return PluginDataStatic

    @property
    def plugin_data_serializer(self) -> PluginDataStaticSerializer:
        """Return the plugin data serializer."""
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginDataStaticSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> PluginDataStaticSerializer:
        """Return the plugin data serializer class."""
        return PluginDataStaticSerializer

    @property
    def plugin_data_django_model(self) -> dict:
        """Return the plugin data definition as a json object."""
        # recast the Pydantic model the the PluginDataStatic Django ORM model
        return {
            "plugin": self.plugin_meta,
            "description": self.manifest.spec.data.description,
            "static_data": self.manifest.spec.data.staticData,
        }

    @property
    def custom_tool(self) -> dict:
        """Return the plugin tool."""
        if self.ready:
            return {
                "type": "function",
                "function": {
                    "name": self.function_calling_identifier,
                    "description": self.plugin_data.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "inquiry_type": {
                                "type": "string",
                                "enum": self.plugin_data.return_data_keys,
                            },
                        },
                        "required": ["inquiry_type"],
                    },
                },
            }
        return None

    @classmethod
    def example_manifest(cls, kwargs: dict = None) -> dict:
        return {
            SAMKeys.APIVERSION.value: SmarterApiVersions.V1.value,
            SAMKeys.KIND.value: MANIFEST_KIND,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "EverlastingGobstopper",
                SAMPluginMetadataKeys.PLUGIN_CLASS.value: SAMPluginMetadataClassValues.STATIC.value,
                SAMMetadataKeys.DESCRIPTION.value: "Get additional information about the Everlasting Gobstopper product created by Willy Wonka Chocolate Factory. Information includes sales promotions, coupon codes, company contact information and biographical background on the company founder.",
                SAMMetadataKeys.VERSION.value: "0.1.0",
                SAMMetadataKeys.TAGS.value: ["candy", "treats", "chocolate", "Gobstoppers", "Willy Wonka"],
            },
            SAMKeys.SPEC.value: {
                SAMPluginSpecKeys.SELECTOR.value: {
                    SAMPluginSpecSelectorKeys.DIRECTIVE.value: SAMPluginSpecSelectorKeys.SEARCHTERMS.value,
                    SAMPluginSpecSelectorKeys.SEARCHTERMS.value: [
                        "Gobstopper",
                        "Gobstoppers",
                        "Gobbstopper",
                        "Gobbstoppers",
                    ],
                },
                SAMPluginSpecKeys.PROMPT.value: {
                    SAMPluginSpecPromptKeys.SYSTEMROLE.value: "You are a helpful marketing agent for the [Willy Wonka Chocolate Factory](https://wwcf.com).\n",
                    SAMPluginSpecPromptKeys.MODEL.value: SettingsDefaults.OPENAI_DEFAULT_MODEL,
                    SAMPluginSpecPromptKeys.TEMPERATURE.value: SettingsDefaults.OPENAI_DEFAULT_TEMPERATURE,
                    SAMPluginSpecPromptKeys.MAXTOKENS.value: SettingsDefaults.OPENAI_DEFAULT_MAX_TOKENS,
                },
                SAMPluginSpecKeys.DATA.value: {
                    SmartApiPluginSpecDataKeys.DESCRIPTION.value: "Get additional information about the Everlasting Gobstopper product created by Willy Wonka Chocolate Factory. Information includes sales promotions, coupon codes, company contact information and biographical background on the company founder.",
                    SmartApiPluginSpecDataKeys.STATIC_DATA.value: {
                        "contact": [
                            {"name": "Willy Wonka"},
                            {"title": "Founder and CEO"},
                            {"location": "1234 Chocolate Factory Way, Chocolate City, Chocolate State, USA"},
                            {"phone": "+1 123-456-7890"},
                            {"website": "https://wwcf.com"},
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
