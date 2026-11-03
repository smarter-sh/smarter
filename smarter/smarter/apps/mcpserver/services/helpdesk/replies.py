"""
The rules that a reply to a user must follow, and the check that finds where a draft reply breaks them.

An AI agent that drafts a help desk reply has read the platform's logs, its health and a user's account,
which are for staff. The reply goes to one user, so it must carry only what is that user's business.
The instructions of the MCPServer's staff-only endpoint say so, and the ``check_reply`` tool
(:class:`~smarter.apps.mcpserver.protocol.tools.helpdesk.CheckReplyTool`) checks a draft before a staff member
sends it. :func:`check_reply` finds:

- **personal data and secrets**, with the platform's own Guardrail detectors
  (:func:`~smarter.apps.guardrail.services.strategies.detectors.detect`): email addresses, except the
  requester's own, IP addresses, phone numbers, credit card numbers, api keys, AWS keys, private keys,
  JWTs and passwords. The same detectors protect LLMClients' prompts and replies.
- **the platform's internals**, with the rules of :data:`REPLY_RULES`: pod and node names, internal
  host names and urls, log lines, stack traces, exception names, the placeholders that the log store
  puts in place of redacted values, version numbers and cloud account ids.
- **account enumeration**: wording that tells whether an email address has an account, e.g. "there is
  no account with that address". Such a reply lets anyone find out who uses the platform, so it is never
  sent, whatever the address.

The check is a safety net, not a guarantee: a finding is a reason for the staff member to read the draft
again, and a clean result does not mean that the draft is right. A person sends the reply.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import re
from dataclasses import dataclass
from typing import Optional

from smarter.apps.guardrail.manifest.enum import SAMGuardrailDetector
from smarter.apps.guardrail.services.strategies.detectors import detect

MAX_FINDINGS = 30
"""The most findings that a check reports."""


@dataclass(frozen=True)
class ReplyRule:
    """
    One rule of what a reply to a user must not contain, beyond the Guardrail detectors.

    :func:`check_reply` reports every match of its pattern in a draft as a :class:`ReplyFinding`.
    """

    name: str
    """The rule's short name, e.g. ``pod_name``, which a finding names."""

    pattern: re.Pattern
    """What the rule finds."""

    why: str
    """Why a reply must not contain it, in one sentence, for the staff member."""


REPLY_RULES: tuple[ReplyRule, ...] = (
    ReplyRule(
        "pod_name",
        re.compile(r"\b[a-z0-9]+(?:-[a-z0-9]+)*-[a-f0-9]{8,10}-[a-z0-9]{5}\b|\bsmarter-mariadb-\d+\b"),
        "Pod names describe the platform's internals.",
    ),
    ReplyRule(
        "node_name",
        re.compile(r"\bip-\d{1,3}-\d{1,3}-\d{1,3}-\d{1,3}(?:\.[\w.-]+)?\b"),
        "Node names describe the platform's internals, and contain private IP addresses.",
    ),
    ReplyRule(
        "internal_host",
        re.compile(
            r"\b[\w.-]+\.(?:internal|svc\.cluster\.local|svc|cluster\.local|amazonaws\.com)\b"
            r"|\blocalhost(?::\d+)?\b|\bsmarter-(?:loki|redis|mariadb|alloy)\b"
        ),
        "Internal host names and services describe the platform's internals.",
    ),
    ReplyRule(
        "internal_url",
        re.compile(r"/admin/|/api/v1/mcp/smarter-operations|:\d{4,5}/"),
        "Admin, operations and internal urls are for staff.",
    ),
    ReplyRule(
        "log_line",
        re.compile(r"- (?:DEBUG|INFO|WARNING|ERROR|CRITICAL) - |\b(?:DEBUG|INFO|WARNING|ERROR)/\w+Process"),
        "Log lines are for staff, and may mention other users.",
    ),
    ReplyRule(
        "stack_trace",
        re.compile(r"Traceback \(most recent call last\)|\bFile \"[^\"]+\", line \d+"),
        "Stack traces describe the platform's code.",
    ),
    ReplyRule(
        "exception_name",
        re.compile(r"\b[A-Z][A-Za-z]+(?:Error|Exception)\b"),
        "Exception names describe the platform's code. Describe the problem in words instead.",
    ),
    ReplyRule(
        "redaction_marker",
        re.compile(r"<(?:redacted|email|ip)>|\bidentity=[0-9a-f]{16}\b"),
        "These come from the logs: the reply quotes log text.",
    ),
    ReplyRule(
        "version",
        # three numbers, e.g. 0.40.6 or v1.19.0-eksbuild.2, but not four, which is an IP address.
        re.compile(r"(?<![\d.])v?\d+\.\d+\.\d+(?:-[\w.]+)?(?!\d)(?!\.\d)"),
        "Version numbers of the platform and its components are internal.",
    ),
    ReplyRule(
        "account_id",
        re.compile(r"(?<!\d)\d{12}(?!\d)"),
        "A twelve digit number may be a cloud account id.",
    ),
    ReplyRule(
        "account_enumeration",
        re.compile(
            r"(?i)\b(?:no|not an?|isn't an?|is not an?)\s+(?:smarter\s+)?(?:account|user)\b[^.]{0,60}"
            r"\b(?:exists?|registered|found|with (?:that|this|your) (?:address|email))"
            r"|\b(?:account|email|address|user)\b[^.]{0,40}\b(?:does not|doesn't|did not|didn't) exist"
            r"|\bunknown (?:user|account|email)\b"
            r"|\b(?:is|isn't|is not) registered\b"
        ),
        "It tells whether an address has an account, which lets anyone find out who uses the platform.",
    ),
)
"""The rules of what a reply must not contain, beyond the Guardrail detectors, in the order they are checked.

:meta hide-value:
"""

