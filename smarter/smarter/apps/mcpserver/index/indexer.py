"""
The indexer of The Smarter Project's repositories.

:func:`index_repository` brings one repository's :class:`~smarter.apps.mcpserver.models.RepositoryIndex`
up to date with its branch:

1. It asks the GitHub api for the branch's latest commit. If that commit is already
   indexed, there is nothing to do, so a repository that has not changed costs one small
   request.
2. Otherwise it downloads the repository's gzipped tar archive at that commit, from
   GitHub's codeload service, streaming it to a temporary file whose size is capped.
3. It reads the archive's text files, in memory, without extracting anything to disk. It
   keeps documentation and source code, and skips binaries, generated and vendored files,
   lock files, and files that are too large to be useful to an LLM. The images of the
   published Sphinx documentation get their published urls, as Markdown images: see
   :func:`link_documentation_images`.
4. It replaces the repository's files in one transaction, so that a search never sees a
   partial index.

The urls are fixed GitHub urls of public repositories, not user-supplied ones, so the
requests do not go through :mod:`smarter.apps.llmtool.plugin.safe_http`. GitHub's api allows
60 unauthenticated requests an hour, and an hourly refresh of every repository needs one
request for each.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import fnmatch
import posixpath
import re
import tarfile
import tempfile
from typing import IO, Iterator, Optional
from urllib.parse import urlparse

import requests
from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel, ConfigDict

from smarter.apps.mcpserver.const import USER_AGENT
from smarter.apps.mcpserver.exceptions import SmarterMCPServerIndexError
from smarter.apps.mcpserver.models import (
    RepositoryFile,
    RepositoryFileKind,
    RepositoryIndex,
    RepositoryIndexStatus,
)
from smarter.apps.mcpserver.repositories import ProjectRepository, get_repository
from smarter.apps.mcpserver.signals import (
    mcpserver_repository_index_failed,
    mcpserver_repository_indexed,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .search import MAX_LINE_LENGTH

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])

REQUEST_TIMEOUT = 60
"""Seconds to wait for GitHub to respond, and between the chunks of an archive."""
CHUNK_SIZE = 1024 * 1024

MAX_ARCHIVE_BYTES = 250_000_000
"""The maximum size of a repository's compressed archive."""
MAX_FILE_BYTES = 256_000
"""The maximum size of an indexed file. Larger files are mostly generated."""
MAX_FILES = 20_000
"""The maximum number of files to index of a repository."""
MAX_INDEX_BYTES = 64_000_000
"""The maximum total size of a repository's indexed files."""
MAX_TITLE_LENGTH = 255
BATCH_SIZE = 50
"""Rows per INSERT.

Files are up to MAX_FILE_BYTES each, and a batch must fit in one database packet.
"""

DOCUMENTATION_EXTENSIONS = frozenset({".rst", ".md", ".mdx", ".txt"})
CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".pyi",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".go",
        ".mod",
        ".html",
        ".css",
        ".scss",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".in",
        ".sh",
        ".tf",
        ".tfvars",
        ".hcl",
        ".tpl",
        ".j2",
        ".sql",
        ".xml",
        ".env",
        ".example",
    }
)
DOCUMENTATION_FILENAMES = frozenset({"LICENSE", "COPYING", "NOTICE", "AUTHORS"})
CODE_FILENAMES = frozenset({"Makefile", "Dockerfile", "Procfile", "CODEOWNERS", ".gitignore", ".dockerignore"})
EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        "coverage",
        "htmlcov",
        "vendor",
        ".next",
        ".terraform",
    }
)
EXCLUDED_PATTERNS = (
    "*.min.js",
    "*.min.css",
    "*.bundle.js",
    "*.bundle.css",
    "*.map",
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "go.sum",
    "*/static/assets/*",
)
"""Generated, vendored and lock files, which match many searches and answer none."""

RST_UNDERLINE = re.compile(r"^([=\-~^\"'`#*+:.])\1{2,}\s*$")
MARKDOWN_HEADING = re.compile(r"^#{1,3}\s+(.+?)\s*#*\s*$")
RST_IMAGE_DIRECTIVE = re.compile(r"^(?P<indent>\s*)\.\. (?P<directive>image|figure)::\s*(?P<target>\S*)\s*$")
RST_OPTION = re.compile(r"^\s*:(?P<name>[\w-]+):\s*(?P<value>.*)$")
WHITESPACE = re.compile(r"\s+")
BADGE_HOSTS = frozenset({"img.shields.io"})
"""Hosts of status badges, which are images, but illustrate nothing."""
MAX_IMAGE_LINE_LENGTH = MAX_LINE_LENGTH
"""The maximum length of a line with a Markdown image: the longest line that a search's passage shows whole."""


