""" " test SmarterAuthTokenSerializer class"""

from unittest.mock import Mock

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..serializers import SmarterAuthTokenSerializer


class TestSmarterAuthTokenSerializer(SmarterTestBase):
    """Test the SmarterAuthTokenSerializer class."""

    def setUp(self):
        super().setUp()
        # Create a mock SmarterAuthToken instance with some fields
        self.mock_instance = Mock()
        self.mock_instance.id = 1
        self.mock_instance.token_key = "abc123"
        self.mock_instance.is_active = True
        self.mock_instance.last_used_at = None

    def test_serializer_fields(self):
        serializer = SmarterAuthTokenSerializer(instance=self.mock_instance)
        data = serializer.data
        self.assertIsInstance(data, dict)
        self.assertIn("id", data)
        self.assertIn("token_key", data)
        self.assertIn("is_active", data)
        self.assertIn("last_used_at", data)
