# pylint: disable=wrong-import-position
"""Test SAMVectorstore Pydantic Model."""

import os

from pydantic_core import ValidationError

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.vectorstore.manifest.models.vectorstore.model import SAMVectorstore
from smarter.lib.manifest.loader import SAMLoader, SAMLoaderError

HERE = os.path.abspath(os.path.dirname(__file__))


class TestSmarterSecretPydanticModel(TestAccountMixin):
    """Test SAMVectorstore Pydantic Model."""

    def get_data_full_filepath(self, filename: str) -> str:
        return os.path.join(HERE, "data", filename)

    def test_manifest_initalization_good(self):
        """
        Test the manifest initialization with a good manifest file.
        """

        filespec = self.get_data_full_filepath("vectorstore-good.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")
        sam_secret = SAMVectorstore(**loader.pydantic_model_dump())

        # dump the pydantic model to a dictionary
        # round_trip_dict = sam_secret.model_dump()
        sam_secret.model_dump_json()
        # assert that everything in content is in round_trip_dict
        # self.assertTrue(dict_is_contained_in(content, round_trip_dict))

    def test_manifest_initalization_bad(self):
        """
        Test the manifest initialization with a manifest file
        this is missing the required spec key, 'value'.
        """

        filespec = self.get_data_full_filepath("vectorstore-bad.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")

        with self.assertRaises(ValidationError) as context:
            SAMVectorstore(**loader.pydantic_model_dump())

        self.assertIn("1 validation error for SAMVectorstore", str(context.exception))
        self.assertIn("spec.config.value", str(context.exception))
        self.assertIn("Field required [type=missing", str(context.exception))

    def test_manifest_initalization_bad2(self):
        """
        Test the manifest initialization with a manifest file
        this is missing the required metadata key, 'description'.
        """

        filespec = self.get_data_full_filepath("vectorstore-bad2.yaml")
        with self.assertRaises(SAMLoaderError) as context:
            SAMLoader(file_path=filespec)

        self.assertIn("Missing required key description", str(context.exception))

    def test_manifest_initalization_bad3(self):
        """
        Test the manifest initialization with a manifest file
        that has an invalid expiration_date
        """

        filespec = self.get_data_full_filepath("vectorstore-bad3.yaml")
        loader = SAMLoader(file_path=filespec)
        self.assertTrue(loader.ready, msg="loader is not ready")

        with self.assertRaises(ValidationError) as context:
            SAMVectorstore(**loader.pydantic_model_dump())

        # Assert that the exception message contains the expected details
        self.assertIn("1 validation error for SAMVectorstore", str(context.exception))
        self.assertIn("spec.config.expiration_date", str(context.exception))
        self.assertIn("Input should be a valid datetime or date", str(context.exception))
