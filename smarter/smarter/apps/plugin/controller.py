"""
Helper class to map a Pydantic manifest model's metadata.pluginClass to an
instance of the the correct plugin class.
"""

from smarter.apps.plugin.api.v0.manifests.enum import SAMPluginMetadataClassValues
from smarter.apps.plugin.api.v0.manifests.models.plugin import SAMPlugin

from .plugin.api import PluginApi
from .plugin.base import PluginBase
from .plugin.sql import PluginSql
from .plugin.static import PluginStatic


class PluginController:
    """Map the Pydantic metadata.pluginClass to the corresponding instance of PluginBase."""

    _manifest: SAMPlugin = None
    _plugin: PluginBase = None
    plugin_map = {
        SAMPluginMetadataClassValues.API: PluginApi,
        SAMPluginMetadataClassValues.SQL: PluginSql,
        SAMPluginMetadataClassValues.STATIC: PluginStatic,
    }

    def __init__(self, manifest: SAMPlugin):
        self._manifest = manifest

    @property
    def manifest(self) -> SAMPlugin:
        return self._manifest

    @property
    def plugin(self) -> PluginBase:
        if self._plugin:
            return self._plugin
        Plugin = self.plugin_map[self.manifest.metadata.pluginClass]
        self._plugin = Plugin(self.manifest)
        return self._plugin
