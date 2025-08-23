"""Ultility functions for plugins."""

import io
import logging
import os
from typing import Optional

import yaml
from django.core.management import call_command

from smarter.apps.account.models import UserProfile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import PROJECT_ROOT
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .plugin.utils import PluginExamples


HERE = os.path.abspath(os.path.dirname(__file__))


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# pylint: disable=W0613,C0415
def add_example_plugins(user_profile: Optional[UserProfile]) -> bool:
    """Create example plugins for a new user."""

    plugin_examples = PluginExamples()
    data: Optional[dict] = None
    if not isinstance(user_profile, UserProfile):
        raise SmarterValueError("User profile is required to add example plugins.")
    username: str = user_profile.user.username
    output = io.StringIO()
    error_output = io.StringIO()

    # Add required secrets
    manifest_path = os.path.join(PROJECT_ROOT, "apps/account/data/sample-secrets/smarter-test-db.yaml")
    call_command("apply_manifest", filespec=manifest_path, username=username, stdout=output)
    logger.info("Applied manifest %s. output: %s", manifest_path, output.getvalue())
    try:
        call_command(
            "update_secret",
            name=smarter_settings.smarter_mysql_test_database_secret_name,
            username=username,
            value=smarter_settings.smarter_mysql_test_database_password,
            stdout=output,
            stderr=error_output,
        )
        if error_output.getvalue():
            logger.warning("Command completed with warnings: %s", error_output.getvalue())
        else:
            logger.info(
                "Updated secret %s with username %s. output: %s",
                smarter_settings.smarter_mysql_test_database_secret_name,
                username,
                output.getvalue(),
            )

    except Exception as exc:
        logger.error("Failed to update secret %s: %s", smarter_settings.smarter_mysql_test_database_secret_name, exc)
        raise SmarterValueError(f"Failed to update secret: {exc}") from exc

    # add required connections
    manifest_path = os.path.join(HERE, "data/sample-connections/smarter-test-db.yaml")
    try:
        call_command("apply_manifest", filespec=manifest_path, username=username, stdout=output, stderr=error_output)
        if error_output.getvalue():
            logger.warning("Command completed with warnings: %s", error_output.getvalue())
        else:
            logger.info("Applied manifest %s. output: %s", manifest_path, output.getvalue())
    except Exception as exc:
        logger.error("Failed to apply manifest %s: %s", manifest_path, exc)
        raise SmarterValueError(f"Failed to apply manifest: {exc}") from exc

    manifest_path = os.path.join(HERE, "data/sample-connections/smarter-test-api.yaml")
    try:
        call_command("apply_manifest", filespec=manifest_path, username=username, stdout=output, stderr=error_output)
        if error_output.getvalue():
            logger.warning("Command completed with warnings: %s", error_output.getvalue())
        else:
            logger.info("Applied manifest %s. output: %s", manifest_path, output.getvalue())
    except Exception as exc:
        logger.error("Failed to apply manifest %s: %s", manifest_path, exc)
        raise SmarterValueError(f"Failed to apply manifest: {exc}") from exc

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
    """Get the names of all example plugins."""
    plugin_examples = PluginExamples()
    return [plugin.name for plugin in plugin_examples.plugins if plugin.name is not None]
