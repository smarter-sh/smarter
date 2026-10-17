"""
Smarter.common.utils.repository
===============================

Utility functions for finding the source code repository of the running platform.

A fork of Smarter has its own repository, its own CI workflows and
their badges, so the web console links to the repository that this codebase was
cloned from, which ``git remote -v`` reports. The Docker image has no ``.git``
directory, so a platform that runs in a container falls back to
:data:`~smarter.common.const.SMARTER_PROJECT_REPOSITORY_URL`.

Functions
---------
- get_repository_url: Returns the https url of the repository, without credentials.
- parse_git_remotes: Returns the url of a repository from the output of ``git remote -v``.
"""

import re
import subprocess  # nosec B404
from functools import cache
from typing import Optional
from urllib.parse import urlparse, urlunparse

from smarter.common.const import REPO_ROOT, SMARTER_PROJECT_REPOSITORY_URL
from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

GIT_TIMEOUT = 2  # seconds. git answers instantly, or not at all.

# git@github.com:smarter-sh/smarter.git
SCP_LIKE_REMOTE = re.compile(r"^(?:[\w.-]+@)?(?P<host>[\w.-]+):(?P<path>(?!//)[^\s]+)$")


def normalize_remote_url(remote: str) -> Optional[str]:
    """
    Return the https url of a git remote, or None if it isn't one that a browser can open.

    Converts ssh remotes (``git@github.com:org/repo.git``, ``ssh://git@github.com/org/repo``)
    to https, on any host, and removes credentials, an ssh port, a trailing ``.git`` and a
    trailing slash, so that a token embedded in the remote never reaches the browser.

    :param remote: The url of a git remote.
    :type remote: str
    :returns: The https url of the repository, or None.
    :rtype: Optional[str]
    """
    remote = remote.strip()
    match = SCP_LIKE_REMOTE.match(remote)
    if match and "://" not in remote:
        host, path = match.group("host"), match.group("path")
    else:
        parsed = urlparse(remote)
        if parsed.scheme not in ("http", "https", "ssh", "git") or not parsed.hostname:
            return None
        host, path = parsed.hostname, parsed.path
        # an https remote's port is the web server's; an ssh remote's isn't.
        if parsed.scheme in ("http", "https") and parsed.port:
            host = f"{host}:{parsed.port}"
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    if not path:
        return None
    return urlunparse(("https", host, f"/{path}", "", "", ""))


def parse_git_remotes(output: str) -> Optional[str]:
    """
    Return the https url of a repository from the output of ``git remote -v``.

    Prefers the ``origin`` remote's fetch url, then any other fetch url.

    :param output: The output of ``git remote -v``: lines of ``<name>\\t<url> (fetch|push)``.
    :type output: str
    :returns: The https url of the repository, or None if no remote has one.
    :rtype: Optional[str]
    """
    fetch_remotes: list[tuple[str, str]] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == "(fetch)":
            fetch_remotes.append((parts[0], parts[1]))
    fetch_remotes.sort(key=lambda remote: remote[0] != "origin")
    for _, url in fetch_remotes:
        normalized = normalize_remote_url(url)
        if normalized:
            return normalized
    return None


@cache
def get_repository_url() -> str:
    """
    Return the https url of the source code repository of the running platform.

    Runs ``git remote -v`` in the repository's root folder. Falls back to
    :data:`~smarter.common.const.SMARTER_PROJECT_REPOSITORY_URL` when git, or a
    ``.git`` directory, isn't there, as in the Docker image, or no remote has a url
    that a browser can open.

    Example:
        >>> get_repository_url()
        'https://github.com/smarter-sh/smarter'

    :returns: The https url of the repository, without credentials.
    :rtype: str
    """
    try:
        result = subprocess.run(  # nosec B603 B607
            ["git", "remote", "-v"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logger.debug("%s.get_repository_url() git remote -v failed, using the default: %s", logger_prefix, e)
        return SMARTER_PROJECT_REPOSITORY_URL
    return parse_git_remotes(result.stdout) or SMARTER_PROJECT_REPOSITORY_URL


__all__ = ["get_repository_url", "normalize_remote_url", "parse_git_remotes"]
