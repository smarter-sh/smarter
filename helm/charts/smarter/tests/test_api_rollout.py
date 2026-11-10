"""
Tests of the app Deployment's rolling update, app.rollingUpdate in values.yaml.

A deploy whose strategy has maxUnavailable: 0 never stops an old app pod until a new one is
ready. When no node has room for the extra pod, and the cluster autoscaler can't add a node,
the new pod stays Pending and the deploy never finishes. These tests check that the chart's
default lets a deploy stop one old pod to make room, and that the template takes its strategy
from values.yaml instead of hard-coding one.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import re
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
VALUES_PATH = CHART_PATH / "values.yaml"
TEMPLATE_PATH = CHART_PATH / "templates" / "deployment-api.yaml"

ROLLING_UPDATE_PATTERN = re.compile(
    r"^app:\n(?:(?:  .*|\s*)\n)*?  rollingUpdate:\n((?:    .*\n)+)",
    re.MULTILINE,
)
"""The block of app.rollingUpdate in values.yaml: its lines indented by four spaces."""


def rolling_update_values() -> dict[str, str]:
    """
    Return app.rollingUpdate from values.yaml.

    :returns: Each of its keys, with its value as written.
    """
    text = VALUES_PATH.read_text(encoding="utf-8")
    match = ROLLING_UPDATE_PATTERN.search(text)
    if match is None:
        raise AssertionError("values.yaml has no app.rollingUpdate")
    values = {}
    for line in match.group(1).splitlines():
        key, value = line.strip().split(":", 1)
        values[key] = value.strip()
    return values


class TestApiRollingUpdate(unittest.TestCase):
    """The app Deployment's default rolling update can always finish."""

    def test_max_unavailable_is_above_zero(self):
        """A deploy may stop an old pod before its replacement is ready."""
        values = rolling_update_values()
        max_unavailable = values["maxUnavailable"]
        self.assertNotIn(max_unavailable, ("0", "0%", '"0%"'))

    def test_max_surge_is_set(self):
        """A deploy still adds a new pod first, when a node has room for it."""
        values = rolling_update_values()
        self.assertIn("maxSurge", values)

    def test_template_uses_values(self):
        """The template renders app.rollingUpdate instead of a fixed strategy."""
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("toYaml $.Values.app.rollingUpdate", template)
        self.assertNotIn("maxUnavailable: 0", template)


if __name__ == "__main__":
    unittest.main()
