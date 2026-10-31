#!/usr/bin/env python3
"""Write the results of a run of the Tests workflow (.github/workflows/test.yml) as one Slack message.

Usage::

    python3 -I scripts/slack_test_report.py --title "Tests #160" \\
        --react-result success --react-results vitest-results.json \\
        --react-coverage coverage-summary.json \\
        --python-result success --python-results shards --python-coverage coverage.json \\
        --slack-bot-result success [--react-passed-before] [--python-passed-before] \\
        [--ref alpha] [--actor someone] [--pr-title "..."] [--pr-url URL] [--run-url URL] \\
        | python3 -I scripts/slack_post.py --channel smarter

The GitHub app for Slack only says whether a run succeeded. This message also gives what the
run's job summaries show: the React test files and tests (Vitest's JSON report), the Python tests
(the shards' JUnit XML reports), each suite's coverage, and the names of the tests that failed.

A ``--*-result`` is the job's result as GitHub reports it (``success``, ``failure``, ``cancelled``
or ``skipped``). A missing or unreadable report is left out of the message, never an error: a job
that failed early writes none. ``--*-passed-before`` says that the suite was skipped because the
same files passed in an earlier run (see the workflow's fingerprint job).

The message, in Slack's mrkdwn, is printed. scripts/slack_post.py posts it.
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET  # nosec B405: the workflow's own test reports
from dataclasses import dataclass, field
from pathlib import Path

MAX_FAILURES = 15
"""The most failed tests listed per suite. The rest are counted."""
MAX_NAME = 150


@dataclass
class SuiteReport:
    """What one suite's reports say: its counts, the tests that failed, and its coverage."""

    files: int | None = None
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: list[str] = field(default_factory=list)
    coverage: str | None = None

    @property
    def total(self) -> int:
        """The number of tests that ran or were skipped."""
        return self.passed + self.failed + self.skipped


def escape(text: str) -> str:
    """Escape text for Slack's mrkdwn."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def shorten(text: str, limit: int = MAX_NAME) -> str:
    """Return text cut to ``limit`` characters, with an ellipsis when it was cut."""
    return text if len(text) <= limit else text[: limit - 1] + "…"


def read_json(path: str | None) -> dict | None:
    """Return a JSON file's object, or None when there is no path, no file, or no valid JSON."""
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def vitest_report(results_path: str | None, coverage_path: str | None) -> SuiteReport | None:
    """
    Return the React suite's report, from Vitest's JSON reporter and its coverage summary.

    :param results_path: The file written by ``--reporter=json --outputFile.json=...``.
    :param coverage_path: ``coverage/coverage-summary.json``, written by the json-summary
        coverage reporter.
    :returns: None when there is no readable results file.
    """
    data = read_json(results_path)
    if data is None:
        return None
    report = SuiteReport()
    files = data.get("testResults") or []
    report.files = len(files)
    for test_file in files:
        name = Path(str(test_file.get("name", ""))).name
        for test in test_file.get("assertionResults") or []:
            status = test.get("status")
            if status == "passed":
                report.passed += 1
            elif status == "failed":
                report.failed += 1
                report.failures.append(f"{name} › {test.get('fullName') or test.get('title', '')}")
            else:  # pending, skipped, todo
                report.skipped += 1
        # A file that fails to load has no tests, only a failed status and a message.
        if test_file.get("status") == "failed" and not test_file.get("assertionResults"):
            report.failed += 1
            report.failures.append(f"{name} (did not load)")
    coverage = read_json(coverage_path)
    if coverage is not None:
        percent = (coverage.get("total") or {}).get("lines", {}).get("pct")
        if isinstance(percent, (int, float)):
            report.coverage = f"{percent:.1f}%"
    return report


def junit_report(results_dir: str | None, coverage_path: str | None) -> SuiteReport | None:
    """
    Return the Python suite's report, from the shards' JUnit XML reports and the combined coverage.

    :param results_dir: A directory searched for ``test-results-shard-*.xml``, e.g. the
        downloaded artifacts of every shard.
    :param coverage_path: The ``coverage json`` report of the combined coverage.
    :returns: None when no report is found.
    """
    if not results_dir or not Path(results_dir).is_dir():
        return None
    paths = sorted(Path(results_dir).rglob("test-results-shard-*.xml"))
    report = SuiteReport()
    found = False
    for path in paths:
        try:
            root = ET.parse(path).getroot()  # nosec B314: the workflow's own test reports
        except (OSError, ET.ParseError):
            continue
        found = True
        for case in root.iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                report.failed += 1
                report.failures.append(f"{case.get('classname', '')}.{case.get('name', '')}")
            elif case.find("skipped") is not None:
                report.skipped += 1
            else:
                report.passed += 1
    if not found:
        return None
    coverage = read_json(coverage_path)
    if coverage is not None:
        display = (coverage.get("totals") or {}).get("percent_covered_display")
        if display:
            report.coverage = f"{display}%"
    return report


