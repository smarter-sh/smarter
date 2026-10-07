"""Test the cli 'validate' command, :class:`smarter.apps.api.v1.cli.views.validate.ApiV1CliValidateApiView`."""

import copy
import json
import os
from http import HTTPStatus

import yaml

from smarter.apps.guardrail.models import Guardrail
from smarter.lib.journal.enum import SmarterJournalApiResponseKeys

from .base_class import ApiV1CliTestBase

GUARDRAIL_MANIFEST = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "..",
    "guardrail",
    "manifest",
    "brokers",
    "tests",
    "data",
    "guardrail.yaml",
)


class TestApiCliV1Validate(ApiV1CliTestBase):
    """Test that the validate command reports a manifest's errors, with their paths, without saving it."""

    path = "/api/v1/cli/validate/"

    def setUp(self):
        super().setUp()
        with open(GUARDRAIL_MANIFEST, encoding="utf-8") as f:
            self.manifest = yaml.safe_load(f)
        self.manifest["metadata"]["name"] = "test_cli_validate"
        self.addCleanup(Guardrail.objects.filter(name="test_cli_validate").delete)

    def validate(self, manifest: dict) -> dict:
        """Validate a manifest, and return the response's data."""
        response, status = self.get_response(path=self.path, data=manifest)
        self.assertEqual(status, HTTPStatus.OK, response)
        self.assertEqual(response[SmarterJournalApiResponseKeys.METADATA]["command"], "validate")
        return response[SmarterJournalApiResponseKeys.DATA]

    def locs(self, data: dict) -> list[list[str]]:
        return [error["loc"] for error in data["errors"]]

    def test_valid(self):
        """Test that a valid manifest has no errors, and is not saved."""
        data = self.validate(self.manifest)
        self.assertEqual(data, {"valid": True, "errors": []})
        self.assertFalse(Guardrail.objects.filter(name="test_cli_validate").exists())

    def test_missing_field(self):
        """Test that a missing field is reported with its path."""
        manifest = copy.deepcopy(self.manifest)
        del manifest["metadata"]["version"]
        data = self.validate(manifest)
        self.assertFalse(data["valid"])
        self.assertIn(["metadata", "version"], self.locs(data))

    def test_invalid_value(self):
        """Test that an invalid value is reported with its path."""
        manifest = copy.deepcopy(self.manifest)
        manifest["spec"]["config"]["severity"] = "not a number"
        data = self.validate(manifest)
        self.assertFalse(data["valid"])
        self.assertTrue(any(loc[:3] == ["spec", "config", "severity"] for loc in self.locs(data)), data)

    def test_model_validator_error(self):
        """Test that an error of the model's validators, which crosses fields, is reported."""
        manifest = copy.deepcopy(self.manifest)
        manifest["spec"]["config"]["strategy"] = "llm_judge"
        data = self.validate(manifest)
        self.assertFalse(data["valid"])
        self.assertTrue(all(error["message"] for error in data["errors"]), data)

    def test_unknown_kind(self):
        """Test that an unknown kind is reported as an error of kind."""
        manifest = copy.deepcopy(self.manifest)
        manifest["kind"] = "NotAKind"
        data = self.validate(manifest)
        self.assertFalse(data["valid"])
        self.assertEqual(self.locs(data), [["kind"]])
        self.assertIn("Guardrail", data["errors"][0]["message"])

    def test_missing_kind(self):
        """Test that a manifest without a kind is reported as an error of kind."""
        manifest = copy.deepcopy(self.manifest)
        del manifest["kind"]
        data = self.validate(manifest)
        self.assertFalse(data["valid"])
        self.assertEqual(
            data["errors"], [{"loc": ["kind"], "message": data["errors"][0]["message"], "type": "invalid_kind"}]
        )

    def test_kind_is_case_insensitive(self):
        """Test that the kind's broker is found case insensitively, like the other cli commands."""
        manifest = copy.deepcopy(self.manifest)
        manifest["kind"] = "guardrail"
        data = self.validate(manifest)
        self.assertNotIn(["kind"], [error["loc"] for error in data["errors"] if error["type"] == "invalid_kind"])

    def test_not_an_object(self):
        """Test that a manifest that is not a JSON object is reported as an invalid manifest, with an empty loc."""
        response, status = self.get_response(path=self.path, manifest=json.dumps(["not", "a", "manifest"]))
        self.assertEqual(status, HTTPStatus.OK, response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertFalse(data["valid"])
        self.assertEqual(len(data["errors"]), 1)
        self.assertEqual(data["errors"][0]["loc"], [])
        self.assertEqual(data["errors"][0]["type"], "invalid_manifest")

    def test_message(self):
        """Test that the response's message counts the errors."""
        response, _ = self.get_response(path=self.path, data=self.manifest)
        self.assertEqual(response[SmarterJournalApiResponseKeys.MESSAGE], "Manifest is valid")
        manifest = copy.deepcopy(self.manifest)
        del manifest["metadata"]["version"]
        response, _ = self.get_response(path=self.path, data=manifest)
        errors = response[SmarterJournalApiResponseKeys.DATA]["errors"]
        self.assertEqual(response[SmarterJournalApiResponseKeys.MESSAGE], f"Manifest has {len(errors)} error(s)")
