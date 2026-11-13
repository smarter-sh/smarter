#!/usr/bin/env python3
"""Report the functions that a change makes too complex, and none of those that already were.

Usage, from the repository's root::

    python3 -I scripts/complexity_new_violations.py                  # the Python files changed since HEAD
    python3 -I scripts/complexity_new_violations.py --base alpha     # ... since another commit
    python3 -I scripts/complexity_new_violations.py scripts/slack_post.py ...

The complexity is mccabe's cyclomatic complexity, which flake8 reports as C901 for a function
above ``max-complexity`` in ``.flake8``. Smarter has a backlog of functions above that limit, so
the flake8 hook leaves C901 out, and this script checks it instead. It runs flake8 with
``--select=C901`` twice on the same files: as they are in the working tree, and as they were at
``--base``, which ``git archive`` exports into a temporary folder (see ``new_findings.py``). Both
runs use the working tree's ``.flake8``, so that they have the same limit. A function is matched
by its file and qualified name (``Class.method``), not its line, because a change moves lines.

A function fails when it is above the limit now, and it was not at the base (it is new, or the
change raised it over the limit), or its complexity rose. A function of the backlog that the
change leaves as it is, or makes simpler, passes. A file that is renamed has no base to compare
with, so each of its functions above the limit counts as new.

flake8 runs with the interpreter that runs this script, which must have flake8 (``--python``
names another one). It exits with 1 when the change makes a function too complex, 0 when it
doesn't, and 2 when flake8 can't run.
"""

import argparse
import os
import re
import shutil
import subprocess  # nosec B404: runs flake8, with fixed arguments
import sys
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

SCRIPTS_FOLDER = Path(__file__).resolve().parent
# python3 -I leaves the script's own folder off sys.path, so the shared module's folder is added.
if str(SCRIPTS_FOLDER) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_FOLDER))

import new_findings  # noqa: E402  pylint: disable=wrong-import-position

FLAKE8_FORMAT = "%(path)s\t%(row)d\t%(text)s"
"""Flake8's output format: one finding per line, its fields separated by tabs."""
MESSAGE_PATTERN = re.compile(r"^'(?P<name>.+)' is too complex \((?P<complexity>\d+)\)$")
"""Mccabe's message, e.g. ``'SAMLLMClientBroker.apply' is too complex (47)``."""

FunctionKey = tuple[str, str]
"""A function, without its line: its file, relative to the root, and its qualified name."""


@dataclass(frozen=True)
class Violation:
    """A function above the complexity limit, as one flake8 run reports it."""

    path: str
    """The file, relative to the folder that flake8 ran in."""
    line: int
    """The 1-based line of the function's ``def``."""
    name: str
    """The qualified name, e.g. ``SAMLLMClientBroker.apply``."""
    complexity: int
    """Mccabe's cyclomatic complexity."""


@dataclass(frozen=True)
class NewViolation:
    """A function that the change made too complex."""

    current: Violation
    """The function in the working tree."""
    base_complexity: Optional[int]
    """Its complexity at the base, or None when it was within the limit there, or didn't exist."""


def parse_violations(output: str) -> list[Violation]:
    """
    Read the C901 findings of one flake8 run.

    :param output: flake8's output, written with ``FLAKE8_FORMAT``.
    :returns: The functions above the limit. Lines that aren't C901 findings are skipped.
    """
    violations = []
    for row in output.splitlines():
        fields = row.split("\t")
        if len(fields) != 3:
            continue
        path, line, text = fields
        match = MESSAGE_PATTERN.match(text)
        if match is None:
            continue
        normalized_path = os.path.normpath(path)
        complexity = int(match.group("complexity"))
        violation = Violation(normalized_path, int(line), match.group("name"), complexity)
        violations.append(violation)
    return violations


def group_by_function(violations: list[Violation]) -> dict[FunctionKey, list[Violation]]:
    """
    Group violations by their file and qualified name, the most complex first.

    A file can define two functions with the same qualified name, e.g. a property's getter and
    setter, or a function defined in both branches of an ``if``. They are compared in order of
    complexity: the most complex now with the most complex at the base, and so on.

    :param violations: The violations of one run.
    :returns: Each function's violations, sorted by complexity, highest first.
    """
    groups: dict[FunctionKey, list[Violation]] = defaultdict(list)
    for violation in violations:
        key = (violation.path, violation.name)
        groups[key].append(violation)
    for key, group in groups.items():
        group.sort(key=lambda violation: violation.complexity, reverse=True)
    return groups


