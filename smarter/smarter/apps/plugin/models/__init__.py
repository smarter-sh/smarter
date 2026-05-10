"""
Plugin models for the Smarter platform.
"""

from smarter.apps.api.v1.manifests.enum import SAMKinds

from .exceptions import PluginDataValueError
from .plugin_data_api import PluginDataApi
from .plugin_data_base import PluginDataBase
from .plugin_data_sql import PluginDataSql
from .plugin_data_static import PluginDataStatic
from .plugin_meta import PluginMeta
from .plugin_prompt import PluginPrompt
from .plugin_selector import PluginSelector
from .plugin_selector_history import (
    PluginSelectorHistory,
    PluginSelectorHistorySerializer,
)

PluginDataType = type[PluginDataStatic] | type[PluginDataApi] | type[PluginDataSql]
PLUGIN_DATA_MAP: dict[str, PluginDataType] = {
    SAMKinds.API_PLUGIN.value: PluginDataApi,
    SAMKinds.SQL_PLUGIN.value: PluginDataSql,
    SAMKinds.STATIC_PLUGIN.value: PluginDataStatic,
}


__all__ = [
    "PluginDataBase",
    "PluginDataStatic",
    "PluginDataApi",
    "PluginDataSql",
    "PluginMeta",
    "PluginPrompt",
    "PluginSelector",
    "PluginSelectorHistory",
    "PluginSelectorHistorySerializer",
    "PluginDataValueError",
    "PLUGIN_DATA_MAP",
]
