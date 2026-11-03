"""Test smarter.apps.mcpserver.services.helpdesk.users, with the in-memory pod logs and throwaway users and journal rows."""

from datetime import timedelta
from http import HTTPStatus
from unittest import mock

from social_django.models import UserSocialAuth

from smarter.apps.account.login_audit import login_identity
from smarter.apps.account.models import User
from smarter.apps.infrastructure.services import (
    InMemoryLogService,
    LogLine,
    configure_logs,
)
from smarter.apps.mcpserver.services.helpdesk.users import (
    MULTITENANT_BACKEND,
    SupportSnapshot,
    error_details,
    hints,
    subscription_active,
    support_snapshot,
)
from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.journal.models import SAMJournal

from .operations_base import OperationsTestBase

SOCIAL_EMAIL = "test-helpdesk-social@example.com"


class HelpdeskTestBase(OperationsTestBase):
    """A throwaway user who signs in only with Google, failed sign-ins in the logs, and failed journal rows."""

    def setUp(self):
        super().setUp()
        # a hosted platform checks the subscription with the Account Manager: never call it from a test.
        verify = mock.patch("smarter.lib.social_core.backends.multitenant.verify_payment_status", return_value=True)
        self.verify_payment_status = verify.start()
        self.addCleanup(verify.stop)
        self.social_user = User.objects.create(username="test_helpdesk_social", email=SOCIAL_EMAIL)
        self.social_user.set_unusable_password()
        self.social_user.save()
        UserSocialAuth.objects.create(user=self.social_user, provider="google-oauth2", uid="test-helpdesk-uid")
        self.addCleanup(self.social_user.delete)
        self.add_sign_in_failure(self.admin_user.email, "wrong_password", minutes_ago=30)
        self.add_sign_in_failure(self.admin_user.email, "wrong_password", minutes_ago=20)
        self.add_sign_in_failure(self.admin_user.email.upper(), "wrong_password", minutes_ago=10)
        self.add_sign_in_failure("someone-else@example.com", "unknown_account", minutes_ago=5)
        self.journal = [
            SAMJournal.objects.create(
                user=self.admin_user,
                thing=SmarterJournalThings.PROMPT.value,
                command=SmarterJournalCliCommands.PROMPT.value,
                request={},
                response={"error": {"error_class": "SmarterProviderError", "description": "the provider timed out"}},
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            ),
            SAMJournal.objects.create(
                user=self.admin_user,
                thing=SmarterJournalThings.PROMPT.value,
                command=SmarterJournalCliCommands.PROMPT.value,
                request={},
                response={"data": {}},
                status_code=HTTPStatus.OK,
            ),
        ]
        self.addCleanup(lambda: SAMJournal.objects.filter(key__in=[row.key for row in self.journal]).delete())

    def add_sign_in_failure(self, email: str, reason: str, minutes_ago: int):
        """Add the log line that a failed sign-in writes, with the address's identity, never the address."""
        line = (
            "[2026-11-02 13:50:00 +0000] - WARNING - MainProcess - smarter.apps.account.login_audit."
            f"log_login_failure() sign-in failed: reason={reason} identity={login_identity(email)}"
        )
        self.logs.lines.append(
            LogLine(
                timestamp=self.now - timedelta(minutes=minutes_ago), component="smarter", pod="smarter-a", line=line
            )
        )


