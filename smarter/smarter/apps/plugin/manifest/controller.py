"""
Helper class to map to/from Pydantic manifest model, Plugin and Django ORM models.
"""

import json
import logging
from functools import cached_property
from typing import Dict, Optional, Type, Union

from smarter.apps.account.models import Account, User, UserProfile
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

# lib manifest
from smarter.lib.journal.enum import SmarterJournalThings
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.controller import AbstractController
from smarter.lib.manifest.exceptions import SAMExceptionBase

# plugin
from ..models import PluginMeta
from ..plugin.api import ApiPlugin
from ..plugin.base import PluginBase
from ..plugin.sql import SqlPlugin
from ..plugin.static import StaticPlugin

# common plugin
from .enum import SAMPluginCommonMetadataClassValues

# api plugin
from .models.api_plugin.const import MANIFEST_KIND as API_MANIFEST_KIND
from .models.api_plugin.model import SAMApiPlugin
from .models.common.plugin.model import SAMPluginCommon

# sql plugin
from .models.sql_plugin.const import MANIFEST_KIND as SQL_MANIFEST_KIND
from .models.sql_plugin.model import SAMSqlPlugin

# static plugin
from .models.static_plugin.const import MANIFEST_KIND as STATIC_MANIFEST_KIND
from .models.static_plugin.model import SAMStaticPlugin


VALID_MANIFEST_KINDS = [STATIC_MANIFEST_KIND, SQL_MANIFEST_KIND, API_MANIFEST_KIND]
PluginType = Union[SAMStaticPlugin, SAMSqlPlugin, SAMApiPlugin]


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


PLUGIN_MAP = {
    SAMPluginCommonMetadataClassValues.API.value: ApiPlugin,
    SAMPluginCommonMetadataClassValues.SQL.value: SqlPlugin,
    SAMPluginCommonMetadataClassValues.STATIC.value: StaticPlugin,
}

SAM_MAP = {
    API_MANIFEST_KIND: SAMApiPlugin,
    SQL_MANIFEST_KIND: SAMSqlPlugin,
    STATIC_MANIFEST_KIND: SAMStaticPlugin,
}


class SAMPluginControllerError(SAMExceptionBase):
    """Base exception for Smarter API Plugin Controller handling."""


