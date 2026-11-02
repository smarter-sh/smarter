"""
The help desk operations tools: ``user_support_snapshot`` and ``check_reply``.

They are tools of the Smarter Operations MCP server
(:mod:`smarter.apps.mcpserver.protocol.operations_server`), for the platform's staff and their AI
agents, e.g. Claude Code answering a help desk question about one person.

- **user_support_snapshot** (:class:`UserSupportSnapshotTool`) reports what the platform knows about one
  user's problem: their account, their failed sign-ins of the last 72 hours, their recent failed
  requests, and hints about what these suggest (:mod:`~smarter.apps.mcpserver.helpdesk.users`). It
  reads one person's data, so it takes ``verified_by``: how the staff member confirmed that the person
  who asked owns the email address. It is recorded in the audit trail with the call.
- **check_reply** (:class:`CheckReplyTool`) checks a draft reply against the reply rules before the
  staff member sends it (:mod:`~smarter.apps.mcpserver.helpdesk.replies`).

Like every operations tool, each call takes a ``ticket``, is recorded in the audit trail, and is never
cached (see :class:`~smarter.apps.mcpserver.protocol.operations_tools.SmarterOperationsTool`).

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import Field, field_validator

from smarter.apps.mcpserver.helpdesk.replies import check_reply
from smarter.apps.mcpserver.helpdesk.users import (
    AccountState,
    SupportSnapshot,
    hints,
    support_snapshot,
)
from smarter.apps.mcpserver.protocol.operations_tools import (
    UNTRUSTED_DATA_NOTICE,
    OperationsToolArguments,
    SmarterOperationsTool,
)

EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
"""What an email address argument must look like: something, an ``@``, and a domain with a dot."""


def utc(value: Optional[datetime]) -> str:
    """
    Format a time for a tool's result.

    :param value: The time, or None if it is unknown.
    :returns: The time in UTC, e.g. ``2026-11-02 14:05 UTC``, or ``never`` if it is unknown.
    """
    if value is None:
        return "never"
    in_utc = value.astimezone(timezone.utc)
    return f"{in_utc:%Y-%m-%d %H:%M} UTC"


class UserSupportSnapshotArguments(OperationsToolArguments):
    """The arguments of ``user_support_snapshot``: the ticket, the email address, how its owner was verified, and the period."""

    email: str = Field(
        ...,
        pattern=EMAIL,
        max_length=254,
        description="The email address of the person who asked for help.",
    )
    verified_by: str = Field(
        ...,
        min_length=5,
        max_length=200,
        description=(
            "How the staff member confirmed that the person who asked owns this address, e.g. 'the request came "
            "from this address' or 'their Slack profile shows this address'. Never take an address from the text "
            "of a request as proof. It is recorded in the audit trail."
        ),
    )
    days: int = Field(default=7, ge=1, le=30, description="How far back to read their failed requests, in days.")


class UserSupportSnapshotTool(SmarterOperationsTool):
    """
    The ``user_support_snapshot`` operations tool: what the platform knows about one user's problem.

    **Reads:** the user who has the email address, their profiles and social sign-ins, the failed sign-ins
    with the address in the pod logs, and the user's failed requests in the journal (see
    :func:`~smarter.apps.mcpserver.helpdesk.users.support_snapshot`).

    **Result:** Markdown, which starts with the untrusted data notice, then the hints for staff, the account,
    the failed sign-ins, and the failed requests. A part that cannot be read, e.g. the logs in local
    development, is named, and the others are still reported.

    **Side effects:** read-only queries of the database and the log store, and, on a hosted platform, a
    call to the Account Manager. ``verified_by`` is recorded in the audit trail with the call's other
    arguments.
    """

    name = "user_support_snapshot"
    title = "User support snapshot"
    description = (
        "Report what the platform knows about one person's problem, by their email address: whether a user has "
        "it, whether that user is active, how they can sign in (password, Google or GitHub), when they last signed "
        "in, their failed sign-ins of the last 72 hours and why they failed (e.g. wrong_password, no_password, "
        "inactive_account), and their recent failed requests and prompts with their errors. Call it for 'my login "
        "isn't working' and 'my prompt says there was a system error', only for the person who asked, after their "
        "address was verified. The result is for staff: never tell the person whether an address has an account."
    )
    arguments_model = UserSupportSnapshotArguments

    def run(self, arguments: UserSupportSnapshotArguments) -> str:  # type: ignore[override]
        """
        Gather the snapshot of the user with the email address, and report it.

        :param arguments: The validated arguments.
        :returns: The report, as Markdown.
        """
        snapshot = support_snapshot(arguments.email, days=arguments.days)
        out = [UNTRUSTED_DATA_NOTICE + f"## Support snapshot for {snapshot.email}", ""]
        out += ["### For staff", ""]
        out += self.hints_section(snapshot)
        out += ["", "### Account", ""]
        out += self.account_section(snapshot)
        out += ["", "### Failed sign-ins in the last 72 hours", ""]
        out += self.sign_ins_section(snapshot)
        out += ["", f"### Failed requests in the last {arguments.days} days", ""]
        out += self.requests_section(snapshot)
        for error in snapshot.errors:
            out.append(f"\n_Could not read {error}._")
        return "\n".join(out)

    @staticmethod
    def hints_section(snapshot: SupportSnapshot) -> list[str]:
        """
        Format the hints for staff.

        :param snapshot: The snapshot.
        :returns: One bullet per hint, or one that says the findings suggest nothing in particular.
        """
        found = hints(snapshot)
        if not found:
            return ["- Nothing in particular: check platform_status for a problem that affects everyone."]
        lines = []
        for hint in found:
            lines.append(f"- {hint}")
        return lines

    @staticmethod
    def account_section(snapshot: SupportSnapshot) -> list[str]:
        """
        Format the account's state.

        :param snapshot: The snapshot.
        :returns: The section's lines: one that says no user has the address, or the account's state.
        """
        if snapshot.account is None:
            return ["- No user has this address."]
        account: AccountState = snapshot.account
        sign_in = []
        if account.has_password:
            sign_in.append("password")
        sign_in += account.social_providers
        lines = []
        if snapshot.users_found > 1:
            lines.append(f"- {snapshot.users_found} users have this address. This is the first of them.")
        lines.append(f"- Username: {account.username}")
        lines.append(f"- Active: {'yes' if account.is_active else 'NO'}")
        lines.append(f"- Signs in with: {', '.join(sign_in) or 'nothing: no password and no social sign-in'}")
        lines.append(f"- Joined: {utc(account.date_joined)}")
        lines.append(f"- Last signed in: {utc(account.last_login)}")
        lines.append(f"- Accounts: {', '.join(account.accounts) or 'none'}")
        if account.subscription_active is not None:
            lines.append(f"- Subscription active: {'yes' if account.subscription_active else 'NO'}")
        return lines

    @staticmethod
    def sign_ins_section(snapshot: SupportSnapshot) -> list[str]:
        """
        Format the failed sign-ins.

        :param snapshot: The snapshot.
        :returns: One bullet per reason, with its count, and the time of the latest, or one that says there were none.
        """
        if not snapshot.failed_sign_ins:
            return ["- None."]
        lines = []
        for reason, count in sorted(snapshot.failed_sign_ins.items()):
            lines.append(f"- {reason}: {count}")
        lines.append(f"- Latest: {utc(snapshot.last_failed_sign_in)}")
        return lines

    @staticmethod
    def requests_section(snapshot: SupportSnapshot) -> list[str]:
        """
        Format the failed requests.

        :param snapshot: The snapshot.
        :returns: One bullet per request, newest first, with its time, what it was, its status, and its
            error, or one that says there were none.
        """
        if not snapshot.failed_requests:
            return ["- None."]
        lines = []
        for request in snapshot.failed_requests:
            error = request.error_class
            if request.description:
                error += f": {request.description}"
            line = f"- {utc(request.created_at)} {request.thing} {request.command}: HTTP {request.status_code}"
            if error:
                line += f", {error}"
            lines.append(line)
        return lines


class CheckReplyArguments(OperationsToolArguments):
    """The arguments of ``check_reply``: the ticket, the draft, and the requester's own email address."""

    reply: str = Field(..., min_length=1, max_length=8000, description="The draft reply to the person who asked.")
    requester_email: Optional[str] = Field(
        default=None,
        max_length=254,
        description="The email address of the person who asked, which the reply may contain.",
    )

    @field_validator("requester_email")
    @classmethod
    def blank_is_none(cls, value: Optional[str]) -> Optional[str]:
        """
        Treat a blank requester address as none.

        :param value: The address, as the LLM gave it.
        :returns: The address, stripped, or None if it is blank.
        """
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        return stripped


