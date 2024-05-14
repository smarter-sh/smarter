"""A PLugin that uses a remote SQL database server to retrieve its return data"""

import logging

from smarter.apps.plugin.models import PluginDataSql
from smarter.apps.plugin.serializers import PluginDataSqlSerializer

from .base import PluginBase


logger = logging.getLogger(__name__)


class PluginSql(PluginBase):
    """A PLugin that uses an SQL query executed on a remote SQL database server to retrieve its return data"""

    _plugin_data: PluginDataSql = None
    _plugin_data_serializer: PluginDataSqlSerializer = None

    @property
    def plugin_data(self) -> PluginDataSql:
        """Return the plugin data."""
        return self._plugin_data

    @property
    def plugin_data_class(self) -> type:
        """Return the plugin data class."""
        return PluginDataSql

    @property
    def plugin_data_serializer(self) -> PluginDataSqlSerializer:
        """Return the plugin data serializer."""
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginDataSqlSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> PluginDataSqlSerializer:
        """Return the plugin data serializer class."""
        return PluginDataSqlSerializer

    @property
    def plugin_data_django_model(self) -> dict:
        """Return the plugin data definition as a json object."""
        # recast the Pydantic model the the PluginDataSql Django ORM model
        return {
            "plugin": self.plugin_meta,
            "description": self.manifest.spec.data.description,
            "sql_data": self.manifest.spec.data.sqlData,
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
                                "enum": self.plugin_data.parameters.keys() if self.plugin_data.parameters else None,
                            },
                        },
                        "required": ["inquiry_type"],
                    },
                },
            }
        return None

    def create(self):
        super().create()

        logger.info("PluginSql.create() called.")