class PluginController(AbstractController):
    """Helper class to map to/from Pydantic manifest model, Plugin and Django ORM models."""

    _manifest: Optional[PluginType] = None
    _plugin: Optional[PluginBase] = None
    _plugin_meta: Optional[PluginMeta] = None
    _name: Optional[str] = None

    def __init__(
        self,
        account: Account,
        user: User,
        *args,
        user_profile: Optional[UserProfile] = None,
        manifest: Optional[PluginType] = None,
        plugin_meta: Optional[PluginMeta] = None,
        name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(account, user, *args, user_profile, **kwargs)
        if (bool(manifest) and bool(plugin_meta)) or (not bool(manifest) and not bool(plugin_meta) and not bool(name)):
            raise SAMPluginControllerError(
                f"One and only one of manifest or plugin_meta should be provided. Received? manifest: {bool(manifest)}, plugin_meta: {bool(plugin_meta)}, name: {bool(name)}."
            )
        if manifest and not isinstance(manifest, SAMPluginCommon):
            if not isinstance(manifest, dict):
                raise SAMPluginControllerError(
                    f"Manifest should descend from {SAMPluginCommon}. Received? {type(manifest)}."
                )
            if "kind" not in manifest:
                raise SAMPluginControllerError("Manifest dict should contain 'kind' key to determine the plugin type.")
            if manifest["kind"] not in VALID_MANIFEST_KINDS:
                raise SAMPluginControllerError(
                    f"Manifest kind {manifest['kind']} should be one of: {VALID_MANIFEST_KINDS}."
                )
            SAMPluginCls = self.sam_map.get(manifest["kind"])
            logger.warning(
                "%s received %s manifest as dict, converting to %s. This may be deprecated in the future.",
                self.formatted_class_name,
                manifest["kind"],
                type(SAMPluginCls).__name__,
            )
            manifest = SAMPluginCls(**manifest)  # type: ignore[call-arg]

        if manifest:
            self._manifest = manifest
            logger.info("%s received manifest: %s", self.formatted_class_name, self._manifest.metadata.name)
            if self._manifest.kind not in VALID_MANIFEST_KINDS:
                raise SAMPluginControllerError(
                    f"Manifest kind {self._manifest.kind} should be one of: {VALID_MANIFEST_KINDS}."
                )

        if plugin_meta:
            self._plugin_meta = plugin_meta
            logger.info("%s received plugin_meta: %s", self.formatted_class_name, self._plugin_meta.name)

        if name:
            self._name = name
            logger.info("%s received name: %s", self.formatted_class_name, self._name)

        logger.info(
            "%s initialized with account: %s, user: %s, user_profile: %s, manifest: %s, plugin_meta: %s, name: %s",
            self.formatted_class_name,
            self.account,
            self.user,
            self.user_profile,
            self.manifest,
            self.plugin_meta,
            self.name,
        )

    ###########################################################################
    # Abstract property implementations
    ###########################################################################
    @property
    def manifest(self) -> Optional[SAMPluginCommon]:
        return self._manifest

    @property
    def name(self) -> Optional[str]:
        if self._name:
            return self._name
        if self.manifest:
            self._name = self.manifest.metadata.name
        return self._name

    @property
    def plugin_meta(self) -> Optional[PluginMeta]:
        if not self._plugin_meta and self.account and self.name and self.manifest:
            try:
                self._plugin_meta = PluginMeta.objects.get(
                    account=self.account,
                    name=self.name,
                    plugin_class=self.plugin_class,
                )
                logger.info("%s retrieved plugin_meta: %s", self.formatted_class_name, self._plugin_meta.name)
            except PluginMeta.DoesNotExist:
                pass
        return self._plugin_meta

    @property
    def plugin_class(self) -> Optional[str]:
        """Returns the plugin class based on the manifest kind."""
        if not self.manifest or not self.manifest.kind:
            return None

        if self.manifest.kind == SmarterJournalThings.API_PLUGIN.value:
            return SAMPluginCommonMetadataClassValues.API.value
        if self.manifest.kind == SmarterJournalThings.SQL_PLUGIN.value:
            return SAMPluginCommonMetadataClassValues.SQL.value
        if self.manifest.kind == SmarterJournalThings.STATIC_PLUGIN.value:
            return SAMPluginCommonMetadataClassValues.STATIC.value
        return None

    @property
    def plugin(self) -> Optional[PluginBase]:
        return self.obj

    @cached_property
    def map(self) -> Dict[str, Type[PluginBase]]:
        return PLUGIN_MAP

    @cached_property
    def sam_map(self) -> Dict[str, Type[PluginType]]:
        """Maps manifest kinds to their respective SAM plugin classes."""
        return SAM_MAP

    @property
    def obj(self) -> Optional[PluginBase]:
        if self._plugin:
            return self._plugin
        if self._plugin_meta:
            Plugin = (
                self.map[self.plugin_meta.plugin_class]
                if self.plugin_meta and self.plugin_meta.plugin_class in self.map
                else None
            )
            if not Plugin:
                plugin_class = self.plugin_meta.plugin_class if self.plugin_meta else "Unknown"
                raise SAMPluginControllerError(f"Plugin class {plugin_class} is not supported.")
            self._plugin = (
                Plugin(plugin_meta=self.plugin_meta, user_profile=self.user_profile)
                if self.plugin_meta and self.user_profile
                else None
            )
            if isinstance(self._plugin, SAMPluginCommon):
                self._manifest = self._plugin.manifest
        elif self.manifest:
            Plugin = self.map[self.manifest.metadata.pluginClass]
            self._plugin = Plugin(manifest=self.manifest, user_profile=self.user_profile)  # type: ignore[call-arg]
        return self._plugin

    def model_dump_json(self) -> Optional[dict]:
        if self.plugin:
            return json.loads(self.plugin.manifest.model_dump_json()) if self.plugin and self.plugin.manifest else None
        return None

    def get_model_titles(self) -> list[dict[str, str]]:
        if self.plugin and self.plugin.manifest:
            return [{"name": f, "type": str(t)} for f, t in self.plugin.manifest.__annotations__.items()]
        return []
