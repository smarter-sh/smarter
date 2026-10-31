"""Test :func:`smarter.apps.api.v1.cli.validation.validate_manifest`.

The cli 'validate' view's tests, in test_validate.py, cover the errors over HTTP.
"""

import os
from unittest import mock

import yaml

from smarter.apps.api.v1.cli.validation import validate_manifest
from smarter.apps.guardrail.manifest.brokers.guardrail import SAMGuardrailBroker
from smarter.lib.unittest.base_classes import SmarterTestBase

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


class TestValidateManifest(SmarterTestBase):
    """Test validate_manifest() without HTTP."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open(GUARDRAIL_MANIFEST, encoding="utf-8") as f:
            cls.manifest = yaml.safe_load(f)

    def test_valid(self):
        """A valid manifest has no errors."""
        validation = validate_manifest(self.manifest)
        self.assertTrue(validation.valid)
        self.assertEqual(validation.errors, [])

    def test_not_an_object_and_unknown_kind(self):
        """A manifest that is not an object, or whose kind is unknown, has one error."""
        self.assertEqual(validate_manifest(["a list"]).errors[0].type, "invalid_manifest")
        self.assertEqual(validate_manifest({**self.manifest, "kind": "Chatbot"}).errors[0].loc, ["kind"])
        self.assertEqual(validate_manifest({"apiVersion": "smarter.sh/v1"}).errors[0].type, "invalid_kind")

    def test_external_checks(self):
        """External checks run by default, and are passed to the broker."""
        with mock.patch.object(SAMGuardrailBroker, "validation_errors", return_value=[]) as validation_errors:
            validate_manifest(self.manifest)
            validate_manifest(self.manifest, external_checks=False)
        self.assertEqual(
            [call.kwargs["external_checks"] for call in validation_errors.call_args_list],
            [True, False],
        )
