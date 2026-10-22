# pylint: disable=W0613
"""Plugin utils module for core plugin functionality."""

import os
import re
from typing import Iterator, Optional, Union

import yaml

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import (
    get_cached_smarter_admin_user_profile,
)
from smarter.apps.llmtool.manifest.controller import PluginController
from smarter.apps.llmtool.models import PluginDataValueError, PluginMeta
from smarter.common.const import PYTHON_ROOT
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.typing import SmarterDictType

from .base import PluginBase


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class Plugins:
    """
    A class for managing and interacting with multiple plugins.

    This class provides methods to retrieve, serialize, and work with plugins associated with a user and account. It loads plugins using metadata and controllers, and exposes their data in dictionary and JSON formats.

    :param user: The user for whom plugins are loaded.
    :type user: User
    :param account: The account context for plugin retrieval.
    :type account: Account

    .. note::

        A plugin that cannot be loaded, for example one whose plugin data
        is missing, is logged and skipped.

    .. seealso::

        :class:`PluginController` for plugin instantiation.
        :class:`PluginMeta` for plugin metadata.

    **Example usage**::

        plugins = Plugins(user=my_user, account=my_account)
        plugin_dicts = plugins.data
        plugin_json = plugins.to_json()
    """

    account: Optional[Account] = None
    user_profile: Optional[UserProfile] = None
    plugins: list[PluginBase] = []

    def __init__(self, user: User, account: Account):

        self.plugins = []
        self.account = account or UserProfile.get_cached_object(user=user).account
        self.user_profile = UserProfile.get_cached_object(user=user, account=account)

        # plugins for this user profile, followed by those of the smarter admin user profile
        smarter_admin_user_profile = get_cached_smarter_admin_user_profile()
        for user_profile in (self.user_profile, smarter_admin_user_profile):
            for plugin_meta in PluginMeta.objects.filter(user_profile=user_profile):
                plugin = self.load_plugin(plugin_meta=plugin_meta, user_profile=user_profile)
                if plugin is not None:
                    self.plugins.append(plugin)

    def __len__(self) -> int:
        """Return the number of loaded plugins, ready or not."""
        return len(self.plugins)

    def __iter__(self) -> Iterator[PluginBase]:
        """Iterate over the loaded plugins, ready or not."""
        return iter(self.plugins)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} user_profile={self.user_profile} count={len(self)}>"

    @staticmethod
    def load_plugin(plugin_meta: PluginMeta, user_profile: UserProfile) -> Optional[PluginBase]:
        """
        Load a plugin, or log and skip it if it cannot be loaded.

        One malformed plugin, for example one whose plugin data is missing,
        should not prevent the others from being listed.

        :param plugin_meta: The plugin's PluginMeta.
        :type plugin_meta: PluginMeta
        :param user_profile: The plugin's owner.
        :type user_profile: Optional[UserProfile]
        :returns: The plugin, or None if it cannot be loaded.
        :rtype: Optional[PluginBase]
        """
        try:
            plugin_controller = PluginController(
                user_profile=user_profile,
                plugin_meta=plugin_meta,
            )
            if not plugin_controller or not plugin_controller.plugin:
                raise PluginDataValueError(
                    f"PluginController could not be created for plugin_id: {plugin_meta.id}, user_profile: {user_profile}"  # type: ignore[arg-type]
                )
            return plugin_controller.plugin
        # pylint: disable=W0718
        except Exception as e:
            base_logger.warning(
                "Plugins.load_plugin() skipping plugin %s (id: %s) for %s, which cannot be loaded: %s",
                plugin_meta.name,
                plugin_meta.id,  # type: ignore[reportAttributeAccessIssue]
                user_profile,
                e,
            )
            return None

    @property
    def data(self) -> list[SmarterDictType]:
        """Return a list of plugins in dictionary format."""
        retval = []
        for plugin in self.plugins:
            if plugin.ready:
                retval.append(plugin.data)
        return retval

    def to_json(self) -> list[SmarterDictType]:
        """Return a list of plugins in JSON format."""
        retval = []
        for plugin in self.plugins:
            if plugin.ready:
                retval.append(plugin.to_json())
        return retval
