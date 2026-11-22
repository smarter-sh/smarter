"""
Tests of the chart's env Secret, templates/secret-env.yaml, and of smarter.env, which builds it.

When the pods have an IAM role (serviceAccount.awsRoleArn), the deploy workflow sets
env.AWS_ACCESS_KEY_ID and env.AWS_SECRET_ACCESS_KEY to null, because a key in the pods'
environment would win over the role. values.yaml has no default for them, so the null reaches
the schema and the template. A schema that only allowed a string once failed a prod deploy at
helm upgrade. These tests check that both accept the null, and that the Secret leaves it out.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import json
import re
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
SCHEMA_PATH = CHART_PATH / "values.schema.json"
VALUES_PATH = CHART_PATH / "values.yaml"
TEMPLATE_PATH = CHART_PATH / "templates" / "secret-env.yaml"

HELPERS_PATH = CHART_PATH / "templates" / "_helpers.tpl"
MARIADB_SECRET_PATH = CHART_PATH / "templates" / "secret-mariadb.yaml"
MIGRATE_JOB_PATH = CHART_PATH / "templates" / "job-migrate.yaml"
MIGRATE_SECRET_PATH = CHART_PATH / "templates" / "secret-env-migrate.yaml"

OPTIONAL_KEYS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")

DERIVED_KEYS = (
    "DJANGO_SETTINGS_MODULE",
    "DJANGO_CELERY_BROKER_URL",
    "SMARTER_SUBSYSTEM_K8S_NAMESPACE",
    "SMARTER_PLATFORM_S3_BUCKET",
)
"""The settings that smarter.env derives from the others, which values.yaml therefore doesn't set."""

INFRASTRUCTURE_SECRETS = ("mysql-smarter", "mysql-root", "smarter-admin", "smarter-django-secret-key", "aws-ses-config")
"""The Kubernetes Secrets that smarter-infrastructure creates in each environment's namespace."""


def env_helper() -> str:
    """
    Return the smarter.env template of _helpers.tpl.

    :returns: Its text, from its define to its end.
    """
    text = HELPERS_PATH.read_text(encoding="utf-8")
    start = text.index('{{- define "smarter.env" -}}')
    end = text.index("{{- end }}", start)
    return text[start:end]


class TestOptionalAwsKeys(unittest.TestCase):
    """The AWS access keys can be left out of the pods' environment."""

    def test_schema_accepts_null(self):
        """The schema allows a string or null for each key."""
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        env_properties = schema["properties"]["env"]["properties"]
        for key in OPTIONAL_KEYS:
            with self.subTest(key=key):
                allowed = env_properties[key]["type"]
                self.assertIn("string", allowed)
                self.assertIn("null", allowed)

    def test_no_default_key(self):
        """Values.yaml sets no key, so a placeholder can never win over the IAM role."""
        text = VALUES_PATH.read_text(encoding="utf-8")
        for key in OPTIONAL_KEYS:
            with self.subTest(key=key):
                self.assertNotIn(f"\n  {key}:", text)

    def test_secret_leaves_out_null_values(self):
        """The env Secret skips a null value, rather than rendering an empty one."""
        self.assertIn('{{- $isNull := kindIs "invalid" $value -}}', env_helper())
        self.assertIn('include "smarter.env" . | fromYaml', TEMPLATE_PATH.read_text(encoding="utf-8"))


class TestEnvironment(unittest.TestCase):
    """Smarter.env: the settings that the chart writes into the env Secret, without a deploy workflow."""

    def test_leaves_out_placeholders(self):
        """A SET-ME placeholder is left out, so the setting gets Smarter's default, not the placeholder's text."""
        self.assertIn('(hasPrefix "SET-ME" $value)', env_helper())

    def test_derives_the_deployment_values(self):
        """The values that a deploy workflow used to compute are derived, unless env sets them."""
        helper = env_helper()
        for key in DERIVED_KEYS:
            with self.subTest(key=key):
                self.assertIn(f'(get $env "{key}" | default', helper)
                self.assertNotIn(f"\n  {key}:", VALUES_PATH.read_text(encoding="utf-8"))

    def test_reads_the_infrastructure_secrets(self):
        """Every Kubernetes Secret that smarter-infrastructure creates is mapped to the settings it holds."""
        values = VALUES_PATH.read_text(encoding="utf-8")
        for secret_name in INFRASTRUCTURE_SECRETS:
            with self.subTest(secret=secret_name):
                self.assertIn(f"\n    {secret_name}:\n", values)
        self.assertIn('lookup "v1" "Secret" $.Release.Namespace $secretName', env_helper())

    def test_mariadb_reads_the_platform_passwords(self):
        """MariaDB's Secret keeps the subchart's own name, so that its pod spec doesn't change."""
        values = VALUES_PATH.read_text(encoding="utf-8")
        self.assertIn('existingSecret: "{{ .Release.Name }}-mariadb"', values)
        template = MARIADB_SECRET_PATH.read_text(encoding="utf-8")
        self.assertIn('{{- $name := printf "%s-mariadb" .Release.Name }}', template)
        for key in ("mariadb-root-password", "mariadb-password", "mariadb-replication-password"):
            with self.subTest(key=key):
                self.assertIn(f"  {key}:", template)


class TestMigrateEnvironment(unittest.TestCase):
    """
    The pre-upgrade migrate Job runs with the new release's settings, not the previous release's.

    Helm applies secret-env.yaml only after the pre-upgrade hooks. v0.46.16 renamed SECRET_KEY to
    DJANGO_SECRET_KEY, and its migrate Job, which read secret-env.yaml's Secret, failed with
    "DJANGO_SECRET_KEY is not set" and stopped the deploy.
    """

    @staticmethod
    def hook_weight(template: str) -> int:
        """
        Return a hook template's helm.sh/hook-weight.

        :param template: The template's text.
        :returns: Its weight.
        """
        match = re.search(r'"helm\.sh/hook-weight": "(-?\d+)"', template)
        if match is None:
            raise AssertionError("the template has no hook weight")
        weight = int(match.group(1))
        return weight

    def test_job_reads_the_hook_secret(self):
        """The Job's envFrom names the hook Secret, not the release's env Secret."""
        job = MIGRATE_JOB_PATH.read_text(encoding="utf-8")
        self.assertIn('name: "{{ .Values.global.appName }}-env-migrate"', job)
        self.assertNotIn('name: "{{ .Values.global.appName }}-env"\n', job)

    def test_hook_secret_has_the_platform_settings(self):
        """The hook Secret is built by smarter.env, like the env Secret, so it has the new release's names."""
        secret = MIGRATE_SECRET_PATH.read_text(encoding="utf-8")
        self.assertIn('name: "{{ .Values.global.appName }}-env-migrate"', secret)
        self.assertIn('include "smarter.env" . | fromYaml', secret)

    def test_hook_secret_is_created_before_the_job(self):
        """Both are pre-upgrade hooks, and the Secret's lower weight makes Helm create it first."""
        secret = MIGRATE_SECRET_PATH.read_text(encoding="utf-8")
        job = MIGRATE_JOB_PATH.read_text(encoding="utf-8")
        for template in (secret, job):
            self.assertIn('"helm.sh/hook": pre-upgrade', template)
        self.assertLess(self.hook_weight(secret), self.hook_weight(job))

    def test_hook_secret_is_replaced_on_each_upgrade(self):
        """A failed upgrade's copy is replaced by the next upgrade's, and a passing upgrade deletes it."""
        secret = MIGRATE_SECRET_PATH.read_text(encoding="utf-8")
        self.assertIn('"helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded', secret)


if __name__ == "__main__":
    unittest.main()
