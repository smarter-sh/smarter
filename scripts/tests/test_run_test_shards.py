"""Tests of scripts/run_test_shards.py: its names, its commands, and how it reads a shard's output."""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_test_shards  # noqa: E402  pylint: disable=wrong-import-position

PASSING_LOG = """\
[2026-11-08 00:01:16 +0000] - INFO - MainProcess - smarter.settings.base ...
......s.....
----------------------------------------------------------------------
Ran 812 tests in 1204.551s

OK (skipped=26)
"""

FAILING_LOG = """\
\x1b[1;31m[2026-11-08] ERROR something logged\x1b[0m
======================================================================
FAIL: test_detail (smarter.apps.prompt.tests.test_views.TestWorkbench.test_detail)
----------------------------------------------------------------------
Traceback (most recent call last):
AssertionError: 404 != 200
======================================================================
ERROR: test_list (smarter.apps.secret.tests.test_views.TestSecretViews.test_list)
----------------------------------------------------------------------
Traceback (most recent call last):
RuntimeError: boom
----------------------------------------------------------------------
Ran 790 tests in 1100.2s

FAILED (failures=1, errors=1, skipped=3)
"""


class TestNames(unittest.TestCase):
    """Each shard has a Compose project of its own, and Compose names its containers after it."""

    def test_project_and_container(self):
        self.assertEqual(run_test_shards.project(3), "smarter-shard-3")
        self.assertEqual(run_test_shards.container(3, "smarter-api"), "smarter-shard-3-smarter-api-1")

    def test_compose_names_the_project_and_the_shard_file(self):
        command = run_test_shards.compose(2, "up", "-d")
        self.assertEqual(command[:4], ["docker", "compose", "-p", "smarter-shard-2"])
        self.assertEqual(command[4:6], ["-f", str(run_test_shards.COMPOSE_FILE)])
        self.assertEqual(command[6:], ["up", "-d"])
        self.assertTrue(run_test_shards.COMPOSE_FILE.is_file())

    def test_test_command_runs_one_shard_in_its_api(self):
        command = run_test_shards.test_command(3, 8, ["smarter.apps.account", "smarter.apps.secret"])
        self.assertEqual(command[:4], ["docker", "exec", "-e", "SMARTER_TEST_SHARD=3/8"])
        self.assertEqual(command[4], "smarter-shard-3-smarter-api-1")
        self.assertIn("python manage.py test smarter.apps.account smarter.apps.secret --noinput", command[-1])


class TestParseLog(unittest.TestCase):
    """A shard's result comes from the runner's last lines, and its failures from FAIL: and ERROR: lines."""

    def test_passing(self):
        result = run_test_shards.parse_log(1, PASSING_LOG)
        self.assertEqual(result.ran, 812)
        self.assertTrue(result.ok)
        self.assertEqual(result.summary, "OK (skipped=26)")
        self.assertEqual(result.failures, [])

    def test_failing_with_colors(self):
        result = run_test_shards.parse_log(2, FAILING_LOG)
        self.assertEqual(result.ran, 790)
        self.assertFalse(result.ok)
        self.assertEqual(result.summary, "FAILED (failures=1, errors=1, skipped=3)")
        self.assertEqual(
            result.failures,
            [
                "FAIL: test_detail (smarter.apps.prompt.tests.test_views.TestWorkbench.test_detail)",
                "ERROR: test_list (smarter.apps.secret.tests.test_views.TestSecretViews.test_list)",
            ],
        )

    def test_a_shard_that_never_finished_has_failed(self):
        """E.g.

        a container killed for running out of memory: no Ran line, so no result.
        """
        result = run_test_shards.parse_log(3, "......\nKilled\n")
        self.assertIsNone(result.ran)
        self.assertFalse(result.ok)
        self.assertEqual(result.summary, "no result")


class TestReport(unittest.TestCase):
    """The report lists each shard, the total, and every failing test."""

    def test_report(self):
        results = [run_test_shards.parse_log(1, PASSING_LOG), run_test_shards.parse_log(2, FAILING_LOG)]
        output = io.StringIO()
        with redirect_stdout(output):
            passed = run_test_shards.report(results, Path("test-shards"))
        self.assertFalse(passed)
        text = output.getvalue()
        self.assertIn("shard 1: ran 812 tests, OK (skipped=26)", text)
        self.assertIn("1602 tests in 2 shards: FAILED", text)
        self.assertIn("FAIL: test_detail", text)


class TestMain(unittest.TestCase):
    """Main() stops every stack it started, and fails when a step fails."""

    def test_stops_the_stacks_after_a_failed_start(self):
        with tempfile.TemporaryDirectory() as out:
            with (
                patch.object(run_test_shards, "dump_database", return_value=Path(out) / "dump.sql"),
                patch.object(run_test_shards, "start_shard", side_effect=RuntimeError("no memory")),
                patch.object(run_test_shards, "stop_shard") as stop,
                redirect_stdout(io.StringIO()),
                patch("sys.stderr", new_callable=io.StringIO),
            ):
                status = run_test_shards.main(["--shards", "2", "--out", out])
        self.assertEqual(status, 1)
        self.assertEqual(sorted(call.args[0] for call in stop.call_args_list), [1, 2])

    def test_keep_leaves_the_stacks_running(self):
        result = run_test_shards.parse_log(1, PASSING_LOG)
        with tempfile.TemporaryDirectory() as out:
            with (
                patch.object(run_test_shards, "dump_database", return_value=Path(out) / "dump.sql"),
                patch.object(run_test_shards, "start_shard"),
                patch.object(run_test_shards, "run_shard", return_value=result),
                patch.object(run_test_shards, "stop_shard") as stop,
                redirect_stdout(io.StringIO()),
            ):
                status = run_test_shards.main(["--shards", "1", "--out", out, "--keep"])
        self.assertEqual(status, 0)
        stop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
