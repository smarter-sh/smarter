"""Ultility functions for plugins."""

import os
from typing import Union

import yaml

from smarter.apps.account.models import UserProfile

from .models import PluginMeta
from .plugin.api import PluginApi
from .plugin.sql import PluginSql
from .plugin.static import PluginStatic
from .plugin.utils import PluginExamples


HERE = os.path.abspath(os.path.dirname(__file__))


# pylint: disable=W0613,C0415
def add_example_plugins(user_profile: UserProfile) -> bool:
    """Create example plugins for a new user."""

    plugin_examples = PluginExamples()
    data: dict = None

    for plugin in plugin_examples.plugins:
        data = plugin.to_yaml()
        data = yaml.safe_load(data)
        PluginStatic(user_profile=user_profile, data=data)


def get_plugin_examples_by_name() -> list[str]:
    """Get the names of all example plugins."""
    plugin_examples = PluginExamples()
    return [plugin.name for plugin in plugin_examples.plugins]


def get_plugin_by_id(plugin_id: int) -> Union[PluginStatic, PluginSql, PluginApi, None]:
    """Get a plugin by its ID."""
    try:
        plugin_meta = PluginMeta.objects.get(id=plugin_id)
    except PluginMeta.DoesNotExist:
        return None

    if plugin_meta.plugin_class == "static":
        return PluginStatic(plugin_id=plugin_id)
    if plugin_meta.plugin_class == "sql":
        return PluginSql(plugin_id=plugin_id)
    if plugin_meta.plugin_class == "api":
        raise NotImplementedError("API plugins are not yet implemented.")
    return None
