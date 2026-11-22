"""
Tests of scripts/required_checks.py, which fails when a ruleset requires a check the Tests may never report.

They need only the standard library, and never call GitHub. Run them from the repository's root:

    python -m unittest discover -s scripts/tests -t scripts
"""

import io
import json
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import required_checks  # noqa: E402  pylint: disable=wrong-import-position

# The rules of main when a pull request got stuck: python-report from one ruleset, and the eight
# shard names, which a skipped matrix never reports, from another.
STUCK_RULES = [
    {"type": "deletion", "ruleset_id": 26764322},
    {
        "type": "required_status_checks",
        "ruleset_id": 26764323,
        "parameters": {
            "required_status_checks": [{"context": f"python (shard {n} of 8)", "integration_id": 15368} for n in (1, 2)]
        },
    },
    {"type": "pull_request", "ruleset_id": 25985286, "parameters": {}},
    {
        "type": "required_status_checks",
        "ruleset_id": 25985286,
        "parameters": {"required_status_checks": [{"context": "python-report", "integration_id": 15368}]},
    },
]

GOOD_RULES = [STUCK_RULES[0], STUCK_RULES[2], STUCK_RULES[3]]


class FakeResponse(io.BytesIO):
    """A urlopen response: a readable body that is also a context manager."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def respond(rules):
    """A fake urlopen that answers with these rules."""

    def urlopen(request, timeout):
        return FakeResponse(json.dumps(rules).encode())

    return urlopen


def run(argv, urlopen, environ=None):
    """Run main() with a fake urlopen and no retry delay.

    Returns (exit code, stdout).
    """
    out = io.StringIO()
    with (
        mock.patch("urllib.request.urlopen", urlopen),
        mock.patch.object(required_checks, "RETRY_SECONDS", 0),
        mock.patch.dict("os.environ", environ or {}, clear=True),
        redirect_stdout(out),
    ):
        code = required_checks.main(argv)
    return code, out.getvalue()


class TestRequiredChecks(unittest.TestCase):
    """Required_checks() and disallowed_checks() find the checks a ruleset shouldn't require."""

    def test_required_checks_reads_only_status_check_rules(self):
        checks = required_checks.required_checks(STUCK_RULES)
        self.assertEqual(
            checks,
            [(26764323, "python (shard 1 of 8)"), (26764323, "python (shard 2 of 8)"), (25985286, "python-report")],
        )

    def test_required_checks_of_no_rules(self):
        self.assertEqual(required_checks.required_checks([]), [])

    def test_disallowed_checks(self):
        checks = required_checks.required_checks(STUCK_RULES)
        disallowed = required_checks.disallowed_checks(checks, ["python-report"])
        self.assertEqual(disallowed, [(26764323, "python (shard 1 of 8)"), (26764323, "python (shard 2 of 8)")])


class TestMain(unittest.TestCase):
    """Main() fails on a ruleset that requires a shard, and never on GitHub's outage."""

    def test_passes_when_only_allowed_checks_are_required(self):
        code, out = run(["--allow", "python-report"], respond(GOOD_RULES))
        self.assertEqual(code, 0)
        self.assertIn("are fine: python-report", out)

    def test_passes_when_nothing_is_required(self):
        code, out = run(["--allow", "python-report"], respond([]))
        self.assertEqual(code, 0)
        self.assertIn("are fine: none", out)

    def test_fails_and_names_the_ruleset_and_check(self):
        code, out = run(["--allow", "python-report", "--repository", "owner/repo"], respond(STUCK_RULES))
        self.assertEqual(code, 1)
        self.assertIn("::error::Ruleset 26764323 of main requires the status check 'python (shard 1 of 8)'", out)
        self.assertIn("https://github.com/owner/repo/settings/rules/26764323", out)
        self.assertNotIn("'python-report'", out)

    def test_more_than_one_allowed_check(self):
        code, _ = run(
            ["--allow", "python-report", "--allow", "python (shard 1 of 8)", "--allow", "python (shard 2 of 8)"],
            respond(STUCK_RULES),
        )
        self.assertEqual(code, 0)

    def test_sends_the_token_and_reads_the_branch(self):
        requests = []

        def urlopen(request, timeout):
            requests.append(request)
            return FakeResponse(b"[]")

        environ = {"GITHUB_TOKEN": "a-token", "GITHUB_REPOSITORY": "owner/repo", "GITHUB_API_URL": "https://api.test"}
        code, out = run(["--branch", "alpha", "--allow", "python-report"], urlopen, environ)
        self.assertEqual(code, 0)
        self.assertEqual(requests[0].full_url, "https://api.test/repos/owner/repo/rules/branches/alpha?per_page=100")
        self.assertEqual(requests[0].get_header("Authorization"), "Bearer a-token")
        self.assertNotIn("a-token", out)

    def test_no_token_sends_no_authorization(self):
        requests = []

        def urlopen(request, timeout):
            requests.append(request)
            return FakeResponse(b"[]")

        run(["--allow", "python-report"], urlopen)
        self.assertIsNone(requests[0].get_header("Authorization"))

    def test_retries_then_succeeds(self):
        answers = [urllib.error.HTTPError("url", 502, "Bad Gateway", None, None), FakeResponse(b"[]")]

        def urlopen(request, timeout):
            answer = answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer

        code, _ = run(["--allow", "python-report"], urlopen)
        self.assertEqual(code, 0)
        self.assertEqual(answers, [])

    def test_warns_and_passes_when_github_does_not_answer(self):
        calls = []

        def urlopen(request, timeout):
            calls.append(request)
            raise urllib.error.URLError("unreachable")

        code, out = run(["--allow", "python-report"], urlopen)
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), required_checks.ATTEMPTS)
        self.assertIn("::warning::Could not read the rules of main", out)

    def test_warns_and_passes_on_a_body_that_is_not_json(self):
        def urlopen(request, timeout):
            return FakeResponse(b"<html>")

        code, out = run(["--allow", "python-report"], urlopen)
        self.assertEqual(code, 0)
        self.assertIn("::warning::", out)


if __name__ == "__main__":
    unittest.main()
