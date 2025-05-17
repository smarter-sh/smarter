"""Test the Serializers class."""

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
    mortal_user_factory,
)
from smarter.lib.django.serializers import UserMiniSerializer, UserSerializer
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestUserSerializers(SmarterTestBase):
    """Test the UserSerializer and UserMiniSerializer classes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user, cls.account, cls.user_profile = admin_user_factory()
        cls.mortal_user, _, cls.user_profile = mortal_user_factory(account=cls.account)

    @classmethod
    def tearDownClass(cls):
        factory_account_teardown(cls.admin_user, cls.account, cls.user_profile)
        factory_account_teardown(cls.mortal_user, cls.account, cls.user_profile)
        super().tearDownClass()

    def test_user_serializer_fields(self):
        serializer = UserSerializer(instance=self.user)
        data = serializer.data
        self.assertIsInstance(data, dict)

    def test_user_mini_serializer_fields(self):
        serializer = UserMiniSerializer(instance=self.user)
        data = serializer.data
        self.assertIsInstance(data, dict)
