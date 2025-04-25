# pylint: disable=wrong-import-position
"""Test Secret."""

import hashlib
import os
import random
import unittest

from smarter.apps.account.manifest.models.secret.model import SAMSecret
from smarter.apps.account.models import Account, UserProfile
from smarter.common.utils import dict_is_contained_in
from smarter.lib.django.user import User
from smarter.lib.manifest.loader import SAMLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class TestSmarterSecretPydanticModel(unittest.TestCase):
    """Test Secret."""

    def get_data_full_filepath(self, filename: str) -> str:
        return os.path.join(HERE, "data", filename)

    def get_manifest_data(self, filename: str) -> dict:
        """Get the manifest data from the file."""
        filepath = self.get_data_full_filepath(filename)
        with open(filepath) as file:
            data = file.read()
        return data

    def setUp(self):
        self.hash_suffix = "_" + hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()

        self.account = Account.objects.create(
            company_name="TestCompany" + self.hash_suffix,
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )
        non_admin_username = "non_admin_testuser" + self.hash_suffix
        self.non_admin_user = User.objects.create_user(username=non_admin_username, password="12345")
        self.non_admin_user_profile = UserProfile.objects.create(user=self.non_admin_user, account=self.account)

        admin_username = "admin_testuser" + self.hash_suffix
        self.admin_user = User.objects.create_user(
            username=admin_username, password="12345", is_staff=True, is_superuser=True
        )
        self.user_profile = UserProfile.objects.create(user=self.admin_user, account=self.account)

    def tearDown(self):
        try:
            self.non_admin_user_profile.delete()
        except UserProfile.DoesNotExist:
            pass
        try:
            self.non_admin_user.delete()
        except User.DoesNotExist:
            pass
        try:
            self.admin_user.delete()
        except User.DoesNotExist:
            pass
        try:
            self.account.delete()
        except Account.DoesNotExist:
            pass

    def test_manifest_initalization(self):

        filespec = self.get_data_full_filepath("secret-good.yaml")
        loader = SAMLoader(file_path=filespec)
        pydantic_model = SAMSecret(**loader.pydantic_model_dump())

        # dump the pydantic model to a dictionary
        # round_trip_dict = pydantic_model.model_dump()
        pydantic_model.model_dump()

        # assert that everything in content is in round_trip_dict
        # self.assertTrue(dict_is_contained_in(content, round_trip_dict))
