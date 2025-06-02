"""
Helper class to map to/from Pydantic manifest model, Plugin and Django ORM models.
"""

from logging import getLogger
from typing import Dict, Type, Union

from smarter.apps.account.models import Account, UserProfile

# lib manifest
from smarter.lib.django.user import UserType
from smarter.lib.manifest.controller import AbstractController
from smarter.lib.manifest.exceptions import SAMExceptionBase

# plugin
from ..models import PluginMeta
from ..plugin.api import ApiPlugin
from ..plugin.base import PluginBase
from ..plugin.sql import SqlPlugin
from ..plugin.static import StaticPlugin
from .enum import SAMPluginCommonMetadataClassValues
from .models.api_plugin.const import MANIFEST_KIND as API_MANIFEST_KIND
from .models.api_plugin.model import SAMApiPlugin
from .models.sql_plugin.const import MANIFEST_KIND as SQL_MANIFEST_KIND
from .models.sql_plugin.model import SAMSqlPlugin

# plugin manifest
from .models.static_plugin.const import MANIFEST_KIND as STATIC_MANIFEST_KIND
from .models.static_plugin.model import SAMStaticPlugin


VALID_MANIFEST_KINDS = [STATIC_MANIFEST_KIND, SQL_MANIFEST_KIND, API_MANIFEST_KIND]
logger = getLogger(__name__)


class SAMPluginControllerError(SAMExceptionBase):
    """Base exception for Smarter API Plugin Controller handling."""


class PluginController(AbstractController):
    """Helper class to map to/from Pydantic manifest model, Plugin and Django ORM models."""

    _manifest: Union[SAMStaticPlugin, SAMSqlPlugin, SAMApiPlugin] = None
    _plugin: PluginBase = None
    _plugin_meta: PluginMeta = None
    _name: str = None

    def __init__(
        self,
        account: Account,
        user: UserType,
        *args,
        user_profile: UserProfile = None,
        manifest: Union[SAMStaticPlugin, SAMSqlPlugin, SAMApiPlugin] = None,
        plugin_meta: PluginMeta = None,
        name: str = None,
        **kwargs,
    ):
        super().__init__(account, user, *args, user_profile, **kwargs)
        if (bool(manifest) and bool(plugin_meta)) or (not bool(manifest) and not bool(plugin_meta) and not bool(name)):
            raise SAMPluginControllerError(
                f"One and only one of manifest or plugin_meta should be provided. Received? manifest: {bool(manifest)}, plugin_meta: {bool(plugin_meta)}, name: {bool(name)}."
            )
        if manifest and not isinstance(manifest, (SAMStaticPlugin, SAMSqlPlugin, SAMApiPlugin)):
            raise SAMPluginControllerError(
                f"Manifest should be one of {SAMStaticPlugin}, {SAMSqlPlugin}, {SAMApiPlugin}. Received? {type(manifest)}."
            )
        if manifest:
            self._manifest = manifest
            logger.info("%s received manifest: %s", self.formatted_class_name, self._manifest.metadata.name)
            if self.manifest.kind not in VALID_MANIFEST_KINDS:
                raise SAMPluginControllerError(
                    f"Manifest kind {self.manifest.kind} should be one of: {VALID_MANIFEST_KINDS}."
                )

        if plugin_meta:
            self._plugin_meta = plugin_meta
            logger.info("%s received plugin_meta: %s", self.formatted_class_name, self._plugin_meta.name)

        if name:
            self._name = name
            logger.info("%s received name: %s", self.formatted_class_name, self._name)

    ###########################################################################
    # Abstract property implementations
    ###########################################################################
    @property
    def manifest(self) -> Union[SAMStaticPlugin, SAMSqlPlugin, SAMApiPlugin]:
        return self._manifest

    @property
    def name(self) -> str:
        if self._name:
            return self._name
        if self.manifest:
            self._name = self.manifest.metadata.name
        return self._name

    @property
    def plugin_meta(self) -> PluginMeta:
        if not self._plugin_meta and self.account and self.name:
            try:
                self._plugin_meta = PluginMeta(
                    account=self.account,
                    name=self.name,
                )
            except PluginMeta.DoesNotExist as e:
                raise SAMPluginControllerError(f"{self.manifest.kind} {self.name} does not exist.") from e
        return self._plugin_meta

    @property
    def plugin(self) -> PluginBase:
        return self.obj

    @property
    def map(self) -> Dict[str, Type[PluginBase]]:
        return {
            SAMPluginCommonMetadataClassValues.API.value: ApiPlugin,
            SAMPluginCommonMetadataClassValues.SQL.value: SqlPlugin,
            SAMPluginCommonMetadataClassValues.STATIC.value: StaticPlugin,
        }

    @property
    def obj(self) -> PluginBase:
        if self._plugin:
            return self._plugin
        if self._plugin_meta:
            Plugin = self.map[self.plugin_meta.plugin_class]
            self._plugin = Plugin(plugin_meta=self.plugin_meta, user_profile=self.user_profile)
            self._manifest = self._plugin.manifest
        elif self.manifest:
            Plugin = self.map[self.manifest.metadata.pluginClass]
            self._plugin = Plugin(manifest=self.manifest, user_profile=self.user_profile)
        return self._plugin

    def model_dump_json(self) -> dict:
        if self.plugin:
            return self.plugin.manifest.model_dump_json()
        return None

    def get_model_titles(self) -> list[dict[str, str]]:
        if self.plugin and self.plugin.manifest:
            return [{"name": f, "type": str(t)} for f, t in self.plugin.manifest.__annotations__.items()]
        return []
