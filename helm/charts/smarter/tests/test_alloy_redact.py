"""
Tests of the log redaction of the Helm chart's Grafana Alloy, loki.process "redact" in values.yaml.

Alloy redacts credentials and personal data from each log line before Loki stores it. These
tests read its expressions from values.yaml, and apply them as Alloy's stage.replace does, with
Python's re, whose syntax for these expressions is the same as Alloy's RE2. They check that real
credentials are redacted, and that the false positives of issue #913 are not: a Secret's name,
values that Smarter already masked, and a Python source line in a traceback.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import re
import unittest
from pathlib import Path

VALUES_PATH = Path(__file__).resolve().parent.parent / "values.yaml"

BLOCK_START = 'loki.process "redact" {'

STAGE_PATTERN = re.compile(r'expression = "((?:[^"\\]|\\.)*)"\s*\n\s*replace\s*= "((?:[^"\\]|\\.)*)"')
"""One stage.replace: its expression and its replacement, as Alloy strings."""


def alloy_string(value: str) -> str:
    """
    Return the text of an Alloy string literal, without its escapes.

    :param value: The literal's content, between its quotes.
    :returns: The text, with ``\\\\`` as one backslash and ``\\"`` as a quote.
    """
    return re.sub(r"\\(.)", r"\1", value)


def redact_stages() -> list[tuple[re.Pattern, str]]:
    """
    Return the stages of loki.process "redact", in order.

    :returns: Each stage's compiled expression and its replacement.
    """
    text = VALUES_PATH.read_text(encoding="utf-8")
    start = text.index(BLOCK_START)
    end = text.index("forward_to", start)
    block = text[start:end]
    stages = []
    for match in STAGE_PATTERN.finditer(block):
        expression = alloy_string(match.group(1))
        replace = alloy_string(match.group(2))
        stages.append((re.compile(expression), replace))
    return stages


STAGES = redact_stages()


def redact(line: str) -> str:
    """
    Redact a log line as Alloy does: each stage replaces what its capture group matched.

    :param line: A log line.
    :returns: The line that Loki would store.
    """
    for expression, replace in STAGES:
        parts = []
        position = 0
        for match in expression.finditer(line):
            if match.group(1) is None:
                continue
            parts.append(line[position : match.start(1)])
            parts.append(replace)
            position = match.end(1)
        parts.append(line[position:])
        line = "".join(parts)
    return line


class TestAlloyRedactStages(unittest.TestCase):
    """The stages themselves: found, and valid RE2."""

    def test_stages_are_found(self):
        """Every stage.replace of the block is read, each with one capture group."""
        self.assertEqual(len(STAGES), 9)
        for expression, _ in STAGES:
            self.assertEqual(expression.groups, 1, expression.pattern)

    def test_no_lookaround(self):
        """RE2 has no lookahead or lookbehind, so Alloy would refuse an expression that uses them."""
        for expression, _ in STAGES:
            for construct in ("(?=", "(?!", "(?<=", "(?<!"):
                self.assertNotIn(construct, expression.pattern)


class TestAlloyRedactsCredentials(unittest.TestCase):
    """Credentials and personal data are redacted."""

    def test_password(self):
        self.assertEqual(redact("login failed, password=hunter2xyz"), "login failed, password=<redacted>")

    def test_secret_value(self):
        self.assertEqual(redact('{"secret": "abcd1234"}'), '{"secret": "<redacted>"}')

    def test_api_key(self):
        self.assertEqual(redact('"api_key": "sk-proj-abcdefghijklmnopqrstuv"'), '"api_key": "<redacted>"')
        self.assertEqual(redact("api_key=abcd1234efgh"), "api_key=<redacted>")

    def test_url_password(self):
        self.assertEqual(redact("mysql://u:p4ss@h:3306/db"), "mysql://u:<redacted>@h:3306/db")

    def test_bearer_token(self):
        self.assertEqual(
            redact("Authorization: Bearer abcdefghijklmnop12"),
            "Authorization: Bearer <redacted>",
        )
        self.assertEqual(redact("token=abcdefghijklmnop, user=1"), "token=<redacted>, user=1")

    def test_provider_keys(self):
        self.assertEqual(redact("key AKIAABCDEFGHIJKLMNOP used"), "key <redacted> used")
        self.assertEqual(redact("pat ghp_" + "a" * 36), "pat <redacted>")

    def test_email_and_ip(self):
        self.assertEqual(redact("user someone@example.com from 10.0.0.1"), "user <email> from <ip>")


class TestAlloyKeepsWhatIsNotACredential(unittest.TestCase):
    """The false positives of issue #913 pass unchanged."""

    def test_secret_name(self):
        """Secret_accessed_receiver() names a Secret as "Secret <name>", which is not a value of secret."""
        line = (
            "smarter.apps.secret.receivers.secret_accessed() from SecretTransformer, Secret openai_api_key, id: 1, "
            "user_profile: pk=1"
        )
        self.assertEqual(redact(line), line)

    def test_masked_connection_string(self):
        """SqlConnection.get_connection_string() masks the password as ******."""
        line = (
            "smarter.apps.connection.receivers.sql_connection_success() "
            "django.db.backends.mysql://smarter:******@smarter-mariadb:3306/smarter_test_db is READY"
        )
        self.assertEqual(redact(line), line)

    def test_masked_api_key(self):
        """Mask_string() masks all but the last four characters with *."""
        self.assertEqual(redact('    "api_key": "****abcd",'), '    "api_key": "****abcd",')
        self.assertEqual(redact("Prompt configuration: api_key=****abcd"), "Prompt configuration: api_key=****abcd")

    def test_traceback_source_line(self):
        """A traceback's source line that calls something is code, not a token."""
        line = "    stored_token = self.redis.get(self.name)"
        self.assertEqual(redact(line), line)


if __name__ == "__main__":
    unittest.main()
