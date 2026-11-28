"""
Test smarter.common.conf.credentials, Settings.check_restricted_worker_credentials() and Settings.check_pod_credentials().

Each credential says which kinds of pod hold it (ADR-038, phase 3). The tool worker and the Extension worker must hold
no credential but their own Redis user's password (ADR-038, phase 2).
"""

import json
import os
from unittest.mock import PropertyMock, patch

from smarter.apps.provider.const import BUILTIN_PROVIDER_API_KEY_SECRET_NAMES
from smarter.common.conf import Settings
from smarter.common.conf.credentials import (
    CHART_CREDENTIALS_PATH,
    credential_holders,
    credential_holders_by_variable,
    environment_variables,
    forbidden_credentials,
    is_credential,
    may_hold,
    render_chart_credentials,
    restricted_workers_may_hold,
)
from smarter.common.const import SmarterKubernetesPodKinds
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
        self.assertTrue(is_credential(fields["github_token"]))
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
            environment_variables("subsystem_smtp_password", fields["subsystem_smtp_password"]),
            ["SMARTER_SUBSYSTEM_SMTP_PASSWORD"],
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
        # a Provider's key has no setting, so it isn't a credential that a pod holds.
        self.assertEqual(forbidden_credentials(settings, environ), ["aws_secret_access_key"])
        self.assertEqual(forbidden_credentials(settings, RESTRICTED_WORKER_ENVIRONMENT), [])
        self.assertEqual(forbidden_credentials(settings, environ, SmarterKubernetesPodKinds.JOB_INIT), [])


class TestHolders(SmarterTestBase):
    """Each credential says which kinds of pod hold it, and the chart's copy of that says the same."""

    def test_every_credential_says_who_holds_it(self):
        """A new SecretStr setting without HeldBy fails here, rather than reach every pod, or none, silently."""
        for name, field in Settings.model_fields.items():
            if not is_credential(field):
                continue
            with self.subTest(credential=name):
                holders = credential_holders(field)
                self.assertIsNotNone(holders, f"{name} needs HeldBy(...) in its annotation.")
                assert holders is not None
                self.assertLessEqual(holders, set(SmarterKubernetesPodKinds.all))

    def test_the_pod_kinds(self):
        """Every kind has a label, and has a database unless it is a restricted worker."""
        self.assertEqual(SmarterKubernetesPodKinds.all, list(SmarterKubernetesPodKinds.labels))
        expected = [kind for kind in SmarterKubernetesPodKinds.all if kind not in SmarterKubernetesPodKinds.restricted]
        self.assertEqual(SmarterKubernetesPodKinds.with_database, expected)

    def test_the_platform_pods(self):
        """The pods that do the platform's work hold its Fernet key, Django key and SMTP credentials; beat doesn't."""
        platform = SmarterKubernetesPodKinds.platform
        self.assertLess(set(platform), set(SmarterKubernetesPodKinds.with_database))
        for kind in (
            SmarterKubernetesPodKinds.BEAT,
            SmarterKubernetesPodKinds.JOB_MIGRATE,
            SmarterKubernetesPodKinds.BASTION,
        ):
            self.assertNotIn(kind, platform)
        fields = Settings.model_fields
        for name in ("platform_fernet_encryption_key", "django_secret_key"):
            with self.subTest(credential=name):
                self.assertEqual(credential_holders(fields[name]), frozenset(platform))
        # the backup Job emails its own result, so it holds SMTP's credentials too.
        smtp_holders = frozenset({*platform, SmarterKubernetesPodKinds.JOB_BACKUP})
        self.assertEqual(credential_holders(fields["subsystem_smtp_password"]), smtp_holders)

    def test_the_backup_job(self):
        """The backup Job dumps the database, saves it to S3, and emails and posts its result: no more (#1084)."""
        held_by_backup = []
        for name, field in Settings.model_fields.items():
            if is_credential(field) and may_hold(field, SmarterKubernetesPodKinds.JOB_BACKUP):
                held_by_backup.append(name)
        expected = [
            "aws_access_key_id",
            "aws_secret_access_key",
            "subsystem_redis_password",
            "subsystem_slack_bot_token",
            "subsystem_smtp_password",
            "subsystem_smtp_username",
            "subsystem_sql_backup_password",
            "subsystem_sql_password",
            "subsystem_sql_root_password",
        ]
        self.assertEqual(sorted(held_by_backup), expected)

    def test_the_chart_only_credentials(self):
        """The backup account's password and the Slack app token are settings, so that the map says who holds them."""
        fields = Settings.model_fields
        self.assertEqual(
            credential_holders(fields["subsystem_sql_backup_password"]),
            frozenset(
                {
                    SmarterKubernetesPodKinds.JOB_INIT,
                    SmarterKubernetesPodKinds.JOB_BACKUP,
                    SmarterKubernetesPodKinds.BASTION,
                }
            ),
        )
        # only the Slack bot, which isn't a kind of Smarter pod, holds the app token.
        self.assertEqual(credential_holders(fields["subsystem_slack_app_token"]), frozenset())
        holders = credential_holders_by_variable(Settings)
        self.assertEqual(holders["SMARTER_SUBSYSTEM_SLACK_APP_TOKEN"], [])
        self.assertEqual(holders["SMARTER_SUBSYSTEM_SQL_BACKUP_PASSWORD"], ["bastion", "job-backup", "job-init"])

    def test_phase_0s_findings(self):
        """The init Job alone holds the admin password; beat holds only the database's and Redis's passwords."""
        fields = Settings.model_fields
        self.assertEqual(
            credential_holders(fields["platform_admin_password"]), frozenset({SmarterKubernetesPodKinds.JOB_INIT})
        )
        self.assertEqual(
            credential_holders(fields["subsystem_social_auth_github_secret"]),
            frozenset({SmarterKubernetesPodKinds.API}),
        )
        held_by_beat = []
        for name, field in fields.items():
            if is_credential(field) and may_hold(field, SmarterKubernetesPodKinds.BEAT):
                held_by_beat.append(name)
        self.assertEqual(sorted(held_by_beat), ["subsystem_redis_password", "subsystem_sql_password"])
        # the workers sign account contacts' unsubscribe links, which the app verifies: they need the shared key.
        self.assertTrue(may_hold(fields["django_secret_key"], SmarterKubernetesPodKinds.WORKER))
        self.assertFalse(may_hold(fields["django_secret_key"], SmarterKubernetesPodKinds.JOB_MIGRATE))

    def test_a_credential_with_a_smarter_secret_has_no_setting(self):
        """A built-in Provider's key has its Smarter Secret as its only source: no setting reads it (issue #1099)."""
        for secret_name in BUILTIN_PROVIDER_API_KEY_SECRET_NAMES.values():
            with self.subTest(secret=secret_name):
                for name in Settings.model_fields:
                    self.assertFalse(name.endswith(secret_name), name)

    def test_the_committed_file_is_current(self):
        """Credentials.json, which make chart-credentials copies into the Helm chart, matches the settings."""
        with open(CHART_CREDENTIALS_PATH, encoding="utf-8") as f:
            committed = f.read()
        self.assertEqual(committed, render_chart_credentials(Settings), "Run `make chart-credentials`, and commit.")
        holders = json.loads(committed)
        self.assertEqual(holders, credential_holders_by_variable(Settings))
        self.assertEqual(holders["SMARTER_STRIPE_LIVE_SECRET_KEY"], [])


