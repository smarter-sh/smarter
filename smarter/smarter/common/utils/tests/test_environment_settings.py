"""Test :mod:`smarter.common.utils.environment_settings`: a group's settings, by environment variable."""

import re
from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from smarter.common.conf import smarter_settings
from smarter.common.conf.const import DEFAULT_MISSING_VALUE
from smarter.common.utils import (
    ENVIRONMENT_VARIABLE_PREFIX,
    environment_setting_log_value,
    get_environment_settings,
    get_environment_variables,
    log_environment_settings,
    log_environment_variables,
)
from smarter.common.utils.environment_settings import ENVIRONMENT_VARIABLE_LOG_INDENT
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestEnvironmentSettings(SmarterTestBase):
    """A group's settings, named after their variables, with values that never show a secret."""

    def test_every_field_of_the_group_by_variable_name(self):
        """Each platform_* field is SMARTER_PLATFORM_<NAME>, whatever the product's branded name."""
        settings = get_environment_settings(smarter_settings, "PLATFORM")
        fields = [name for name in type(smarter_settings).model_fields if name.startswith("platform_")]
        self.assertEqual(len(settings), len(fields))
        prefix = f"{ENVIRONMENT_VARIABLE_PREFIX}PLATFORM_"
        self.assertTrue(all(variable.startswith(prefix) for variable in settings))
        self.assertEqual(settings["SMARTER_PLATFORM_ROOT_DOMAIN"], str(smarter_settings.platform_root_domain))
        self.assertEqual(list(settings), sorted(settings))

    def test_the_group_is_a_parameter(self):
        """Other groups work the same way, in either case; a group without fields is empty."""
        subsystem = get_environment_settings(smarter_settings, "subsystem")
        self.assertIn("SMARTER_SUBSYSTEM_SMTP_PORT", subsystem)
        self.assertIn("SMARTER_APP_CONNECTION_ENABLE", get_environment_settings(smarter_settings, "APP"))
        self.assertEqual(get_environment_settings(smarter_settings, "NO_SUCH_GROUP"), {})

    def test_values_never_show_a_secret(self):
        """A SecretStr is only set or not set; an email address and the primary contact are masked."""
        secret = f"unit-test-secret-{self.hash_suffix}"
        value = environment_setting_log_value
        self.assertEqual(value("platform_fernet_encryption_key", SecretStr(secret)), "set")
        self.assertEqual(value("platform_admin_password", SecretStr(DEFAULT_MISSING_VALUE)), "not set")
        self.assertNotIn("person", value("platform_email_admin", "person@example.com"))
        self.assertNotIn("Ada Lovelace", value("platform_branding_primary_contact", "Ada Lovelace"))
        self.assertEqual(value("platform_sensitive_files_amnesty_patterns", [re.compile("^/api/"), "x"]), "[^/api/, x]")
        self.assertEqual(value("platform_root_domain", "example.com"), "example.com")
        self.assertEqual(value("platform_branding_address2", None), "None")
        logged = " ".join(get_environment_settings(smarter_settings, "PLATFORM").values())
        self.assertNotIn(smarter_settings.platform_fernet_encryption_key.get_secret_value(), logged)

    def test_log_environment_settings(self):
        """One DEBUG line per variable, between two rules, with the caller's logger."""
        logger = MagicMock()
        log_environment_settings(logger, smarter_settings, "PLATFORM")
        lines = [call.args for call in logger.debug.call_args_list]
        settings = get_environment_settings(smarter_settings, "PLATFORM")
        self.assertEqual(len(lines), len(settings) + 2)
        self.assertEqual(lines[1], ("%s: %s", *next(iter(settings.items()))))


class TestEnvironmentVariables(SmarterTestBase):
    """An app's variables in the environment: the setting that each sets, or its own value; never a secret."""

    def test_a_setting_shows_the_settings_value(self):
        """A variable that a field reads shows the field's value, which is what the platform runs with."""
        environ = {"SMARTER_APP_LLMCLIENT_TASKS_DEFAULT_TTL": "not what the platform runs with"}
        variables = get_environment_variables(smarter_settings, "APP_LLMCLIENT", environ)
        self.assertEqual(
            variables["SMARTER_APP_LLMCLIENT_TASKS_DEFAULT_TTL"], str(smarter_settings.app_llmclient_tasks_default_ttl)
        )

    def test_a_variable_without_a_setting_shows_its_value(self):
        """A variable that no field reads shows its value; an api key is a field, so it is masked."""
        secret = f"sk-unit-test-{self.hash_suffix}"
        environ = {
            "SMARTER_APP_PROVIDER_OPENAI_API_KEY": secret,
            "APP_PROVIDER_EXAMPLE_REGION": "us-east-1",
            "SMARTER_APP_PROXY_ENABLE": "true",
            "OPENAI_API_KEY": secret,
        }
        variables = get_environment_variables(smarter_settings, "app_provider", environ)
        self.assertIn(variables["SMARTER_APP_PROVIDER_OPENAI_API_KEY"], ("set", "not set"))
        self.assertEqual(variables["APP_PROVIDER_EXAMPLE_REGION"], "us-east-1")
        self.assertNotIn("SMARTER_APP_PROXY_ENABLE", variables)
        self.assertNotIn("OPENAI_API_KEY", variables)
        self.assertNotIn(secret, " ".join(variables.values()))

    def test_log_environment_variables(self):
        """One DEBUG line per variable, with the caller's logger; nothing for a group that isn't set."""
        logger = MagicMock()
        log_environment_variables(logger, smarter_settings, "APP_NO_SUCH_APP")
        logger.debug.assert_not_called()
        environ = {"SMARTER_APP_LLMCLIENT_ENABLE": "true"}
        with patch.dict("os.environ", environ):
            log_environment_variables(logger, smarter_settings, "APP_LLMCLIENT")
        lines = [call.args for call in logger.debug.call_args_list]
        variables = [line[2] for line in lines]
        self.assertIn("SMARTER_APP_LLMCLIENT_ENABLE", variables)
        # indented, and set off with a dash, as children of the line that the caller logs before them.
        self.assertTrue(all(line[:2] == ("%s - %s: %s", ENVIRONMENT_VARIABLE_LOG_INDENT) for line in lines))
        self.assertTrue((lines[0][0] % lines[0][1:]).startswith("     - SMARTER_APP_LLMCLIENT_"))
