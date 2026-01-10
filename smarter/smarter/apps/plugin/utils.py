"""Ultility functions for plugins."""

import io
import logging
import os
from typing import Optional

import yaml
from django.core.management import call_command

from smarter.apps.account.const import DATA_PATH as ACCOUNT_DATA_PATH
from smarter.apps.account.models import UserProfile
from smarter.apps.api.utils import apply_manifest
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .plugin.utils import PluginExamples


HERE = os.path.abspath(os.path.dirname(__file__))


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# pylint: disable=W0613,C0415
def add_example_plugins(user_profile: Optional[UserProfile], verbose: bool = False) -> bool:
    """
    Create example plugins for a new user.

    This function provisions example plugins for a user by applying required secrets and connections,
    then instantiating plugin manifests for validation. It is intended to help new users get started
    with pre-configured plugin examples.

    :param user_profile: The `UserProfile` instance representing the new user. Must not be `None`.
    :type user_profile: Optional[UserProfile]

    :return: Returns `True` if all example plugins are created and validated successfully.
    :rtype: bool

    :raises SmarterValueError: If `user_profile` is not provided, or if manifest/secret application fails,
        or if a plugin does not have a valid YAML representation.

    .. note::

        - This function applies sample secrets and connections using Django management commands. Manifests for these are located in smarter/apps/plugin/data.
        - This function is called during deployment jobs.

    .. important::

        - The `user_profile` parameter must be a valid `UserProfile` instance. Passing `None` or an incorrect type will result in an error.
        - If any manifest or secret update fails, the function raises an exception and does not proceed with plugin creation.


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

    plugin_examples = PluginExamples()
    data: Optional[dict] = None
    if not isinstance(user_profile, UserProfile):
        raise SmarterValueError("User profile is required to add example plugins.")
    username: str = user_profile.user.username
    output = io.StringIO()
    error_output = io.StringIO()

    # Add required secrets
    manifest_path = os.path.join(ACCOUNT_DATA_PATH, "example-manifests", "secret-smarter-test-db.yaml")
    if not apply_manifest(filespec=manifest_path, username=username, verbose=verbose):
        raise SmarterValueError(f"Failed to apply manifest: {error_output.getvalue()}")

    # add required connections
    manifest_path = os.path.join(HERE, "data/sample-connections/smarter-test-db.yaml")
    if not apply_manifest(filespec=manifest_path, username=username, verbose=verbose):
        raise SmarterValueError(f"Failed to apply manifest: {error_output.getvalue()}")

    manifest_path = os.path.join(HERE, "data/sample-connections/smarter-test-api.yaml")
    if not apply_manifest(filespec=manifest_path, username=username, verbose=verbose):
        raise SmarterValueError(f"Failed to apply manifest: {error_output.getvalue()}")

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
            # we do this to ensure that that plugin can instantiate correctly.
            # Note that plugins self-validate in their own way, so this is just a basic check.
            # pylint: disable=W0104
            plugin_controller.plugin
        else:
            raise SmarterValueError(f"Plugin {plugin.name} does not have a valid YAML representation.")
    return True


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
