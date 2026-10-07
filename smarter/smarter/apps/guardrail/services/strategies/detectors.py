"""
Built-in detectors of personal data and secrets, for the ``detector`` strategy.

Each detector is a regular expression, and, where the data has a checksum, a validator,
so that e.g. a 16 digit order number is not mistaken for a credit card number. The
detectors favor precision over recall: they match well-formed data, and do not attempt
to find every possible formatting of it.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import ipaddress
import re
from dataclasses import dataclass
from typing import Callable, Optional

from smarter.apps.guardrail.manifest.enum import SAMGuardrailDetector
from smarter.apps.provider.services.text_completion.contracts import GuardrailMatch

MAX_MATCHES = 100
"""The maximum number of matches reported per segment."""


def luhn_valid(digits: str) -> bool:
    """Return whether a string of digits passes the Luhn checksum of credit card numbers."""
    total = 0
    for i, char in enumerate(reversed(digits)):
        value = int(char)
        if i % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def credit_card_valid(text: str) -> bool:
    """Return whether text is a plausible credit card number: 13 to 19 digits, not all the same, that pass Luhn."""
    digits = re.sub(r"[ -]", "", text)
    return 13 <= len(digits) <= 19 and len(set(digits)) > 1 and luhn_valid(digits)


def iban_valid(text: str) -> bool:
    """Return whether text passes the ISO 13616 mod-97 checksum of IBANs."""
    iban = text.replace(" ", "").upper()
    if not 15 <= len(iban) <= 34:
        return False
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(int(char, 36)) for char in rearranged)
    return int(numeric) % 97 == 1


def ip_address_valid(text: str) -> bool:
    """Return whether text is a valid IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(text)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class Detector:
    """
    A built-in detector.

    :ivar name: The detector's name, as in the manifest's ``detectors``.
    :ivar pattern: The regular expression. If it has a group named ``value``, only that group
        is matched, e.g. the password of ``password=hunter22``, rather than the assignment.
    :ivar validator: An optional function that confirms a match.
    """

    name: str
    pattern: re.Pattern
    validator: Optional[Callable[[str], bool]] = None


#: The built-in detectors, by name.
#:
#: :meta hide-value:
DETECTORS: dict[str, Detector] = {
    detector.name: detector
    for detector in (
        Detector(
            SAMGuardrailDetector.CREDIT_CARD.value,
            re.compile(r"(?<![\d-])\d(?:[ -]?\d){12,18}(?![\d-])"),
            credit_card_valid,
        ),
        Detector(
            SAMGuardrailDetector.US_SSN.value,
            re.compile(r"(?<![\d-])(?!000|666|9\d\d)\d{3}[- ](?!00)\d{2}[- ](?!0000)\d{4}(?![\d-])"),
        ),
        Detector(
            SAMGuardrailDetector.EMAIL.value,
            re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])"),
        ),
        Detector(
            SAMGuardrailDetector.PHONE_NUMBER.value,
            re.compile(
                r"(?<![\w+])(?:"
                r"\+\d{1,3}[ .-]?(?:\(\d{1,4}\)|\d{1,4})(?:[ .-]?\d{2,4}){2,4}"  # international, with a + prefix
                r"|(?:1[ .-])?(?:\(\d{3}\)\s?|\d{3}[ .-])\d{3}[ .-]\d{4}"  # North American, with separators
                r")(?![\w])"
            ),
        ),
        Detector(
            SAMGuardrailDetector.IP_ADDRESS.value,
            re.compile(
                r"(?<![\w.:])(?:(?:\d{1,3}\.){3}\d{1,3}|(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{1,4})*)(?![\w.:])"
            ),
            ip_address_valid,
        ),
        Detector(
            SAMGuardrailDetector.IBAN.value,
            re.compile(r"(?<![A-Za-z0-9])[A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30}(?![A-Za-z0-9])"),
            iban_valid,
        ),
        Detector(
            SAMGuardrailDetector.AWS_ACCESS_KEY.value,
            re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}(?![A-Z0-9])"),
        ),
        Detector(
            SAMGuardrailDetector.PRIVATE_KEY.value,
            re.compile(
                r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY(?: BLOCK)?-----[\s\S]*?(?:-----END (?:[A-Z]+ )*PRIVATE KEY(?: BLOCK)?-----|\Z)"
            ),
        ),
        Detector(
            SAMGuardrailDetector.API_KEY.value,
            re.compile(
                r"(?<![\w-])(?:"
                r"sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}"  # OpenAI, Anthropic
                r"|gh[pousr]_[A-Za-z0-9]{36,}"  # GitHub
                r"|github_pat_[A-Za-z0-9_]{22,}"  # GitHub fine-grained
                r"|xox[abposr]-[A-Za-z0-9-]{10,}"  # Slack
                r"|AIza[0-9A-Za-z_-]{35}"  # Google
                r"|(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{24,}"  # Stripe
                r"|glpat-[A-Za-z0-9_-]{20,}"  # GitLab
                r"|hf_[A-Za-z0-9]{30,}"  # Hugging Face
                r")(?![\w-])"
            ),
        ),
        Detector(
            SAMGuardrailDetector.JWT.value,
            re.compile(r"(?<![\w-])eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![\w-])"),
        ),
        Detector(
            SAMGuardrailDetector.PASSWORD_ASSIGNMENT.value,
            re.compile(
                r"(?i)\b(?:password|passwd|pwd|passphrase|secret|client_secret|api[_-]?key|access[_-]?token|auth[_-]?token)"
                r"[ \t]*[:=][ \t]*[\"']?(?P<value>[^\s\"',;]{6,})"
            ),
        ),
    )
}
"""The built-in detectors, by name."""


def detect(text: str, detectors: list[str]) -> list[GuardrailMatch]:
    """
    Return the matches of the named detectors in text.

    Overlapping matches are merged, keeping the longest, so that e.g. a credit card number is
    not also reported as a phone number.

    :param text: The text to scan.
    :param detectors: The names of the detectors to run.
    :returns: The matches, in order of their position in the text.
    :raises KeyError: If a detector name is unknown.
    """
    candidates: list[GuardrailMatch] = []
    for name in detectors:
        detector = DETECTORS[name]
        for match in detector.pattern.finditer(text):
            group = "value" if "value" in detector.pattern.groupindex and match.group("value") else 0
            value = match.group(group)
            if detector.validator and not detector.validator(value):
                continue
            candidates.append(GuardrailMatch(start=match.start(group), end=match.end(group), text=value, label=name))
    candidates.sort(key=lambda m: (m.start, -(m.end - m.start)))
    merged: list[GuardrailMatch] = []
    for candidate in candidates:
        if merged and candidate.start < merged[-1].end:
            continue
        merged.append(candidate)
        if len(merged) >= MAX_MATCHES:
            break
    return merged


__all__ = ["DETECTORS", "Detector", "detect", "luhn_valid", "iban_valid", "credit_card_valid"]
