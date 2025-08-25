"""Test SmarterAuthTokenSerializer class"""

from datetime import datetime, timedelta, timezone
from logging import getLogger

from dateutil.parser import isoparse

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
)
from smarter.lib.drf.manifest.brokers.auth_token import SmarterAuthTokenSerializer
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..models import SmarterAuthToken


logger = getLogger(__name__)


class TestSmarterAuthTokenSerializer(SmarterTestBase):
    """Test the SmarterAuthTokenSerializer class."""

    def setUp(self):
        super().setUp()
        self.admin_user, self.account, self.user_profile = admin_user_factory()
        logger.info("TestSmarterAuthTokenSerializer() Setting up test class with name: %s", self.name)
        self.auth_token, self.token_key = SmarterAuthToken.objects.create(
            name=self.admin_user.username,
            user=self.admin_user,
            description=self.admin_user.username,
        )  # type: ignore

    def tearDown(self) -> None:
        try:
            factory_account_teardown(user=self.admin_user, account=self.account, user_profile=self.user_profile)
            self.auth_token.delete()
        except SmarterAuthToken.DoesNotExist:
            pass
        super().tearDownClass()

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
        self.assertEqual(isoparse(data["last_used_at"]).replace(microsecond=0), future.replace(microsecond=0))
