"""
Tests of scripts/suite_fingerprints.py, which tells the Tests workflow which suites a change touches.

They need only the standard library. git is faked, except in the last test, which reads this
repository's own HEAD. Run them from the repository's root:

    python -m unittest discover -s scripts/tests -t scripts
"""

import importlib.util
import io
import subprocess  # nosec B404: the tests fake git's failure, and read this repository's HEAD
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "suite_fingerprints.py"
spec = importlib.util.spec_from_file_location("suite_fingerprints", SCRIPT_PATH)
fingerprints = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fingerprints)


def entry(path: str, blob: str = "a" * 40) -> str:
    """One file, as ``git ls-tree -r`` prints it."""
    return f"100644 blob {blob}\t{path}"


BASE = [
    entry("README.md"),
    entry("changelogs/CHANGELOG.md"),
    entry("docs/source/index.rst"),
    entry("helm/charts/smarter/values.yaml"),
    entry("smarter/react/packages/smarter-chat/package.json"),
    entry("smarter/react/packages/smarter-chat/src/App.tsx"),
    entry("smarter/smarter/urls.py"),
]
"""The base branch's files."""


def changed(entries: list[str], path: str) -> list[str]:
    """The same files, with one of them changed."""
    result = []
    for line in entries:
        if line.endswith("\t" + path):
            line = entry(path, "b" * 40)
        result.append(line)
    return result


def outputs_of(head: list[str], base: list[str] | None) -> dict[str, str]:
    """The script's output, as a dict."""
    result = {}
    for line in fingerprints.outputs(head, base):
        key, value = line.split("=", 1)
        result[key] = value
    return result


class TestPathMatches(unittest.TestCase):
    """Files, folders and globs, as git's pathspecs match them."""

    def test_file(self):
        """A file matches only itself."""
        self.assertTrue(fingerprints.path_matches("README.md", "README.md"))
        self.assertFalse(fingerprints.path_matches("docs/README.md", "README.md"))

    def test_folder(self):
        """A folder matches everything in it, and not a sibling whose name starts the same."""
        self.assertTrue(fingerprints.path_matches("smarter/smarter/apps/x.py", "smarter/smarter"))
        self.assertFalse(fingerprints.path_matches("smarter/smarter-extra/x.py", "smarter/smarter"))

    def test_glob(self):
        """A glob's * matches one package's folder."""
        pattern = "smarter/react/packages/*/package.json"
        self.assertTrue(fingerprints.path_matches("smarter/react/packages/chat/package.json", pattern))
        self.assertFalse(fingerprints.path_matches("smarter/react/package.json", pattern))


class TestOutputs(unittest.TestCase):
    """Which suites a change touches."""

    def test_no_base_means_changed(self):
        """Without a base, every suite runs."""
        result = outputs_of(BASE, None)
        self.assertEqual(result["python-changed"], "true")
        self.assertEqual(result["react-changed"], "true")

    def test_same_files(self):
        """A change that touches neither suite's files runs neither."""
        head = changed(BASE, "helm/charts/smarter/values.yaml")
        head = changed(head, "docs/source/index.rst")
        result = outputs_of(head, BASE)
        self.assertEqual(result["python-changed"], "false")
        self.assertEqual(result["react-changed"], "false")

    def test_changelog_is_not_a_python_file(self):
        """A release's change log doesn't run the Python suite."""
        head = changed(BASE, "changelogs/CHANGELOG.md")
        result = outputs_of(head, BASE)
        self.assertEqual(result["python-changed"], "false")

    def test_python_change(self):
        """A change to the Django code runs only the Python suite."""
        head = changed(BASE, "smarter/smarter/urls.py")
        result = outputs_of(head, BASE)
        self.assertEqual(result["python-changed"], "true")
        self.assertEqual(result["react-changed"], "false")

    def test_react_change(self):
        """A change to a React app's source runs only the React suite."""
        head = changed(BASE, "smarter/react/packages/smarter-chat/src/App.tsx")
        result = outputs_of(head, BASE)
        self.assertEqual(result["python-changed"], "false")
        self.assertEqual(result["react-changed"], "true")

    def test_react_file_that_python_reads(self):
        """A package.json names built pages that the console loads, so it runs both suites."""
        head = changed(BASE, "smarter/react/packages/smarter-chat/package.json")
        result = outputs_of(head, BASE)
        self.assertEqual(result["python-changed"], "true")
        self.assertEqual(result["react-changed"], "true")

    def test_added_and_removed_files(self):
        """Adding or removing a suite's file changes it."""
        added = BASE + [entry("smarter/smarter/new.py")]
        self.assertEqual(outputs_of(added, BASE)["python-changed"], "true")
        removed = BASE[:-1]
        self.assertEqual(outputs_of(removed, BASE)["python-changed"], "true")

    def test_key_depends_only_on_the_suites_files(self):
        """The pass marker's key is the same for two commits whose suite files are the same."""
        head = changed(BASE, "docs/source/index.rst")
        self.assertEqual(outputs_of(head, None)["python-key"], outputs_of(BASE, None)["python-key"])
        self.assertTrue(outputs_of(BASE, None)["python-key"].startswith("tests-passed-python-"))


class TestMain(unittest.TestCase):
    """The command line."""

    def test_unreadable_base_runs_everything(self):
        """When git can't read the base, every suite counts as changed."""

        def fake_tree_entries(revision: str) -> list[str]:
            if revision == "HEAD":
                return BASE
            raise subprocess.CalledProcessError(128, ["git"], stderr="fatal: bad revision")

        stdout = io.StringIO()
        with mock.patch.object(fingerprints, "tree_entries", side_effect=fake_tree_entries):
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                exit_code = fingerprints.main(["--base", "HEAD^1"])
        self.assertEqual(exit_code, 0)
        self.assertIn("python-changed=true", stdout.getvalue())
        self.assertIn("react-changed=true", stdout.getvalue())

    def test_this_repository(self):
        """HEAD compared with itself changes nothing."""
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            fingerprints.main(["--base", "HEAD"])
        self.assertIn("python-changed=false", stdout.getvalue())
        self.assertIn("react-changed=false", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
