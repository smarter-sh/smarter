"""
Resolution of the remote locations from which a SkillPlugin can source its skill.

A skill can be sourced from a public GitHub repository, such as Anthropic's
https://github.com/anthropics/skills, by referring to either the skill's directory
or its ``SKILL.md`` file. Any other ``https`` URL of a ``SKILL.md`` file is supported too.

.. code-block:: text

    # a skill directory in a GitHub repository
    https://github.com/anthropics/skills/tree/main/skills/pdf

    # a SKILL.md file in a GitHub repository
    https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md
    https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/SKILL.md

    # a GitHub repository whose root is a skill. HEAD is its default branch.
    https://github.com/example-org/my-skill

    # any other SKILL.md file
    https://example.com/skills/my-skill/SKILL.md

.. note::

    GitHub branch names may contain slashes, which makes a URL such as
    ``/tree/feature/x/skills/pdf`` ambiguous. The first path segment after ``tree`` or
    ``blob`` is always taken to be the ref, so refer to such branches by commit SHA instead.

.. note::

    **Experimental.** The SkillPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import posixpath
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, urlparse

from smarter.common.exceptions import SmarterValueError

from .document import SKILL_FILENAME

GITHUB_HOSTS = ("github.com", "www.github.com")
GITHUB_RAW_HOST = "raw.githubusercontent.com"
GITHUB_DEFAULT_REF = "HEAD"
MAX_SOURCE_URL_LENGTH = 2048


class SkillSourceError(SmarterValueError):
    """Raised when a skill source URL is invalid, or a skill cannot be retrieved from it."""


@dataclass(frozen=True)
class SkillSourceLocation:
    """
    The resolved location of a remote skill.

    :ivar url: The URL as written in the manifest.
    :ivar skill_url: The URL from which to download SKILL.md.
    :ivar base_url: The URL of the skill root directory, ending in ``/``. Bundled files are
        resolved relative to it.
    :ivar owner: The GitHub repository owner, for GitHub sources.
    :ivar repo: The GitHub repository name, for GitHub sources.
    :ivar ref: The GitHub branch, tag or commit, for GitHub sources.
    :ivar path: The path of the skill root directory within the GitHub repository, for
        GitHub sources. Empty if the skill is the repository root.
    """

    url: str
    skill_url: str
    base_url: str
    owner: Optional[str] = None
    repo: Optional[str] = None
    ref: Optional[str] = None
    path: Optional[str] = None

    @property
    def is_github(self) -> bool:
        """True if the skill is hosted in a GitHub repository."""
        return self.owner is not None

    @property
    def skill_directory_name(self) -> Optional[str]:
        """The name of the skill root directory, which the specification requires to match the skill's name."""
        if self.is_github:
            return posixpath.basename(self.path) if self.path else self.repo
        parent = posixpath.dirname(urlparse(self.skill_url).path.rstrip("/"))
        return posixpath.basename(parent) or None

    def resource_url(self, path: str) -> str:
        """Return the download URL of a bundled file, given its normalized path relative to the skill root."""
        return self.base_url + quote(path)


def _github_location(url: str, owner: str, repo: str, ref: str, path: str) -> SkillSourceLocation:
    path = path.strip("/")
    if path.split("/")[-1] == SKILL_FILENAME:
        path = posixpath.dirname(path)
    base = f"https://{GITHUB_RAW_HOST}/{quote(owner)}/{quote(repo)}/{quote(ref)}/"
    base_url = base + (quote(path) + "/" if path else "")
    return SkillSourceLocation(
        url=url,
        skill_url=base_url + SKILL_FILENAME,
        base_url=base_url,
        owner=owner,
        repo=repo,
        ref=ref,
        path=path,
    )


# pylint: disable=too-many-branches
def parse_source_url(url: str) -> SkillSourceLocation:
    """
    Resolve a skill source URL to the location of its SKILL.md file and bundled files.

    :param url: A GitHub URL of a skill directory or SKILL.md file, or an https URL of a SKILL.md file.
    :return: The resolved location.
    :raises SkillSourceError: If the URL is not a supported https URL.

    **Example:**

    .. code-block:: python

        location = parse_source_url("https://github.com/anthropics/skills/tree/main/skills/pdf")
        location.skill_url
        # 'https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/SKILL.md'
    """
    if not isinstance(url, str) or not url.strip():
        raise SkillSourceError("skill source url must not be empty.")
    url = url.strip()
    if len(url) > MAX_SOURCE_URL_LENGTH:
        raise SkillSourceError(f"skill source url must be at most {MAX_SOURCE_URL_LENGTH} characters.")
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise SkillSourceError(f"skill source url must be an https url: {url}")
    if not parsed.hostname:
        raise SkillSourceError(f"skill source url has no host: {url}")
    if parsed.username or parsed.password:
        raise SkillSourceError("skill source url must not contain credentials.")
    host = parsed.hostname.lower()
    segments = [segment for segment in parsed.path.split("/") if segment]

    if host in GITHUB_HOSTS:
        if len(segments) < 2:
            raise SkillSourceError(f"GitHub skill source url must refer to a repository: {url}")
        owner, repo = segments[0], segments[1].removesuffix(".git")
        if len(segments) == 2:
            return _github_location(url, owner, repo, GITHUB_DEFAULT_REF, "")
        if segments[2] not in ("tree", "blob") or len(segments) < 4:
            raise SkillSourceError(
                f"GitHub skill source url must refer to a skill directory (/tree/<ref>/<path>) or a "
                f"{SKILL_FILENAME} file (/blob/<ref>/<path>/{SKILL_FILENAME}): {url}"
            )
        if segments[2] == "blob" and segments[-1] != SKILL_FILENAME:
            raise SkillSourceError(f"GitHub skill source file url must refer to a {SKILL_FILENAME} file: {url}")
        return _github_location(url, owner, repo, segments[3], "/".join(segments[4:]))

    if host == GITHUB_RAW_HOST:
        if len(segments) < 4 or segments[-1] != SKILL_FILENAME:
            raise SkillSourceError(
                f"{GITHUB_RAW_HOST} skill source url must refer to a {SKILL_FILENAME} file "
                f"(/<owner>/<repo>/<ref>/<path>/{SKILL_FILENAME}): {url}"
            )
        return _github_location(url, segments[0], segments[1], segments[2], "/".join(segments[3:]))

    if not segments or segments[-1] != SKILL_FILENAME:
        raise SkillSourceError(f"skill source url must refer to a GitHub repository or a {SKILL_FILENAME} file: {url}")
    skill_url = parsed._replace(query="", fragment="").geturl()
    return SkillSourceLocation(url=url, skill_url=skill_url, base_url=skill_url[: -len(SKILL_FILENAME)])
