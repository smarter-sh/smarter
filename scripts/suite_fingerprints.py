#!/usr/bin/env python3
"""Fingerprint the files that each test suite depends on, and say whether a pull request changed them.

Usage, from the repository's root::

    python3 -I scripts/suite_fingerprints.py                      # fingerprints of HEAD
    python3 -I scripts/suite_fingerprints.py --base HEAD^1        # ... and whether they differ from HEAD^1

It prints ``key=value`` lines for ``$GITHUB_OUTPUT``, one pair per suite::

    python-key=tests-passed-python-<sha256>
    python-changed=true

The Tests workflow (.github/workflows/test.yml) skips a suite when ``<suite>-changed`` is
``false``: the pull request leaves every file the suite depends on as the base branch has it, and
the base branch's files passed the suite before they were merged. It also skips a suite when
``<suite>-key`` names a pass marker that an earlier run of the same pull request saved.

A suite's fingerprint is a hash of the mode, blob id and path of each of its files, as
``git ls-tree -r`` lists them, so it changes when, and only when, one of them is added, removed or
changed. Without ``--base``, or when the base can't be read, every suite counts as changed, so
that the tests run.

It needs only the standard library, and git.
"""

import argparse
import fnmatch
import hashlib
import subprocess  # nosec B404: runs git, with fixed arguments
import sys

SUITES: dict[str, tuple[str, ...]] = {
    "python": (
        "smarter/smarter",
        "smarter/manage.py",
        "smarter/requirements",
        "smarter/.coveragerc",
        # The few files in smarter/react that the Python tests read: the console's messages
        # (update_console_messages), the onboarding app's constants (test_onboarding), and the
        # files that name the built pages that the console's templates load.
        "smarter/react/i18n",
        "smarter/react/packages/smarter-onboarding/src/lib/const.ts",
        "smarter/react/packages/*/package.json",
        "smarter/react/packages/*/vite.config.ts",
        # The markdown pages that the docs app serves. changelogs/CHANGELOG.md is left out:
        # every release rewrites it, its test checks only that the page loads, and with it every
        # pull request from alpha to main would run the whole suite again.
        "README.md",
        "CODE_OF_CONDUCT.md",
        # What builds the platform that the tests run in.
        "Dockerfile",
        ".dockerignore",
        "docker-compose.yml",
        "Makefile",
        ".env.example",
        "package.json",
        ".github/workflows/test.yml",
        ".github/actions/react-build",
        "scripts/suite_fingerprints.py",
    ),
    # smarter/react is self-contained: its tests read nothing outside it.
    "react": (
        "smarter/react",
        ".github/workflows/test.yml",
        "scripts/suite_fingerprints.py",
    ),
}
"""Each suite's files: a file, a folder (with everything in it), or a glob whose ``*`` may match ``/``, as in git's pathspecs."""

GLOB_CHARACTERS = "*?["
"""A pattern that contains one of these is a glob."""


def path_matches(path: str, pattern: str) -> bool:
    """
    Whether a file's path is one of a pattern's files.

    :param path: A path relative to the repository's root, e.g. ``smarter/smarter/urls.py``.
    :param pattern: A file, a folder, or a glob, e.g. ``smarter/react/packages/*/package.json``.
    :returns: True when the path is the file, is in the folder, or matches the glob.
    """
    is_glob = False
    for character in GLOB_CHARACTERS:
        if character in pattern:
            is_glob = True
    if is_glob:
        return fnmatch.fnmatchcase(path, pattern)
    if path == pattern:
        return True
    folder = pattern + "/"
    return path.startswith(folder)


def tree_entries(revision: str) -> list[str]:
    """
    List every file of a commit, as ``git ls-tree -r`` prints it.

    :param revision: A commit, e.g. ``HEAD`` or ``HEAD^1``.
    :returns: One line per file: its mode, type, blob id, a tab, and its path.
    :raises subprocess.CalledProcessError: when git can't read the commit.
    """
    command = ["git", "ls-tree", "-r", "--full-tree", revision]
    result = subprocess.run(command, capture_output=True, text=True, check=True)  # nosec B603
    return result.stdout.splitlines()


def fingerprint(entries: list[str], patterns: tuple[str, ...]) -> str:
    """
    Hash the entries of a suite's files.

    :param entries: A commit's files, from :func:`tree_entries`.
    :param patterns: The suite's files, from :data:`SUITES`.
    :returns: The sha256 hex digest of the suite's entries, in git's order.
    """
    digest = hashlib.sha256()
    for entry in entries:
        path = entry.split("\t", 1)[1]
        for pattern in patterns:
            if path_matches(path, pattern):
                digest.update(entry.encode("utf-8"))
                digest.update(b"\n")
                break
    return digest.hexdigest()


def outputs(head_entries: list[str], base_entries: list[str] | None) -> list[str]:
    """
    Build the ``key=value`` lines for ``$GITHUB_OUTPUT``.

    :param head_entries: The files of the commit under test.
    :param base_entries: The files of the base branch's commit, or None when there is none.
    :returns: ``<suite>-key`` and ``<suite>-changed`` for each suite.
    """
    lines = []
    for suite, patterns in SUITES.items():
        head_fingerprint = fingerprint(head_entries, patterns)
        changed = True
        if base_entries is not None:
            base_fingerprint = fingerprint(base_entries, patterns)
            changed = head_fingerprint != base_fingerprint
        lines.append(f"{suite}-key=tests-passed-{suite}-{head_fingerprint}")
        lines.append(f"{suite}-changed={str(changed).lower()}")
    return lines


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """
    Parse the command line.

    :param argv: The arguments, without the program's name. None reads ``sys.argv``.
    :returns: The parsed arguments.
    """
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--head", default="HEAD", help="The commit under test (default: HEAD).")
    parser.add_argument("--base", default="", help="The base branch's commit to compare with, e.g. HEAD^1.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """
    Print each suite's fingerprint, and whether it changed from the base.

    :param argv: The arguments, without the program's name. None reads ``sys.argv``.
    :returns: The exit code: 0, or git's failure to read the commit under test.
    """
    args = parse_args(argv)
    head_entries = tree_entries(args.head)
    base_entries = None
    if args.base:
        try:
            base_entries = tree_entries(args.base)
        except subprocess.CalledProcessError as error:
            print(f"suite_fingerprints: can't read {args.base}, so every suite runs: {error.stderr}", file=sys.stderr)
    for line in outputs(head_entries, base_entries):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
