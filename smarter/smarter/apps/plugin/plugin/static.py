"""A PLugin that returns a static json object stored in the Plugin itself."""

import logging

from smarter.apps.plugin.models import PluginDataStatic
from smarter.apps.plugin.serializers import PluginDataStaticSerializer

from .base import PluginBase


logger = logging.getLogger(__name__)


class PluginStatic(PluginBase):
    """A PLugin that returns a static json object stored in the Plugin itself."""

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

    def create(self):
        super().create()

        logger.info("PluginStatic.create() called.")
