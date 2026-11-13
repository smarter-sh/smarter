"""
Tests of scripts/complexity_new_violations.py, which reports the functions that a change makes too complex.

They need only the standard library, and don't run flake8 or git. Run them from the repository's root:

    python -m unittest discover -s scripts/tests -t scripts
"""

import importlib.util
import subprocess  # nosec B404: only to build fake results
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "complexity_new_violations.py"
spec = importlib.util.spec_from_file_location("complexity_new_violations", SCRIPT_PATH)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def violation(name: str, complexity: int, line: int = 1, path: str = "smarter/a.py"):
    """One function above the limit."""
    return checker.Violation(path, line, name, complexity)


class TestParseViolations(unittest.TestCase):
    """Reading flake8's output."""

    def test_reads_name_complexity_and_line(self):
        """A C901 finding becomes a violation, with its path normalized."""
        output = "./smarter/a.py\t12\t'Broker.apply' is too complex (47)\n"
        violations = checker.parse_violations(output)
        self.assertEqual(violations, [violation("Broker.apply", 47, line=12)])

    def test_skips_other_lines(self):
        """Lines that aren't C901 findings are skipped."""
        output = "smarter/a.py\t3\tundefined name 'x'\nnot a finding\n"
        self.assertEqual(checker.parse_violations(output), [])


class TestNewViolations(unittest.TestCase):
    """Matching functions by file and name, and reporting only what the change made worse."""

    def test_unchanged_backlog_passes(self):
        """A function of the backlog that only moved is not new."""
        base = [violation("f", 15, line=3)]
        current = [violation("f", 15, line=30)]
        self.assertEqual(checker.new_violations(current, base), [])

    def test_simpler_backlog_passes(self):
        """A function of the backlog that the change made simpler, but not enough, passes."""
        self.assertEqual(checker.new_violations([violation("f", 12)], [violation("f", 15)]), [])

    def test_more_complex_backlog_fails(self):
        """A function of the backlog that the change made more complex fails, with its old complexity."""
        added = checker.new_violations([violation("f", 16)], [violation("f", 15)])
        self.assertEqual(added, [checker.NewViolation(violation("f", 16), 15)])

    def test_new_or_newly_complex_function_fails(self):
        """A function above the limit that the base didn't report fails."""
        added = checker.new_violations([violation("f", 11)], [])
        self.assertEqual(added, [checker.NewViolation(violation("f", 11), None)])

    def test_same_name_in_another_file_is_another_function(self):
        """Functions are matched by file as well as name."""
        added = checker.new_violations([violation("f", 11, path="smarter/b.py")], [violation("f", 11)])
        self.assertEqual(len(added), 1)

    def test_functions_with_the_same_name_are_paired_by_complexity(self):
        """Two functions with one name are compared most complex first, and only a new one fails."""
        base = [violation("C.x", 12, line=5)]
        current = [violation("C.x", 11, line=9), violation("C.x", 12, line=5)]
        added = checker.new_violations(current, base)
        self.assertEqual(added, [checker.NewViolation(violation("C.x", 11, line=9), None)])

    def test_resolved_count(self):
        """A function of the backlog that is gone from the run counts as fixed."""
        base = [violation("f", 15), violation("g", 12)]
        current = [violation("f", 14)]
        self.assertEqual(checker.resolved_count(current, base), 1)


class TestReport(unittest.TestCase):
    """The report's text."""

    def test_report(self):
        """The report gives the counts, and each new violation with what it was before."""
        added = [
            checker.NewViolation(violation("f", 16, line=7), 15),
            checker.NewViolation(violation("g", 11, line=20), None),
        ]
        lines = checker.format_report(added, resolved=2).splitlines()
        self.assertEqual(lines[0], "complexity: 2 function(s) made too complex, 2 fixed.")
        self.assertEqual(lines[1], "smarter/a.py:7  [C901]  'f' is too complex (16, was 15)")
        self.assertEqual(lines[2], "smarter/a.py:20  [C901]  'g' is too complex (11, was within the limit, or new)")


class TestRunFlake8(unittest.TestCase):
    """Running flake8."""

    def test_selects_only_complexity(self):
        """Flake8 runs with the configuration given, C901 only, and its output is parsed."""
        result = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="smarter/a.py\t3\t'f' is too complex (11)\n", stderr=""
        )
        with mock.patch.object(checker.subprocess, "run", return_value=result) as run:
            violations = checker.run_flake8(["smarter/a.py"], Path("/repo"), Path("/repo/.flake8"), "python")
        command = run.call_args.args[0]
        self.assertIn("--select=C901", command)
        self.assertIn("--config=/repo/.flake8", command)
        self.assertEqual(violations, [violation("f", 11, line=3)])

    def test_failure_raises(self):
        """Flake8's own failure is an error, not an empty result."""
        result = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="No module named flake8")
        with mock.patch.object(checker.subprocess, "run", return_value=result):
            with self.assertRaises(RuntimeError):
                checker.run_flake8(["smarter/a.py"], Path("/repo"), Path("/repo/.flake8"), "python")


class TestMain(unittest.TestCase):
    """The exit codes."""

    def test_main_exit_codes(self):
        """Main returns 1 for a new violation, 0 for none, 2 when flake8 can't run."""
        with mock.patch.object(checker, "compare", return_value=("report", 1)):
            self.assertEqual(checker.main(["smarter/a.py"]), 1)
        with mock.patch.object(checker, "compare", return_value=("report", 0)):
            self.assertEqual(checker.main(["smarter/a.py"]), 0)
        with mock.patch.object(checker, "compare", side_effect=RuntimeError("no flake8")):
            self.assertEqual(checker.main(["smarter/a.py"]), 2)

    def test_main_without_changed_files(self):
        """Main returns 0 when nothing changed."""
        with mock.patch.object(checker.new_findings, "changed_files", return_value=[]):
            self.assertEqual(checker.main([]), 0)


if __name__ == "__main__":
    unittest.main()
