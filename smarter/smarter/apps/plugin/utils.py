"""Ultility functions for plugins."""

import os
from typing import Optional

import yaml

from smarter.apps.account.models import UserProfile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.common.exceptions import SmarterValueError

from .plugin.utils import PluginExamples


HERE = os.path.abspath(os.path.dirname(__file__))


# pylint: disable=W0613,C0415
def add_example_plugins(user_profile: Optional[UserProfile]) -> bool:
    """Create example plugins for a new user."""

    plugin_examples = PluginExamples()
    data: Optional[dict] = None

    for plugin in plugin_examples.plugins:
        yaml_data = plugin.to_yaml()
        if isinstance(yaml_data, str):
            yaml_data = yaml_data.encode("utf-8")
            data = yaml.safe_load(yaml_data)
            plugin_controller = PluginController(
                user_profile=user_profile,
                account=user_profile.account,  # type: ignore[arg-type]
                user=user_profile.user,  # type: ignore[arg-type]
                manifest=data,  # type: ignore[arg-type]
            )
            plugin_controller.plugin
        else:
            raise SmarterValueError(f"Plugin {plugin.name} does not have a valid YAML representation.")
    return True


def get_plugin_examples_by_name() -> Optional[list[str]]:
    """Get the names of all example plugins."""
    plugin_examples = PluginExamples()
    return [plugin.name for plugin in plugin_examples.plugins if plugin.name is not None]