DETECTOR_REASONS: dict[str, str] = {
    SAMGuardrailDetector.EMAIL.value: "Email addresses other than the requester's are another person's data.",
    SAMGuardrailDetector.IP_ADDRESS.value: "IP addresses are personal data, or describe the platform's network.",
    SAMGuardrailDetector.PHONE_NUMBER.value: "Phone numbers are personal data.",
    SAMGuardrailDetector.CREDIT_CARD.value: "Card numbers are payment data.",
    SAMGuardrailDetector.US_SSN.value: "Social security numbers are personal data.",
    SAMGuardrailDetector.IBAN.value: "Bank account numbers are payment data.",
    SAMGuardrailDetector.AWS_ACCESS_KEY.value: "Keys are secrets.",
    SAMGuardrailDetector.PRIVATE_KEY.value: "Keys are secrets.",
    SAMGuardrailDetector.API_KEY.value: "Keys are secrets.",
    SAMGuardrailDetector.JWT.value: "Tokens are secrets.",
    SAMGuardrailDetector.PASSWORD_ASSIGNMENT.value: "Passwords are secrets.",
}
"""Why a reply must not contain what each Guardrail detector finds, by the detector's name."""


@dataclass(frozen=True)
class ReplyFinding:
    """Something in a draft reply that breaks a rule, as ``check_reply`` reports it."""

    rule: str
    """The rule or Guardrail detector that found it, e.g. ``pod_name`` or ``email``."""

    text: str
    """What it found, as it is in the draft."""

    why: str
    """Why a reply must not contain it."""


def detector_findings(reply: str, requester_email: Optional[str]) -> list[ReplyFinding]:
    """
    Find personal data and secrets in a draft, with the platform's Guardrail detectors.

    :param reply: The draft.
    :param requester_email: The requester's own email address, which the reply may contain, or None.
    :returns: Each match of every detector of :data:`DETECTOR_REASONS`, except the requester's address,
        in the order of the draft.
    """
    allowed = ""
    if requester_email:
        allowed = requester_email.strip().lower()
    detectors = list(DETECTOR_REASONS)
    findings = []
    for match in detect(reply, detectors):
        label = match.label
        if label is None:
            # detect() always labels its matches; this only satisfies the type checker.
            continue
        if label == SAMGuardrailDetector.EMAIL.value and match.text.lower() == allowed:
            continue
        why = DETECTOR_REASONS[label]
        finding = ReplyFinding(rule=label, text=match.text, why=why)
        findings.append(finding)
    return findings


def rule_findings(reply: str) -> list[ReplyFinding]:
    """
    Find the platform's internals and account enumeration in a draft, with the rules of :data:`REPLY_RULES`.

    :param reply: The draft.
    :returns: Each match of every rule, rule by rule, without repeating the same text for one rule.
    """
    findings = []
    for rule in REPLY_RULES:
        seen = set()
        for match in rule.pattern.finditer(reply):
            text = match.group(0)
            if text in seen:
                continue
            seen.add(text)
            findings.append(ReplyFinding(rule=rule.name, text=text, why=rule.why))
    return findings


def check_reply(reply: str, requester_email: Optional[str] = None) -> list[ReplyFinding]:
    """
    Find everything in a draft reply that breaks the reply rules.

    :param reply: The draft reply to the user.
    :param requester_email: The requester's own email address, which the reply may contain, or None.
    :returns: The findings, those of the Guardrail detectors first, at most :data:`MAX_FINDINGS`, or an
        empty list if none of the rules finds anything.
    """
    findings = detector_findings(reply, requester_email)
    findings += rule_findings(reply)
    return findings[:MAX_FINDINGS]


__all__ = [
    "DETECTOR_REASONS",
    "REPLY_RULES",
    "ReplyFinding",
    "ReplyRule",
    "check_reply",
]