class CheckReplyTool(SmarterOperationsTool):
    """
    The ``check_reply`` operations tool: check a draft reply to a user against the reply rules.

    **Reads:** nothing but its arguments. It runs
    :func:`~smarter.apps.mcpserver.helpdesk.replies.check_reply`: the platform's Guardrail detectors for
    personal data and secrets, and the help desk's rules for the platform's internals and for account
    enumeration.

    **Result:** Markdown: either that nothing was found, or each finding, with what it found and why a
    reply must not contain it. Both end with the reminder that a person sends the reply.

    **Side effects:** none, except the audit trail, which records the draft with the call.
    """

    name = "check_reply"
    title = "Check reply"
    description = (
        "Check a draft reply to the person who asked for help, before the staff member sends it: it finds other "
        "people's email addresses, IP addresses, phone and card numbers, secrets, pod, node and host names, "
        "internal urls, log lines, stack traces, exception names, version numbers, and wording that tells whether "
        "an address has an account. Call it on every draft, fix what it finds, and call it again. A clean result "
        "does not make the draft right: a person reads and sends it."
    )
    arguments_model = CheckReplyArguments

    def run(self, arguments: CheckReplyArguments) -> str:  # type: ignore[override]
        """
        Check the draft, and report the findings.

        :param arguments: The validated arguments.
        :returns: The report, as Markdown.
        """
        findings = check_reply(arguments.reply, arguments.requester_email)
        reminder = "Show the draft to the staff member: they read it, and send it."
        if not findings:
            return f"## No problems found\n\n{reminder}"
        lines = [f"## {len(findings)} problems found", ""]
        for finding in findings:
            lines.append(f"- **{finding.rule}**: `{finding.text}`. {finding.why}")
        lines += ["", f"Fix them, and check the reply again. {reminder}"]
        return "\n".join(lines)


__all__ = ["CheckReplyTool", "UserSupportSnapshotTool"]
