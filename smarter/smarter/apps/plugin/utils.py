"""Ultility functions for plugins."""

import os
from typing import Optional

import yaml

from smarter.apps.account.models import UserProfile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .plugin.utils import PluginExamples

HERE = os.path.abspath(os.path.dirname(__file__))


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])
logger_prefix = formatted_text(f"{__name__}")


# pylint: disable=W0613,C0415,R0914
def add_example_plugins(user_profile: Optional[UserProfile], verbose: bool = False) -> bool:
    """
    Create example plugins for a new user.

    This function provisions example plugins for a user by instantiating each example's plugin manifest,
    which also validates it. It is intended to help new users get started with pre-configured plugin examples.

    :param user_profile: The `UserProfile` instance representing the new user. Must not be `None`.
    :type user_profile: Optional[UserProfile]

    :return: Returns `True` if all example plugins are created and validated successfully.
    :rtype: bool

    :raises SmarterValueError: If `user_profile` is not provided, or if a plugin does not have a valid
        YAML representation.

    .. note::

        - None of the examples needs a Secret or a Connection. The Stackademy Secrets and Connections,
          whose names are fixed, are applied by ``manage.py create_stackademy``, which runs after this
          function in every deployment job.
        - This function is called during deployment jobs.

    .. important::

        - The `user_profile` parameter must be a valid `UserProfile` instance. Passing `None` or an incorrect type will result in an error.

    .. seealso::

        - :class:`PluginExamples`
        - :class:`PluginController`
        - :class:`SmarterValueError`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.account.models import UserProfile
        from smarter.apps.plugin.utils import add_example_plugins

        user_profile = UserProfile.objects.get(user__username="newuser")
        success = add_example_plugins(user_profile)
        if success:
            print("Example plugins created successfully.")
    """
    # pylint: disable=W0621
    logger_prefix = formatted_text(f"{__name__}.add_example_plugins()")
    logger.debug("%s.add_example_plugins Adding example plugins for user profile: %s", logger_prefix, user_profile)

    plugin_examples = PluginExamples()
    if not isinstance(user_profile, UserProfile):
        raise SmarterValueError("User profile is required to add example plugins.")
    retval = True
    for plugin in plugin_examples.plugins:
        yaml_data = plugin.to_yaml()
        if not isinstance(yaml_data, str):
            raise SmarterValueError(f"Plugin {plugin.name} does not have a valid YAML representation.")
        data = yaml.safe_load(yaml_data.encode("utf-8"))
        try:
            plugin_controller = PluginController(
                user_profile=user_profile,
                manifest=data,  # type: ignore[arg-type]
            )
            # we do this to ensure that that plugin can instantiate correctly.
            # Note that plugins self-validate in their own way, so this is just a basic check.
            # pylint: disable=W0104
            plugin_controller.plugin
        # pylint: disable=W0718
        except Exception as e:
            # some examples have prerequisites, like the api key Secret of a
            # WebsearchPlugin, that the user might not have.
            logger.warning(
                "%s skipping example plugin %s, which could not be created for %s: %s",
                logger_prefix,
                plugin.name,
                user_profile,
                e,
            )
            retval = False
    return retval


def get_plugin_examples_by_name() -> Optional[list[str]]:
    """
    Get the names of all example plugins.

    This function returns a list of names for all available example plugins, or `None` if no names are found.
    It is useful for displaying or referencing example plugins in onboarding flows, documentation, or UI elements.

    :return: A list of example plugin names, or `None` if no plugins are available.
    :rtype: Optional[list[str]]

    .. seealso::

        - :class:`PluginExamples`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.utils import get_plugin_examples_by_name

        plugin_names = get_plugin_examples_by_name()
        if plugin_names:
            print("Available example plugins:", plugin_names)
        else:
            print("No example plugins found.")
    """
    plugin_examples = PluginExamples()
    return [plugin.name for plugin in plugin_examples.plugins if plugin.name is not None]
