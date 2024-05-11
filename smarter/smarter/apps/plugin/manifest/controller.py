"""
Helper class to map a Pydantic manifest model's metadata.pluginClass to an
instance of the the correct plugin class.
"""

from smarter.lib.manifest.controller import AbstractController

from ..models import PluginMeta
from ..plugin.api import PluginApi
from ..plugin.base import PluginBase
from ..plugin.sql import PluginSql
from ..plugin.static import PluginStatic
from .enum import SAMPluginMetadataClassValues
from .models.plugin import SAMPlugin


class PluginController(AbstractController):
    """Map the Pydantic metadata.pluginClass to the corresponding instance of PluginBase."""

    _manifest: SAMPlugin = None
    _plugin: PluginBase = None
    _plugin_meta: PluginMeta = None

    def __init__(self, manifest: SAMPlugin = None, plugin_meta: PluginMeta = None):
        self._manifest = manifest
        self._plugin_meta = plugin_meta

    ###########################################################################
    # Abstract property implementations
    ###########################################################################
    @property
    def manifest(self) -> SAMPlugin:
        return self._manifest

    @property
    def plugin_meta(self) -> PluginMeta:
        return self._plugin_meta

    @property
    def map(self):
        return {
            SAMPluginMetadataClassValues.API: PluginApi,
            SAMPluginMetadataClassValues.SQL: PluginSql,
            SAMPluginMetadataClassValues.STATIC: PluginStatic,
        }

    @property
    def obj(self) -> PluginBase:
        if self._plugin:
            return self._plugin
        if self.manifest:
            Plugin = self.map[self.manifest.metadata.pluginClass]
            self._plugin = Plugin(self.manifest)
        if self.plugin_meta:
            Plugin = self.map[self.plugin_meta.plugin_class]
            self._plugin = Plugin(self.manifest)
        return self._plugin
