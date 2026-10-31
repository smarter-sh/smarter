"""
Tests of scripts/slack_test_report.py, which posts the Tests workflow's results to Slack.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s scripts/tests
"""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "slack_test_report.py"
spec = importlib.util.spec_from_file_location("slack_test_report", SCRIPT_PATH)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

VITEST_RESULTS = {
    "testResults": [
        {
            "name": "/repo/smarter/react/packages/a/src/App.test.tsx",
            "status": "passed",
            "assertionResults": [
                {"fullName": "App renders", "status": "passed"},
                {"fullName": "App skips", "status": "skipped"},
            ],
        },
        {
            "name": "/repo/smarter/react/packages/b/src/List.test.tsx",
            "status": "failed",
            "assertionResults": [
                {"fullName": "List renders", "status": "passed"},
                {"fullName": "List <deletes> & renames", "status": "failed"},
            ],
        },
        {"name": "/repo/smarter/react/packages/c/src/Broken.test.tsx", "status": "failed", "assertionResults": []},
    ]
}
VITEST_COVERAGE = {"total": {"lines": {"pct": 91.234}}}
JUNIT_SHARD_1 = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="a" tests="3">
    <testcase classname="smarter.apps.a.tests.TestA" name="test_one"/>
    <testcase classname="smarter.apps.a.tests.TestA" name="test_two"><failure message="no"/></testcase>
    <testcase classname="smarter.apps.a.tests.TestA" name="test_three"><skipped message="infrastructure"/></testcase>
  </testsuite>
</testsuites>
"""
JUNIT_SHARD_2 = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="b" tests="2">
    <testcase classname="smarter.apps.b.tests.TestB" name="test_one"/>
    <testcase classname="smarter.apps.b.tests.TestB" name="test_two"><error message="boom"/></testcase>
  </testsuite>
</testsuites>
"""
PYTHON_COVERAGE = {"totals": {"percent_covered_display": "93"}}


class SlackTestReportTestCase(unittest.TestCase):
    """Writes the reports that the workflow hands the script into a temporary directory."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.vitest = self.write("vitest-results.json", json.dumps(VITEST_RESULTS))
        self.vitest_coverage = self.write("coverage-summary.json", json.dumps(VITEST_COVERAGE))
        self.shards = self.dir / "shards"
        self.write("shards/python-shard-1/test-results-shard-1.xml", JUNIT_SHARD_1)
        self.write("shards/python-shard-2/test-results-shard-2.xml", JUNIT_SHARD_2)
        self.python_coverage = self.write("coverage.json", json.dumps(PYTHON_COVERAGE))

    def write(self, name: str, text: str) -> str:
        path = self.dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return str(path)

    def args(self, *extra: str) -> list[str]:
        return [
            "--title",
            "Tests #160",
            "--react-result",
            "success",
            "--python-result",
            "success",
            *extra,
        ]

    def run_dry(self, *extra: str) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            code = report.main(self.args(*extra))
        self.assertEqual(code, 0)
        return out.getvalue()


class TestVitestReport(SlackTestReportTestCase):
    """Vitest_report() reads Vitest's JSON report and coverage summary."""

    def test_counts_tests_and_failures(self):
        suite = report.vitest_report(self.vitest, self.vitest_coverage)
        self.assertEqual((suite.passed, suite.failed, suite.skipped), (2, 2, 1))
        self.assertEqual(suite.total, 5)
        self.assertEqual(suite.failures, ["List.test.tsx › List <deletes> & renames", "Broken.test.tsx (did not load)"])
        self.assertEqual(suite.coverage, "91.2%")

    def test_missing_or_invalid_files(self):
        self.assertIsNone(report.vitest_report(None, None))
        self.assertIsNone(report.vitest_report(str(self.dir / "missing.json"), None))
        self.assertIsNone(report.vitest_report(self.write("bad.json", "{not json"), None))
        self.assertIsNone(report.vitest_report(self.write("list.json", "[]"), None))
        suite = report.vitest_report(self.vitest, None)
        self.assertIsNone(suite.coverage)


