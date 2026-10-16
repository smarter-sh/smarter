"""Tests of smarter.apps.llmtool.views.listview.contract: the Extensions tab api's models and schema."""

import io
import json
from typing import get_args

from django.core.management import call_command

from smarter.apps.llmtool.models import ExtensionSource, ExtensionTrustBadge
from smarter.apps.llmtool.views.listview.contract import (
    SCHEMA_PATH,
    ExtensionListItem,
    ExtensionListPage,
    contract_schema,
    contract_schema_json,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestExtensionListContract(SmarterTestBase):
    """Test the contract's JSON, and that its committed schema is current."""

    def test_schema_is_current(self):
        """The committed schema is the models' schema."""
        self.assertEqual(
            json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
            contract_schema(),
            "extension-list.schema.json is out of date. Run `make llmtool-list-contract`, and commit it.",
        )
        self.assertEqual(contract_schema_json(), SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_schema_definitions(self):
        """The schema has the page, its items and its pagination, with every field of a response required."""
        definitions = contract_schema()["$defs"]
        for name in ("ExtensionListPage", "ExtensionListItem", "ListViewPagination"):
            self.assertIn(name, definitions)
        item = definitions["ExtensionListItem"]
        self.assertIn("displayName", item["properties"])
        self.assertIn("version", item["required"])
        self.assertFalse(item["additionalProperties"])

    def test_json_is_camel_case(self):
        """The api's JSON is camelCase."""
        self.assertIn("trustBadgeLabel", ExtensionListItem.model_json_schema(mode="serialization")["properties"])
        self.assertEqual(
            set(ExtensionListPage.model_json_schema(mode="serialization")["properties"]), {"objects", "pagination"}
        )

    def test_literals_match_the_model_choices(self):
        """The source and trust badge Literals are the Extension model's choices."""
        fields = ExtensionListItem.model_fields
        self.assertEqual(set(get_args(fields["source"].annotation)), set(ExtensionSource.values))
        self.assertEqual(set(get_args(fields["trust_badge"].annotation)), set(ExtensionTrustBadge.values))

    def test_export_command(self):
        """The export command writes the schema."""
        output = io.StringIO()
        call_command("export_extension_list_schema", stdout=output)
        self.assertIn("extension-list.schema.json", output.getvalue())
