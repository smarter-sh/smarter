"""
Tests of the AWS access keys in the chart's env Secret, templates/secret-env.yaml.

When the pods have an IAM role (serviceAccount.awsRoleArn), the deploy workflow sets
env.AWS_ACCESS_KEY_ID and env.AWS_SECRET_ACCESS_KEY to null, because a key in the pods'
environment would win over the role. values.yaml has no default for them, so the null reaches
the schema and the template. A schema that only allowed a string once failed a prod deploy at
helm upgrade. These tests check that both accept the null, and that the Secret leaves it out.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import json
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
SCHEMA_PATH = CHART_PATH / "values.schema.json"
VALUES_PATH = CHART_PATH / "values.yaml"
TEMPLATE_PATH = CHART_PATH / "templates" / "secret-env.yaml"

OPTIONAL_KEYS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")


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
        text = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn('{{- if not (kindIs "invalid" $value) }}', text)


if __name__ == "__main__":
    unittest.main()