class TestPodCredentials(SmarterTestBase):
    """Outside the local environment, a pod reports the credentials that it holds but doesn't use, and starts."""

    def check(self, environment: dict[str, str]):
        """Build the settings from an environment, then run the check as if outside the local environment."""
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings()
            with patch.object(Settings, "environment_is_local", new_callable=PropertyMock, return_value=False):
                settings.check_pod_credentials()

    def test_an_extra_credential_is_reported_by_name(self):
        environment = {"SERVICE_TYPE": "beat", "GITHUB_TOKEN": "sk-test-value"}
        with self.assertLogs("smarter.common.conf.settings", level="ERROR") as logs:
            self.check(environment)
        self.assertIn("Celery Beat holds credentials that it doesn't use", logs.output[0])
        self.assertIn("github_token", logs.output[0])
        self.assertNotIn("sk-test-value", logs.output[0])

    def test_a_pod_with_only_its_own_credentials_logs_nothing(self):
        environment = {"SERVICE_TYPE": "beat", "SMARTER_SUBSYSTEM_SQL_PASSWORD": "a-database-password"}
        with patch("smarter.common.conf.settings.logger") as logger:
            self.check(environment)
        logger.error.assert_not_called()

    def test_a_process_of_no_known_kind_is_left_alone(self):
        with patch("smarter.common.conf.settings.logger") as logger:
            self.check({"SMARTER_APP_PROVIDER_OPENAI_API_KEY": "sk-test-value"})
        logger.error.assert_not_called()

    def test_beat_needs_no_django_secret_key(self):
        """Beat signs nothing, so it starts without the platform's key, with a random one of its own."""
        with patch.dict(os.environ, {"SERVICE_TYPE": "beat"}, clear=True):
            settings = Settings()
            with patch.object(Settings, "environment_is_local", new_callable=PropertyMock, return_value=False):
                settings.require_django_secret_key()


class TestRestrictedWorkerCredentials(SmarterTestBase):
    """Settings refuses to start a restricted worker that was given a credential, and leaves every other process alone."""

    def test_a_restricted_worker_with_only_its_redis_password_starts(self):
        """The environment that the Helm chart gives a restricted worker is accepted."""
        with patch.dict(os.environ, RESTRICTED_WORKER_ENVIRONMENT, clear=True):
            settings = Settings()
        self.assertTrue(settings.database_unavailable)

    def test_a_restricted_worker_with_another_credential_is_refused(self):
        """A restricted worker given e.g. a provider's SmarterKubernetesPodKinds.API key refuses to start, naming the setting, not its value."""
        environment = {**RESTRICTED_WORKER_ENVIRONMENT, "GITHUB_TOKEN": "sk-test-value"}
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(SmarterConfigurationError) as raised:
                Settings()
        message = str(raised.exception)
        self.assertIn("github_token", message)
        self.assertNotIn("sk-test-value", message)
        self.assertNotIn("a-redis-password", message)

    def test_other_processes_are_left_alone(self):
        """A process with the database, e.g. the api server, may hold every credential."""
        environment = {"SMARTER_APP_PROVIDER_OPENAI_API_KEY": "sk-test-value"}
        with patch.dict(os.environ, environment, clear=True):
            settings = Settings()
        self.assertFalse(settings.database_unavailable)