class TestSupportSnapshot(HelpdeskTestBase):
    """Test support_snapshot()."""

    def test_user_with_errors(self):
        snapshot = support_snapshot(f"  {self.admin_user.email.upper()} ")
        self.assertEqual(snapshot.users_found, 1, "the address is matched case insensitively")
        account = snapshot.account
        self.assertEqual(account.username, self.admin_user.get_username())
        self.assertTrue(account.is_active)
        self.assertTrue(account.has_password)
        self.assertTrue(account.accounts)
        self.assertEqual(snapshot.failed_sign_ins, {"wrong_password": 3}, "the same address, typed differently")
        self.assertIsNotNone(snapshot.last_failed_sign_in)
        self.assertEqual(len(snapshot.failed_requests), 1, "only the failed request")
        failed = snapshot.failed_requests[0]
        self.assertEqual((failed.status_code, failed.error_class), (500, "SmarterProviderError"))
        self.assertEqual(failed.description, "the provider timed out")
        self.assertEqual(snapshot.errors, [])

    def test_social_user(self):
        account = support_snapshot(SOCIAL_EMAIL).account
        self.assertFalse(account.has_password)
        self.assertEqual(account.social_providers, ["google-oauth2"])
        self.assertEqual(account.accounts, [])

    def test_no_user(self):
        snapshot = support_snapshot("someone-else@example.com")
        self.assertEqual(snapshot.users_found, 0)
        self.assertIsNone(snapshot.account)
        self.assertEqual(snapshot.failed_sign_ins, {"unknown_account": 1}, "sign-ins are searched for anyway")

    def test_days(self):
        SAMJournal.objects.filter(key=self.journal[0].key).update(created_at=self.now - timedelta(days=10))
        self.assertEqual(support_snapshot(self.admin_user.email, days=7).failed_requests, [])
        self.assertEqual(len(support_snapshot(self.admin_user.email, days=30).failed_requests), 1)

    def test_logs_not_available(self):
        configure_logs(lambda: InMemoryLogService(ready=False))
        snapshot = support_snapshot(self.admin_user.email)
        self.assertEqual(snapshot.failed_sign_ins, {})
        self.assertTrue(snapshot.errors[0].startswith("sign-ins: the log store is not available"))
        self.assertIsNotNone(snapshot.account, "the other parts are still read")

    def test_log_lines_without_a_reason(self):
        self.logs.lines = [
            LogLine(timestamp=self.now, component="smarter", line=f"identity={login_identity(self.admin_user.email)}")
        ]
        self.assertEqual(support_snapshot(self.admin_user.email).failed_sign_ins, {})


class TestSubscription(HelpdeskTestBase):
    """Test subscription_active(), on a hosted platform and on one without subscriptions."""

    def test_hosted(self):
        self.verify_payment_status.return_value = False
        with mock.patch("smarter.apps.mcpserver.services.helpdesk.users.settings") as settings:
            settings.AUTHENTICATION_BACKENDS = [MULTITENANT_BACKEND]
            self.assertFalse(subscription_active(self.admin_user))
        self.verify_payment_status.assert_called_once_with(self.admin_user.get_username())

    def test_no_subscriptions(self):
        with mock.patch("smarter.apps.mcpserver.services.helpdesk.users.settings") as settings:
            settings.AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
            self.assertIsNone(subscription_active(self.admin_user))
        self.verify_payment_status.assert_not_called()


class TestErrorDetails(HelpdeskTestBase):
    """Test error_details() on the responses that the journal holds."""

    def test_error_details(self):
        self.assertEqual(error_details({"error": {"error_class": "X", "description": "y" * 400}})[1], "y" * 300)
        self.assertEqual(error_details({"error": "not an object"}), ("", ""))
        self.assertEqual(error_details(None), ("", ""))


class TestHints(HelpdeskTestBase):
    """Test hints()."""

    def test_no_user(self):
        found = hints(support_snapshot("nobody-here@example.com"))
        self.assertIn("Do not tell them whether the address has an account", found[0])

    def test_wrong_passwords_and_errors(self):
        found = " ".join(hints(support_snapshot(self.admin_user.email)))
        self.assertIn("reset their password", found)
        self.assertIn("1 of their recent requests failed on the platform", found)

    def test_social_and_inactive(self):
        User.objects.filter(pk=self.social_user.pk).update(is_active=False)
        found = " ".join(hints(support_snapshot(SOCIAL_EMAIL)))
        self.assertIn("The user is inactive", found)
        self.assertIn("they signed up with google-oauth2", found)

    def test_sign_in_reasons(self):
        snapshot = SupportSnapshot(email="x@example.com", failed_sign_ins={"invalid_form": 1, "error": 1})
        found = " ".join(hints(snapshot))
        self.assertIn("incomplete or had an invalid email address", found)
        self.assertIn("raised an error on the platform", found)

    def test_inactive_subscription(self):
        snapshot = support_snapshot(self.admin_user.email)
        snapshot.account.subscription_active = False
        self.assertIn("subscription is not active", " ".join(hints(snapshot)))