class ArchiveFile(BaseModel):
    """A text file read from a repository's archive, before it is stored as a :class:`~smarter.apps.mcpserver.models.RepositoryFile`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    kind: RepositoryFileKind
    title: str
    content: str
    size: int
    line_count: int


def file_kind(path: str) -> Optional[RepositoryFileKind]:
    """
    Return what a file of a repository is, or None if it is not indexed.

    :param path: The file's path in the repository.
    :returns: Documentation, code, or None.
    """
    parts = path.split("/")
    if any(part in EXCLUDED_DIRECTORIES for part in parts[:-1]):
        return None
    if any(
        fnmatch.fnmatchcase(path, pattern) or fnmatch.fnmatchcase(parts[-1], pattern) for pattern in EXCLUDED_PATTERNS
    ):
        return None
    filename = parts[-1]
    extension = posixpath.splitext(filename)[1].lower()
    if extension in DOCUMENTATION_EXTENSIONS or filename in DOCUMENTATION_FILENAMES:
        return RepositoryFileKind.DOCUMENTATION
    if extension in CODE_EXTENSIONS or filename in CODE_FILENAMES:
        return RepositoryFileKind.CODE
    return None


def document_title(content: str) -> str:
    """
    Return a document's first heading, in reStructuredText or Markdown.

    :param content: The document.
    :returns: The heading, or an empty string if it has none.
    """
    lines = content.splitlines()[:60]
    for i, line in enumerate(lines):
        match = MARKDOWN_HEADING.match(line)
        if match:
            return match.group(1)[:MAX_TITLE_LENGTH]
        text = line.strip()
        if text and not RST_UNDERLINE.match(line) and i + 1 < len(lines) and RST_UNDERLINE.match(lines[i + 1]):
            if len(lines[i + 1].strip()) >= len(text):
                return text[:MAX_TITLE_LENGTH]
    return ""


def markdown_image(description: str, url: str, prefix_length: int = 0) -> tuple[str, bool]:
    """
    Return a Markdown image, ``![description](url)``, that fits on one line of a search's passage.

    The LLM cannot see an image, so its description, e.g. its alt text, is what tells the LLM
    what it shows, and Smarter Chat displays the image when the LLM includes it in an answer.

    :param description: What the image shows. Brackets become parentheses, which Markdown allows.
    :param url: The image's url.
    :param prefix_length: The length of the text before the image on its line.
    :returns: The image, and whether its description is complete. A description that does not
        fit within :data:`MAX_IMAGE_LINE_LENGTH` is shortened, and ends with an ellipsis.
    """
    text = WHITESPACE.sub(" ", description).strip().replace("[", "(").replace("]", ")") or "Illustration"
    budget = MAX_IMAGE_LINE_LENGTH - prefix_length - len(url) - len("![](…)")
    if len(text) <= budget:
        return f"![{text}]({url})", True
    short = text[: max(budget, 0)].rsplit(" ", 1)[0].rstrip(",;:.") if budget >= 20 else ""
    return (f"![{short}…]({url})" if short else f"![Illustration]({url})"), False


def documentation_image_url(repository: ProjectRepository, target: str) -> Optional[str]:
    """
    Return the published url of an image of a repository's Sphinx documentation.

    Sphinx copies a local image to the ``_images/`` folder of the built site, by its file name.

    :param repository: The repository.
    :param target: The image directive's argument, e.g. ``/_static/api-key-claude.png``, or a url.
    :returns: The url, or None for a status badge, or a local image of a repository without
        published documentation.
    """
    if target.startswith(("http://", "https://")):
        return None if urlparse(target).hostname in BADGE_HOSTS else target
    if not target or not repository.docs_url or any(character in target for character in "()<>"):
        return None
    return f"{repository.docs_url}_images/{posixpath.basename(target)}"


def link_documentation_images(repository: ProjectRepository, file: ArchiveFile) -> ArchiveFile:
    """
    Append a Markdown image to each ``image`` and ``figure`` directive of a Sphinx source file.

    An LLM cannot turn ``.. image:: /_static/x.png`` into a link, so the line that names the
    image gets its published url, as a Markdown image whose description is the directive's
    ``:alt:``, or else a figure's caption. The image is appended to the line, rather than added on a
    line of its own, so that line numbers still match the file on GitHub.

    :param repository: The repository.
    :param file: The file.
    :returns: The file, with its images linked, or unchanged if it is not a reStructuredText
        file of the repository's published documentation.
    """
    if not repository.docs_root or not file.path.startswith(repository.docs_root.rstrip("/") + "/"):
        return file
    if not file.path.endswith(".rst"):
        return file
    lines = file.content.split("\n")
    changed = False
    for i, line in enumerate(lines):
        match = RST_IMAGE_DIRECTIVE.match(line)
        if not match:
            continue
        indent = len(match.group("indent"))
        target, target_line, j = match.group("target"), i, i + 1
        if not target and j < len(lines) and indentation(lines[j]) > indent and not RST_OPTION.match(lines[j]):
            target, target_line, j = lines[j].strip(), j, j + 1
        url = documentation_image_url(repository, target)
        if url is None:
            continue
        alt, caption, blank = "", "", False
        while j < len(lines) and (not lines[j].strip() or indentation(lines[j]) > indent):
            option = RST_OPTION.match(lines[j])
            if not lines[j].strip():
                blank = True
            elif option and not blank:
                alt = option.group("value") if option.group("name") == "alt" else alt
            elif blank and not caption and match.group("directive") == "figure":
                caption = lines[j].strip()
            j += 1
        prefix = lines[target_line].rstrip() + "  "
        image, _ = markdown_image(alt or caption, url, prefix_length=len(prefix))
        lines[target_line] = prefix + image
        changed = True
    if not changed:
        return file
    content = "\n".join(lines)
    return file.model_copy(update={"content": content, "size": len(content.encode())})


def indentation(line: str) -> int:
    """Return the number of spaces before a line's text."""
    return len(line) - len(line.lstrip())


