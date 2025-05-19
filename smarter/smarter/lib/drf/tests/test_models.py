"""test SmarterAuthToken, SmarterAuthTokenManager class"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin

from ..models import SmarterAuthToken, SmarterAuthTokenManager


class TestBase(TestAccountMixin):
    """Base class for tests"""


class TestSmarterAuthTokenManager(TestBase):
    """Test the SmarterAuthTokenManager class."""

    @patch("smarter.lib.drf.models.AuthTokenManager.create")
    def test_create_sets_fields_and_returns(self, mock_super_create):
        user = Mock(is_staff=True)
        auth_token = Mock()
        token = "token"
        mock_super_create.return_value = (auth_token, token)

        manager = SmarterAuthTokenManager()
        result = manager.create(user, name="Test", description="desc", is_active=False)
        self.assertEqual(result, (auth_token, token))
        self.assertEqual(auth_token.name, "Test")
        self.assertEqual(auth_token.description, "desc")
        self.assertEqual(auth_token.is_active, False)
        auth_token.save.assert_called_once()


class TestSmarterAuthToken(TestBase):
    """Test the SmarterAuthToken class."""

    def setUp(self):
        super().setUp()
        self.token = SmarterAuthToken()
        self.token.user = self.admin_user
        self.token.created = None
        self.token.is_active = True
        self.token.last_used_at = None

    def test_save_only_staff(self):
        self.token.user.is_staff = False
        with self.assertRaises(Exception):
            self.token.save()

    def test_save_sets_created(self):
        self.token.user.is_staff = True
        self.token.created = None
        with patch("smarter.lib.drf.models.timezone") as mock_tz:
            now = datetime(2024, 1, 1)
            mock_tz.now.return_value = now
            with patch("smarter.lib.drf.models.AuthToken.save") as mock_super_save:
                self.token.save()
                self.assertEqual(self.token.created, now)
                mock_super_save.assert_called_once()

    def test_has_permissions(self):
        user = Mock(is_authenticated=True, is_staff=True, is_superuser=False)
        self.assertTrue(self.token.has_permissions(user))
        user = Mock(is_authenticated=True, is_staff=False, is_superuser=True)
        self.assertTrue(self.token.has_permissions(user))
        user = Mock(is_authenticated=True, is_staff=False, is_superuser=False)
        self.assertFalse(self.token.has_permissions(user))
        user = Mock(is_authenticated=False, is_staff=True, is_superuser=True)
        self.assertFalse(self.token.has_permissions(user))
        user = object()
        self.assertFalse(self.token.has_permissions(user))

    def test_activate_deactivate_toggle(self):
        with patch.object(self.token, "save") as mock_save:
            self.token.is_active = False
            self.token.activate()
            self.assertTrue(self.token.is_active)
            mock_save.assert_called()
            self.token.deactivate()
            self.assertFalse(self.token.is_active)
            self.token.toggle_active()
            self.assertTrue(self.token.is_active)

    def test_accessed_sets_last_used_at(self):
        with patch.object(self.token, "save") as mock_save:
            self.token.last_used_at = None
            with patch("smarter.lib.drf.models.datetime") as mock_dt:
                now = datetime(2024, 1, 1, 12, 0, 0)
                mock_dt.now.return_value = now
                self.token.accessed()
                self.assertEqual(self.token.last_used_at, now)
                mock_save.assert_called_once()

    def test_accessed_updates_if_older_than_5min(self):
        with patch.object(self.token, "save") as mock_save:
            old_time = datetime.now() - timedelta(minutes=10)
            self.token.last_used_at = old_time
            with patch("smarter.lib.drf.models.datetime") as mock_dt:
                now = datetime.now()
                mock_dt.now.return_value = now
                self.token.accessed()
                self.assertEqual(self.token.last_used_at, now)
                mock_save.assert_called_once()

    def test_accessed_does_not_update_if_recent(self):
        with patch.object(self.token, "save") as mock_save:
            recent_time = datetime.now()
            self.token.last_used_at = recent_time
            with patch("smarter.lib.drf.models.datetime") as mock_dt:
                mock_dt.now.return_value = recent_time
                self.token.accessed()
                mock_save.assert_not_called()

    def test_str_returns_identifier(self):
        self.token.digest = "digestvalue"
        self.assertTrue(str(self.token).startswith("******"))
