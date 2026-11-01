#!/usr/bin/env python3
"""Redact credentials and personal data from downloaded logs, in place, before anyone reviews them.

Usage::

    python3 -E -s scripts/pod_log_redact.py <folder>

Every ``*.log`` and ``*.txt`` file under the folder is rewritten, with each match replaced by a
placeholder that names what it was, e.g. ``<redacted:email>``, so that a reviewer still sees
that, e.g., a log line carries an email address. It prints only counts, never what it found.

It runs before an automated review (``.github/workflows/podLogReview.yml``) writes public GitHub
issues from the logs: the issues must never quote a credential or a person's data. The patterns
follow the Guardrail's built-in detectors (``smarter.apps.guardrail.services.strategies.detectors``),
and this script copies them rather than importing them, so that it runs without Django.

Smarter's logs must never hold a credential or personal data, so redacting is a safety net, not
the fix: **every redaction is a finding.** Either Smarter logged something it must not, and the
code that wrote the line must change, or a pattern here matched something harmless, and the
pattern must change. Both get a GitHub issue. So the script also writes :data:`REPORT_NAME` in the
folder, which says where each placeholder is (file, kind, line numbers, never the value), the
review's prompt names the count, a run with redactions is never reported as healthy, and the
workflow's log gets a warning.

It uses only Python's standard library, which comes with every Python install:

- ``argparse`` reads the command line: here, the one argument, the folder.
- ``pathlib`` handles file paths as objects: ``Path.rglob("*")`` lists every file under a folder,
  at any depth, and ``read_text()`` and ``write_text()`` read and replace a whole file.
- ``re`` is regular expressions: :data:`PATTERNS` describes what a credential looks like, and
  ``Pattern.sub()`` replaces every match in a text with what a function returns for it.
- ``ipaddress`` parses an IP address and says whether it is private (``10.0.0.1``) or public.
- ``json`` writes the report, :data:`REPORT_NAME`, and reads it back in :func:`read_report`.
- ``collections.Counter`` is a dict that counts: ``counts["email"] += 1`` works even before the
  first email, starting from 0.
- ``functools.partial`` fills in some of a function's arguments ahead of time, so that
  ``Pattern.sub()``, which passes only the match, can call :func:`redact_match` with its kind and
  counts too.
- ``sys`` gives the exit code and the error stream (``sys.stderr``).
"""

import argparse
import collections
import functools
import ipaddress
import json
import pathlib
import re
import sys

DESCRIPTION = "Redact credentials and personal data from downloaded logs, in place."
"""The command line's description."""

