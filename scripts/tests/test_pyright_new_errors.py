"""
Tests of scripts/pyright_new_errors.py, which reports the pyright errors that a change adds.

They need only the standard library, and don't run pyright. Run them from the repository's root:

    python -m unittest discover -s scripts/tests
"""

import importlib.util
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "pyright_new_errors.py"
spec = importlib.util.spec_from_file_location("pyright_new_errors", SCRIPT_PATH)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

ROOT = Path("/repo")


def diagnostic(path: str, line: int, message: str, rule: str = "reportCallIssue", severity: str = "error") -> dict:
    """One diagnostic, as ``pyright --outputjson`` writes it, with a 0-based line."""
    return {
        "file": str(ROOT / path),
        "severity": severity,
        "message": message,
        "rule": rule,
        "range": {"start": {"line": line - 1, "character": 0}, "end": {"line": line - 1, "character": 1}},
    }


class TestPyrightNewErrors(unittest.TestCase):
    """Matching errors without their lines, and reporting only the new ones."""

    def test_key_has_no_line_and_only_the_first_message_line(self):
        """An error's key is its relative file, rule and first message line."""
        error = diagnostic("smarter/a.py", 12, 'No parameter named "x"\n  details')
        key = checker.diagnostic_key(error, ROOT)
        self.assertEqual(key, ("smarter/a.py", "reportCallIssue", 'No parameter named "x"'))

    def test_count_errors_skips_warnings_and_keeps_lines(self):
        """Warnings are left out, and each key keeps its 1-based lines."""
        output = {
            "generalDiagnostics": [
                diagnostic("smarter/a.py", 3, "boom"),
                diagnostic("smarter/a.py", 9, "boom"),
                diagnostic("smarter/a.py", 4, "meh", severity="warning"),
            ]
        }
        counts, lines = checker.count_errors(output, ROOT)
        key = ("smarter/a.py", "reportCallIssue", "boom")
        self.assertEqual(counts, Counter({key: 2}))
        self.assertEqual(lines[key], [3, 9])

    def test_moved_error_is_not_new(self):
        """An error that only moved to another line is not new."""
        base, _ = checker.count_errors({"generalDiagnostics": [diagnostic("smarter/a.py", 3, "boom")]}, ROOT)
        current, _ = checker.count_errors({"generalDiagnostics": [diagnostic("smarter/a.py", 30, "boom")]}, ROOT)
        self.assertEqual(checker.new_errors(current, base), Counter())

    def test_extra_occurrence_is_new(self):
        """A second occurrence of an existing error is new."""
        base, _ = checker.count_errors({"generalDiagnostics": [diagnostic("smarter/a.py", 3, "boom")]}, ROOT)
        output = {"generalDiagnostics": [diagnostic("smarter/a.py", 3, "boom"), diagnostic("smarter/a.py", 7, "boom")]}
        current, _ = checker.count_errors(output, ROOT)
        added = checker.new_errors(current, base)
        self.assertEqual(sum(added.values()), 1)

    def test_report_lists_every_line_of_a_new_key(self):
        """The report gives the counts, and every current line of a new error's key."""
        key = ("smarter/a.py", "reportCallIssue", "boom")
        report = checker.format_report(Counter({key: 1}), {key: [7, 3]}, fixed=2)
        self.assertEqual(report.splitlines()[0], "pyright: 1 new error(s), 2 fixed.")
        self.assertEqual(report.splitlines()[1], "smarter/a.py:3,7  [reportCallIssue]  boom")

    def test_main_exit_codes(self):
        """Main returns 1 for new errors, 0 for none, 2 when pyright can't run."""
        with mock.patch.object(checker, "compare", return_value=("report", 1)):
            self.assertEqual(checker.main(["smarter/a.py"]), 1)
        with mock.patch.object(checker, "compare", return_value=("report", 0)):
            self.assertEqual(checker.main(["smarter/a.py"]), 0)
        with mock.patch.object(checker, "compare", side_effect=RuntimeError("no npx")):
            self.assertEqual(checker.main(["smarter/a.py"]), 2)

    def test_main_without_changed_files(self):
        """Main returns 0 when nothing changed."""
        with mock.patch.object(checker, "changed_files", return_value=[]):
            self.assertEqual(checker.main([]), 0)


if __name__ == "__main__":
    unittest.main()
