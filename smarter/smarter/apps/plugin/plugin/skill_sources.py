"""
Retrieval of remote Agent Skills for the SkillPlugin.

A SkillPlugin manifest can refer to a skill by URL rather than containing it verbatim.
See :py:mod:`smarter.apps.plugin.manifest.models.skill_plugin.source` for the supported
URLs. The skill is retrieved when the manifest is applied, and a snapshot of it is stored
with the plugin, so that tool calls never depend on the availability of the remote host.

- **GitHub:** the skill directory is listed with the GitHub git trees api, and SKILL.md and
  every file beneath the skill directory is downloaded from raw.githubusercontent.com.
  Files that are not UTF-8 text, such as images and fonts, are recorded without contents.
- **Any other https URL:** SKILL.md is downloaded, along with the bundled files that it
  refers to by relative path. Files that cannot be downloaded are recorded without contents.

.. warning::

    Skill source URLs are user supplied, so requests are made with
    :py:mod:`smarter.apps.plugin.plugin.safe_http`, which restricts them to https, to hosts
    whose addresses are all public, and to a bounded number of redirects and response sizes,
    in order to prevent server-side request forgery and resource exhaustion.

.. note::

    GitHub api requests are unauthenticated, and so are rate limited to 60 per hour per
    client IP address. One api request is made per GitHub-sourced skill, per apply.

.. note::

    **Experimental.** The SkillPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

from smarter.apps.plugin.manifest.models.skill_plugin.document import (
    MAX_RESOURCE_LENGTH,
    MAX_RESOURCES,
    MAX_SKILL_DOCUMENT_LENGTH,
    SKILL_FILENAME,
    SkillDocument,
    SkillDocumentError,
    find_resource_references,
    normalize_resource_path,
    parse_skill_document,
)
from smarter.apps.plugin.manifest.models.skill_plugin.source import (
    SkillSourceError,
    SkillSourceLocation,
    parse_source_url,
)
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from . import safe_http

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])

GITHUB_API_URL = "https://api.github.com"
REQUEST_TIMEOUT = 15
"""Seconds to wait for each remote request."""
MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 4 * MAX_RESOURCE_LENGTH
"""The maximum size of any single response, in bytes.

UTF-8 characters are at most 4 bytes.
"""
MAX_GITHUB_TREE_BYTES = 20_000_000
"""The maximum size of a GitHub git tree listing, in bytes."""
MAX_TOTAL_RESOURCE_BYTES = 10_000_000
"""The maximum combined size of a skill's bundled files, in bytes."""
USER_AGENT = "smarter-skill-plugin"


@dataclass
class RetrievedSkill:
    """
    A skill retrieved from a remote source.

    :ivar location: The resolved source location.
    :ivar document: The parsed SKILL.md document.
    :ivar resources: The bundled files, keyed by path relative to the skill root. A ``None``
        value denotes a file whose contents are unavailable, such as a binary asset.
    :ivar retrieved_at: When the skill was retrieved.
    """

    location: SkillSourceLocation
    document: SkillDocument
    resources: dict[str, Optional[str]] = field(default_factory=dict)
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def validate_public_https_url(url: str) -> None:
    """
    Validate that a URL is https, and that every address its host resolves to is public.

    :raises SkillSourceError: If the URL is not https, has no host, cannot be resolved, or
        resolves to a loopback, private, link-local, reserved or otherwise non-public address.

    .. seealso:: :py:func:`smarter.apps.plugin.plugin.safe_http.validate_public_url`
    """
    try:
        safe_http.validate_public_url(url)
    except safe_http.SafeHttpError as e:
        raise SkillSourceError(f"skill source is not permitted: {e}") from e


def fetch(url: str, max_bytes: int = MAX_RESPONSE_BYTES, headers: Optional[dict[str, str]] = None) -> bytes:
    """
    Download a remote file, safely.

    :param url: The https URL to download.
    :param max_bytes: The maximum size of the response body.
    :param headers: Additional request headers.
    :return: The response body.
    :raises SkillSourceError: If the URL is not a public https URL, the request fails or
        times out, the response is not 200 OK, or the response is too large.

    .. seealso:: :py:func:`smarter.apps.plugin.plugin.safe_http.fetch`
    """
    try:
        return safe_http.fetch(
            url,
            headers={"User-Agent": USER_AGENT, **(headers or {})},
            timeout=REQUEST_TIMEOUT,
            max_bytes=max_bytes,
            max_redirects=MAX_REDIRECTS,
        ).content
    except safe_http.SafeHttpError as e:
        raise SkillSourceError(f"skill source could not be retrieved: {e}") from e


def fetch_text(url: str, max_bytes: int = MAX_RESPONSE_BYTES) -> Optional[str]:
    """
    Download a remote text file.

    :return: The file contents, or None if the file is not UTF-8 text, such as an image.
    :raises SkillSourceError: If the file cannot be downloaded.
    """
    content = fetch(url, max_bytes=max_bytes)
    if b"\x00" in content:
        return None
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return None