class TestJunitReport(SlackTestReportTestCase):
    """Junit_report() reads every shard's JUnit XML report and the combined coverage."""

    def test_counts_every_shard(self):
        suite = report.junit_report(str(self.shards), self.python_coverage)
        self.assertEqual((suite.passed, suite.failed, suite.skipped), (2, 2, 1))
        self.assertEqual(suite.failures, ["smarter.apps.a.tests.TestA.test_two", "smarter.apps.b.tests.TestB.test_two"])
        self.assertEqual(suite.coverage, "93%")

    def test_no_reports(self):
        self.assertIsNone(report.junit_report(None, None))
        self.assertIsNone(report.junit_report(str(self.dir / "missing"), None))
        empty = self.dir / "empty"
        empty.mkdir()
        self.assertIsNone(report.junit_report(str(empty), None))

    def test_skips_an_unreadable_shard(self):
        self.write("shards/python-shard-3/test-results-shard-3.xml", "<testsuites>")
        suite = report.junit_report(str(self.shards), None)
        self.assertEqual(suite.total, 5)
        self.assertIsNone(suite.coverage)


class TestMessage(SlackTestReportTestCase):
    """The message that main() prints."""

    def test_passed(self):
        passing = self.write("passing.json", json.dumps({"testResults": [VITEST_RESULTS["testResults"][0]]}))
        text = self.run_dry(
            "--react-results",
            passing,
            "--react-coverage",
            self.vitest_coverage,
            "--python-results",
            str(self.dir / "missing"),
            "--python-passed-before",
            "--repo",
            "smarter-sh/smarter",
            "--ref",
            "alpha",
            "--actor",
            "someone",
            "--run-url",
            "https://github.com/o/r/actions/runs/1",
        )
        lines = text.splitlines()
        self.assertEqual(
            lines[0],
            ":white_check_mark: *Tests #160 passed* · <https://github.com/smarter-sh/smarter|smarter-sh/smarter> · `alpha` · someone",
        )
        self.assertEqual(lines[1], ":white_check_mark: *React*: 1 passed · 1 skipped · coverage 91.2%")
        self.assertEqual(lines[2], ":white_check_mark: *Python*: unchanged, passed in an earlier run")
        self.assertEqual(lines[3], "<https://github.com/o/r/actions/runs/1|View the run>")

    def test_failed_lists_and_escapes_the_failures(self):
        text = self.run_dry(
            "--react-result",
            "failure",
            "--react-results",
            self.vitest,
            "--python-result",
            "failure",
            "--python-results",
            str(self.shards),
            "--pr-title",
            "feat: <b>",
            "--pr-url",
            "https://github.com/o/r/pull/7",
        )
        self.assertIn(":x: *Tests #160 failed*", text)
        self.assertIn("<https://github.com/o/r/pull/7|feat: &lt;b&gt;>", text)
        self.assertIn(":x: *React*: 2 passed · *2 failed* · 1 skipped", text)
        self.assertIn("`List.test.tsx › List &lt;deletes&gt; &amp; renames`", text)
        self.assertIn(":x: *Python*: 2 passed · *2 failed* · 1 skipped", text)
        self.assertIn("`smarter.apps.b.tests.TestB.test_two`", text)

    def test_failed_job_without_a_report(self):
        text = self.run_dry("--react-result", "failure", "--slack-bot-result", "failure")
        self.assertIn(":x: *React*: failure, no test report", text)
        self.assertIn(":white_check_mark: *Python*: success, no test report", text)
        self.assertIn(":x: *Slack bot*: failure", text)

    def test_job_failed_although_every_test_passed(self):
        passing = self.write("passing.json", json.dumps({"testResults": [VITEST_RESULTS["testResults"][0]]}))
        text = self.run_dry("--react-result", "failure", "--react-results", passing)
        self.assertIn(":x: *React*: 1 passed · 1 skipped (job failure)", text)

    def test_lists_at_most_max_failures(self):
        many = {
            "testResults": [
                {
                    "name": "x.test.ts",
                    "status": "failed",
                    "assertionResults": [{"fullName": f"t{i}", "status": "failed"} for i in range(20)],
                }
            ]
        }
        text = self.run_dry("--react-result", "failure", "--react-results", self.write("many.json", json.dumps(many)))
        self.assertEqual(text.count("      • "), report.MAX_FAILURES)
        self.assertIn(f"…and {20 - report.MAX_FAILURES} more", text)

    def test_shorten(self):
        self.assertEqual(report.shorten("abc", 5), "abc")
        self.assertEqual(report.shorten("abcdef", 5), "abcd…")


if __name__ == "__main__":
    unittest.main()
