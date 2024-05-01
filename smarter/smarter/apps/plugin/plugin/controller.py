"""Helper class to map the manifest model metadata.pluginClass to an instance of the the correct plugin class."""

from smarter.apps.plugin.api.v0.manifests.enum import SAMPluginMetadataClassValues
from smarter.apps.plugin.api.v0.manifests.models.plugin import SAMPlugin

from .api import PluginApi
from .base import PluginBase
from .sql import PluginSql
from .static import PluginStatic


class PluginController:
    """Helper class to map the manifest model metadata.pluginClass to an instance of the the correct plugin class."""

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
