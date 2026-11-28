"""
Tests of the chart's copy of the credentials map, files/credentials.json (ADR-038, phase 3).

Each credential setting says which kinds of pod hold it. ``manage.py export_chart_credentials`` writes that, as
JSON, to smarter/smarter/common/conf/credentials.json, which a Django test keeps equal to the settings, and
``make chart-credentials`` copies it here, because the chart can read only its own files. These tests keep the
copy equal to the original, and check its shape, so that the chart's Secrets can rely on it.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import json
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
REPOSITORY_PATH = CHART_PATH.parent.parent.parent
CHART_COPY_PATH = CHART_PATH / "files" / "credentials.json"
ORIGINAL_PATH = REPOSITORY_PATH / "smarter" / "smarter" / "common" / "conf" / "credentials.json"

POD_KINDS = (
    "api",
    "worker",
    "worker-infrastructure",
    "beat",
    "worker-tools",
    "worker-extensions",
    "job-init",
    "job-migrate",
    "bastion",
)
"""The kinds of pod, as SERVICE_TYPE names them: smarter.common.const.SmarterKubernetesPodKinds.all."""


class TestCredentials(unittest.TestCase):
    """The chart's copy of the credentials map is the settings' own, and names only known kinds of pod."""

    def test_the_copy_is_current(self):
        copy = CHART_COPY_PATH.read_text(encoding="utf-8")
        original = ORIGINAL_PATH.read_text(encoding="utf-8")
        self.assertEqual(copy, original, "Run `make chart-credentials`, and commit both copies.")

    def test_its_shape(self):
        """Each environment variable maps to a sorted list of known kinds of pod, possibly empty."""
        holders = json.loads(CHART_COPY_PATH.read_text(encoding="utf-8"))
        self.assertTrue(holders)
        for variable, pods in holders.items():
            with self.subTest(variable=variable):
                self.assertIsInstance(pods, list)
                self.assertEqual(pods, sorted(pods))
                for pod in pods:
                    self.assertIn(pod, POD_KINDS)

    def test_the_restricted_workers_hold_only_redis(self):
        """The tool worker and the Extension worker hold no credential but their Redis user's password (ADR-038)."""
        holders = json.loads(CHART_COPY_PATH.read_text(encoding="utf-8"))
        restricted = []
        for variable, pods in holders.items():
            if "worker-tools" in pods or "worker-extensions" in pods:
                restricted.append(variable)
        self.assertEqual(restricted, ["SMARTER_SUBSYSTEM_REDIS_PASSWORD"])


if __name__ == "__main__":
    unittest.main()
