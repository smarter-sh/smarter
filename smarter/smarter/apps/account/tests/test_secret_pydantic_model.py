# pylint: disable=wrong-import-position
"""Test Secret."""

import os
import unittest

from pydantic_core import ValidationError

from smarter.apps.account.manifest.models.secret.model import SAMSecret
from smarter.lib.manifest.loader import SAMLoader, SAMLoaderError

from .factories import admin_user_factory, admin_user_teardown, mortal_user_factory


HERE = os.path.abspath(os.path.dirname(__file__))


class TestSmarterSecretPydanticModel(unittest.TestCase):
    """Test Secret."""

    def get_data_full_filepath(self, filename: str) -> str:
        return os.path.join(HERE, "data", filename)

    def setUp(self):
        self.admin_user, self.account, self.user_profile = admin_user_factory()
        self.non_admin_user, _, self.non_admin_user_profile = mortal_user_factory(account=self.account)

    def tearDown(self):
        admin_user_teardown(user=self.admin_user, account=None, user_profile=self.user_profile)
        admin_user_teardown(user=self.non_admin_user, account=self.account, user_profile=self.non_admin_user_profile)

    def test_manifest_initalization_good(self):
        """
        Test the manifest initialization with a good manifest file.
        """

        filespec = self.get_data_full_filepath("secret-good.yaml")
        loader = SAMLoader(file_path=filespec)
        pydantic_model = SAMSecret(**loader.pydantic_model_dump())

        # dump the pydantic model to a dictionary
        # round_trip_dict = pydantic_model.model_dump()
        pydantic_model.model_dump()

        # assert that everything in content is in round_trip_dict
        # self.assertTrue(dict_is_contained_in(content, round_trip_dict))

    def test_manifest_initalization_bad(self):
        """
        Test the manifest initialization with a manifest file
        this is missing the required spec key, 'value'.
        """

        filespec = self.get_data_full_filepath("secret-bad.yaml")
        loader = SAMLoader(file_path=filespec)

        with self.assertRaises(ValidationError) as context:
            SAMSecret(**loader.pydantic_model_dump())

        self.assertIn("1 validation error for SAMSecret", str(context.exception))
        self.assertIn("spec.config.value", str(context.exception))
        self.assertIn("Field required [type=missing", str(context.exception))

    def test_manifest_initalization_bad2(self):
        """
        Test the manifest initialization with a manifest file
        this is missing the required metadata key, 'description'.
        """

        filespec = self.get_data_full_filepath("secret-bad2.yaml")
        with self.assertRaises(SAMLoaderError) as context:
            SAMLoader(file_path=filespec)

        self.assertIn("Missing required key description", str(context.exception))

    def test_manifest_initalization_bad3(self):
        """
        Test the manifest initialization with a manifest file
        that has an invalid expiration_date
        """

        filespec = self.get_data_full_filepath("secret-bad3.yaml")
        loader = SAMLoader(file_path=filespec)

        with self.assertRaises(ValidationError) as context:
            SAMSecret(**loader.pydantic_model_dump())

        # Assert that the exception message contains the expected details
        self.assertIn("1 validation error for SAMSecret", str(context.exception))
        self.assertIn("spec.config.expiration_date", str(context.exception))
        self.assertIn("Input should be a valid date or datetime", str(context.exception))