def suite_passed(result: str, passed_before: bool) -> bool:
    """Whether a suite's job stands for a pass: it succeeded, or was skipped because it passed before."""
    return result == "success" or (result == "skipped" and passed_before)


def suite_lines(name: str, result: str, passed_before: bool, report: SuiteReport | None) -> list[str]:
    """
    Return the message's lines for one suite: a summary line, then the tests that failed.

    :param name: The suite's name in the message, e.g. ``React``.
    :param result: The job's result.
    :param passed_before: Whether the suite was skipped because the same files passed before.
    :param report: What the suite's reports say, if they could be read.
    """
    icon = ":white_check_mark:" if suite_passed(result, passed_before) else ":x:"
    if passed_before and result in ("success", "skipped") and report is None:
        return [f"{icon} *{name}*: unchanged, passed in an earlier run"]
    if report is None:
        return [f"{icon} *{name}*: {result}, no test report"]
    parts = []
    if report.files is not None:
        parts.append(f"{report.files:,} files")
    parts.append(f"{report.passed:,} passed")
    if report.failed:
        parts.append(f"*{report.failed:,} failed*")
    if report.skipped:
        parts.append(f"{report.skipped:,} skipped")
    if report.coverage:
        parts.append(f"coverage {report.coverage}")
    lines = [f"{icon} *{name}*: " + " · ".join(parts)]
    if not suite_passed(result, passed_before) and not report.failed:
        lines[0] += f" (job {result})"
    shown = report.failures[:MAX_FAILURES]
    lines.extend(f"      • `{escape(shorten(failure))}`" for failure in shown)
    if len(report.failures) > len(shown):
        lines.append(f"      …and {len(report.failures) - len(shown)} more")
    return lines


def message(args: argparse.Namespace, react: SuiteReport | None, python: SuiteReport | None) -> str:
    """Return the Slack message: a heading, the pull request, one block per suite, and a link to the run."""
    passed = (
        suite_passed(args.react_result, args.react_passed_before)
        and suite_passed(args.python_result, args.python_passed_before)
        and suite_passed(args.slack_bot_result, False)
    )
    heading = f"{':white_check_mark:' if passed else ':x:'} *{escape(args.title)} {'passed' if passed else 'failed'}*"
    context = [f"`{escape(args.ref)}`" if args.ref else "", escape(args.actor) if args.actor else ""]
    context = [part for part in context if part]
    if context:
        heading += " · " + " · ".join(context)
    lines = [heading]
    if args.pr_title and args.pr_url:
        lines.append(f"<{args.pr_url}|{escape(shorten(args.pr_title))}>")
    lines.extend(suite_lines("React", args.react_result, args.react_passed_before, react))
    lines.extend(suite_lines("Python", args.python_result, args.python_passed_before, python))
    if not suite_passed(args.slack_bot_result, False):
        lines.append(f":x: *Slack bot*: {args.slack_bot_result}")
    if args.run_url:
        lines.append(f"<{args.run_url}|View the run>")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Return the command line's arguments."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--title", required=True, help="The run's name, e.g. 'Tests #160'.")
    parser.add_argument("--react-result", required=True)
    parser.add_argument("--react-results", help="Vitest's JSON report.")
    parser.add_argument("--react-coverage", help="Vitest's coverage-summary.json.")
    parser.add_argument("--react-passed-before", action="store_true")
    parser.add_argument("--python-result", required=True)
    parser.add_argument("--python-results", help="A directory holding the shards' JUnit XML reports.")
    parser.add_argument("--python-coverage", help="The combined coverage, as coverage json writes it.")
    parser.add_argument("--python-passed-before", action="store_true")
    parser.add_argument("--slack-bot-result", default="success")
    parser.add_argument("--ref", default="")
    parser.add_argument("--actor", default="")
    parser.add_argument("--pr-title", default="")
    parser.add_argument("--pr-url", default="")
    parser.add_argument("--run-url", default="")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Print the message.

    Returns the exit code.
    """
    args = parse_args(argv)
    react = vitest_report(args.react_results, args.react_coverage)
    python = junit_report(args.python_results, args.python_coverage)
    print(message(args, react, python))
    return 0


if __name__ == "__main__":
    sys.exit(main())
