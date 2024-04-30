"""Ultility functions for plugins."""

import os

import yaml

from smarter.apps.account.models import UserProfile

from .plugin.base import PluginExamples
from .plugin.static import PluginStatic


HERE = os.path.abspath(os.path.dirname(__file__))


# pylint: disable=W0613,C0415
def add_example_plugins(user_profile: UserProfile) -> bool:
    """Create example plugins for a new user."""

    plugin_examples = PluginExamples()
    data: dict = None

    for plugin in plugin_examples.plugins:
        data = plugin.to_yaml()
        data = yaml.safe_load(data)
        data["user_profile"] = user_profile
        PluginStatic(data=data)
