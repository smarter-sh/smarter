#!/usr/bin/env python3
"""Report the pyright type errors that a change adds, and none of those that were already there.

Usage, from the repository's root::

    python3 -I scripts/pyright_new_errors.py                  # the Python files changed since HEAD
    python3 -I scripts/pyright_new_errors.py --base alpha     # ... since another commit
    python3 -I scripts/pyright_new_errors.py smarter/smarter/apps/llmclient/views.py ...

Pyright is the engine of Pylance, the type checker of VS Code. Smarter has a backlog of pyright
errors, so a check of whole files would fail on errors that nobody's change made. This script runs
pyright twice on the same files: as they are in the working tree, and as they were at ``--base``,
which ``git archive`` exports into a temporary folder. Both runs use the working tree's
``pyproject.toml``, so that they have the same rules. An error is matched by its file, rule and
message, not its line, because a change moves lines. Whatever is left in the working tree's run
is new, and is printed with its line.

It needs Node.js (pyright runs with ``npx``), and the virtual environment that has the platform's
packages (``--python``, default ``venv/bin/python``), so that pyright can resolve the imports.
It exits with 1 when the change adds an error, 0 when it doesn't, and 2 when pyright can't run.
"""

import argparse
import json
import os
import shutil
import subprocess  # nosec B404: runs git and pyright, with fixed arguments
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

PYRIGHT_VERSION = "1.1.414"
"""The pyright release, pinned so that a new release's checks don't look like new errors."""
SOURCE_ROOT = "smarter/"
"""Only Python files under this folder are checked."""

DiagnosticKey = tuple[str, str, str]
"""An error, without its line: its file, relative to the root, its rule, and its message's first line."""


def diagnostic_key(diagnostic: dict, root: Path) -> DiagnosticKey:
    """
    Identify an error of pyright's JSON output by its file, rule and message, without its line.

    :param diagnostic: One of the ``generalDiagnostics`` of ``pyright --outputjson``.
    :param root: The folder that pyright ran in, which the file's path is made relative to.
    :returns: The key, e.g. ``("smarter/smarter/apps/x.py", "reportCallIssue", "No parameter named ...")``.
    """
    file_path = Path(diagnostic["file"]).resolve()
    relative_path = os.path.relpath(file_path, root.resolve())
    rule = diagnostic.get("rule", "")
    message_lines = diagnostic["message"].splitlines()
    first_line = message_lines[0] if message_lines else ""
    return (relative_path, rule, first_line)


def count_errors(output: dict, root: Path) -> tuple[Counter, dict[DiagnosticKey, list[int]]]:
    """
    Count the errors of one pyright run, by key, and find their lines.

    :param output: The parsed output of ``pyright --outputjson``.
    :param root: The folder that pyright ran in.
    :returns: How many times each key occurs, and the 1-based lines where it occurs.
    """
    counts: Counter = Counter()
    lines: dict[DiagnosticKey, list[int]] = defaultdict(list)
    for diagnostic in output.get("generalDiagnostics", []):
        if diagnostic.get("severity") != "error":
            continue
        key = diagnostic_key(diagnostic, root)
        counts[key] += 1
        line = diagnostic["range"]["start"]["line"] + 1
        lines[key].append(line)
    return counts, lines


def new_errors(current: Counter, base: Counter) -> Counter:
    """
    The errors that the working tree has more of than the base.

    :param current: The working tree's errors, by key.
    :param base: The base's errors, by key.
    :returns: Each key that occurs more often now, with how many more times.
    """
    added = current - base
    return added


def format_report(added: Counter, lines: dict[DiagnosticKey, list[int]], fixed: int) -> str:
    """
    Write the new errors, one per line, as ``path:line  [rule]  message``.

    When a key occurs more often than before, every line where it occurs now is listed, because
    the run can't tell which of them is the new one.

    :param added: The new errors, by key.
    :param lines: The working tree's lines of each key.
    :param fixed: How many of the base's errors the change removed.
    :returns: The report.
    """
    report_lines = []
    total = sum(added.values())
    report_lines.append(f"pyright: {total} new error(s), {fixed} fixed.")
    for key in sorted(added):
        path, rule, message = key
        where = ",".join(str(line) for line in sorted(lines[key]))
        report_lines.append(f"{path}:{where}  [{rule}]  {message}")
    report = "\n".join(report_lines)
    return report


