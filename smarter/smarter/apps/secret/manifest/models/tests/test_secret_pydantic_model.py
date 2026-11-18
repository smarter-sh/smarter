# pylint: disable=wrong-import-position
"""Test SAMSecret Pydantic Model."""

import os

from pydantic_core import ValidationError

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.manifest.models.secret.model import SAMSecret
from smarter.lib.manifest.parsing import read_manifest_file

HERE = os.path.abspath(os.path.dirname(__file__))


class TestSmarterSecretPydanticModel(TestAccountMixin):
    """Test SAMSecret Pydantic Model."""

    def get_data_full_filepath(self, filename: str) -> str:
        return os.path.join(HERE, "data", filename)

    def test_manifest_initalization_good(self):
        """Test the manifest initialization with a good manifest file."""

        filespec = self.get_data_full_filepath("secret-good.yaml")
        manifest_data = read_manifest_file(filespec)
        self.assertTrue(manifest_data, msg="the manifest is empty")
        sam_secret = SAMSecret(**manifest_data)

        # dump the pydantic model to a dictionary
        # round_trip_dict = sam_secret.model_dump()
        sam_secret.model_dump_json()
        # assert that everything in content is in round_trip_dict
        # self.assertTrue(dict_is_contained_in(content, round_trip_dict))

    def test_manifest_initalization_bad(self):
        """
        Test the manifest initialization with a manifest file.

        this is missing the required spec key, 'value'.
        """

        filespec = self.get_data_full_filepath("secret-bad.yaml")
        manifest_data = read_manifest_file(filespec)
        self.assertTrue(manifest_data, msg="the manifest is empty")

        with self.assertRaises(ValidationError) as context:
            SAMSecret(**manifest_data)

        self.assertIn("1 validation error for SAMSecret", str(context.exception))
        self.assertIn("spec.config.value", str(context.exception))
        self.assertIn("Field required [type=missing", str(context.exception))

    def test_manifest_initalization_bad2(self):
        """
        Test the manifest initialization with a manifest file.

        this is missing the required metadata key, 'description'.
        """

        filespec = self.get_data_full_filepath("secret-bad2.yaml")
        # parsing checks nothing. The Pydantic model validates the metadata.
        manifest_data = read_manifest_file(filespec)
        with self.assertRaises(ValidationError) as context:
            SAMSecret(**manifest_data)

        self.assertIn("metadata.description", str(context.exception))

    def test_manifest_initalization_bad3(self):
        """Test the manifest initialization with a manifest file that has an invalid expiration_date."""

        filespec = self.get_data_full_filepath("secret-bad3.yaml")
        manifest_data = read_manifest_file(filespec)
        self.assertTrue(manifest_data, msg="the manifest is empty")

        with self.assertRaises(ValidationError) as context:
            SAMSecret(**manifest_data)

        # Assert that the exception message contains the expected details
        self.assertIn("1 validation error for SAMSecret", str(context.exception))
        self.assertIn("spec.config.expiration_date", str(context.exception))
        self.assertIn("Input should be a valid datetime or date", str(context.exception))
