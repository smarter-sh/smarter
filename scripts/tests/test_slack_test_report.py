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

    def passing_shard(self) -> str:
        """A directory with one shard whose tests all passed, or were skipped."""
        shard = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites><testsuite name="a" tests="2">
  <testcase classname="smarter.apps.a.tests.TestA" name="test_one"/>
  <testcase classname="smarter.apps.a.tests.TestA" name="test_two"><skipped message="infrastructure"/></testcase>
</testsuite></testsuites>
"""
        self.write("passing/python-shard-1/test-results-shard-1.xml", shard)
        return str(self.dir / "passing")

    def test_passed(self):
        text = self.run_dry(
            "--python-results",
            self.passing_shard(),
            "--python-coverage",
            self.python_coverage,
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
        self.assertEqual(lines[1], ":white_check_mark: *Python*: 1 passed · 1 skipped · coverage 93%")
        self.assertEqual(lines[2], "<https://github.com/o/r/actions/runs/1|View the run>")
        self.assertNotIn("React", text)

    def test_unchanged(self):
        text = self.run_dry("--python-result", "skipped", "--python-passed-before")
        self.assertIn(":white_check_mark: *Tests #160 passed*", text)
        self.assertIn(":white_check_mark: *Python*: unchanged, not tested again", text)

    def test_failed_lists_and_escapes_the_failures(self):
        self.write(
            "shards/python-shard-3/test-results-shard-3.xml",
            '<testsuites><testsuite name="c"><testcase classname="smarter.apps.c" name="test_&lt;b&gt; &amp; c">'
            '<failure message="no"/></testcase></testsuite></testsuites>',
        )
        text = self.run_dry(
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
        self.assertIn(":x: *Python*: 2 passed · *3 failed* · 1 skipped", text)
        self.assertIn("`smarter.apps.b.tests.TestB.test_two`", text)
        self.assertIn("`smarter.apps.c.test_&lt;b&gt; &amp; c`", text)

    def test_failed_job_without_a_report(self):
        text = self.run_dry("--python-result", "failure", "--slack-bot-result", "failure")
        self.assertIn(":x: *Python*: failure, no test report", text)
        self.assertIn(":x: *Slack bot*: failure", text)

    def test_slack_bot_failure_fails_the_run(self):
        text = self.run_dry("--slack-bot-result", "failure")
        self.assertIn(":x: *Tests #160 failed*", text)
        self.assertIn(":white_check_mark: *Python*: success, no test report", text)

    def test_job_failed_although_every_test_passed(self):
        text = self.run_dry("--python-result", "failure", "--python-results", self.passing_shard())
        self.assertIn(":x: *Python*: 1 passed · 1 skipped (job failure)", text)

    def test_lists_at_most_max_failures(self):
        cases = "".join(
            f'<testcase classname="smarter.x" name="t{i}"><failure message="no"/></testcase>' for i in range(20)
        )
        self.write(
            "many/python-shard-1/test-results-shard-1.xml", f"<testsuites><testsuite>{cases}</testsuite></testsuites>"
        )
        text = self.run_dry("--python-result", "failure", "--python-results", str(self.dir / "many"))
        self.assertEqual(text.count("      • "), report.MAX_FAILURES)
        self.assertIn(f"…and {20 - report.MAX_FAILURES} more", text)

    def test_shorten(self):
        self.assertEqual(report.shorten("abc", 5), "abc")
        self.assertEqual(report.shorten("abcdef", 5), "abcd…")


if __name__ == "__main__":
    unittest.main()
