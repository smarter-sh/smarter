#!/usr/bin/env python3
"""Triage a Smarter log file: failures, warnings, possible secrets and PII, unprefixed messages and noise.

Usage::

    python3 -I skills/smarter-log-review/scripts/scan-log.py path/to/log.txt [--top 15]

It reads the log as data and prints a report. It never changes anything. The output is a starting
point for a human review, not a verdict: read the lines it points at before you report them.
"""

import argparse
import collections
import re
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*m|\[[0-9;]*m")
HEADER = re.compile(r"^\[(?P<ts>[\d\- :+]+)\] - (?P<level>[A-Z]+) - (?P<proc>\S+) - (?P<msg>.*)$")
PREFIX = re.compile(r"^(smarter\.[\w.]+|[A-Z]\w+\[\d+\]|SAMLoader\[\d+\]|-{10,}|\s*$)")
FAILURE = re.compile(
    r"Traceback|Exception|\bError\b|\bfailed\b|Failed|suspended|Response [45]\d\d|HTTP/1\.1 [45]\d\d", re.IGNORECASE
)
NOT_FAILURE = re.compile(r"0 failed|failClosed|\"lastError\": null|ValueError\(|SmarterValueError")

SECRETS = {
    "aws access key": re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"),
    "aws account id": re.compile(r"(?:account[ :]+|arn:aws:[\w-]+:[\w-]*:)(\d{12})\b"),
    "openai-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "bearer/token value": re.compile(r"(?i)(bearer|token)[\"' :=]+[A-Za-z0-9._-]{12,}"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "password in url": re.compile(r"://[^:/\s]+:(?!\*+@)[^@\s]+@"),
    "load balancer / cdn host": re.compile(r"\b[\w-]+\.(elb\.[\w-]+\.amazonaws\.com|cloudfront\.net)\b"),
}
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
LLM_PAYLOAD = re.compile(r'"(messages|content|systemRole|defaultSystemRole|judgePrompt)":')
PYWARN = re.compile(r"(\w+Warning): (.*)")


def template(msg: str) -> str:
    """Reduce a message to a template, so that repeats group together."""
    msg = re.sub(r"\[\d{6,}\]|\(\d{6,}\)|id=\d+", "[N]", msg)
    msg = re.sub(r"_[0-9a-f]{32}\b", "_<hash>", msg)
    msg = re.sub(r"\b\d+(\.\d+)?\b", "N", msg)
    return msg[:160]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    levels = collections.Counter()
    warnings = collections.Counter()
    failures = []
    unprefixed = collections.Counter()
    noise = collections.Counter()
    secrets = collections.defaultdict(set)
    emails = collections.Counter()
    pywarnings = collections.Counter()
    payload_lines = 0

    with open(args.path, encoding="utf-8", errors="replace") as handle:
        for number, raw in enumerate(handle, 1):
            line = ANSI.sub("", raw.rstrip("\n"))
            match = HEADER.match(line)
            msg = match.group("msg") if match else line
            if match:
                level = match.group("level")
                levels[level] += 1
                noise[template(msg).split(" ")[0]] += 1
                if level in ("WARNING", "ERROR", "CRITICAL"):
                    warnings[(level, template(msg))] += 1
                if not PREFIX.match(msg):
                    unprefixed[template(msg)] += 1
            if FAILURE.search(line) and not NOT_FAILURE.search(line):
                failures.append((number, line.strip()[:220]))
            for name, pattern in SECRETS.items():
                for found in pattern.finditer(line):
                    secrets[name].add(found.group(0)[:80])
            for found in EMAIL.findall(line):
                emails[found] += 1
            if LLM_PAYLOAD.search(line):
                payload_lines += 1
            warn = PYWARN.search(line)
            if warn and not match:
                pywarnings[f"{warn.group(1)}: {warn.group(2)[:140]}"] += 1

    def section(title: str) -> None:
        print(f"\n== {title} ==")

    section("log levels")
    for level, count in levels.most_common():
        print(f"{count:7d}  {level}")

    section("failure-looking lines (read each one)")
    for number, line in failures[: args.top * 3]:
        print(f"{number:7d}: {line}")

    section("warnings and errors, by template (is each one a real problem?)")
    for (level, msg), count in warnings.most_common():
        print(f"{count:5d}  {level:8s} {msg}")

    section("python warnings printed to stderr")
    for msg, count in pywarnings.most_common():
        print(f"{count:5d}  {msg}")

    section("possible secrets and infrastructure identifiers")
    for name, values in secrets.items():
        print(f"  {name}: {sorted(values)[:5]}")

    section("email addresses (PII?)")
    for address, count in emails.most_common(args.top):
        print(f"{count:5d}  {address}")
    print(f"\n  lines that look like LLM prompt or response payloads: {payload_lines}")

    section("messages without an origin prefix (style defects)")
    for msg, count in unprefixed.most_common(args.top):
        print(f"{count:5d}  {msg}")

    section("noisiest message starts (candidates for DEBUG)")
    total = sum(noise.values()) or 1
    for start, count in noise.most_common(args.top):
        print(f"{count:7d}  {100 * count / total:5.1f}%  {start[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
