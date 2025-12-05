# pylint: disable=W0613
"""Plugin utils module for core plugin functionality."""

import logging
import os
import re
from typing import Any, Optional, Union

import yaml

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.models import PluginDataValueError, PluginMeta
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import PYTHON_ROOT
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .base import PluginBase


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= smarter_settings.log_level


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

    :raises PluginDataValueError:
        If a plugin cannot be loaded or is malformed

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
        self.account = account or get_cached_user_profile(user=user).account
        self.user_profile = get_cached_user_profile(user=user, account=account)

        for plugin in PluginMeta.objects.filter(account=self.account):
            plugin_controller = PluginController(
                user_profile=self.user_profile,
                account=self.account,
                user=user,
                plugin_meta=plugin,
            )
            if not plugin_controller or not plugin_controller.plugin:
                raise PluginDataValueError(
                    f"PluginController could not be created for plugin_id: {plugin.id}, user_profile: {self.user_profile}"  # type: ignore[arg-type]
                )
            self.plugins.append(plugin_controller.plugin)

    @property
    def data(self) -> list[dict]:
        """Return a list of plugins in dictionary format."""
        retval = []
        for plugin in self.plugins:
            if plugin.ready:
                retval.append(plugin.data)
        return retval

    def to_json(self) -> list[dict[str, Any]]:
        """Return a list of plugins in JSON format."""
        retval = []
        for plugin in self.plugins:
            if plugin.ready:
                retval.append(plugin.to_json())
        return retval


class PluginExample:
    """
    A class for loading and working with built-in YAML-based plugin examples.

    This class reads plugin example files in YAML format, parses their contents, and exposes metadata and serialization methods for inspection and testing.

    :param filepath: The directory path containing the YAML file.
    :type filepath: str
    :param filename: The name of the YAML file to load.
    :type filename: str

    .. seealso::

        :class:`PluginExamples` for managing collections of plugin examples.

    **Example usage**::

        example = PluginExample(filepath="/path/to/examples", filename="my_plugin.yaml")
        print(example.name)
        print(example.to_yaml())
        print(example.to_json())

    """

    _filename: Optional[str]
    _json: Optional[Union[list, dict]]
    _yaml: Optional[str]

    def __init__(self, filepath: str, filename: str):
        """Initialize the class from a yaml file"""
        with open(os.path.join(filepath, filename), encoding="utf-8") as file:
            self._yaml = file.read()
            self._json = yaml.safe_load(self._yaml)

        self._filename = filename

    @property
    def filename(self) -> Optional[str]:
        """Return the name of the plugin."""
        return self._filename

    @property
    def name(self) -> Optional[str]:
        """Return the name of the plugin."""
        try:
            retval = self._json["metadata"]["name"] if isinstance(self._json, dict) else None
        except KeyError:
            logger.warning("PluginExample: %d is malformed and has no metadata.name", self.filename)
            retval = self.convert_filename()
        return retval

    def to_yaml(self) -> Optional[str]:
        """Return the plugin as a yaml string."""
        return self._yaml

    # TODO: this fails on Plugin.create() due to missing tags
    # django.core.exceptions.ValidationError: ["Invalid data: missing meta_data['tags']"]
    def to_json(self) -> Optional[Union[dict, list]]:
        """Return the plugin as a dictionary."""
        return self._json

    def convert_filename(self) -> Optional[str]:
        """Convert the filename to the desired format."""
        if not isinstance(self.filename, str):
            return self.filename
        try:
            filename = os.path.splitext(self.filename)[0]  # Remove the file extension
            name = re.sub(r"[-_]", " ", filename)  # Replace hyphens and underscores with spaces
            name = name.title().replace(" ", "")  # Capitalize each word and remove spaces
            return name
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("PluginExample: %s failed to convert filename: %s", self.filename, e)
            return self.filename


class PluginExamples:
    """
    A class for managing a collection of :class:`PluginExample` instances.

    This class loads all YAML-based plugin examples from a specified directory, providing access to the collection and utility methods for counting and retrieving examples.

    :param args: Optional positional arguments (unused).
    :type args: tuple
    :param kwargs: Optional keyword arguments (unused).
    :type kwargs: dict

    .. note::

        Only files ending with ``.yaml`` in the plugins path are loaded as examples.

    .. tip::

        Use :meth:`count` to get the number of loaded plugin examples, and the :meth:`plugins` property to access the list.

    .. seealso::

        :class:`PluginExample` for individual example details.

    **Example usage**::

        examples = PluginExamples()
        print(examples.count())
        for example in examples.plugins:
            print(example.filename, example.name)

    """

    _plugin_examples: list[PluginExample] = []
    HERE = os.path.abspath(os.path.dirname(__file__))
    PLUGINS_PATH = os.path.join(PYTHON_ROOT, "smarter", "apps", "plugin", "data", "sample-plugins")

    def __init__(self, *args, **kwargs):
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
