#!/usr/bin/env python3
"""Fail when a ruleset of the base branch requires a status check that the Tests may never report.

Usage::

    python3 -I scripts/required_checks.py --branch main --allow python-report

The Tests workflow (test.yml) skips its eight Python shards when a pull request leaves the suite's
files unchanged. A skipped matrix job reports one check named after its template,
``python (shard ${{ matrix.shard }} of 8)``, never the eight real names. So the one required status
check of main is python-report, which stands for all eight shards and passes on a skip. A ruleset
that requires anything else, e.g. ``python (shard 1 of 8)``, leaves such a pull request waiting
forever, with no error anywhere. This happened once, after main's classic branch protection was
turned into rulesets that kept the shard names.

This script reads the rules that apply to the branch (``GET /repos/{repo}/rules/branches/{branch}``),
and exits with 1, naming each ruleset and check, when a rule requires a check that isn't allowed.
python-report runs it first, so the required check itself fails, and says why.

The token is read from ``GITHUB_TOKEN``, never from an argument, and is never printed. The repository
is public, so the workflow's read-only token is enough. When GitHub's api doesn't answer, it prints a
warning and exits with 0: an outage of GitHub's api must not block a merge.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API_URL = "https://api.github.com"
TIMEOUT_SECONDS = 30
ATTEMPTS = 3
RETRY_SECONDS = 5


def fetch_rules(api_url: str, repository: str, branch: str, token: str) -> list[dict]:
    """
    The rules of every active ruleset that applies to a branch.

    :param api_url: GitHub's api, e.g. https://api.github.com.
    :param repository: owner/name, e.g. smarter-sh/smarter.
    :param branch: The branch, e.g. main.
    :param token: A GitHub token, or an empty string.
    :returns: GitHub's list of rules, each with its ``type``, ``ruleset_id`` and ``parameters``.
    :raises OSError: When GitHub doesn't answer, or answers with an error, after every attempt.
    """
    url = f"{api_url}/repos/{repository}/rules/branches/{branch}?per_page=100"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)  # nosec B310: GitHub's api url
    last_error: OSError = OSError("no attempt was made")
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # nosec B310
                body = response.read().decode()
            rules = json.loads(body)
            return rules
        except OSError as error:
            last_error = error
            if attempt < ATTEMPTS:
                time.sleep(RETRY_SECONDS)
    raise last_error


def required_checks(rules: list[dict]) -> list[tuple[int, str]]:
    """
    The status checks that the rules require.

    :param rules: The rules of a branch, as :func:`fetch_rules` returns them.
    :returns: One (ruleset id, check name) for each required check.
    """
    checks = []
    for rule in rules:
        if rule.get("type") != "required_status_checks":
            continue
        ruleset_id = rule.get("ruleset_id", 0)
        parameters = rule.get("parameters") or {}
        for check in parameters.get("required_status_checks", []):
            context = check.get("context", "")
            checks.append((ruleset_id, context))
    return checks


def disallowed_checks(checks: list[tuple[int, str]], allowed: list[str]) -> list[tuple[int, str]]:
    """
    The required checks that aren't allowed.

    :param checks: (ruleset id, check name) pairs, from :func:`required_checks`.
    :param allowed: The check names that may be required.
    :returns: The pairs whose check name isn't in ``allowed``.
    """
    disallowed = []
    for ruleset_id, context in checks:
        if context not in allowed:
            disallowed.append((ruleset_id, context))
    return disallowed


def main(argv: list[str] | None = None) -> int:
    """Check the branch's required status checks, and return the exit code."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--branch", default="main", help="The protected branch, e.g. main.")
    parser.add_argument(
        "--allow",
        action="append",
        required=True,
        help="A check that may be required, e.g. python-report. Repeat it for more than one.",
    )
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "smarter-sh/smarter"))
    parser.add_argument("--api-url", default=os.environ.get("GITHUB_API_URL", API_URL), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    token = os.environ.get("GITHUB_TOKEN", "")

    try:
        rules = fetch_rules(args.api_url, args.repository, args.branch, token)
    except (OSError, ValueError) as error:
        print(f"::warning::Could not read the rules of {args.branch}, so they weren't checked: {error}")
        return 0

    checks = required_checks(rules)
    disallowed = disallowed_checks(checks, args.allow)
    if not disallowed:
        names = sorted({context for _, context in checks})
        print(f"The required status checks of {args.branch} are fine: {', '.join(names) or 'none'}.")
        return 0

    allowed = ", ".join(args.allow)
    for ruleset_id, context in disallowed:
        settings_url = f"https://github.com/{args.repository}/settings/rules/{ruleset_id}"
        print(
            f"::error::Ruleset {ruleset_id} of {args.branch} requires the status check '{context}', which the"
            f" Tests may never report, so pull requests can wait for it forever. Only {allowed} may be"
            f" required. Remove it: {settings_url}"
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
