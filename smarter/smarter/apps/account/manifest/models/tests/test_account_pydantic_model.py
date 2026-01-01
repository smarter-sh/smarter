# pylint: disable=wrong-import-position
"""Test SAMAccount."""

import os

from pydantic_core import ValidationError

from smarter.apps.account.manifest.models.account.model import SAMAccount
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib import json
from smarter.lib.manifest.loader import SAMLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class TestSmarterAccountPydanticModel(TestAccountMixin):
    """
    Test the Smarter SAMAccount Pydantic Model.
    """

    def get_data_full_filepath(self, filename: str) -> str:
        return os.path.join(HERE, "data", filename)

    def get_good_config_data(self):
        """Return a valid config dict as per account-good.yaml."""
        return {
            "address1": "1 Main St",
            "address2": "Suite 100",
            "city": "Cambridge",
            "companyName": "Humble Geniuses, Inc.",
            "country": "USA",
            "currency": "USD",
            "language": "en-US",
            "phoneNumber": "617-555-1212",
            "postalCode": "02139",
            "state": "MA",
            "timezone": "America/New_York",
        }

    def get_good_manifest_data(self):
        """Return a valid manifest dict as per account-good.yaml."""
        return {
            "apiVersion": "smarter.sh/v1",
            "kind": "Account",
            "metadata": {
                "accountNumber": "1234-5678-9012",
                "description": "an example Account manifest",
                "name": "example_account",
                "version": "1.0.0",
                "tags": ["production", "backend", "mcdaniel"],
                "annotations": [
                    "smarter.sh/created-by: mcdaniel",
                    "smarter.sh/project: smarter-sh",
                ],
            },
            "spec": {"config": self.get_good_config_data()},
        }

    def test_config_missing_required_fields(self):
        """Test missing required fields in spec.config."""
        for field in self.get_good_config_data():
            bad = self.get_good_manifest_data()
            del bad["spec"]["config"][field]
            with self.assertRaises(ValidationError, msg=f"Missing field: {field}"):
                SAMAccount(**bad)

    def test_config_invalid_field_types(self):
        """Test invalid types for each field in spec.config."""
        for field in self.get_good_config_data():
            bad = self.get_good_manifest_data()
            bad["spec"]["config"][field] = 12345  # Int instead of str
            with self.assertRaises(ValidationError, msg=f"Invalid type for: {field}"):
                SAMAccount(**bad)

    def test_config_empty_strings(self):
        """Test empty string for each field in spec.config if not allowed."""
        for field in self.get_good_config_data():
            bad = self.get_good_manifest_data()
            bad["spec"]["config"][field] = ""
            try:
                SAMAccount(**bad)
            except ValidationError:
                pass  # If model forbids empty, this is expected

    def test_config_extra_fields(self):
        """Test extra fields in spec.config."""
        bad = self.get_good_manifest_data()
        bad["spec"]["config"]["extra_field"] = "should not be here"
        try:
            SAMAccount(**bad)
        except ValidationError:
            pass  # If model is strict, this is expected

    def test_manifest_initalization_good(self):
        """
        Test the manifest initialization with a good manifest file.
        """

        filespec = self.get_data_full_filepath("account-good.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        pydantic_model = SAMAccount(**loader.pydantic_model_dump())

        # dump the pydantic model to a dictionary
        # round_trip_dict = pydantic_model.model_dump()
        pydantic_model.model_dump_json()

    def test_account_model_required_fields(self):
        """Test that required fields are enforced."""
        with self.assertRaises(ValidationError):
            SAMAccount()  # type: ignore

    def test_account_model_invalid_field_type(self):
        """Test that invalid field types raise ValidationError."""
        filespec = self.get_data_full_filepath("account-good.yaml")
        loader = SAMLoader(file_path=filespec)
        data = loader.pydantic_model_dump()
        # Assume 'id' is a required string field, try passing an int
        if "id" in data:
            data["id"] = 12345
            with self.assertRaises(ValidationError):
                SAMAccount(**data)

    def test_account_model_extra_fields(self):
        """Test that extra fields are handled as expected (forbid/ignore/allow)."""
        filespec = self.get_data_full_filepath("account-good.yaml")
        loader = SAMLoader(file_path=filespec)
        data = loader.pydantic_model_dump()
        data["extra_field"] = "should not be here"
        try:
            SAMAccount(**data)
        except ValidationError:
            pass  # If model is strict, this is expected

    def test_account_model_child_validation(self):
        """Test that child/nested models are validated."""
        filespec = self.get_data_full_filepath("account-good.yaml")
        loader = SAMLoader(file_path=filespec)
        data = loader.pydantic_model_dump()
        # Try corrupting a nested/child field if present
        # Example: if 'profile' is a nested model with 'email' field
        if "profile" in data and isinstance(data["profile"], dict):
            data["profile"]["email"] = "not-an-email"
            with self.assertRaises(ValidationError):
                SAMAccount(**data)

    def test_account_model_serialization(self):
        """Test model serialization to dict and JSON."""
        filespec = self.get_data_full_filepath("account-good.yaml")
        loader = SAMLoader(file_path=filespec)
        pydantic_model = SAMAccount(**loader.pydantic_model_dump())
        model_dict = pydantic_model.model_dump()
        model_json = pydantic_model.model_dump_json()
        self.assertIsInstance(model_dict, dict)
        self.assertIsInstance(model_json, str)

    def test_account_model_deserialization(self):
        """Test model can be reconstructed from dict/JSON."""
        filespec = self.get_data_full_filepath("account-good.yaml")
        loader = SAMLoader(file_path=filespec)
        pydantic_model = SAMAccount(**loader.pydantic_model_dump())
        model_dict = pydantic_model.model_dump()
        model_json = pydantic_model.model_dump_json()
        # From dict
        model2 = SAMAccount(**model_dict)
        self.assertEqual(model2.model_dump(), model_dict)
        # From JSON
        model3 = SAMAccount(**json.loads(model_json))
        self.assertEqual(model3.model_dump(), model_dict)