def decode_text(data: bytes) -> Optional[str]:
    """
    Return a file's bytes as text, or None if it is binary.

    :param data: The file's content.
    :returns: The text.
    """
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def read_archive(archive: IO[bytes]) -> Iterator[ArchiveFile]:
    """
    Read the indexable text files of a repository's gzipped tar archive.

    GitHub's archives contain one top-level folder, ``<repository>-<commit>/``, which is
    removed from the paths. Only regular files are read: links, which could point outside
    the repository, are skipped. Nothing is extracted to disk.

    :param archive: The archive, positioned at its start.
    :returns: The files, in the archive's order.
    :raises SmarterMCPServerIndexError: If the archive cannot be read.
    """
    try:
        with tarfile.open(fileobj=archive, mode="r:gz") as tar:
            for member in tar:
                if not member.isfile() or "/" not in member.name:
                    continue
                path = member.name.split("/", 1)[1]
                kind = file_kind(path)
                if kind is None or member.size > MAX_FILE_BYTES:
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                content = decode_text(extracted.read(MAX_FILE_BYTES + 1))
                if content is None or not content.strip():
                    continue
                yield ArchiveFile(
                    path=path,
                    kind=kind,
                    title=document_title(content) if kind == RepositoryFileKind.DOCUMENTATION else "",
                    content=content,
                    size=member.size,
                    line_count=content.count("\n") + (0 if content.endswith("\n") else 1),
                )
    except (tarfile.TarError, OSError, EOFError) as e:
        raise SmarterMCPServerIndexError(f"the archive could not be read: {e}") from e


