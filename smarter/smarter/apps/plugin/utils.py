"""Ultility functions for plugins."""

import io
import logging
import os
from typing import Optional

import yaml
from django.core.management import call_command

from smarter.apps.account.models import UserProfile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
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
    logger_prefix = formatted_text(f"{__name__}.add_example_plugins()")
    logger.debug("%s.add_example_plugins Adding example plugins for user profile: %s", logger_prefix, user_profile)

    plugin_examples = PluginExamples()
    data: Optional[dict] = None
    if not isinstance(user_profile, UserProfile):
        raise SmarterValueError("User profile is required to add example plugins.")
    username: str = user_profile.user.username
    output = io.StringIO()
    error_output = io.StringIO()

    def apply(file_path):

        call_command("apply_manifest", filespec=file_path, username=username, stdout=output, stderr=error_output)
        if error_output.getvalue():
            print(f"Command completed with warnings: {error_output.getvalue()}")
        else:
            print(f"Applied manifest {file_path}. output: {output.getvalue()}")

    try:
        file_paths = [
            os.path.join("smarter", "apps", "account", "data", "example-manifests", "secret-smarter-test-db.yaml"),
            os.path.join("smarter", "apps", "account", "data", "example-manifests", "secret-smarter-test-db.yaml"),
            os.path.join(
                "smarter", "apps", "account", "data", "example-manifests", "secret-smarter-test-db-proxy-password.yaml"
            ),
            os.path.join("smarter", "apps", "plugin", "data", "sample-connections", "smarter-test-db.yaml"),
            os.path.join("smarter", "apps", "plugin", "data", "sample-connections", "smarter-test-api.yaml"),
        ]
        for file_path in file_paths:
            apply(file_path)

    # pylint: disable=W0718
    except Exception as e:
        raise SmarterValueError(f"Failed to apply manifest or secret for example plugins: {e}") from e

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
