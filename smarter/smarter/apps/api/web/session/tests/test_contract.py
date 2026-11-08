"""Tests of smarter.apps.api.web.session.contract: the console session's schema."""

import io
import json

from django.core.management import call_command

from smarter.apps.api.web.session.contract import (
    SCHEMA_PATH,
    contract_schema,
    contract_schema_json,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestConsoleSessionContract(SmarterTestBase):
    """Test the contract's schema, and that its committed copy is current."""

    def test_schema_is_current(self):
        """The committed schema is the models' schema."""
        self.assertEqual(
            json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
            contract_schema(),
            "console-session.schema.json is out of date. Run `make console-session-contract`, and commit it.",
        )
        self.assertEqual(contract_schema_json(), SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_every_field_is_required(self):
        """Every model always has every field, so that the TypeScript types have no optional ones."""
        definitions = contract_schema()["$defs"]
        for name, definition in definitions.items():
            with self.subTest(name=name):
                self.assertEqual(set(definition["required"]), set(definition["properties"]))

    def test_fields_are_camel_case(self):
        """The JSON is camelCase, as the React code reads it."""
        properties = contract_schema()["$defs"]["ConsoleSession"]["properties"]
        self.assertIn("isAuthenticated", properties)
        self.assertIn("signIn", properties)
        self.assertNotIn("is_authenticated", properties)

    def test_export_command(self):
        """The export command writes the schema."""
        output = io.StringIO()
        call_command("export_console_session_schema", stdout=output)
        self.assertIn("console-session.schema.json", output.getvalue())