def new_violations(current: list[Violation], base: list[Violation]) -> list[NewViolation]:
    """
    The functions that are above the limit now, and weren't at the base, or are more complex.

    :param current: The working tree's violations.
    :param base: The base's violations.
    :returns: The new violations, by file and line.
    """
    base_groups = group_by_function(base)
    current_groups = group_by_function(current)
    added = []
    for key, group in current_groups.items():
        base_group = base_groups.get(key, [])
        for index, violation in enumerate(group):
            base_complexity = None
            if index < len(base_group):
                base_complexity = base_group[index].complexity
            if base_complexity is not None and violation.complexity <= base_complexity:
                continue
            added.append(NewViolation(violation, base_complexity))
    added.sort(key=lambda new_violation: (new_violation.current.path, new_violation.current.line))
    return added


def resolved_count(current: list[Violation], base: list[Violation]) -> int:
    """
    How many of the base's functions above the limit no longer are.

    :param current: The working tree's violations.
    :param base: The base's violations.
    :returns: The count, of functions that the change made simple enough, or removed.
    """
    base_groups = group_by_function(base)
    current_groups = group_by_function(current)
    resolved = 0
    for key, base_group in base_groups.items():
        current_group = current_groups.get(key, [])
        extra = len(base_group) - len(current_group)
        if extra > 0:
            resolved += extra
    return resolved


def format_report(added: list[NewViolation], resolved: int) -> str:
    """
    Write the new violations, one per line, as ``path:line  [C901]  'name' is too complex (n, was m)``.

    :param added: The new violations.
    :param resolved: How many of the base's violations the change resolved.
    :returns: The report.
    """
    report_lines = [f"complexity: {len(added)} function(s) made too complex, {resolved} fixed."]
    for new_violation in added:
        violation = new_violation.current
        if new_violation.base_complexity is None:
            before = "within the limit, or new"
        else:
            before = str(new_violation.base_complexity)
        location = f"{violation.path}:{violation.line}"
        message = f"'{violation.name}' is too complex ({violation.complexity}, was {before})"
        report_lines.append(f"{location}  [C901]  {message}")
    report = "\n".join(report_lines)
    return report


def run_flake8(files: list[str], cwd: Path, config: Path, python: str) -> list[Violation]:
    """
    Run flake8's complexity check on files, and read its findings.

    :param files: The files, relative to ``cwd``.
    :param cwd: The folder to run in.
    :param config: The ``.flake8`` file whose ``max-complexity`` and excludes apply.
    :param python: The interpreter that has flake8.
    :returns: The functions above the limit.
    :raises RuntimeError: If flake8 doesn't run.
    """
    command = [
        python,
        "-m",
        "flake8",
        f"--config={config}",
        "--select=C901",
        f"--format={FLAKE8_FORMAT}",
        "--exit-zero",
        *files,
    ]
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)  # nosec B603
    if result.returncode != 0:
        raise RuntimeError(f"flake8 failed: {result.stderr.strip()}")
    violations = parse_violations(result.stdout)
    return violations


def compare(files: list[str], base: str, root: Path, python: str) -> tuple[str, int]:
    """
    Run the complexity check on the files in the working tree and at the base, and compare them.

    :param files: The files to check, relative to ``root``.
    :param base: The commit to compare with.
    :param root: The repository's root, which holds ``.flake8``.
    :param python: The interpreter that has flake8.
    :returns: The report, and how many functions the change made too complex.
    :raises RuntimeError: If flake8 can't run.
    """
    config = root / ".flake8"
    current = run_flake8(files, root, config, python)
    base_violations: list[Violation] = []
    with tempfile.TemporaryDirectory() as temporary_folder:
        base_root = Path(temporary_folder)
        base_files = new_findings.files_at_base(base, files)
        if base_files:
            new_findings.export_base(base, base_files, base_root)
            # A copy beside the base's files, because flake8 reads the excludes' paths relative
            # to the folder of its configuration.
            base_config = base_root / ".flake8"
            shutil.copy(config, base_config)
            base_violations = run_flake8(base_files, base_root, base_config, python)
    added = new_violations(current, base_violations)
    resolved = resolved_count(current, base_violations)
    report = format_report(added, resolved)
    return report, len(added)


def main(argv: list[str] | None = None) -> int:
    """
    Check the complexity of the working tree and the base, and print the functions the change made too complex.

    :param argv: The command line's arguments, without the program's name.
    :returns: 1 when the change makes a function too complex, 0 when it doesn't, 2 when flake8 can't run.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="*", help="Python files to check. Default: those changed since --base.")
    parser.add_argument("--base", default="HEAD", help="The commit to compare with. Default: HEAD.")
    parser.add_argument("--python", default=sys.executable, help="The interpreter that has flake8.")
    args = parser.parse_args(argv)

    root = Path.cwd()
    files = args.files or new_findings.changed_files(args.base)
    if not files:
        print("complexity: no changed Python files.")
        return 0
    try:
        report, added = compare(files, args.base, root, args.python)
    except RuntimeError as e:
        print(f"complexity: {e}", file=sys.stderr)
        return 2
    print(report)
    if added:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
