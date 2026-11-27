"""
Test smarter.common.conf.credentials, and Settings.check_restricted_worker_credentials().

The tool worker and the Extension worker must hold no credential but their own Redis user's password (ADR-038).
"""

import os
from unittest.mock import patch

from smarter.common.conf import Settings
from smarter.common.conf.credentials import (
    environment_variables,
    forbidden_credentials,
    is_credential,
    restricted_workers_may_hold,
)
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.unittest.base_classes import SmarterTestBase

RESTRICTED_WORKER_ENVIRONMENT = {
    "SMARTER_DATABASE_UNAVAILABLE": "true",
    "SMARTER_SUBSYSTEM_REDIS_USERNAME": "extensions",
    "SMARTER_SUBSYSTEM_REDIS_PASSWORD": "a-redis-password",
}
"""A restricted worker's whole environment, as the Helm chart's smarter.toolWorkerEnv gives it: no other credential."""


class TestCredentials(SmarterTestBase):
    """Every SecretStr setting is a credential; only the marked ones may be held by the restricted workers."""

    def test_is_credential(self):
        """A SecretStr or Optional[SecretStr] setting is a credential; any other type isn't."""
        fields = Settings.model_fields
        # SecretStr, and Optional[SecretStr].
        self.assertTrue(is_credential(fields["platform_fernet_encryption_key"]))
        self.assertTrue(is_credential(fields["app_provider_openai_api_key"]))
        self.assertFalse(is_credential(fields["subsystem_redis_username"]))

    def test_only_the_redis_password_is_allowed(self):
        """Of every credential, the restricted workers may hold only their own Redis user's password."""
        allowed = []
        for name, field in Settings.model_fields.items():
            if is_credential(field) and restricted_workers_may_hold(field):
                allowed.append(name)
        self.assertEqual(allowed, ["subsystem_redis_password"])

    def test_environment_variables(self):
        """A setting is read from SMARTER_<NAME>, or from its validation_alias."""
        fields = Settings.model_fields
        self.assertEqual(
            environment_variables("app_provider_openai_api_key", fields["app_provider_openai_api_key"]),
            ["SMARTER_APP_PROVIDER_OPENAI_API_KEY"],
        )
        self.assertEqual(environment_variables("aws_access_key_id", fields["aws_access_key_id"]), ["AWS_ACCESS_KEY_ID"])

    def test_forbidden_credentials(self):
        """A credential counts when its variable has a value; the Redis password, a placeholder or an empty one don't."""
        settings = Settings()
        environ = {
            "SMARTER_SUBSYSTEM_REDIS_PASSWORD": "a-redis-password",
            "SMARTER_APP_PROVIDER_OPENAI_API_KEY": "sk-test",
            "AWS_SECRET_ACCESS_KEY": "an-aws-secret",
            "SMARTER_SUBSYSTEM_SQL_PASSWORD": "SET-ME-PLEASE",
            "SMARTER_GITHUB_TOKEN": "  ",
        }
        self.assertEqual(
            forbidden_credentials(settings, environ), ["app_provider_openai_api_key", "aws_secret_access_key"]
        )
        self.assertEqual(forbidden_credentials(settings, RESTRICTED_WORKER_ENVIRONMENT), [])


class TestRestrictedWorkerCredentials(SmarterTestBase):
    """Settings refuses to start a restricted worker that was given a credential, and leaves every other process alone."""

    def test_a_restricted_worker_with_only_its_redis_password_starts(self):
        """The environment that the Helm chart gives a restricted worker is accepted."""
        with patch.dict(os.environ, RESTRICTED_WORKER_ENVIRONMENT, clear=True):
            settings = Settings()
        self.assertTrue(settings.database_unavailable)

    def test_a_restricted_worker_with_another_credential_is_refused(self):
        """A restricted worker given e.g. a provider's API key refuses to start, naming the setting, not its value."""
        environment = {**RESTRICTED_WORKER_ENVIRONMENT, "SMARTER_APP_PROVIDER_OPENAI_API_KEY": "sk-test-value"}
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(SmarterConfigurationError) as raised:
                Settings()
        message = str(raised.exception)
        self.assertIn("app_provider_openai_api_key", message)
        self.assertNotIn("sk-test-value", message)
        self.assertNotIn("a-redis-password", message)

    def test_other_processes_are_left_alone(self):
        """A process with the database, e.g. the api server, may hold every credential."""
        environment = {"SMARTER_APP_PROVIDER_OPENAI_API_KEY": "sk-test-value"}
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings()
        self.assertFalse(settings.database_unavailable)
