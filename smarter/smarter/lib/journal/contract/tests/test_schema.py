"""Test :mod:`smarter.lib.journal.contract.schema`, and the ``export_journal_contract_schema`` command."""

import json
import os
import tempfile

from django.core.management import call_command

from smarter.lib.journal.contract.const import SCHEMA_PATH
from smarter.lib.journal.contract.models import CONTRACT_MODELS
from smarter.lib.journal.contract.schema import (
    SCHEMA_ID,
    journal_contract_schema,
    journal_contract_schema_json,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestJournalContractSchema(SmarterTestBase):
    """Test the JSON Schema of the Smarter Journal api contract."""

    def test_schema_defines_every_model(self):
        schema = journal_contract_schema()
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["$id"], SCHEMA_ID)
        for model in CONTRACT_MODELS:
            with self.subTest(model=model.__name__):
                self.assertIn(model.__name__, schema["$defs"])

    def test_committed_schema_is_up_to_date(self):
        """Journal-contract.schema.json must be regenerated when the models change."""
        with open(SCHEMA_PATH, encoding="utf-8") as file:
            committed = file.read()
        self.assertEqual(
            committed,
            journal_contract_schema_json(),
            "journal-contract.schema.json is out of date. Run `manage.py export_journal_contract_schema`.",
        )

    def test_export_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "schema.json")
            call_command("export_journal_contract_schema", output=path)
            with open(path, encoding="utf-8") as file:
                self.assertEqual(json.load(file), json.loads(journal_contract_schema_json()))
