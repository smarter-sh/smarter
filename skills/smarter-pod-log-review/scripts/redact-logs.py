#!/usr/bin/env python3
"""Redact credentials and personal data from downloaded logs, in place, before anyone reviews them.

Usage::

    python3 -I skills/smarter-pod-log-review/scripts/redact-logs.py <folder>

Every ``*.log`` and ``*.txt`` file under the folder is rewritten, with each match replaced by a
placeholder that names what it was, e.g. ``<redacted:email>``, so that a reviewer still sees
that, e.g., a log line carries an email address. It prints only counts, never what it found.

It runs before an automated review (``.github/workflows/podLogReview.yml``) writes public GitHub
issues from the logs: the issues must never quote a credential or a person's data. The patterns
follow the Guardrail's built-in detectors (``smarter.apps.guardrail.services.strategies.detectors``),
and this script copies them rather than importing them, so that it runs without Django.
"""

import argparse
import collections
import ipaddress
import pathlib
import re
import sys

PATTERNS: list[tuple[str, re.Pattern]] = [
    # in order: a credential is redacted before the token and secret patterns, which would only
    # redact part of it.
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)")),
    ("jwt", re.compile(r"(?<![\w-])eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![\w-])")),
    (
        "api-key",
        re.compile(
            r"(?<![\w-])(?:"
            r"sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}"
            r"|gh[pousr]_[A-Za-z0-9]{36,}"
            r"|github_pat_[A-Za-z0-9_]{22,}"
            r"|xox[abposr]-[A-Za-z0-9-]{10,}"
            r"|AIza[0-9A-Za-z_-]{35}"
            r"|(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{24,}"
            r"|glpat-[A-Za-z0-9_-]{20,}"
            r"|hf_[A-Za-z0-9]{30,}"
            r")(?![\w-])"
        ),
    ),
    ("aws-access-key", re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}(?![A-Z0-9])")),
    ("aws-account-id", re.compile(r"arn:aws:[\w-]+:[\w-]*:(?P<value>\d{12}):")),
    ("password-in-url", re.compile(r"://(?P<value>[^:/\s@]+:[^@\s/]+)@")),
    (
        "token",
        re.compile(r"(?i)\b(?:bearer|token|apikey|api-key|api_key)[\"' :=]{1,3}(?P<value>[A-Za-z0-9._~+/-]{16,}=*)"),
    ),
    (
        "secret",
        re.compile(
            r"(?i)\b(?:password|passwd|pwd|secret|client_secret|access_token|auth_token)[\"']?[ \t]*[:=][ \t]*[\"']?"
            r"(?P<value>[^\s\"',;&]{6,})"
        ),
    ),
    ("email", re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])")),
    ("aws-host", re.compile(r"\b[\w.-]+\.(?:elb\.[\w-]+\.amazonaws\.com|cloudfront\.net)\b")),
]
IP_ADDRESS = re.compile(
    r"(?<![\w.:])(?:(?:\d{1,3}\.){3}\d{1,3}|(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{1,4})*)(?![\w.:])"
)
KEEP_IPS = {"127.0.0.1", "0.0.0.0", "::1"}  # nosec B104: addresses to keep, not to bind
"""Addresses that say where a server listens, not who connected."""


def redact(text: str, counts: collections.Counter) -> str:
    """Return the text with every match replaced, and count the matches by kind."""
    for kind, pattern in PATTERNS:

        def replace(match: re.Match, kind: str = kind) -> str:
            # a pattern with a group named value replaces only that group, e.g. the password of password=...
            if "value" not in match.re.groupindex:
                counts[kind] += 1
                return f"<redacted:{kind}>"
            if match.group("value").startswith("<redacted"):
                return match.group(0)
            counts[kind] += 1
            start, end = match.span("value")
            offset = match.start()
            whole = match.group(0)
            return f"{whole[: start - offset]}<redacted:{kind}>{whole[end - offset :]}"

        text = pattern.sub(replace, text)

    def replace_ip(match: re.Match) -> str:
        value = match.group(0)
        try:
            address = ipaddress.ip_address(value)
        except ValueError:
            return value  # e.g. a time, 14:04:45
        if value in KEEP_IPS or address.is_private or address.is_loopback:
            return value
        counts["ip-address"] += 1
        return "<redacted:ip-address>"

    return IP_ADDRESS.sub(replace_ip, text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder")
    args = parser.parse_args()
    folder = pathlib.Path(args.folder)
    if not folder.is_dir():
        print(f"redact-logs.py: {folder} is not a folder", file=sys.stderr)
        return 1
    total: collections.Counter = collections.Counter()
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix in (".log", ".txt"))
    for path in files:
        counts: collections.Counter = collections.Counter()
        text = path.read_text(encoding="utf-8", errors="replace")
        path.write_text(redact(text, counts), encoding="utf-8")
        total.update(counts)
    summary = ", ".join(f"{kind} {count}" for kind, count in sorted(total.items())) or "nothing"
    print(f"redacted {len(files)} file(s): {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
