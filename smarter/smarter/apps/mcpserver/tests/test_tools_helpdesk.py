"""Test smarter.apps.mcpserver.protocol.tools.helpdesk: user_support_snapshot and check_reply."""

from unittest import mock

from smarter.apps.account.tests.mixins import DuplicateUsersMixin
from smarter.apps.infrastructure.services import InMemoryLogService, configure_logs
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.protocol.tools.helpdesk import (
    CheckReplyTool,
    UserSupportSnapshotTool,
    utc,
)
from smarter.apps.mcpserver.protocol.tools.staff import UNTRUSTED_DATA_NOTICE

from .operations_base import TICKET
from .test_helpdesk_replies import GOOD_REPLY
from .test_helpdesk_users import SOCIAL_EMAIL, HelpdeskTestBase

VERIFIED = "the request came from this address"


class TestUserSupportSnapshotTool(HelpdeskTestBase):
    """Test user_support_snapshot."""

    def snapshot(self, **arguments) -> str:
        tool = UserSupportSnapshotTool(self.admin_user)
        return tool.call({"ticket": TICKET, "verified_by": VERIFIED, **arguments})

    def test_user_with_errors(self):
        text = self.snapshot(email=self.admin_user.email)
        self.assertTrue(text.startswith(UNTRUSTED_DATA_NOTICE))
        self.assertIn("Several wrong passwords: suggest that they reset their password.", text)
        self.assertIn(f"- Username: {self.admin_user.get_username()}", text)
        self.assertIn("- Active: yes", text)
        self.assertIn("- Signs in with: password", text)
        self.assertIn("- wrong_password: 3", text)
        self.assertIn(": HTTP 500, SmarterProviderError: the provider timed out", text)
        row = self.audit_rows().first()
        self.assertEqual(row.tool, "user_support_snapshot")
        self.assertEqual(row.arguments["verified_by"], VERIFIED, "how the owner was verified is audited")

    def test_social_user(self):
        text = self.snapshot(email=SOCIAL_EMAIL)
        self.assertIn("- Signs in with: google-oauth2", text)
        self.assertIn("- Failed sign-ins in the last 72 hours", text.replace("### ", "- "))
        self.assertIn("- None.", text)

    def test_no_user(self):
        text = self.snapshot(email="nobody-here@example.com")
        self.assertIn("- No user has this address.", text)
        self.assertIn("Do not tell them whether the address has an account.", text)

    def test_nothing_in_particular(self):
        """A user with no failures gets the hint to check the platform's health."""
        self.social_user.set_password("a-password-for-this-test")
        self.social_user.save()
        self.assertIn("Nothing in particular: check platform_status", self.snapshot(email=SOCIAL_EMAIL))

    def test_logs_not_available(self):
        configure_logs(lambda: InMemoryLogService(ready=False))
        text = self.snapshot(email=self.admin_user.email)
        self.assertIn("_Could not read sign-ins: the log store is not available", text)

    def test_arguments(self):
        with self.assertRaisesRegex(SmarterMCPServerToolError, "email"):
            self.snapshot(email="not an address")
        with self.assertRaisesRegex(SmarterMCPServerToolError, "verified_by"):
            UserSupportSnapshotTool(self.admin_user).call({"ticket": TICKET, "email": self.admin_user.email})
        with self.assertRaisesRegex(SmarterMCPServerToolError, "days"):
            self.snapshot(email=self.admin_user.email, days=90)

    def test_subscription_line(self):
        """On a hosted platform, the subscription's state is reported."""
        with mock.patch("smarter.apps.mcpserver.services.helpdesk.users.subscription_active", return_value=False):
            text = self.snapshot(email=self.admin_user.email)
        self.assertIn("- Subscription active: NO", text)
        self.assertIn("subscription is not active", text)


class TestUserSupportSnapshotDuplicates(DuplicateUsersMixin, HelpdeskTestBase):
    """
    Test user_support_snapshot on a platform that still has users who share an address.

    The unique index on ``auth_user.email`` forbids them, so this only happens before the
    upgrade's merge migration runs.
    """

    def test_two_users(self):
        self.duplicate_user(SOCIAL_EMAIL.upper(), with_profile=False)
        text = UserSupportSnapshotTool(self.admin_user).call(
            {"ticket": TICKET, "verified_by": VERIFIED, "email": SOCIAL_EMAIL}
        )
        self.assertIn("- 2 users have this address. This is the first of them.", text)


class TestCheckReplyTool(HelpdeskTestBase):
    """Test check_reply."""

    def check(self, **arguments) -> str:
        return CheckReplyTool(self.admin_user).call({"ticket": TICKET, **arguments})

    def test_clean(self):
        text = self.check(reply=GOOD_REPLY)
        self.assertTrue(text.startswith("## No problems found"))
        self.assertIn("they read it, and send it", text)

    def test_findings(self):
        text = self.check(reply="There is no account with that address. Ask bob@example.com.", requester_email="  ")
        self.assertIn("## 2 problems found", text)
        self.assertIn("- **email**: `bob@example.com`.", text)
        self.assertIn("- **account_enumeration**:", text)
        self.assertIn("Fix them, and check the reply again.", text)

    def test_requester_email(self):
        text = self.check(reply="We sent a reset link to you@example.com.", requester_email="you@example.com")
        self.assertTrue(text.startswith("## No problems found"))

    def test_audit(self):
        self.check(reply=GOOD_REPLY)
        self.assertEqual(self.audit_rows().first().arguments["reply"], GOOD_REPLY)


class TestUtc(HelpdeskTestBase):
    """Test utc()."""

    def test_utc(self):
        self.assertEqual(utc(None), "never")
        self.assertEqual(utc(self.now.replace(hour=14, minute=5)).split(" ")[1], "14:05")
