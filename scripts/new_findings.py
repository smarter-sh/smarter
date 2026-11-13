"""Compare a linter's findings in the working tree with those at a base commit.

Smarter has a backlog of pyright errors and of functions that are too complex, so a hook that
checked whole files would fail on findings that nobody's change made. The ratchet hooks run their
tool twice, on the changed files as they are in the working tree and as they were at a base commit
(default HEAD), and fail only on what the change adds. This module holds the git side that they
share: which files changed, which of them the base has, and exporting the base's files into a
temporary folder with ``git archive``. Each hook matches its own findings without their lines,
because a change moves lines:

- ``pyright_new_errors.py``: an error by its file, rule and message.
- ``complexity_new_violations.py``: a function by its file and qualified name.

It uses only the standard library.
"""

import shutil
import subprocess  # nosec B404: runs git, with fixed arguments
import tarfile
from pathlib import Path


def git_executable() -> str:
    """
    The path of git, or its bare name when it isn't on PATH.

    :returns: The executable to run.
    """
    git = shutil.which("git")
    if git is None:
        return "git"
    return git


def changed_files(base: str, source_root: str = "") -> list[str]:
    """
    The Python files that differ from the base, or are new and not ignored.

    :param base: The commit to compare with.
    :param source_root: Only files under this folder, e.g. ``"smarter/"``. Default: every folder.
    :returns: Their paths, relative to the repository's root, sorted.
    """
    git = git_executable()
    diff = subprocess.run(  # nosec B603: fixed arguments
        [git, "diff", "--name-only", "--diff-filter=d", base], capture_output=True, text=True, check=True
    )
    untracked = subprocess.run(  # nosec B603: fixed arguments
        [git, "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True, check=True
    )
    paths = diff.stdout.splitlines() + untracked.stdout.splitlines()
    files = []
    for path in sorted(set(paths)):
        if not path.startswith(source_root):
            continue
        if not path.endswith(".py"):
            continue
        files.append(path)
    return files


def files_at_base(base: str, files: list[str]) -> list[str]:
    """
    The files that exist at the base.

    A new file has nothing to compare with.

    :param base: The commit to look in.
    :param files: The paths to look for, relative to the repository's root.
    :returns: Those that the base has, in the same order.
    """
    git = git_executable()
    existing = []
    for path in files:
        result = subprocess.run(  # nosec B603: fixed arguments
            [git, "cat-file", "-e", f"{base}:{path}"], capture_output=True, check=False
        )
        if result.returncode == 0:
            existing.append(path)
    return existing


def export_base(base: str, paths: list[str], destination: Path) -> None:
    """
    Export files or folders of the base into a folder, at the same relative paths, with ``git archive``.

    :param base: The commit to export.
    :param paths: The files or folders to export, relative to the repository's root. Each must
        exist at the base.
    :param destination: The folder to export into.
    """
    git = git_executable()
    archive_path = destination / "base.tar"
    with open(archive_path, "wb") as archive_file:
        subprocess.run(  # nosec B603: fixed arguments
            [git, "archive", base, "--", *paths], stdout=archive_file, check=True
        )
    with tarfile.open(archive_path) as archive:
        archive.extractall(destination, filter="data")
    archive_path.unlink()
