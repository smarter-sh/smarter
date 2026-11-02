"""Test smarter.apps.account.login_audit."""

from unittest.mock import patch

from django.test import override_settings

from smarter.apps.account import login_audit
from smarter.apps.account.login_audit import (
    LOGIN_IDENTITY_LENGTH,
    LoginFailure,
    log_login_failure,
    login_identity,
    password_failure,
)
from smarter.apps.account.models import User
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestLoginIdentity(SmarterTestBase):
    """Test login_identity()."""

    def test_is_a_short_hex_hash(self):
        """Test that the identity is LOGIN_IDENTITY_LENGTH hexadecimal characters, not the address."""
        identity = login_identity("someone@example.com")
        self.assertEqual(len(identity), LOGIN_IDENTITY_LENGTH)
        int(identity, 16)
        self.assertNotIn("someone", identity)

    def test_normalizes_the_address(self):
        """Test that case and surrounding spaces don't change the identity."""
        self.assertEqual(login_identity(" Someone@Example.COM "), login_identity("someone@example.com"))

    def test_differs_between_addresses(self):
        """Test that two addresses have different identities."""
        self.assertNotEqual(login_identity("a@example.com"), login_identity("b@example.com"))

    def test_no_address(self):
        """Test that a missing or blank address is 'none'."""
        self.assertEqual(login_identity(None), "none")
        self.assertEqual(login_identity("   "), "none")

    def test_is_keyed_with_the_secret_key(self):
        """Test that another SECRET_KEY gives another identity, so it differs between platforms."""
        identity = login_identity("someone@example.com")
        with override_settings(SECRET_KEY="another-secret-key-for-this-test-only"):
            self.assertNotEqual(login_identity("someone@example.com"), identity)


class TestPasswordFailure(SmarterTestBase):
    """Test password_failure(), with unsaved users."""

    def test_inactive_account(self):
        """Test that an inactive user is INACTIVE_ACCOUNT, even with a password."""
        user = User(username="inactive", is_active=False)
        user.set_password("a-password")
        self.assertEqual(password_failure(user), LoginFailure.INACTIVE_ACCOUNT)

    def test_no_password(self):
        """Test that an active user without a usable password is NO_PASSWORD."""
        user = User(username="social", is_active=True)
        user.set_unusable_password()
        self.assertEqual(password_failure(user), LoginFailure.NO_PASSWORD)

    def test_wrong_password(self):
        """Test that an active user with a password is WRONG_PASSWORD."""
        user = User(username="active", is_active=True)
        user.set_password("a-password")
        self.assertEqual(password_failure(user), LoginFailure.WRONG_PASSWORD)


class TestLogLoginFailure(SmarterTestBase):
    """Test log_login_failure()."""

    def test_logs_the_reason_and_identity_at_warning(self):
        """Test that the line is a WARNING with the reason and the identity, and not the address."""
        with patch.object(login_audit, "logger") as logger:
            log_login_failure("someone@example.com", LoginFailure.WRONG_PASSWORD)
        logger.warning.assert_called_once()
        args = logger.warning.call_args.args
        self.assertIn("reason=%s identity=%s", args[0])
        self.assertEqual(args[2], LoginFailure.WRONG_PASSWORD)
        self.assertEqual(args[3], login_identity("someone@example.com"))
        self.assertNotIn("someone@example.com", repr(args))

    def test_reason_values(self):
        """Test that the reasons' values are the strings that the logs and the help desk search for."""
        self.assertEqual(
            sorted(str(failure) for failure in LoginFailure),
            sorted(
                [
                    "error",
                    "inactive_account",
                    "invalid_form",
                    "no_password",
                    "unknown_account",
                    "wrong_password",
                ]
            ),
        )
