"""
Helper class to map to/from Pydantic manifest model, Plugin and Django ORM models.
"""

import json
from logging import getLogger
from typing import Dict, Optional, Type

from smarter.apps.account.models import Account, UserProfile

# lib manifest
from smarter.lib.django.user import UserType
from smarter.lib.journal.enum import SmarterJournalThings
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
from .models.common.plugin.model import SAMPluginCommon
from .models.sql_plugin.const import MANIFEST_KIND as SQL_MANIFEST_KIND

# plugin manifest
from .models.static_plugin.const import MANIFEST_KIND as STATIC_MANIFEST_KIND


VALID_MANIFEST_KINDS = [STATIC_MANIFEST_KIND, SQL_MANIFEST_KIND, API_MANIFEST_KIND]
logger = getLogger(__name__)


class SAMPluginControllerError(SAMExceptionBase):
    """Base exception for Smarter API Plugin Controller handling."""


class PluginController(AbstractController):
    """Helper class to map to/from Pydantic manifest model, Plugin and Django ORM models."""

    _manifest: Optional[SAMPluginCommon] = None
    _plugin: Optional[PluginBase] = None
    _plugin_meta: Optional[PluginMeta] = None
    _name: Optional[str] = None

    def __init__(
        self,
        account: Account,
        user: UserType,
        *args,
        user_profile: Optional[UserProfile] = None,
        manifest: Optional[SAMPluginCommon] = None,
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
            raise SAMPluginControllerError(
                f"Manifest should descend from {SAMPluginCommon}. Received? {type(manifest)}."
            )
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

    @property
    def map(self) -> Dict[str, Type[PluginBase]]:
        return {
            SAMPluginCommonMetadataClassValues.API.value: ApiPlugin,
            SAMPluginCommonMetadataClassValues.SQL.value: SqlPlugin,
            SAMPluginCommonMetadataClassValues.STATIC.value: StaticPlugin,
        }

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
            if isinstance(self._plugin, SAMPluginCommon) or self._plugin is None:
                self._manifest = self._plugin.manifest if self._plugin else None
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
