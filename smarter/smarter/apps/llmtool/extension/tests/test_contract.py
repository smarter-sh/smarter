"""Tests of smarter.apps.llmtool.extension.contract: the Extensions console api's models and schema."""

import io
import json

from django.core.management import call_command

from smarter.apps.llmtool.extension.contract import (
    SCHEMA_PATH,
    ConfigureRequest,
    ExtensionSummary,
    contract_schema,
    contract_schema_json,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestExtensionConsoleContract(SmarterTestBase):
    """Test the contract's JSON, and that its committed schema is current."""

    def test_schema_is_current(self):
        """The committed schema is the models' schema."""
        self.assertEqual(
            json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
            contract_schema(),
            "extension-console.schema.json is out of date. Run `make extension-contract`, and commit it.",
        )
        self.assertEqual(contract_schema_json(), SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_json_is_camel_case(self):
        """The api's JSON is camelCase, and requests are validated by either name."""
        self.assertIn("displayName", ExtensionSummary.model_json_schema(mode="serialization")["properties"])
        request = ConfigureRequest.model_validate({"secrets": {"api_key": {"secretId": 3}}})
        self.assertEqual(request.secrets["api_key"].secret_id, 3)

    def test_export_command(self):
        """The export command writes the schema."""
        output = io.StringIO()
        call_command("export_extension_console_schema", stdout=output)
        self.assertIn("extension-console.schema.json", output.getvalue())