PATTERNS: list[tuple[str, re.Pattern]] = [
    # In this order: a credential is redacted whole before the "token" and "secret" patterns below,
    # which would redact only part of it. The examples are shortened with "…".
    #
    # A PEM private key: the whole block, from its "-----BEGIN <type> PRIVATE KEY-----" line,
    # e.g. RSA or EC, through its base64 lines to the matching END line, or to the end of a log
    # that was cut off inside it.
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)")),
    #
    # A JSON Web Token: three base64url parts, the first two starting with eyJ ('{"' encoded):
    #   eyJhbGciOi….eyJzdWIiOi….SflKxwRJSM…
    ("jwt", re.compile(r"(?<![\w-])eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?![\w-])")),
    #
    # A provider's api key, recognized by its prefix. Not part of a longer word.
    (
        "api-key",
        re.compile(
            r"""(?<![\w-])(?:
                sk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}       # OpenAI or Anthropic: sk-proj-Ab3…, sk-ant-api03-…
              | gh[pousr]_[A-Za-z0-9]{36,}                 # GitHub token: ghp_16C7e42F…
              | github_pat_[A-Za-z0-9_]{22,}               # GitHub fine-grained token: github_pat_11ABC…
              | xox[abposr]-[A-Za-z0-9-]{10,}              # Slack token: xoxb-1234-5678-AbCd…
              | AIza[0-9A-Za-z_-]{35}                      # Google api key: AIzaSyD…
              | (?:sk|rk)_(?:live|test)_[0-9A-Za-z]{24,}   # Stripe secret or restricted key: sk_live_51H…
              | glpat-[A-Za-z0-9_-]{20,}                   # GitLab token: glpat-xYz…
              | hf_[A-Za-z0-9]{30,}                        # Hugging Face token: hf_AbCd…
            )(?![\w-])""",
            re.VERBOSE,
        ),
    ),
    #
    # An AWS access key id: AKIA (long-lived) or ASIA (temporary), then 16 capital letters or
    # digits, 20 characters in all.
    ("aws-access-key", re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA|ABIA|ACCA)[A-Z0-9]{16}(?![A-Z0-9])")),
    #
    # The 12-digit account id in an AWS ARN, arn:aws:<service>:<region>:<account id>:<resource>;
    # the rest of the ARN stays.
    ("aws-account-id", re.compile(r"arn:aws:[\w-]+:[\w-]*:(?P<value>\d{12}):")),
    #
    # The user and password in a url; the host stays:
    #   mysql://smarter:s3cret@db:3306/ -> mysql://<redacted:password-in-url>@db:3306/
    ("password-in-url", re.compile(r"://(?P<value>[^:/\s@]+:[^@\s/]+)@")),
    #
    # The value after a word such as Bearer, token or api_key, if it is 16 or more characters:
    #   Authorization: Bearer 9f8e7d6c5b4a3f2e… -> Authorization: Bearer <redacted:token>
    #   "api_key": "AbCdEf0123456789…"           -> "api_key": "<redacted:token>"
    (
        "token",
        re.compile(r"(?i)\b(?:bearer|token|apikey|api-key|api_key)[\"' :=]{1,3}(?P<value>[A-Za-z0-9._~+/-]{16,}=*)"),
    ),
    #
    # The value of a password or secret setting, if it is 6 or more characters:
    #   password=hunter22            -> password=<redacted:secret>
    #   "client_secret": "Zx81…"     -> "client_secret": "<redacted:secret>"
    (
        "secret",
        re.compile(
            r"(?i)\b(?:password|passwd|pwd|secret|client_secret|access_token|auth_token)[\"']?[ \t]*[:=][ \t]*[\"']?"
            r"(?P<value>[^\s\"',;&]{6,})"
        ),
    ),
    #
    # An email address: someone@example.com
    ("email", re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])")),
    #
    # An AWS load balancer's or CloudFront's hostname, which identifies the infrastructure:
    #   a1b2c3-123.elb.us-east-2.amazonaws.com, d111111abcdef8.cloudfront.net
    ("aws-host", re.compile(r"\b[\w.-]+\.(?:elb\.[\w-]+\.amazonaws\.com|cloudfront\.net)\b")),
]
"""What to redact, as ``(kind, pattern)``, in order.

See :func:`redact_match`.
"""

# An IPv4 address, 203.0.113.7, or an IPv6 address, 2001:db8::8a2e:370:7334, not inside a longer
# word or number. It also matches some times, 14:04:45, which redact_ip() then keeps.
IP_ADDRESS = re.compile(
    r"(?<![\w.:])(?:(?:\d{1,3}\.){3}\d{1,3}|(?:[0-9A-Fa-f]{1,4}:){2,7}[0-9A-Fa-f]{0,4}(?::[0-9A-Fa-f]{1,4})*)(?![\w.:])"
)
"""An IPv4 or IPv6 address, or a time that looks like one.

See :func:`redact_ip`.
"""
KEEP_IPS = {"127.0.0.1", "0.0.0.0", "::1"}  # nosec B104: addresses to keep, not to bind
"""Addresses that say where a server listens, not who connected."""

PLACEHOLDER = re.compile(r"<redacted:(?P<kind>[a-z-]+)>")
"""A placeholder that :func:`redact_match` or :func:`redact_ip` wrote, e.g. ``<redacted:email>``."""

REPORT_NAME = "redactions.json"
"""The report that :func:`main` writes in the folder: where each placeholder is.

E.g. ``{"total": 3, "kinds": {"email": 3}, "files": {"smarter/<pod>.log": {"email": {"count": 3,
"lines": [12, 40, 41]}}}}``. It names files, kinds and line numbers, never a redacted value. Its
``.json`` suffix keeps it out of the files that :func:`main` redacts.
"""

MAX_LINES = 20
"""The most line numbers that the report lists for one kind in one file; ``count`` has them all."""


def redact_match(match: re.Match, kind: str, counts: collections.Counter) -> str:
    """
    Return one match of a pattern of :data:`PATTERNS`, redacted.

    A pattern with a group named ``value`` redacts only that group, e.g. the password of
    ``password=...``, and leaves a value that an earlier pattern already redacted alone.

    :param match: The match.
    :param kind: What the pattern finds, e.g. ``secret``.
    :param counts: Counts the matches by kind, updated in place.
    :returns: The match's text, with the whole match or its value replaced by ``<redacted:<kind>>``.
    """
    whole = match.group(0)
    if "value" not in match.re.groupindex:
        start, end = 0, len(whole)
    elif match.group("value").startswith("<redacted"):
        return whole
    else:
        start, end = match.start("value") - match.start(), match.end("value") - match.start()
    counts[kind] += 1
    return f"{whole[:start]}<redacted:{kind}>{whole[end:]}"


