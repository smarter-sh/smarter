"""Test :mod:`smarter.apps.prompt.contract.schema`, and the ``export_chat_contract_schema`` command."""

import json
import os
import tempfile

from django.core.management import call_command

from smarter.apps.prompt.contract.const import SCHEMA_PATH
from smarter.apps.prompt.contract.models import CONTRACT_MODELS
from smarter.apps.prompt.contract.schema import (
    SCHEMA_ID,
    chat_contract_schema,
    chat_contract_schema_json,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestChatContractSchema(SmarterTestBase):
    """Test the JSON Schema of the Smarter Chat api contract."""

    def test_schema_defines_every_model(self):
        schema = chat_contract_schema()
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertEqual(schema["$id"], SCHEMA_ID)
        for model in CONTRACT_MODELS:
            with self.subTest(model=model.__name__):
                self.assertIn(model.__name__, schema["$defs"])

    def test_committed_schema_is_up_to_date(self):
        """Chat-contract.schema.json must be regenerated, and copied into Smarter Chat, when the models change."""
        with open(SCHEMA_PATH, encoding="utf-8") as file:
            committed = file.read()
        self.assertEqual(
            committed,
            chat_contract_schema_json(),
            "chat-contract.schema.json is out of date. Run `manage.py export_chat_contract_schema`, "
            "then `make chat-contract` to copy it into Smarter Chat.",
        )

    def test_export_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "schema.json")
            call_command("export_chat_contract_schema", output=path)
            with open(path, encoding="utf-8") as file:
                self.assertEqual(json.load(file), json.loads(chat_contract_schema_json()))
