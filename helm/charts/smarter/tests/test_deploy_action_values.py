"""
Tests of the values file that the deploy action writes for the chart.

.github/actions/deploy/action.yml builds /tmp/values.json from GitHub expressions, and helm upgrade
checks it against values.schema.json. Nothing else checks it before a deploy, so a value of the
wrong JSON type fails in production: v0.46.14 and v0.46.15 never deployed, because the action
quoted two settings that the schema types as boolean ("Expected: boolean, given: string").

These tests read the env block of that values file, work out the JSON type each expression
writes, and check it against the schema. They need only the standard library. Run them from the
repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import json
import re
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
SCHEMA_PATH = CHART_PATH / "values.schema.json"
ACTION_PATH = CHART_PATH.parent.parent.parent / ".github" / "actions" / "deploy" / "action.yml"

ENTRY = re.compile(r'^\s*"(?P<key>[A-Z][A-Z0-9_]*)":\s*(?P<value>.*?),?\s*$')
"""One "KEY": value line of the env block."""

QUOTED_FORMAT = "format('\"{0}\"'"
"""The expression that writes its input as a JSON string."""


def action_env_values() -> dict[str, str]:
    """
    Return the env block of the values file that the deploy action writes.

    :returns: Each key, mapped to the text of its value: a literal or a GitHub expression.
    """
    text = ACTION_PATH.read_text(encoding="utf-8")
    start = text.index("cat > /tmp/values.json <<EOF")
    start = text.index('"env": {', start)
    entries: dict[str, str] = {}
    for line in text[start:].splitlines()[1:]:
        if line.strip().startswith("}"):
            break
        match = ENTRY.match(line)
        if match:
            entries[match.group("key")] = match.group("value")
    return entries


def json_types(value: str) -> set[str] | None:
    """
    Return the JSON types that a value of the env block can write.

    :param value: The text of the value: a literal, a command substitution or a GitHub expression.
    :returns: The types, e.g. ``{"string", "null"}``, or None for a form this test doesn't know.
    """
    types = set()
    if "'null'" in value:
        types.add("null")
    if value.startswith('"') or value.startswith("$(jq ") or QUOTED_FORMAT in value:
        return types | {"string"}
    if value.startswith("${{"):
        literals = set(re.findall(r"'([^']*)'", value))
        if literals and literals <= {"true", "false", "null"}:
            return types | ({"boolean"} if literals - {"null"} else set())
    return None


class TestDeployActionValues(unittest.TestCase):
    """The deploy action writes each env value with a type that the chart's schema accepts."""

    @classmethod
    def setUpClass(cls):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.schema_env = schema["properties"]["env"]["properties"]
        cls.values = action_env_values()

    def test_reads_the_env_block(self):
        """The parser finds the env block, including the keys that once failed a deploy."""
        self.assertGreater(len(self.values), 50)
        self.assertIn("SMARTER_PLATFORM_STATIC_FILES_ON_CDN", self.values)
        self.assertIn("SMARTER_APP_DASHBOARD_WEB_CONSOLE_TERMINAL_ENABLE", self.values)

    def test_every_value_has_a_known_type(self):
        """Each value is a form that json_types understands, so no key escapes the type check."""
        for key, value in self.values.items():
            with self.subTest(key=key):
                self.assertIsNotNone(json_types(value), f"unknown value form: {value}")

    def test_types_match_the_schema(self):
        """
        Each value's type is one the schema allows for its key.

        null is left out: the action writes it only when an input is empty, and Helm then drops the
        key in favour of values.yaml's default. test_env_secret covers the keys without a default.
        """
        for key, value in self.values.items():
            schema_type = self.schema_env.get(key, {}).get("type")
            if schema_type is None:
                continue
            allowed = {schema_type} if isinstance(schema_type, str) else set(schema_type)
            written = (json_types(value) or set()) - {"null"}
            with self.subTest(key=key):
                self.assertLessEqual(written, allowed, f"{key} is written as {written}, the schema expects {allowed}")

    def test_json_types_of_the_known_forms(self):
        """Json_types tells a quoted input from a boolean one."""
        quoted = "${{ inputs.x && format('\"{0}\"', inputs.x) || 'null' }}"
        boolean = "${{ inputs.x && (inputs.x == 'true' && 'true' || 'false') || 'null' }}"
        self.assertEqual(json_types(quoted), {"string", "null"})
        self.assertEqual(json_types(boolean), {"boolean", "null"})
        self.assertEqual(json_types('"https://${{ inputs.root-domain }}"'), {"string"})
        self.assertEqual(json_types("$(jq -Rn --arg v \"${{ inputs.k }}\" '$v')"), {"string"})
        self.assertIsNone(json_types("${{ inputs.x }}"))


if __name__ == "__main__":
    unittest.main()
