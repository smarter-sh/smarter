"""test SmarterAuthToken, SmarterAuthTokenManager class"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..models import SmarterAuthToken


class TestSmarterAuthTokenModels(SmarterTestBase):
    """Test the SmarterAuthToken class."""

    def setUp(self):
        super().setUp()
        self.admin_user, self.account, self.user_profile = admin_user_factory()
        self.auth_token, self.token_key = SmarterAuthToken.objects.create(
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
        self.auth_token.created = None
        with patch("smarter.lib.drf.models.timezone") as mock_tz:
            now = datetime(2024, 1, 1)
            mock_tz.now.return_value = now
            with patch("smarter.lib.drf.models.AuthToken.save") as mock_super_save:
                self.auth_token.save()
                self.assertEqual(self.auth_token.created, now)
                mock_super_save.assert_called_once()

    def test_has_permissions(self):
        user = Mock(is_authenticated=True, is_staff=True, is_superuser=False)
        self.assertTrue(self.auth_token.has_permissions(user))
        user = Mock(is_authenticated=True, is_staff=False, is_superuser=True)
        self.assertTrue(self.auth_token.has_permissions(user))
        user = Mock(is_authenticated=True, is_staff=False, is_superuser=False)
        self.assertFalse(self.auth_token.has_permissions(user))
        user = Mock(is_authenticated=False, is_staff=True, is_superuser=True)
        self.assertFalse(self.auth_token.has_permissions(user))
        user = object()
        self.assertFalse(self.auth_token.has_permissions(user))

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
        self.assertTrue(str(self.auth_token).startswith("******"))
