"""Test the Serializers class."""

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.django.serializers import UserMiniSerializer, UserSerializer


class TestUserSerializers(TestAccountMixin):
    """Test the UserSerializer and UserMiniSerializer classes."""

    def test_user_serializer_fields(self):
        serializer = UserSerializer(instance=self.admin_user)
        data = serializer.data
        self.assertIsInstance(data, dict)

        serializer = UserSerializer(instance=self.non_admin_user)
        data = serializer.data
        self.assertIsInstance(data, dict)

    def test_user_mini_serializer_fields(self):
        serializer = UserMiniSerializer(instance=self.admin_user)
        data = serializer.data
        self.assertIsInstance(data, dict)

        serializer = UserMiniSerializer(instance=self.non_admin_user)
        data = serializer.data
        self.assertIsInstance(data, dict)
