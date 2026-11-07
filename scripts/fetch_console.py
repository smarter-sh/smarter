#!/usr/bin/env python3
"""Put the web console's build into Django's static folder: a pinned release, or a local build.

Usage::

    python3 -I scripts/fetch_console.py                       # the release in smarter-console-version.txt
    python3 -I scripts/fetch_console.py --version 1.2.0       # another release
    python3 -I scripts/fetch_console.py --from-dir ../smarter-console/dist

The web console is its own repository, smarter-sh/smarter-console (ADR-035). Each of its releases
attaches ``smarter-console-<version>.tar.gz``, its ``dist/`` folder: ``react/@smarter/<package>/``, the
console and the page that a deployed LLMClient's host shows. This script replaces
``smarter/smarter/static/react/`` with it, where ``collectstatic`` and the Docker build pick it up.
CI's build (build.yml), the Python tests (test.yml) and ``make console`` run it.

``--from-dir`` copies a local build instead, ``dist/`` of a smarter-console checkout after its
``make build``, to try a console change against this backend before it is released.

It exits with 1, and changes nothing, when the release can't be downloaded, or when the build has
no console page.
"""

import argparse
import io
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = REPOSITORY_ROOT / "smarter-console-version.txt"
STATIC_DIR = REPOSITORY_ROOT / "smarter" / "smarter" / "static"
RELEASES_URL = "https://github.com/smarter-sh/smarter-console/releases/download"
CONSOLE_PAGE = Path("react") / "@smarter" / "console" / "index.html"
TIMEOUT_SECONDS = 120


def pinned_version(version_file: Path = VERSION_FILE) -> str:
    """The release that this repository pins, without a leading v, e.g. 1.2.0."""
    version = version_file.read_text(encoding="utf-8").strip()
    return version.removeprefix("v")


def release_url(version: str, releases_url: str = RELEASES_URL) -> str:
    """The url of a release's tarball."""
    return f"{releases_url}/v{version}/smarter-console-{version}.tar.gz"


def download(url: str) -> bytes:
    """The bytes at a url."""
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:  # nosec B310: a fixed https url
        return response.read()


def unpack(tarball: bytes, into: Path) -> None:
    """
    Unpack a release's tarball into a folder, refusing any member outside it, links and devices.

    Python's ``data`` extraction filter does the refusing.
    """
    with tarfile.open(fileobj=io.BytesIO(tarball), mode="r:gz") as archive:
        archive.extractall(into, filter="data")


def install(build: Path, static_dir: Path = STATIC_DIR) -> Path:
    """
    Replace the static folder's react/ with a build's.

    :param build: A folder that holds react/@smarter/<package>/, e.g. smarter-console's dist/.
    :param static_dir: Django's static folder.
    :returns: The console's page, in the static folder.
    :raises FileNotFoundError: When the build has no console page, before the static folder is changed.
    """
    if not (build / CONSOLE_PAGE).is_file():
        raise FileNotFoundError(f"{build} has no {CONSOLE_PAGE}: it is not a build of smarter-console.")
    target = static_dir / "react"
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(build / "react", target)
    return static_dir / CONSOLE_PAGE


def main(argv: list[str] | None = None) -> int:
    """Put the console's build into the static folder, and say which one."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--version", help="a release, e.g. 1.2.0; the default is smarter-console-version.txt's")
    source.add_argument("--from-dir", type=Path, help="a local build, e.g. ../smarter-console/dist")
    parser.add_argument("--static-dir", type=Path, default=STATIC_DIR, help=argparse.SUPPRESS)
    parser.add_argument("--releases-url", default=RELEASES_URL, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    try:
        if args.from_dir:
            page = install(args.from_dir, args.static_dir)
            print(f"Installed the web console's local build from {args.from_dir}: {page}")
            return 0
        version = (args.version or pinned_version()).removeprefix("v")
        url = release_url(version, args.releases_url)
        tarball = download(url)
        with tempfile.TemporaryDirectory() as unpacked:
            unpack(tarball, Path(unpacked))
            page = install(Path(unpacked), args.static_dir)
        print(f"Installed the web console {version} from {url}: {page}")
        return 0
    except (OSError, tarfile.TarError) as error:
        print(f"Could not install the web console: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
