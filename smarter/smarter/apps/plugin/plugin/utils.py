"""Plugin utils module."""

import json
import os

import yaml

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.django.user import UserType

from .static import PluginStatic


class Plugins:
    """A class for working with multiple plugins."""

    account: Account = None
    plugins: list[PluginStatic] = []

    def __init__(self, user: UserType = None, account: Account = None):

        self.plugins = []
        if user or account:
            self.account = account or UserProfile.objects.get(user=user).account

            for plugin in PluginMeta.objects.filter(account=self.account):
                self.plugins.append(PluginStatic(plugin_id=plugin.id))

    @property
    def data(self) -> list[dict]:
        """Return a list of plugins in dictionary format."""
        retval = []
        for plugin in self.plugins:
            if plugin.ready:
                retval.append(plugin.data)
        return retval

    def to_json(self) -> list[dict]:
        """Return a list of plugins in JSON format."""
        retval = []
        for plugin in self.plugins:
            if plugin.ready:
                retval.append(plugin.to_json())
        return retval


class PluginExample:
    """A class for working with built-in yaml-based plugin examples."""

    _name: str = None
    _json: json = None
    _yaml: str = None

    def __init__(self, filepath: str, filename: str):
        """Initialize the class from a yaml file"""
        with open(os.path.join(filepath, filename), encoding="utf-8") as file:
            self._yaml = file.read()
            self._json = yaml.safe_load(self._yaml)

        self._name = filename

    @property
    def name(self) -> str:
        """Return the name of the plugin."""
        return self._name

    def to_yaml(self) -> str:
        """Return the plugin as a yaml string."""
        return self._yaml

    # FIX NOTE: this fails on Plugin.create() due to missing tags
    # django.core.exceptions.ValidationError: ["Invalid data: missing meta_data['tags']"]
    def to_json(self) -> dict:
        """Return the plugin as a dictionary."""
        return self._json


class PluginExamples:
    """A class for working with a collection of PluginExample instances."""

    _plugin_examples: list[PluginExample] = []
    HERE = os.path.abspath(os.path.dirname(__file__))
    PLUGINS_PATH = os.path.join(HERE, "data", "sample-plugins")

    def __init__(self):
        """Initialize the class."""
        self._plugin_examples = []
        for file in os.listdir(self.PLUGINS_PATH):
            if file.endswith(".yaml"):
                plugin_example = PluginExample(filepath=self.PLUGINS_PATH, filename=file)
                self._plugin_examples.append(plugin_example)

    def count(self) -> int:
        """Return the number of plugins."""
        return len(self._plugin_examples)

    @property
    def plugins(self) -> list[PluginExample]:
        """Return a list of plugins in dictionary format."""
        return self._plugin_examples
