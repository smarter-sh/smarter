"""
Tests of the user's own Django settings in the chart: values.djangoSettings, templates/secret-django-settings.yaml.

The chart writes djangoSettings to a Secret, and every pod that loads Django's settings mounts it at
/home/smarter_user/user-settings/, where smarter.settings.user applies it after all of Smarter's
settings. A pod that doesn't mount it runs with Smarter's values, silently, so these tests check every
template that runs Django.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import json
import re
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
TEMPLATES_PATH = CHART_PATH / "templates"
SCHEMA_PATH = CHART_PATH / "values.schema.json"
VALUES_PATH = CHART_PATH / "values.yaml"
HELPERS_PATH = TEMPLATES_PATH / "_helpers.tpl"
SECRET_PATH = TEMPLATES_PATH / "secret-django-settings.yaml"

DJANGO_TEMPLATES = (
    "deployment-api.yaml",
    "deployment-beat.yaml",
    "deployment-worker.yaml",
    "deployment-worker-infrastructure.yaml",
    "job-init.yaml",
    "job-migrate.yaml",
)
"""The templates whose pods load Django's settings."""

DEPLOYMENTS = DJANGO_TEMPLATES[:4]
"""The templates whose pods a changed setting must roll."""


class TestDjangoSettings(unittest.TestCase):
    """DjangoSettings reaches every pod that loads Django's settings."""

    def test_values_default_to_none(self):
        """Values.yaml sets no user setting: Smarter's own values apply."""
        text = VALUES_PATH.read_text(encoding="utf-8")
        self.assertIn("\ndjangoSettings: {}\n", text)

    def test_schema_requires_setting_names(self):
        """The schema allows a map whose keys are upper case setting names."""
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        django_settings = schema["properties"]["djangoSettings"]
        self.assertEqual(django_settings["type"], "object")
        pattern = re.compile(django_settings["propertyNames"]["pattern"])
        self.assertTrue(pattern.match("SESSION_COOKIE_AGE"))
        self.assertFalse(pattern.match("session_cookie_age"))

    def test_secret_holds_the_settings_as_yaml(self):
        text = SECRET_PATH.read_text(encoding="utf-8")
        self.assertIn('name: "{{ .Values.global.appName }}-django-settings"', text)
        self.assertIn("settings.yaml: |", text)
        self.assertIn("toYaml (.Values.djangoSettings | default dict)", text)

    def test_the_volume_is_optional_and_read_only(self):
        """A pre-upgrade hook runs before the Secret exists, on the first upgrade that adds it."""
        text = HELPERS_PATH.read_text(encoding="utf-8")
        self.assertIn('secretName: "{{ .Values.global.appName }}-django-settings"\n    optional: true', text)
        self.assertIn("mountPath: /home/smarter_user/user-settings\n  readOnly: true", text)

    def test_every_django_pod_mounts_it(self):
        for name in DJANGO_TEMPLATES:
            with self.subTest(template=name):
                text = (TEMPLATES_PATH / name).read_text(encoding="utf-8")
                self.assertIn('include "smarter.userSettingsVolumes"', text)
                self.assertIn('include "smarter.userSettingsVolumeMounts"', text)

    def test_a_changed_setting_rolls_the_deployments(self):
        for name in DEPLOYMENTS:
            with self.subTest(template=name):
                text = (TEMPLATES_PATH / name).read_text(encoding="utf-8")
                self.assertIn("checksum/django-settings:", text)
                self.assertIn('"/secret-django-settings.yaml"', text)


if __name__ == "__main__":
    unittest.main()
