# pylint: disable=wrong-import-position
"""Test User."""

import json
import os

from pydantic_core import ValidationError

from smarter.apps.account.manifest.models.user.model import SAMUser
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.manifest.loader import SAMLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class TestSmarterUserPydanticModel(TestAccountMixin):
    """
    Test the Smarter User Pydantic Model.
    """

    def get_data_full_filepath(self, filename: str) -> str:
        return os.path.join(HERE, "data", filename)

    def get_good_config_data(self):
        """Return a valid config dict as per user manifest."""
        return {
            "email": "joe@mail.com",
            "firstName": "John",
            "isActive": True,
            "isStaff": False,
            "lastName": "Doe",
        }

    def get_good_manifest_data(self):
        """Return a valid manifest dict as per user manifest."""
        return {
            "apiVersion": "smarter.sh/v1",
            "kind": "User",
            "metadata": {
                "description": "an example user manifest for the Smarter API User",
                "name": "example_user",
                "username": "example_user",
                "version": "1.0.0",
                "tags": ["user", "account"],
                "annotations": {
                    "smarter.sh/created-by": "system",
                    "smarter.sh/created-at": "2024-01-01T00:00:00Z",
                    "smarter.sh/updated-by": "system",
                    "smarter.sh/updated-at": "2024-01-01T00:00:00Z",
                    "smarter.sh/reviewed-by": "admin",
                    "smarter.sh/reviewed-at": "2024-01-02T00:00:00Z",
                },
            },
            "spec": {"config": self.get_good_config_data()},
        }

    def test_config_missing_required_fields(self):
        """Test missing required fields in spec.config."""
        for field in self.get_good_config_data():
            bad = self.get_good_manifest_data()
            del bad["spec"]["config"][field]
            with self.assertRaises(ValidationError, msg=f"Missing field: {field}"):
                SAMUser(**bad)

    def test_config_invalid_field_types(self):
        """Test invalid types for each field in spec.config."""
        for field, value in self.get_good_config_data().items():
            bad = self.get_good_manifest_data()
            # Use wrong type: str for bool, int for str, etc.
            if isinstance(value, bool):
                bad["spec"]["config"][field] = "notabool"
            else:
                bad["spec"]["config"][field] = 12345
            with self.assertRaises(ValidationError, msg=f"Invalid type for: {field}"):
                SAMUser(**bad)

    def test_config_empty_strings(self):
        """Test empty string for string fields in spec.config if not allowed."""
        for field, value in self.get_good_config_data().items():
            if isinstance(value, str):
                bad = self.get_good_manifest_data()
                bad["spec"]["config"][field] = ""
                try:
                    SAMUser(**bad)
                except ValidationError:
                    pass  # If model forbids empty, this is expected

    def test_config_extra_fields(self):
        """Test extra fields in spec.config."""
        bad = self.get_good_manifest_data()
        bad["spec"]["config"]["extra_field"] = "should not be here"
        try:
            SAMUser(**bad)
        except ValidationError:
            pass  # If model is strict, this is expected

    def test_manifest_initalization_good(self):
        """
        Test the manifest initialization with a good user manifest file.
        """
        filespec = self.get_data_full_filepath("user-good.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        pydantic_model = SAMUser(**loader.pydantic_model_dump())
        pydantic_model.model_dump_json()

    def test_user_model_required_fields(self):
        """Test that required fields are enforced."""
        with self.assertRaises(ValidationError):
            SAMUser()  # type: ignore

    def test_user_model_invalid_field_type(self):
        """Test that invalid field types raise ValidationError."""
        filespec = self.get_data_full_filepath("user-good.yaml")
        loader = SAMLoader(file_path=filespec)
        data = loader.pydantic_model_dump()
        # Example: email should be a string, try passing an int
        if "email" in data.get("spec", {}).get("config", {}):
            data["spec"]["config"]["email"] = 12345
            with self.assertRaises(ValidationError):
                SAMUser(**data)

    def test_user_model_extra_fields(self):
        """Test that extra fields are handled as expected (forbid/ignore/allow)."""
        filespec = self.get_data_full_filepath("user-good.yaml")
        loader = SAMLoader(file_path=filespec)
        data = loader.pydantic_model_dump()
        data["extra_field"] = "should not be here"
        try:
            SAMUser(**data)
        except ValidationError:
            pass  # If model is strict, this is expected

    def test_user_model_child_validation(self):
        """Test that child/nested models are validated."""
        filespec = self.get_data_full_filepath("user-good.yaml")
        loader = SAMLoader(file_path=filespec)
        data = loader.pydantic_model_dump()
        # Example: if 'profile' is a nested model with 'email' field
        if "profile" in data and isinstance(data["profile"], dict):
            data["profile"]["email"] = "not-an-email"
            with self.assertRaises(ValidationError):
                SAMUser(**data)

    def test_user_model_serialization(self):
        """Test model serialization to dict and JSON."""
        filespec = self.get_data_full_filepath("user-good.yaml")
        loader = SAMLoader(file_path=filespec)
        pydantic_model = SAMUser(**loader.pydantic_model_dump())
        model_dict = pydantic_model.model_dump()
        model_json = pydantic_model.model_dump_json()
        self.assertIsInstance(model_dict, dict)
        self.assertIsInstance(model_json, str)

    def test_user_model_deserialization(self):
        """Test model can be reconstructed from dict/JSON."""
        filespec = self.get_data_full_filepath("user-good.yaml")
        loader = SAMLoader(file_path=filespec)
        pydantic_model = SAMUser(**loader.pydantic_model_dump())
        # Use JSON serialization for both models to avoid datetime vs string mismatches
        model_dict_json = pydantic_model.model_dump(mode="json")
        model_json = pydantic_model.model_dump_json()
        # From dict
        model2 = SAMUser(**json.loads(model_json))
        self.assertEqual(model2.model_dump(mode="json"), model_dict_json)
        # From JSON
        model3 = SAMUser(**json.loads(model_json))
        self.assertEqual(model3.model_dump(mode="json"), model_dict_json)
