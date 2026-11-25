#!/usr/bin/env python3
"""Hash the Python lockfiles' pins, and check that none of them is too new, with PyPI's JSON API.

Usage::

    python3 -I scripts/python_lockfiles.py hash                         # every lockfile
    python3 -I scripts/python_lockfiles.py cooldown                     # 14 days
    python3 -I scripts/python_lockfiles.py cooldown --days 30
    python3 -I scripts/python_lockfiles.py cooldown --allow langchain   # a security fix that can't wait

``make python-requirements`` runs pip-compile on each ``.in`` file, then both commands. Both read
PyPI's small per-release document, ``/pypi/<name>/<version>/json``, for every pin, 16 at a time,
which takes seconds. See docs/source/smarter-platform/system-administration/security/supply-chain.rst.

``hash`` adds the sha256 of each of the release's files, its wheels and its sdist, to each pin, in
pip-compile's format, replacing any hashes the pin had. The Docker build installs the lockfiles with
``--require-hashes``, so a file replaced on PyPI, or on the way from it, fails the build.
``pip-compile --generate-hashes`` would do the same, but it reads each project's whole history
(``/pypi/<name>/json``, tens of megabytes for botocore), one package at a time, and when that fails,
downloads and hashes every wheel of the release: a lockfile took over ten minutes, and timed out.

``cooldown`` fails when a pin's release was uploaded to PyPI less than ``--days`` ago. Most malicious
releases are found and removed within days of their upload, so the wait keeps them out of Smarter.
Dependabot waits the same 14 days for the npm packages, the GitHub Actions and the Helm chart
(.github/dependabot.yml), but it doesn't manage the Python packages. pip's ``--uploaded-prior-to``
could apply the wait in pip-compile, but to every package, the project's own (``FIRST_PARTY``)
included, which Smarter often adopts on the day they are published. A pin of those, or of a package
named by ``--allow``, is never too new.

Both exit with 2 when PyPI can't be read, and then change nothing. ``cooldown`` exits with 1, and
lists them, when a pin is too new.
"""

import argparse
import concurrent.futures
import datetime
import json
import re
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS_DIR = REPOSITORY_ROOT / "smarter" / "requirements"
PYPI_URL = "https://pypi.org/pypi"
DEFAULT_DAYS = 14
TIMEOUT_SECONDS = 30
ATTEMPTS = 3
WORKERS = 16

# The files that pip installs, and so the ones hashed, as pip-compile does.
HASHED_PACKAGE_TYPES = frozenset({"bdist_wheel", "sdist"})

# The smarter-sh project's own packages on PyPI. An explicit list, not a name prefix, so that a
# look-alike package that someone else publishes as smarter-<something> still waits.
FIRST_PARTY = frozenset({"cache-results", "smarter-types"})

# name==version at the start of a line, e.g. "django==6.0.1" or "cachecontrol[filecache]==0.15.0".
PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?==([^\s;\\]+)")
HASH_LINE = re.compile(r"^\s+--hash=")


@dataclass(frozen=True)
class Pin:
    """One package pinned by a lockfile."""

    name: str
    version: str


@dataclass(frozen=True)
class Release:
    """What PyPI says about one release: when its first file was uploaded, and its files' hashes."""

    first_upload: datetime.datetime
    hashes: tuple[str, ...]


@dataclass(frozen=True)
class TooNew:
    """A pin whose release was uploaded less than the cooldown ago."""

    pin: Pin
    uploaded: datetime.datetime
    allowed_from: datetime.datetime


def normalize(name: str) -> str:
    """A package's name as PyPI compares it (PEP 503), e.g. Django_Rest.Framework becomes django-rest-framework."""
    lowered = name.lower()
    return re.sub(r"[-_.]+", "-", lowered)


def parse_pin(line: str) -> Pin | None:
    """The pin on a lockfile's line, or None when the line isn't one."""
    match = PIN.match(line)
    if match is None:
        return None
    name = normalize(match.group(1))
    return Pin(name=name, version=match.group(2))


def read_pins(lockfile: Path) -> set[Pin]:
    """The pins of one lockfile, ignoring comments, options and hashes."""
    pins = set()
    for line in lockfile.read_text(encoding="utf-8").splitlines():
        pin = parse_pin(line)
        if pin is not None:
            pins.add(pin)
    return pins


def default_lockfiles(requirements_dir: Path = REQUIREMENTS_DIR) -> list[Path]:
    """Every lockfile that pip-compile writes, smarter/requirements/*.txt."""
    return sorted(requirements_dir.glob("*.txt"))


def read_json(url: str) -> dict:
    """
    The JSON document at a url, trying up to ATTEMPTS times.

    :raises OSError: When the last attempt fails.
    """
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # nosec B310: a fixed https url
                document = json.load(response)
            return document
        except OSError:
            if attempt == ATTEMPTS:
                raise
            time.sleep(attempt)
    raise AssertionError("unreachable")


def fetch_release(pin: Pin, pypi_url: str = PYPI_URL) -> Release:
    """
    PyPI's facts about one release.

    :raises OSError: When PyPI can't be read, or doesn't have the release.
    :raises ValueError: When the release has no files that pip installs.
    """
    document = read_json(f"{pypi_url}/{pin.name}/{pin.version}/json")
    uploads = []
    hashes = []
    for file in document.get("urls", []):
        uploaded = datetime.datetime.fromisoformat(file["upload_time_iso_8601"])
        uploads.append(uploaded)
        if file["packagetype"] in HASHED_PACKAGE_TYPES:
            hashes.append("sha256:" + file["digests"]["sha256"])
    if not hashes:
        raise ValueError(f"PyPI has no wheel or sdist of {pin.name} {pin.version}")
    release = Release(first_upload=min(uploads), hashes=tuple(sorted(hashes)))
    return release


