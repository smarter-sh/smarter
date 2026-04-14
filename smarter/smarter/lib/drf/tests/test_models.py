"""test SmarterAuthToken, SmarterAuthTokenManager class"""

from datetime import datetime, timedelta
from logging import getLogger
from unittest.mock import patch

from django.utils import timezone

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
    mortal_user_factory,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..models import SmarterAuthToken

logger = getLogger(__name__)


class TestSmarterAuthTokenModels(SmarterTestBase):
    """Test the SmarterAuthToken class."""

    def setUp(self):
        super().setUp()
        self.admin_user, self.account, self.user_profile = admin_user_factory()
        self.auth_token: SmarterAuthToken
        self.token_key: str
        self.auth_token, self.token_key = SmarterAuthToken.objects.create(  # type: ignore
            user_profile=self.user_profile,
            user=self.admin_user,
            name=self.admin_user.username,
            description=self.admin_user.username,
        )

    def tearDown(self) -> None:
        try:
            self.auth_token.delete()
        except SmarterAuthToken.DoesNotExist:
            pass
        factory_account_teardown(user=self.admin_user, account=self.account, user_profile=self.user_profile)

        super().tearDownClass()

    def test_save_only_staff(self):
        self.auth_token.user.is_staff = False
        with self.assertRaises(Exception):
            self.auth_token.save()

    def test_save_sets_created(self):
        self.auth_token.user.is_staff = True
        self.assertIsInstance(self.auth_token.created, datetime)
        self.assertLess(self.auth_token.created, timezone.now())

    def test_has_permissions(self):

        # object that is not a User should not have permissions
        user = object()
        self.assertFalse(
            SmarterAuthToken.objects.filter(pk=self.auth_token.pk).with_ownership_permission_for(user).exists()
        )

        # superuser should have permissions to anything
        auth_token = (
            SmarterAuthToken.objects.filter(pk=self.auth_token.pk)
            .with_ownership_permission_for(self.admin_user)
            .exists()
        )
        self.assertTrue(auth_token)

        non_admin_same_account, _, non_admin_same_account_user_profile = mortal_user_factory(account=self.account)
        try:
            # non-staff user should not have permissions to anything
            auth_token = (
                SmarterAuthToken.objects.filter(pk=self.auth_token.pk)
                .with_ownership_permission_for(non_admin_same_account)
                .exists()
            )
            self.assertFalse(auth_token)

            # staff user in same account should have permissions to anything in the account
            non_admin_same_account.is_staff = True
            non_admin_same_account.save()
            auth_token = (
                SmarterAuthToken.objects.filter(pk=self.auth_token.pk)
                .with_ownership_permission_for(non_admin_same_account)
                .exists()
            )
            self.assertTrue(auth_token)
        finally:
            factory_account_teardown(
                user=non_admin_same_account, account=None, user_profile=non_admin_same_account_user_profile
            )

        # staff user in different account should not have permissions
        staff_admin_different_account, different_account, staff_admin_different_account_user_profile = (
            admin_user_factory()
        )
        staff_admin_different_account.is_superuser = False
        staff_admin_different_account.is_staff = True
        staff_admin_different_account.save()
        try:
            auth_token = (
                SmarterAuthToken.objects.filter(pk=self.auth_token.pk)
                .with_ownership_permission_for(staff_admin_different_account)
                .exists()
            )
            self.assertFalse(auth_token)
        finally:
            factory_account_teardown(
                user=staff_admin_different_account,
                account=different_account,
                user_profile=staff_admin_different_account_user_profile,
            )

    def test_activate_deactivate_toggle(self):
        with patch.object(self.auth_token, "save") as mock_save:
            self.auth_token.is_active = False
            self.auth_token.activate()
            self.assertTrue(self.auth_token.is_active)
            mock_save.assert_called()
            self.auth_token.deactivate()
            self.assertFalse(self.auth_token.is_active)
            self.auth_token.toggle_active()
            self.assertTrue(self.auth_token.is_active)

    def test_accessed_sets_last_used_at(self):
        with patch.object(self.auth_token, "save") as mock_save:
            self.auth_token.last_used_at = None
            with patch("smarter.lib.drf.models.datetime") as mock_dt:
                now = datetime(2024, 1, 1, 12, 0, 0)
                mock_dt.now.return_value = now
                self.auth_token.accessed()
                self.assertEqual(self.auth_token.last_used_at, now)
                mock_save.assert_called_once()

    def test_accessed_updates_if_older_than_5min(self):
        with patch.object(self.auth_token, "save") as mock_save:
            old_time = datetime.now() - timedelta(minutes=10)
            self.auth_token.last_used_at = old_time
            with patch("smarter.lib.drf.models.datetime") as mock_dt:
                now = datetime.now()
                mock_dt.now.return_value = now
                self.auth_token.accessed()
                self.assertEqual(self.auth_token.last_used_at, now)
                mock_save.assert_called_once()

    def test_accessed_does_not_update_if_recent(self):
        with patch.object(self.auth_token, "save") as mock_save:
            recent_time = datetime.now()
            self.auth_token.last_used_at = recent_time
            with patch("smarter.lib.drf.models.datetime") as mock_dt:
                mock_dt.now.return_value = recent_time
                self.auth_token.accessed()
                mock_save.assert_not_called()

    def test_str_returns_identifier(self):
        self.auth_token.digest = "digestvalue"
        logger.debug(str(self.auth_token))
        self.assertTrue(str(self.auth_token).endswith("******alue"))
