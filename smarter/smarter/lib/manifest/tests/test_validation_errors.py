"""Test :meth:`smarter.lib.manifest.broker.AbstractBroker.validation_errors`."""

import copy
import os

import yaml
from pydantic import BaseModel, model_validator

from smarter.apps.guardrail.manifest.brokers.guardrail import SAMGuardrailBroker
from smarter.apps.guardrail.models import Guardrail
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.unittest.base_classes import SmarterTestBase

GUARDRAIL_MANIFEST = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "apps",
    "guardrail",
    "manifest",
    "brokers",
    "tests",
    "data",
    "guardrail.yaml",
)


class RaisesSAMValidationError(BaseModel):
    """A model whose validator raises a SAMValidationError, which Pydantic does not wrap."""

    @model_validator(mode="before")
    @classmethod
    def fail(cls, data):
        raise SAMValidationError("the manifest is not valid")


class RaisesEmptyError(BaseModel):
    """A model whose validator raises an exception without a message."""

    @model_validator(mode="before")
    @classmethod
    def fail(cls, data):
        raise RuntimeError()


class SAMValidationErrorBroker(AbstractBroker):  # pylint: disable=abstract-method
    """A broker whose model raises a SAMValidationError.

    validation_errors() is a classmethod, so it is never built.
    """

    _pydantic_model = RaisesSAMValidationError  # type: ignore[assignment]


class EmptyErrorBroker(AbstractBroker):  # pylint: disable=abstract-method
    """A broker whose model raises an exception without a message."""

    _pydantic_model = RaisesEmptyError  # type: ignore[assignment]


class TestValidationErrors(SmarterTestBase):
    """Test that validation_errors() reports a manifest's errors, with their paths, without saving it."""

    def setUp(self):
        super().setUp()
        with open(GUARDRAIL_MANIFEST, encoding="utf-8") as f:
            self.manifest = yaml.safe_load(f)
        self.manifest["metadata"]["name"] = "test_validation_errors"
        self.addCleanup(Guardrail.objects.filter(name="test_validation_errors").delete)

    def test_valid(self):
        """Test that a valid manifest has no errors, and is not saved."""
        self.assertEqual(SAMGuardrailBroker.validation_errors(self.manifest), [])
        self.assertFalse(Guardrail.objects.filter(name="test_validation_errors").exists())

    def test_does_not_change_manifest(self):
        """Test that validation does not change the manifest."""
        manifest = copy.deepcopy(self.manifest)
        SAMGuardrailBroker.validation_errors(manifest)
        self.assertEqual(manifest, self.manifest)

    def test_pydantic_errors(self):
        """Test that Pydantic's errors keep their loc, as strings, with a message and a type."""
        manifest = copy.deepcopy(self.manifest)
        del manifest["metadata"]["version"]
        errors = SAMGuardrailBroker.validation_errors(manifest)
        self.assertIn({"loc": ["metadata", "version"], "message": "Field required", "type": "missing"}, errors)
        for error in errors:
            self.assertEqual(set(error.keys()), {"loc", "message", "type"})
            self.assertTrue(all(isinstance(part, str) for part in error["loc"]), error)

    def test_list_index_loc_is_a_string(self):
        """Test that a list index in a loc, e.g. of a detector, is converted to a string."""
        manifest = copy.deepcopy(self.manifest)
        manifest["spec"]["config"]["detectors"] = [{"not": "a detector"}]
        errors = SAMGuardrailBroker.validation_errors(manifest)
        self.assertTrue(errors)
        self.assertTrue(any("0" in error["loc"] for error in errors), errors)
        self.assertTrue(all(isinstance(part, str) for error in errors for part in error["loc"]), errors)

    def test_empty_manifest(self):
        """Test that an empty manifest reports its missing top-level fields."""
        locs = [error["loc"] for error in SAMGuardrailBroker.validation_errors({})]
        for field in ("apiVersion", "kind", "metadata", "spec"):
            self.assertIn([field], locs)

    def test_other_exception(self):
        """Test that a validator's exception other than ValueError is reported with an empty loc, and its message."""
        errors = SAMValidationErrorBroker.validation_errors(self.manifest)
        self.assertEqual(
            errors, [{"loc": [], "message": "the manifest is not valid", "type": SAMValidationError.__name__}]
        )

    def test_exception_without_message(self):
        """Test that an exception without a message is reported with its type's name as its message."""
        errors = EmptyErrorBroker.validation_errors(self.manifest)
        self.assertEqual(errors, [{"loc": [], "message": "RuntimeError", "type": "RuntimeError"}])