def changed_files(base: str) -> list[str]:
    """
    The Python files under ``smarter/`` that differ from the base, or are new and not ignored.

    :param base: The commit to compare with.
    :returns: Their paths, relative to the repository's root.
    """
    git = shutil.which("git") or "git"
    diff = subprocess.run(  # nosec B603: fixed arguments
        [git, "diff", "--name-only", "--diff-filter=d", base], capture_output=True, text=True, check=True
    )
    untracked = subprocess.run(  # nosec B603: fixed arguments
        [git, "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, check=True
    )
    paths = diff.stdout.splitlines() + untracked.stdout.splitlines()
    files = []
    for path in sorted(set(paths)):
        if not path.startswith(SOURCE_ROOT):
            continue
        if not path.endswith(".py"):
            continue
        files.append(path)
    return files


def export_base(base: str, files: list[str], destination: Path) -> list[str]:
    """
    Export the base's source tree into a folder, with ``git archive``.

    The whole of ``smarter/`` is exported, not only the files, so that pyright resolves their
    imports of unchanged modules exactly as it does in the working tree.

    :param base: The commit to export.
    :param files: The files to check. New files, which the base doesn't have, are skipped.
    :param destination: The folder to export into.
    :returns: The files that the base has.
    """
    git = shutil.which("git") or "git"
    existing = []
    for path in files:
        result = subprocess.run(  # nosec B603: fixed arguments
            [git, "cat-file", "-e", f"{base}:{path}"], capture_output=True, check=False
        )
        if result.returncode == 0:
            existing.append(path)
    if not existing:
        return existing
    archive_path = destination / "base.tar"
    with open(archive_path, "wb") as archive_file:
        subprocess.run(  # nosec B603: fixed arguments
            [git, "archive", base, "--", SOURCE_ROOT], stdout=archive_file, check=True
        )
    with tarfile.open(archive_path) as archive:
        archive.extractall(destination, filter="data")
    archive_path.unlink()
    return existing


def run_pyright(files: list[str], cwd: Path, python: Path) -> dict:
    """
    Run pyright on files, and parse its JSON output.

    :param files: The files, relative to ``cwd``.
    :param cwd: The folder to run in, which holds the ``pyproject.toml`` with the rules.
    :param python: The interpreter whose packages pyright resolves imports from.
    :returns: The parsed output.
    :raises RuntimeError: If pyright doesn't run, or prints no JSON.
    """
    npx = shutil.which("npx")
    if npx is None:
        raise RuntimeError("npx was not found: pyright needs Node.js.")
    command = [npx, "-y", f"pyright@{PYRIGHT_VERSION}", "--pythonpath", str(python), "--outputjson", *files]
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)  # nosec B603
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"pyright printed no JSON: {result.stderr.strip()}") from e
    return output


def main(argv: list[str] | None = None) -> int:
    """
    Run pyright on the working tree and the base, and print the errors that the change adds.

    :param argv: The command line's arguments, without the program's name.
    :returns: 1 when the change adds an error, 0 when it doesn't, 2 when pyright can't run.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", help="Python files to check. Default: those changed since --base.")
    parser.add_argument("--base", default="HEAD", help="The commit to compare with. Default: HEAD.")
    parser.add_argument("--python", default="venv/bin/python", help="The interpreter with the platform's packages.")
    args = parser.parse_args(argv)

    root = Path.cwd()
    # Absolute, but not resolved: venv/bin/python is a symlink, and the system interpreter it
    # points to doesn't have the virtual environment's packages.
    python = root / args.python
    files = args.files or changed_files(args.base)
    if not files:
        print("pyright: no changed Python files.")
        return 0
    try:
        report, added = compare(files, args.base, root, python)
    except RuntimeError as e:
        print(f"pyright: {e}", file=sys.stderr)
        return 2
    print(report)
    if added:
        return 1
    return 0


def compare(files: list[str], base: str, root: Path, python: Path) -> tuple[str, int]:
    """
    Run pyright on the files in the working tree and at the base, and compare the errors.

    :param files: The files to check, relative to ``root``.
    :param base: The commit to compare with.
    :param root: The repository's root.
    :param python: The interpreter whose packages pyright resolves imports from.
    :returns: The report, and how many errors the change adds.
    :raises RuntimeError: If pyright can't run.
    """
    with tempfile.TemporaryDirectory() as temporary_folder:
        base_root = Path(temporary_folder)
        base_files = export_base(base, files, base_root)
        shutil.copy(root / "pyproject.toml", base_root / "pyproject.toml")
        current_output = run_pyright(files, root, python)
        base_output: dict = {}
        if base_files:
            base_output = run_pyright(base_files, base_root, python)
        current, lines = count_errors(current_output, root)
        base_counts, _ = count_errors(base_output, base_root)
    added = new_errors(current, base_counts)
    fixed = sum((base_counts - current).values())
    report = format_report(added, lines, fixed)
    added_count = sum(added.values())
    return report, added_count


if __name__ == "__main__":
    sys.exit(main())
