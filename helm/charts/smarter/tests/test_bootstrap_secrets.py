"""
Tests of the platform's bootstrap secrets in the chart: templates/secret-bootstrap.yaml, and its mount (issue #1099).

The keys of the built-in Providers, the search plugins and the managed vector databases become Smarter Secrets in
the init Job, from a Kubernetes Secret that only the init Job mounts, never from an environment variable. These tests
read the templates and values as text, as the chart's other tests do.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import json
import re
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
TEMPLATES_PATH = CHART_PATH / "templates"
SECRET_TEMPLATE_PATH = TEMPLATES_PATH / "secret-bootstrap.yaml"
INIT_JOB_PATH = TEMPLATES_PATH / "job-init.yaml"
VALUES_PATH = CHART_PATH / "values.yaml"
SCHEMA_PATH = CHART_PATH / "values.schema.json"

MOUNT_PATH = "/home/smarter_user/bootstrap-secrets"
"""The mount, smarter_settings.bootstrap_secrets_dir's default."""


class TestBootstrapSecrets(unittest.TestCase):
    """The bootstrap Secret is built from bootstrapSecrets, and only the init Job mounts it."""

    def test_the_secret_comes_from_its_values(self):
        text = SECRET_TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn('name: "{{ .Values.global.appName }}-bootstrap-secrets"', text)
        self.assertIn(".Values.bootstrapSecrets", text)
        # an empty value is left out, so that initialize_bootstrap_secrets never sees it.
        self.assertIn("{{- if $value }}", text)

    def test_only_the_init_job_mounts_it(self):
        init_job = INIT_JOB_PATH.read_text(encoding="utf-8")
        self.assertIn(f"mountPath: {MOUNT_PATH}", init_job)
        self.assertIn('secretName: "{{ .Values.global.appName }}-bootstrap-secrets"', init_job)
        self.assertIn("readOnly: true", init_job)
        # optional, so that a platform without bootstrap secrets still initializes.
        self.assertIn("optional: true", init_job)
        for template in TEMPLATES_PATH.glob("*.yaml"):
            if template.name in ("job-init.yaml", "secret-bootstrap.yaml"):
                continue
            with self.subTest(template=template.name):
                self.assertNotIn("bootstrap-secrets", template.read_text(encoding="utf-8"))

    def test_no_key_is_an_environment_variable(self):
        """The keys are bootstrapSecrets, never env: no pod's environment holds them."""
        values = VALUES_PATH.read_text(encoding="utf-8")
        self.assertIsNotNone(re.search(r"^bootstrapSecrets: \{\}$", values, re.MULTILINE))
        for prefix in ("SMARTER_APP_PROVIDER_", "SMARTER_APP_LLMTOOL_", "SMARTER_APP_VECTORSTORE_"):
            with self.subTest(prefix=prefix):
                pattern = rf"^\s*#?\s*{prefix}\w*(_API_KEY|_B64):"
                self.assertIsNone(re.search(pattern, values, re.MULTILINE))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        env = schema["properties"]["env"]["properties"]
        for variable in env:
            with self.subTest(variable=variable):
                self.assertFalse(variable.endswith("_API_KEY") and variable.startswith("SMARTER_APP_"))
        self.assertIn("bootstrapSecrets", schema["properties"])


if __name__ == "__main__":
    unittest.main()