def list_github_skill_files(location: SkillSourceLocation) -> list[tuple[str, int]]:
    """
    List the files beneath a skill directory in a GitHub repository.

    :return: The (path relative to the skill root, size in bytes) of each file, excluding SKILL.md.
    :raises SkillSourceError: If the repository, ref or directory cannot be found.
    """
    tree_url = (
        f"{GITHUB_API_URL}/repos/{quote(str(location.owner))}/{quote(str(location.repo))}"
        f"/git/trees/{quote(str(location.ref))}?recursive=1"
    )
    content = fetch(tree_url, max_bytes=MAX_GITHUB_TREE_BYTES, headers={"Accept": "application/vnd.github+json"})
    try:
        tree = json.loads(content)
    except ValueError as e:
        raise SkillSourceError(f"GitHub returned an invalid tree listing for {location.url}") from e
    if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
        raise SkillSourceError(f"GitHub returned an invalid tree listing for {location.url}")
    if tree.get("truncated"):
        logger.warning("list_github_skill_files() GitHub tree listing of %s is truncated.", location.url)

    prefix = f"{location.path}/" if location.path else ""
    files: list[tuple[str, int]] = []
    skill_found = False
    for entry in tree["tree"]:
        if not isinstance(entry, dict) or entry.get("type") != "blob":
            continue
        path = entry.get("path", "")
        if not path.startswith(prefix):
            continue
        relative_path = path[len(prefix) :]
        if relative_path == SKILL_FILENAME:
            skill_found = True
            continue
        files.append((relative_path, int(entry.get("size") or 0)))
    if not skill_found and not tree.get("truncated"):
        raise SkillSourceError(f"{SKILL_FILENAME} was not found at {location.url}")
    return sorted(files)


def _retrieve_resources(
    location: SkillSourceLocation, files: list[tuple[str, Optional[int]]]
) -> dict[str, Optional[str]]:
    """
    Download the bundled files of a skill, within the resource limits.

    :param files: The (path, size in bytes) of each file. A size of None denotes a file that
        SKILL.md merely appears to refer to, which is skipped if it cannot be downloaded.
        Listed files that cannot be downloaded are recorded without contents.
    """
    resources: dict[str, Optional[str]] = {}
    total_bytes = 0
    for path, size in files:
        if len(resources) >= MAX_RESOURCES:
            logger.warning(
                "retrieve_skill() %s bundles more than %s files. The remainder are ignored.",
                location.url,
                MAX_RESOURCES,
            )
            break
        try:
            path = normalize_resource_path(path)
        except SkillDocumentError:
            logger.warning("retrieve_skill() ignoring invalid bundled file path %s in %s", path, location.url)
            continue
        if size is not None and (size > MAX_RESPONSE_BYTES or total_bytes + size > MAX_TOTAL_RESOURCE_BYTES):
            logger.warning("retrieve_skill() bundled file %s of %s is too large to retrieve.", path, location.url)
            resources[path] = None
            continue
        try:
            content = fetch_text(location.resource_url(path))
        except SkillSourceError as e:
            logger.warning("retrieve_skill() bundled file %s of %s could not be retrieved: %s", path, location.url, e)
            if size is not None:
                resources[path] = None
            continue
        if content is not None and len(content) > MAX_RESOURCE_LENGTH:
            content = None
        total_bytes += len(content.encode("utf-8")) if content else 0
        resources[path] = content
    return resources


def retrieve_skill(url: str) -> RetrievedSkill:
    """
    Retrieve a skill and its bundled files from a remote source.

    :param url: A skill source URL. See :py:func:`parse_source_url`.
    :return: The retrieved skill.
    :raises SkillSourceError: If the skill cannot be retrieved.
    :raises SkillDocumentError: If the retrieved SKILL.md is invalid.

    **Example:**

    .. code-block:: python

        skill = retrieve_skill("https://github.com/anthropics/skills/tree/main/skills/pdf")
        skill.document.name  # 'pdf'
        list(skill.resources)  # ['LICENSE.txt', 'forms.md', 'reference.md', 'scripts/...', ...]
    """
    location = parse_source_url(url)
    logger.info("retrieve_skill() retrieving skill from %s", location.skill_url)

    files: list[tuple[str, Optional[int]]] = []
    if location.is_github:
        files.extend(list_github_skill_files(location))

    document_text = fetch_text(location.skill_url, max_bytes=4 * MAX_SKILL_DOCUMENT_LENGTH)
    if document_text is None:
        raise SkillSourceError(f"{SKILL_FILENAME} at {location.skill_url} is not UTF-8 text.")
    document = parse_skill_document(document_text)

    expected_name = location.skill_directory_name
    if expected_name and expected_name != document.name:
        logger.warning(
            "retrieve_skill() skill name %s does not match its directory name %s at %s",
            document.name,
            expected_name,
            location.url,
        )

    if not location.is_github:
        files.extend((path, None) for path in find_resource_references(document.body))

    resources = _retrieve_resources(location, files)
    logger.info(
        "retrieve_skill() retrieved skill %s with %s bundled files from %s", document.name, len(resources), location.url
    )
    return RetrievedSkill(location=location, document=document, resources=resources)