def latest_commit_sha(repository: ProjectRepository) -> str:
    """
    Return the latest commit of a repository's branch, from the GitHub api.

    :param repository: The repository.
    :returns: The commit's sha.
    :raises SmarterMCPServerIndexError: If GitHub does not answer with a commit.
    """
    try:
        response = requests.get(
            repository.commit_api_url,
            headers={"Accept": "application/vnd.github.sha", "User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.exceptions.RequestException as e:
        raise SmarterMCPServerIndexError(f"GitHub could not be reached: {type(e).__name__}") from e
    sha = response.text.strip()
    if response.status_code != 200 or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise SmarterMCPServerIndexError(
            f"GitHub responded with HTTP {response.status_code} for the latest commit of {repository.full_name}"
        )
    return sha


def download_archive(repository: ProjectRepository, commit_sha: str, destination: IO[bytes]) -> int:
    """
    Download a repository's gzipped tar archive at a commit.

    :param repository: The repository.
    :param commit_sha: The commit.
    :param destination: A binary file to write the archive to.
    :returns: The archive's size, in bytes.
    :raises SmarterMCPServerIndexError: If the download fails, or the archive is larger than :data:`MAX_ARCHIVE_BYTES`.
    """
    url = repository.archive_url(commit_sha)
    size = 0
    try:
        with requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT, stream=True) as response:
            if response.status_code != 200:
                raise SmarterMCPServerIndexError(f"GitHub responded with HTTP {response.status_code} for {url}")
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_ARCHIVE_BYTES:
                    raise SmarterMCPServerIndexError(
                        f"the archive of {repository.full_name} exceeds {MAX_ARCHIVE_BYTES} bytes."
                    )
                destination.write(chunk)
    except requests.exceptions.RequestException as e:
        raise SmarterMCPServerIndexError(
            f"the archive of {repository.full_name} could not be downloaded: {type(e).__name__}"
        ) from e
    destination.seek(0)
    return size


def collect_files(archive: IO[bytes]) -> list[ArchiveFile]:
    """
    Return the files of an archive to index, within :data:`MAX_FILES` and :data:`MAX_INDEX_BYTES`.

    :param archive: The archive.
    :returns: The files. Files beyond the limits are left out, and a warning is logged.
    """
    files: list[ArchiveFile] = []
    total = 0
    for file in read_archive(archive):
        if len(files) >= MAX_FILES or total + file.size > MAX_INDEX_BYTES:
            logger.warning(
                "%s the index limit was reached at %s files and %s bytes: the remaining files are not indexed.",
                f"{logging.SmarterFormattedText.text(__name__)}.collect_files()",
                len(files),
                total,
            )
            break
        files.append(file)
        total += file.size
    return files


def store_files(index: RepositoryIndex, commit_sha: str, files: list[ArchiveFile]) -> RepositoryIndex:
    """
    Replace a repository's indexed files, in one transaction.

    :param index: The repository's index.
    :param commit_sha: The commit that the files are of.
    :param files: The files.
    :returns: The index, ready to search.
    """
    with transaction.atomic():
        RepositoryFile.objects.filter(index=index).delete()
        RepositoryFile.objects.bulk_create(
            (
                RepositoryFile(
                    index=index,
                    path=file.path,
                    kind=file.kind,
                    title=file.title,
                    content=file.content,
                    size=file.size,
                    line_count=file.line_count,
                )
                for file in files
            ),
            batch_size=BATCH_SIZE,
        )
        index.commit_sha = commit_sha
        index.status = RepositoryIndexStatus.READY
        index.indexed_at = timezone.now()
        index.file_count = len(files)
        index.total_bytes = sum(file.size for file in files)
        index.error = None
        index.save()
    return index


def index_repository(name: str, force: bool = False) -> RepositoryIndex:
    """
    Bring a repository's index up to date with the latest commit of its branch.

    :param name: The repository's name, e.g. ``smarter-cli``.
    :param force: Index the repository even if its latest commit is already indexed.
    :returns: The repository's index. If indexing fails, its ``error`` says why, and an
        existing index is kept.
    :raises SmarterMCPServerIndexError: If there is no such repository.

    **Example usage**::

        index = index_repository("smarter-cli")
        index.status  # 'ready'
    """
    prefix = f"{logging.SmarterFormattedText.text(__name__)}.index_repository()"
    repository = get_repository(name)
    if repository is None:
        raise SmarterMCPServerIndexError(f"{name} is not a repository of The Smarter Project.")
    index, _ = RepositoryIndex.objects.get_or_create(repository=repository.name)
    try:
        commit_sha = latest_commit_sha(repository)
        if index.is_ready and index.commit_sha == commit_sha and not force:
            logger.info("%s %s is up to date at %s.", prefix, repository.name, commit_sha)
            if index.error:
                RepositoryIndex.objects.filter(pk=index.pk).update(error=None)
                index.error = None
            return index
        with tempfile.TemporaryFile() as archive:
            size = download_archive(repository, commit_sha, archive)
            logger.info("%s downloaded %s at %s: %s bytes.", prefix, repository.full_name, commit_sha, size)
            files = [link_documentation_images(repository, file) for file in collect_files(archive)]
        index = store_files(index, commit_sha, files)
    except SmarterMCPServerIndexError as e:
        status = RepositoryIndexStatus.READY if index.is_ready else RepositoryIndexStatus.FAILED
        RepositoryIndex.objects.filter(pk=index.pk).update(status=status, error=e.message)
        index.refresh_from_db()
        mcpserver_repository_index_failed.send(sender=index_repository, repository=repository.name, error=e.message)
        return index
    mcpserver_repository_indexed.send(sender=index_repository, index=index)
    return index


__all__ = [
    "ArchiveFile",
    "collect_files",
    "document_title",
    "documentation_image_url",
    "download_archive",
    "file_kind",
    "index_repository",
    "latest_commit_sha",
    "link_documentation_images",
    "markdown_image",
    "read_archive",
    "store_files",
]