def fetch_releases(pins: set[Pin], pypi_url: str = PYPI_URL) -> dict[Pin, Release]:
    """
    Every pin's release, read WORKERS at a time.

    :raises OSError: When PyPI can't be read for one of them.
    :raises ValueError: When one has no files that pip installs.
    """
    ordered = sorted(pins, key=lambda pin: (pin.name, pin.version))
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        releases = pool.map(lambda pin: fetch_release(pin, pypi_url), ordered)
        by_pin = dict(zip(ordered, releases))
    return by_pin


def with_hashes(text: str, releases: dict[Pin, Release]) -> str:
    """
    A lockfile's text with each pin's hashes, in pip-compile's format, replacing the ones it had.

    A pin becomes ``name==version \\``, then one ``    --hash=sha256:...`` line per file, each but
    the last ending in `` \\``. The other lines (comments, options) are kept as they are.
    """
    lines = text.splitlines()
    result = []
    for line in lines:
        if HASH_LINE.match(line):
            continue
        pin = parse_pin(line)
        if pin is None:
            result.append(line)
            continue
        requirement = line.rstrip().removesuffix("\\").rstrip()
        result.append(requirement + " \\")
        hashes = releases[pin].hashes
        for index, file_hash in enumerate(hashes):
            hash_line = f"    --hash={file_hash}"
            is_last = index == len(hashes) - 1
            if not is_last:
                hash_line += " \\"
            result.append(hash_line)
    return "\n".join(result) + "\n"


def too_new(
    releases: dict[Pin, Release],
    days: int,
    allowed: set[str],
    now: datetime.datetime,
) -> list[TooNew]:
    """
    The pins whose release was uploaded less than ``days`` before ``now``, by name.

    :param allowed: Normalized names that are never too new, besides FIRST_PARTY.
    """
    exempt = FIRST_PARTY | allowed
    cooldown = datetime.timedelta(days=days)
    found = []
    for pin, release in releases.items():
        if pin.name in exempt:
            continue
        allowed_from = release.first_upload + cooldown
        if allowed_from > now:
            found.append(TooNew(pin=pin, uploaded=release.first_upload, allowed_from=allowed_from))
    found.sort(key=lambda item: item.pin.name)
    return found


def hash_command(lockfiles: list[Path], releases: dict[Pin, Release]) -> int:
    """Write each lockfile with its pins' hashes."""
    for lockfile in lockfiles:
        text = lockfile.read_text(encoding="utf-8")
        lockfile.write_text(with_hashes(text, releases), encoding="utf-8")
    print(f"Hashed {len(releases)} pins in {len(lockfiles)} lockfiles.")
    return 0


def cooldown_command(releases: dict[Pin, Release], days: int, allow: list[str], lockfile_count: int) -> int:
    """List the pins that are too new, and fail when there are any."""
    allowed = {normalize(name) for name in allow}
    now = datetime.datetime.now(datetime.timezone.utc)
    found = too_new(releases, days, allowed, now)
    if not found:
        print(f"No pin of {len(releases)} in {lockfile_count} lockfiles was uploaded in the last {days} days.")
        return 0
    print(f"These pins were uploaded to PyPI in the last {days} days:", file=sys.stderr)
    for item in found:
        uploaded = item.uploaded.date().isoformat()
        allowed_from = item.allowed_from.date().isoformat()
        print(
            f"  {item.pin.name}=={item.pin.version}  uploaded {uploaded}, allowed from {allowed_from}", file=sys.stderr
        )
    print(
        "Keep the earlier versions (e.g. a constraint in smarter/requirements/in/constraints.in), or, "
        "for a security fix, allow them: make python-requirements PYTHON_COOLDOWN_ALLOW=<package>.",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    """Read every pin's release from PyPI, then hash the lockfiles or check the cooldown."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    hash_parser = commands.add_parser("hash", help="add each pin's hashes to the lockfiles")
    cooldown_parser = commands.add_parser("cooldown", help="fail when a pin was uploaded too recently")
    cooldown_parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help=f"the default is {DEFAULT_DAYS}")
    cooldown_parser.add_argument("--allow", action="append", default=[], help="a package that may be newer")
    for command_parser in (hash_parser, cooldown_parser):
        command_parser.add_argument("lockfiles", nargs="*", type=Path, help="the default is smarter/requirements/*.txt")
        command_parser.add_argument("--pypi-url", default=PYPI_URL, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    lockfiles = args.lockfiles or default_lockfiles()
    pins: set[Pin] = set()
    for lockfile in lockfiles:
        pins |= read_pins(lockfile)
    try:
        releases = fetch_releases(pins, args.pypi_url)
    except (OSError, ValueError) as error:
        print(f"Could not read PyPI: {error}", file=sys.stderr)
        return 2

    if args.command == "hash":
        return hash_command(lockfiles, releases)
    return cooldown_command(releases, args.days, args.allow, len(lockfiles))


if __name__ == "__main__":
    sys.exit(main())
