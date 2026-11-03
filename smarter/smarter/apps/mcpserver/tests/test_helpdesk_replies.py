"""Test smarter.apps.mcpserver.services.helpdesk.replies: the check of a draft reply against the reply rules."""

from smarter.apps.mcpserver.services.helpdesk.replies import MAX_FINDINGS, check_reply
from smarter.lib.unittest.base_classes import SmarterTestBase

GOOD_REPLY = (
    "Hi, thanks for your patience. Between 13:20 and 13:40 UTC today, one of the AI providers that Smarter "
    "uses was timing out, so some prompts failed with a system error. It has recovered, so please try your "
    "prompt again. If it still fails, reply to this message and we will look again."
)


def rules(reply: str, requester_email=None) -> set[str]:
    """The names of the rules that a reply breaks."""
    return {finding.rule for finding in check_reply(reply, requester_email)}


class TestCheckReply(SmarterTestBase):
    """Test check_reply()."""

    def test_good_reply(self):
        self.assertEqual(check_reply(GOOD_REPLY), [])

    def test_requester_email_is_allowed(self):
        reply = "We sent a password reset link to you@example.com. Bob@example.com saw the same."
        findings = check_reply(reply, requester_email=" YOU@example.com ")
        self.assertEqual([finding.text for finding in findings], ["Bob@example.com"])
        self.assertEqual(findings[0].rule, "email")

    def test_personal_data_and_secrets(self):
        reply = (
            "The client at 203.0.113.7 used the key sk-proj-abcdefghijklmnopqrstuvwxyz0123 and password=hunter22secret."
        )
        self.assertEqual(rules(reply), {"ip_address", "api_key", "password_assignment"})

    def test_internals(self):
        cases = {
            "pod_name": "The pod smarter-worker-5b8d4c9f7d-x9y8z restarted.",
            "node_name": "Node ip-10-0-0-1.ec2.internal ran out of memory.",
            "internal_host": "The database smarter-mariadb was slow.",
            "internal_url": "See https://platform.example.com/admin/ for details.",
            "log_line": "[2026-11-02] - ERROR - MainProcess - boom",
            "stack_trace": "Traceback (most recent call last): oops",
            "exception_name": "It raised a SmarterProviderError.",
            "redaction_marker": "The request came from <ip>.",
            "version": "This was fixed in v0.40.6.",
            "account_id": "In account 123456789012 the role is missing.",
        }
        for rule, reply in cases.items():
            with self.subTest(rule=rule):
                self.assertIn(rule, rules(reply))

    def test_versions_are_not_ip_addresses(self):
        self.assertIn("version", rules("coredns v1.19.0-eksbuild.2 is outdated"))
        self.assertNotIn("version", rules("The client at 203.0.113.7 retried."))

    def test_account_enumeration(self):
        for reply in (
            "There is no account with that address.",
            "That email doesn't exist in our system.",
            "Sorry, unknown user.",
            "Your address is not registered.",
            "We found no Smarter account registered to it.",
        ):
            with self.subTest(reply=reply):
                self.assertIn("account_enumeration", rules(reply))
        self.assertNotIn("account_enumeration", rules("If you have an account, a reset link is on its way."))

    def test_repeats_and_limit(self):
        reply = "smarter-mariadb and smarter-mariadb again."
        findings = [finding for finding in check_reply(reply) if finding.rule == "internal_host"]
        self.assertEqual(len(findings), 1, "the same text is reported once for a rule")
        many = " ".join(f"person{i}@example.com" for i in range(MAX_FINDINGS + 10))
        self.assertEqual(len(check_reply(many)), MAX_FINDINGS)
