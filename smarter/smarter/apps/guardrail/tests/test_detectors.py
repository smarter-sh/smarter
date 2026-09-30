"""
Test :mod:`smarter.apps.guardrail.services.strategies.detectors`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.guardrail.manifest.enum import SAMGuardrailDetector
from smarter.apps.guardrail.services.strategies.detectors import (
    DETECTORS,
    MAX_MATCHES,
    credit_card_valid,
    detect,
    iban_valid,
    luhn_valid,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

# A fake key, assembled so that the detect-private-key pre-commit hook does not mistake this
# test for a leaked key.
FAKE_KEY_TYPE = "RSA " + "PRIVATE KEY"

CASES = {
    "credit_card": (
        ["4111 1111 1111 1111", "4111-1111-1111-1111", "5500005555555559", "378282246310005"],
        ["1234567890123456", "4111 1111 1111 1112", "0000000000000000", "411111111111"],
    ),
    "us_ssn": (
        ["123-45-6789", "123 45 6789"],
        ["000-12-3456", "666-12-3456", "900-12-3456", "123-00-6789", "123456789"],
    ),
    "email": (["jane.doe@example.com", "a+b@mail.example.co.uk"], ["jane@", "@example.com", "jane at example.com"]),
    "phone_number": (
        ["(415) 555-0132", "415-555-0132", "+44 20 7946 0958", "+1 415 555 0132"],
        ["5550132", "2024-01-15"],
    ),
    "ip_address": (["10.0.0.1", "2001:db8::1"], ["999.1.1.1", "10.0.0"]),
    "iban": (["GB82 WEST 1234 5698 7654 32", "DE89370400440532013000"], ["GB00 WEST 1234 5698 7654 32"]),
    "aws_access_key": (["AKIAIOSFODNN7EXAMPLE", "ASIAIOSFODNN7EXAMPLE"], ["AKIA1234", "akiaiosfodnn7example"]),
    "private_key": (
        [f"-----BEGIN {FAKE_KEY_TYPE}-----\nMIIE\n-----END {FAKE_KEY_TYPE}-----"],
        ["-----BEGIN PUBLIC KEY-----"],
    ),
    "api_key": (
        ["sk-proj-abcdefghijklmnopqrstuvwx", "ghp_" + "a" * 36, "sk_live_" + "a" * 24, "hf_" + "a" * 34],
        ["sk-short", "ghp_short"],
    ),
    "jwt": (
        ["eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"],
        ["eyJ.eyJ.x"],
    ),
    "password_assignment": (
        ["password=hunter22!", "API_KEY: s3cr3tvalue"],
        ["password (see the vault)", "my password is long", "password:\nthe next line"],
    ),
}


class TestDetectors(SmarterTestBase):
    """Test the built-in detectors."""

    def test_every_detector_has_cases(self):
        """Test that every detector in the enum is implemented and tested."""
        self.assertEqual(set(DETECTORS), set(SAMGuardrailDetector.all()))
        self.assertEqual(set(CASES), set(DETECTORS))

    def test_detectors(self):
        """Test that each detector finds valid data in a sentence, and ignores look-alikes."""
        for name, (positives, negatives) in CASES.items():
            for value in positives:
                with self.subTest(detector=name, value=value):
                    matches = detect(f"Here it is: {value} thanks", [name])
                    self.assertEqual(len(matches), 1, matches)
                    self.assertEqual(matches[0].label, name)
            for value in negatives:
                with self.subTest(detector=name, negative=value):
                    self.assertEqual(detect(f"Here it is: {value} thanks", [name]), [])

    def test_password_assignment_matches_the_value(self):
        """Test that password_assignment matches only the value, so that redaction keeps the name."""
        matches = detect("config: password = hunter22!", ["password_assignment"])
        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match.text, "hunter22!")
        self.assertEqual("config: password = hunter22!"[match.start : match.end], "hunter22!")

    def test_positions(self):
        """Test that each match's start and end locate its text."""
        text = "Email jane@example.com or call (415) 555-0132."
        for match in detect(text, ["email", "phone_number"]):
            self.assertEqual(text[match.start : match.end], match.text)

    def test_overlaps_are_merged(self):
        """Test that overlapping matches are merged, keeping the longest."""
        matches = detect("card 4111 1111 1111 1111", ["credit_card", "phone_number"])
        self.assertEqual([m.label for m in matches], ["credit_card"])

    def test_max_matches(self):
        """Test that at most MAX_MATCHES matches are reported."""
        text = " ".join(f"user{i}@example.com" for i in range(MAX_MATCHES + 10))
        self.assertEqual(len(detect(text, ["email"])), MAX_MATCHES)

    def test_unknown_detector(self):
        """Test that an unknown detector raises KeyError."""
        with self.assertRaises(KeyError):
            detect("text", ["passport"])

    def test_checksums(self):
        """Test the Luhn and IBAN checksums."""
        self.assertTrue(luhn_valid("4111111111111111"))
        self.assertFalse(luhn_valid("4111111111111112"))
        self.assertFalse(credit_card_valid("4444 4444 4444 4444"))
        self.assertTrue(iban_valid("GB82WEST12345698765432"))
        self.assertFalse(iban_valid("GB82WEST1234"))
