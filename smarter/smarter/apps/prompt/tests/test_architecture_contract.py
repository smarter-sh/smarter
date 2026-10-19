"""Tests of smarter.apps.prompt.views.detailviews.architecture_contract: the workbench's Architecture tab's schema."""

import io
import json

from django.core.management import call_command

from smarter.apps.prompt.views.detailviews.architecture_contract import (
    SCHEMA_PATH,
    contract_schema,
    contract_schema_json,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestLLMClientArchitectureContract(SmarterTestBase):
    """Test the contract's schema, and that its committed copy is current."""

    def test_schema_is_current(self):
        """The committed schema is the models' schema."""
        self.assertEqual(
            json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
            contract_schema(),
            "llmclient-architecture.schema.json is out of date. Run `make llmclient-architecture-contract`, "
            "and commit it.",
        )
        self.assertEqual(contract_schema_json(), SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_every_field_is_required(self):
        """A node always has every field, so that the TypeScript types have no optional ones."""
        node = contract_schema()["$defs"]["SAMDependencyTreeNode"]
        self.assertEqual(set(node["required"]), set(node["properties"]))
        self.assertIn("owner", node["properties"])

    def test_export_command(self):
        """The export command writes the schema."""
        output = io.StringIO()
        call_command("export_llmclient_architecture_schema", stdout=output)
        self.assertIn("llmclient-architecture.schema.json", output.getvalue())
