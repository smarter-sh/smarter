"""Test SmarterAuthTokenSerializer class"""

from datetime import datetime, timedelta, timezone
from logging import getLogger
from unittest.mock import Mock

from smarter.apps.account.tests.mixins import TestAccountMixin

from ..models import SmarterAuthToken
from ..serializers import SmarterAuthTokenSerializer


logger = getLogger(__name__)


class TestSmarterAuthTokenSerializer(TestAccountMixin):
    """Test the SmarterAuthTokenSerializer class."""

    def setUp(self):
        super().setUp()
        logger.info(
            "TestSmarterAuthTokenSerializer() Setting up test class with name: %s, %s",
            self.name,
            self.admin_user.username,
        )
        self.auth_token, self.token_key = SmarterAuthToken.objects.create(
            name=self.name,
            user=self.admin_user,
            description=self.admin_user.username,
        )

    def tearDown(self) -> None:
        try:
            self.auth_token.delete()
        except SmarterAuthToken.DoesNotExist:
            pass
        super().tearDownClass()

    def test_serializer_with_non_datetime_last_used_at(self):
        # Simulate a non-datetime value for last_used_at
        self.auth_token.last_used_at = "not-a-datetime"
        serializer = SmarterAuthTokenSerializer(instance=self.auth_token)
        with self.assertRaises(Exception):
            _ = serializer.data

    def test_serializer_with_missing_all_fields(self):
        # Create a new mock with no attributes
        empty_mock = Mock()
        serializer = SmarterAuthTokenSerializer(instance=empty_mock)
        data = serializer.data
        self.assertIn("id", data)
        self.assertIn("token_key", data)
        self.assertIn("is_active", data)
        self.assertIn("last_used_at", data)
        self.assertIsNone(data["id"])
        self.assertIsNone(data["token_key"])
        self.assertIsNone(data["is_active"])
        self.assertIsNone(data["last_used_at"])

    def test_serializer_with_partial_fields(self):
        # Only set id and token_key
        self.auth_token = Mock()
        self.auth_token.id = 42
        self.auth_token.token_key = "partial"
        serializer = SmarterAuthTokenSerializer(instance=self.auth_token)
        data = serializer.data
        self.assertEqual(data["id"], 42)
        self.assertEqual(data["token_key"], "partial")
        self.assertIsNone(data["is_active"])
        self.assertIsNone(data["last_used_at"])

    def test_serializer_with_naive_datetime(self):
        # last_used_at is a naive datetime (no tzinfo)
        self.auth_token.last_used_at = datetime(2024, 1, 1, 12, 0, 0)
        serializer = SmarterAuthTokenSerializer(instance=self.auth_token)
        data = serializer.data
        # DRF may output naive datetimes as ISO without Z
        self.assertTrue(data["last_used_at"].startswith("2024-01-01T12:00:00"))

    def test_serializer_with_future_last_used_at(self):
        future = datetime.now(timezone.utc) + timedelta(days=365)
        self.auth_token.last_used_at = future
        serializer = SmarterAuthTokenSerializer(instance=self.auth_token)
        data = serializer.data
        self.assertEqual(data["last_used_at"], future.strftime("%Y-%m-%dT%H:%M:%SZ"))