def redact_ip(match: re.Match, counts: collections.Counter) -> str:
    """
    Return a match of :data:`IP_ADDRESS`, redacted if it is a public address.

    :param match: The match, which may also be a time such as ``14:04:45``.
    :param counts: Counts the matches by kind, updated in place.
    :returns: ``<redacted:ip-address>``, or the match's text if it isn't a public address.
    """
    value = match.group(0)
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return value
    if value in KEEP_IPS or address.is_private or address.is_loopback:
        return value
    counts["ip-address"] += 1
    return "<redacted:ip-address>"


def redact(text: str, counts: collections.Counter) -> str:
    """
    Return the text with every match of :data:`PATTERNS` and every public IP address replaced.

    :param text: The text of a log.
    :param counts: Counts the matches by kind, e.g. ``email``, updated in place.
    :returns: The text, with each match replaced by ``<redacted:<kind>>``.
    """
    for kind, pattern in PATTERNS:
        # sub() calls the function with each match, and puts what it returns in the match's place.
        text = pattern.sub(functools.partial(redact_match, kind=kind, counts=counts), text)
    return IP_ADDRESS.sub(functools.partial(redact_ip, counts=counts), text)


def locate(text: str) -> dict[str, dict]:
    """
    Return where the placeholders in a redacted text are, by kind.

    :param text: A log, after :func:`redact`.
    :returns: E.g. ``{"email": {"count": 3, "lines": [12, 40, 41]}}``, with at most
        :data:`MAX_LINES` line numbers, counted from 1, per kind. Empty if there are none.
    """
    found: dict[str, dict] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        for match in PLACEHOLDER.finditer(line):
            entry = found.setdefault(match.group("kind"), {"count": 0, "lines": []})
            entry["count"] += 1
            if len(entry["lines"]) < MAX_LINES and entry["lines"][-1:] != [number]:
                entry["lines"].append(number)
    return found


def read_report(folder: str) -> dict:
    """
    Return the report that :func:`main` wrote in a folder of logs.

    :param folder: The folder of logs, or an empty string.
    :returns: The report (see :data:`REPORT_NAME`), or an empty dict if there is none or it can't
        be read. Its ``total`` is 0 when nothing was redacted.
    """
    if not folder:
        return {}
    try:
        report = json.loads((pathlib.Path(folder) / REPORT_NAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return report if isinstance(report, dict) else {}


def main() -> int:
    """
    Redact every ``*.log`` and ``*.txt`` file under the folder named on the command line, in place.

    Writes :data:`REPORT_NAME` in the folder, and prints only the number of files and of
    placeholders of each kind, never a match. When there are placeholders it also prints a GitHub
    Actions ``::warning::``, because each one is a finding (see the module's docstring).

    :returns: 0, or 1 if the folder doesn't exist.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("folder", help="the folder of downloaded logs, e.g. the one download-logs.sh wrote")
    args = parser.parse_args()
    folder = pathlib.Path(args.folder)
    if not folder.is_dir():
        print(f"pod_log_redact.py: {folder} is not a folder", file=sys.stderr)
        return 1
    # the placeholders of every file, by kind, e.g. {"email": 3}.
    total: collections.Counter = collections.Counter()
    # where they are, by file, e.g. {"smarter/<pod>.log": {"email": {"count": 3, "lines": [...]}}}.
    where: dict[str, dict] = {}
    # every .log and .txt file under the folder, at any depth, e.g. smarter/<pod>.log and inventory/pods.txt.
    files = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix in (".log", ".txt"))
    for path in files:
        # errors="replace" turns bytes that aren't UTF-8 into "�" rather than failing on them.
        text = redact(path.read_text(encoding="utf-8", errors="replace"), collections.Counter())
        path.write_text(text, encoding="utf-8")
        # counted from the placeholders in the redacted text, so that running the script twice
        # on the same folder reports the same thing.
        found = locate(text)
        if found:
            where[path.relative_to(folder).as_posix()] = found
            total.update({kind: entry["count"] for kind, entry in found.items()})
    report = {"total": sum(total.values()), "kinds": dict(sorted(total.items())), "files": where}
    (folder / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = ", ".join(f"{kind} {count}" for kind, count in sorted(total.items())) or "nothing"
    print(f"redacted {len(files)} file(s): {summary}")
    if total:
        print(
            f"::warning::{report['total']} redaction(s) in {len(where)} log(s): Smarter's logs must not hold "
            f"credentials or personal data, so each one is a finding to investigate (see {REPORT_NAME})."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
