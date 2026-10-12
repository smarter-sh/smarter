"""Test :mod:`smarter.apps.prompt.contract.example`, and the ``export_chat_contract_example`` command."""

import json
import os
import tempfile
import warnings

from django.core.management import call_command

from smarter.apps.prompt.contract.const import EXAMPLE_PATH
from smarter.apps.prompt.contract.example import (
    EXAMPLE_JSON_VALUE,
    _example_value,
    chat_contract_example,
    chat_contract_example_json,
)
from smarter.apps.prompt.contract.models import CONTRACT_MODELS
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestChatContractExample(SmarterTestBase):
    """Test the examples of the Smarter Chat api contract."""

    def test_every_example_validates(self):
        examples = chat_contract_example()
        self.assertEqual(set(examples), {model.__name__ for model in CONTRACT_MODELS})
        for model in CONTRACT_MODELS:
            with self.subTest(model=model.__name__), warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                model.model_validate(examples[model.__name__])

    def test_example_declares_optional_fields(self):
        message = chat_contract_example()["PromptChatApiMessage"]
        self.assertEqual(set(message), {"role", "content", "tool_calls", "tool_call_id", "name"})
        self.assertEqual(message["tool_calls"][0]["type"], "function")

    def test_example_value_fallbacks(self):
        self.assertEqual(_example_value({"type": "number"}, {}, "x"), 0.0)
        self.assertEqual(_example_value({"type": "object"}, {}, "x"), {})
        self.assertEqual(_example_value({}, {}, "x"), EXAMPLE_JSON_VALUE)
        self.assertIsNone(_example_value({"anyOf": [{"type": "null"}]}, {}, "x"))

    def test_committed_example_is_up_to_date(self):
        """Chat-contract.example.json must be regenerated when the models change."""
        with open(EXAMPLE_PATH, encoding="utf-8") as file:
            committed = file.read()
        self.assertEqual(
            committed,
            chat_contract_example_json(),
            "chat-contract.example.json is out of date. Run `manage.py export_chat_contract_example`.",
        )

    def test_export_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "example.json")
            call_command("export_chat_contract_example", output=path)
            with open(path, encoding="utf-8") as file:
                self.assertEqual(json.load(file), json.loads(chat_contract_example_json()))
