"""
The source of the web console release that this platform installs, for tests that check the two agree.

The web console is its own repository, smarter-sh/smarter-console. ``make console`` (``scripts/fetch_console.py``)
installs the release that ``smarter-console-version.txt`` pins, and records its version in ``console/version.txt``,
under the project root. A test that checks this backend against the console's source, e.g. that the onboarding hints'
names agree, reads that release's file from GitHub at its tag.

A local build of the console (``make console-local``) has no tag, and GitHub may be out of reach: either way, the
test is skipped, with the reason, rather than failed.
"""

import unittest
import urllib.error
import urllib.request
from pathlib import Path

from django.conf import settings

CONSOLE_RAW_URL = "https://raw.githubusercontent.com/smarter-sh/smarter-console"
"""Where GitHub serves the console repository's files, by tag."""

TIMEOUT_SECONDS = 30


def installed_console_version() -> str:
    """
    The version of the installed console release, e.g. ``1.0.3``.

    :returns: The version.
    :raises unittest.SkipTest: When no console is installed, or the installed one is a local build.
    """
    version_file = Path(settings.PROJECT_ROOT) / "console" / "version.txt"
    if not version_file.is_file():
        raise unittest.SkipTest(f"{version_file} is missing: run make console.")
    version = version_file.read_text(encoding="utf-8").strip()
    if version == "local":
        raise unittest.SkipTest("The installed console is a local build, which has no release to compare with.")
    return version


def console_source_url(path: str, version: str) -> str:
    """
    The url of a file of a console release.

    :param path: The file's path in the console repository, e.g. ``packages/smarter-onboarding/src/lib/const.ts``.
    :param version: The release's version, e.g. ``1.0.3``.
    :returns: The url, at the release's tag.
    """
    return f"{CONSOLE_RAW_URL}/v{version}/{path}"


def console_source(path: str) -> str:
    """
    A file of the installed console release, from GitHub.

    :param path: The file's path in the console repository, e.g. ``packages/smarter-onboarding/src/lib/const.ts``.
    :returns: The file's text.
    :raises unittest.SkipTest: When the console isn't a release, or GitHub can't be reached.
    """
    url = console_source_url(path, installed_console_version())
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:  # nosec B310: a fixed https url
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        # the release exists, so a missing file is a real disagreement: the file moved or was renamed.
        raise AssertionError(f"{url} answered {error.code}: the console's file moved, or the test is wrong.") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise unittest.SkipTest(f"Could not read {url}: {error}") from error


__all__ = ["CONSOLE_RAW_URL", "console_source", "console_source_url", "installed_console_version"]
