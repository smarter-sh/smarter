"""Ultility functions for plugins."""

import os

import yaml

from smarter.apps.account.models import UserProfile

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
