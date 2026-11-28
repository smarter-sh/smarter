"""
Tests of how the chart brings up the platform's database: the init Job and the pods that wait for it.

- The post-install and post-upgrade init Job (job-init.yaml) runs once. A failed step fails it at
  once, rather than running all of ``manage.py initialize_platform`` again with Kubernetes' default
  of six retries, until ``helm upgrade --timeout`` hides the step's own error.
- On a fresh install, the pods of the api, the Celery workers and beat wait in an init container
  (``smarter.waitForDatabase`` in _helpers.tpl) until the init Job has created and migrated the
  database. Only on an install: on an upgrade, job-migrate.yaml has migrated before the rollout.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import re
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
TEMPLATES_PATH = CHART_PATH / "templates"
HELPERS_PATH = TEMPLATES_PATH / "_helpers.tpl"

WAITING_DEPLOYMENTS = (
    "deployment-api.yaml",
    "deployment-worker.yaml",
    "deployment-worker-infrastructure.yaml",
    "deployment-beat.yaml",
)
"""The Deployments whose pods use the database, and so wait for it on a fresh install."""

WAIT_FOR_DATABASE_PATTERN = re.compile(
    r'{{-? define "smarter.waitForDatabase" -}}\n(.*?)\n{{- end }}\n{{- end }}', re.DOTALL
)
"""The body of the smarter.waitForDatabase template in _helpers.tpl."""


def wait_for_database() -> str:
    """
    Return the body of the smarter.waitForDatabase template.

    :returns: Its text, from the line after its define.
    """
    match = WAIT_FOR_DATABASE_PATTERN.search(HELPERS_PATH.read_text(encoding="utf-8"))
    if match is None:
        raise AssertionError("_helpers.tpl has no smarter.waitForDatabase")
    return match.group(1)


class TestInitJob(unittest.TestCase):
    """The init Job runs initialize_platform once per deployment."""

    def test_is_never_retried(self):
        """A failed step fails the Job, instead of starting initialize_platform again."""
        text = (TEMPLATES_PATH / "job-init.yaml").read_text(encoding="utf-8")
        self.assertRegex(text, r"(?m)^spec:\n(?:  #.*\n)*  backoffLimit: 0$")


class TestWaitForDatabase(unittest.TestCase):
    """A fresh install's pods start on a migrated database."""

    def test_only_on_an_install(self):
        """Upgrades have migrated before the rollout, so their pods don't wait."""
        self.assertTrue(
            wait_for_database().startswith(
                "{{- $root := .root -}}\n{{- if $root.Release.IsInstall -}}\ninitContainers:"
            )
        )

    def test_waits_for_the_migrations(self):
        """It retries manage.py migrate --check until it passes."""
        self.assertIn("until python manage.py migrate --check", wait_for_database())

    def test_reads_the_pods_own_environment(self):
        """It connects with the database credentials of its pod's own Secret (ADR-038, phase 3)."""
        self.assertIn('name: "{{ include "smarter.podEnvName" . }}"', wait_for_database())

    def test_every_database_client_waits(self):
        """The api, the Celery workers and beat include it in their pods' spec."""
        for name in WAITING_DEPLOYMENTS:
            with self.subTest(deployment=name):
                text = (TEMPLATES_PATH / name).read_text(encoding="utf-8")
                self.assertRegex(
                    text,
                    r'\n      {{- include "smarter.waitForDatabase" \(dict "root" [.$] "pod" "[a-z-]+"\) \| nindent 6 }}'
                    r"\n      containers:\n",
                )


if __name__ == "__main__":
    unittest.main()
