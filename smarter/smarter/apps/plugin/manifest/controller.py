"""
Helper class to map to/from Pydantic manifest model, Plugin and Django ORM models.
"""

import logging
from functools import cached_property
from typing import Dict, Optional, Union

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.conf import settings as smarter_settings
from smarter.lib import json
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
from ..plugin.sql import SqlPlugin
from ..plugin.static import StaticPlugin

# common plugin
from .enum import SAMPluginCommonMetadataClassValues
from .models.api_plugin.model import SAMApiPlugin
from .models.common.plugin.model import SAMPluginCommon
from .models.sql_plugin.model import SAMSqlPlugin
from .models.static_plugin.model import SAMStaticPlugin


VALID_MANIFEST_KINDS = [SAMKinds.STATIC_PLUGIN.value, SAMKinds.SQL_PLUGIN.value, SAMKinds.API_PLUGIN.value]
PluginType = type[ApiPlugin] | type[SqlPlugin] | type[StaticPlugin]
Plugins = Optional[Union[StaticPlugin, SqlPlugin, ApiPlugin]]
SAMPluginType = type[SAMApiPlugin] | type[SAMSqlPlugin] | type[SAMStaticPlugin]
SAMPlugins = Optional[Union[dict, SAMPluginCommon, SAMApiPlugin, SAMSqlPlugin, SAMStaticPlugin]]
PLUGIN_MAP: dict[str, PluginType] = {
    SAMKinds.API_PLUGIN.value: ApiPlugin,
    SAMKinds.SQL_PLUGIN.value: SqlPlugin,
    SAMKinds.STATIC_PLUGIN.value: StaticPlugin,
}
PLUGIN_META_CLASS_MAP = {
    SAMPluginCommonMetadataClassValues.API.value: ApiPlugin,
    SAMPluginCommonMetadataClassValues.SQL.value: SqlPlugin,
    SAMPluginCommonMetadataClassValues.STATIC.value: StaticPlugin,
}
SAM_MAP: dict[str, SAMPluginType] = {
    SAMKinds.API_PLUGIN.value: SAMApiPlugin,
    SAMKinds.SQL_PLUGIN.value: SAMSqlPlugin,
    SAMKinds.STATIC_PLUGIN.value: SAMStaticPlugin,
}


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMPluginControllerError(SAMExceptionBase):
    """Base exception for Smarter API Plugin Controller handling."""


class PluginController(AbstractController):
    """
    Provides a unified interface for mapping between Pydantic manifest models, plugin implementations,
    and Django ORM models within the Smarter platform.

    The PluginController is responsible for orchestrating the instantiation and management of plugin
    objects based on manifest data, plugin metadata, or plugin names. It supports dynamic loading of
    plugin classes, validation of manifest kinds, and ensures that only valid plugin configurations
    are accepted. This controller acts as a bridge between the declarative plugin manifests (often
    defined in YAML or JSON), the underlying plugin Python classes, and the persistent plugin metadata
    stored in the database.

    **Key Responsibilities**

    - Validates and processes plugin manifest data, ensuring compatibility with supported plugin kinds.
    - Dynamically selects and instantiates the appropriate plugin class (API, SQL, or Static) based on manifest or metadata.
    - Maintains references to the manifest, plugin instance, and plugin metadata for coordinated access.
    - Integrates with user and account context to support multi-tenant plugin management.
    - Provides error handling for invalid or ambiguous plugin initialization scenarios.

    **Model Relationships**

    - Utilizes :class:`smarter.apps.plugin.models.PluginMeta` for persistent plugin metadata.
    - Interacts with Pydantic manifest models such as :class:`smarter.apps.plugin.manifest.models.api_plugin.model.SAMApiPlugin`,
      :class:`smarter.apps.plugin.manifest.models.sql_plugin.model.SAMSqlPlugin`, and
      :class:`smarter.apps.plugin.manifest.models.static_plugin.model.SAMStaticPlugin`.
    - Supports plugin implementations including :class:`smarter.apps.plugin.plugin.api.ApiPlugin`,
      :class:`smarter.apps.plugin.plugin.sql.SqlPlugin`, and :class:`smarter.apps.plugin.plugin.static.StaticPlugin`.

    **Usage Example**

    .. code-block:: python

        # Initialize a PluginController with manifest data
        my_user_profile = get_cached_user_profile(admin_user)
        controller = PluginController(
            account=my_account,
            user=admin_user,
            manifest=my_manifest,
            user_profile=my_user_profile
        )
        plugin_instance = controller.plugin

        # Initialize with plugin metadata
        my_plugin_meta = PluginMeta.objects.get(id=plugin_id)
        controller = PluginController(
            account=my_account,
            user=admin_user,
            plugin_meta=my_plugin_meta,
            user_profile=my_user_profile
        )
        plugin_instance = controller.plugin

    **Notes**

    - Only one of `manifest`, `plugin_meta`, or `name` should be provided during initialization.
    - The controller enforces validation of manifest kinds and plugin class compatibility.
    - Logging and error handling are integrated using the Smarter platform's logging and exception infrastructure.
    """

    _manifest: SAMPlugins = None
    _plugin: Plugins = None
    _plugin_meta: Optional[PluginMeta] = None
    _name: Optional[str] = None

    def __init__(
        self,
        account: Account,
        user: User,
        *args,
        user_profile: Optional[UserProfile] = None,
        manifest: SAMPlugins = None,
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
        return self._manifest  # type: ignore

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
    def plugin(self) -> Plugins:
        return self.obj

    @cached_property
    def map(self) -> Dict[str, PluginType]:
        return PLUGIN_MAP

    @cached_property
    def plugin_meta_class_map(self) -> Dict[str, PluginType]:
        return PLUGIN_META_CLASS_MAP

    @cached_property
    def sam_map(self) -> Dict[str, SAMPluginType]:
        """Maps manifest kinds to their respective SAM plugin classes."""
        return SAM_MAP

    @property
    def obj(self) -> Plugins:
        if self._plugin:
            return self._plugin
        if self._plugin_meta:
            Plugin = (
                self.plugin_meta_class_map[self.plugin_meta.plugin_class]
                if self.plugin_meta and self.plugin_meta.plugin_class in self.plugin_meta_class_map
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
                self._manifest = self._plugin.manifest  # type: ignore[assignment]
        elif self.manifest:
            Plugin = self.map[self.manifest.kind]
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
