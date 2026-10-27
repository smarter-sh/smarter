"""
Keep a cached Sphinx build usable on a fresh git checkout.

Sphinx decides which pages to read and write again by comparing modification times: a page is
read again when its source, or a file it depends on (e.g. a Python module that autodoc
documents), is newer than the cached build. A fresh checkout gives every file the time of the
checkout, so a cached build restored on a CI runner would be thrown away. Commit times are no
substitute, because a merge can bring in a change whose commit is older than the cached build.

So this script works from content. ``save`` records the git blob id of every tracked file next
to the build. ``restore`` sets every tracked file whose blob id hasn't changed since then to an
old, fixed time, so that only the files that did change are newer than the build.

Usage, from the repository's root::

    python scripts/sphinx_cache_mtimes.py restore docs/build/source-blobs.json   # before the build
    python scripts/sphinx_cache_mtimes.py save docs/build/source-blobs.json      # after it succeeds
"""

import argparse
import json
import os
import subprocess  # nosec B404: runs git with fixed arguments
import sys

# 2000-01-01T00:00:00Z: older than any build, so an unchanged file never looks changed.
UNCHANGED_MTIME = 946684800

# Regular files and executables. Symlinks (120000) and submodules (160000) are skipped.
REGULAR_FILE_MODES = ("100644", "100755")


def tracked_blobs() -> dict[str, str]:
    """
    The git blob id of every tracked regular file, as it is in the index.

    :returns: a mapping of each file's path, relative to the repository's root, to its blob id.
    """
    output = subprocess.run(  # nosec B603 B607: fixed git command
        ["git", "ls-files", "--stage", "-z"], check=True, capture_output=True
    ).stdout.decode("utf-8")
    blobs = {}
    for entry in output.split("\0"):
        if not entry:
            continue
        meta, path = entry.split("\t", 1)
        mode, blob, _stage = meta.split(" ")
        if mode in REGULAR_FILE_MODES:
            blobs[path] = blob
    return blobs


def save(manifest: str) -> int:
    """
    Record the blob id of every tracked file in ``manifest``.

    :param manifest: the JSON file to write.
    :returns: the number of files recorded.
    """
    blobs = tracked_blobs()
    directory = os.path.dirname(manifest)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(manifest, "w", encoding="utf-8") as f:
        json.dump(blobs, f, separators=(",", ":"), sort_keys=True)
    return len(blobs)


def restore(manifest: str) -> tuple[int, int]:
    """
    Set every tracked file that hasn't changed since ``manifest`` was saved to an old, fixed time.

    Files that changed, or are new, keep the time of the checkout. Without a manifest, e.g. on
    the first build, nothing is changed and Sphinx builds everything.

    :param manifest: the JSON file that :func:`save` wrote.
    :returns: the number of unchanged files, and of changed or new files.
    """
    try:
        with open(manifest, encoding="utf-8") as f:
            saved = json.load(f)
    except FileNotFoundError:
        return 0, 0
    unchanged = changed = 0
    for path, blob in tracked_blobs().items():
        if saved.get(path) == blob and os.path.isfile(path):
            os.utime(path, (UNCHANGED_MTIME, UNCHANGED_MTIME))
            unchanged += 1
        else:
            changed += 1
    return unchanged, changed


def main(argv: list[str] | None = None) -> int:
    """
    Run the ``save`` or ``restore`` command.

    :param argv: the command line arguments, without the program's name.
    :returns: the exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("command", choices=("save", "restore"))
    parser.add_argument("manifest", help="the JSON file of blob ids, e.g. docs/build/source-blobs.json")
    args = parser.parse_args(argv)

    if args.command == "save":
        print(f"Recorded the blob ids of {save(args.manifest)} tracked files in {args.manifest}.")
    else:
        unchanged, changed = restore(args.manifest)
        if unchanged == changed == 0:
            print(f"No {args.manifest}: Sphinx will build every page.")
        else:
            print(f"{unchanged} tracked files are unchanged since the cached build, and {changed} changed or are new.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
