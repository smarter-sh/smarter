"""
The indexer of The Smarter Project's repositories, which copies their text files from GitHub into the database.

The Smarter Project MCP server answers questions about the project's repositories, e.g. "how does custom
domain verification work?", from its own copy of their files, which is searched in the database by
:mod:`smarter.apps.mcpserver.index.search`, and read by the tools of
:mod:`smarter.apps.mcpserver.index.tools`. This module makes and refreshes that copy.

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

The Celery task :func:`smarter.apps.mcpserver.tasks.index_repository` calls it, on a schedule and
when a tool finds a repository that is not indexed yet. The blog is indexed the same way, from
WordPress instead of GitHub, by :mod:`smarter.apps.mcpserver.index.blog`, which reuses
:class:`ArchiveFile`, :func:`markdown_image` and :func:`store_files`.

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
logger_prefix = logging.SmarterFormattedText.text(__name__)

REQUEST_TIMEOUT = 60
"""Seconds to wait for GitHub to respond, and between the chunks of an archive."""

CHUNK_SIZE = 1024 * 1024
"""Bytes of an archive to read from the network and write to the temporary file at a time: 1 MiB."""

MAX_ARCHIVE_BYTES = 250_000_000
"""The maximum size of a repository's compressed archive. A larger download is stopped, and fails."""

MAX_FILE_BYTES = 256_000
"""
The maximum size of an indexed file.

Larger files are mostly generated, e.g. bundles and data, and are too long for an LLM to read.
"""

MAX_FILES = 20_000
"""The maximum number of files to index of a repository.

The files after it are left out.
"""

MAX_INDEX_BYTES = 64_000_000
"""The maximum total size of a repository's indexed files.

The files after it are left out.
"""

MAX_TITLE_LENGTH = 255
"""The most characters of a document's title that are stored, the length of the ``title`` column."""

BATCH_SIZE = 50
"""
Rows per INSERT.

Files are up to :data:`MAX_FILE_BYTES` each, and a batch must fit in one database packet.
"""

DOCUMENTATION_EXTENSIONS = frozenset({".rst", ".md", ".mdx", ".txt"})
"""The extensions of the files that are indexed as documentation, which ``search_documentation`` searches."""

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
"""
The extensions of the files that are indexed as code, which ``search_code`` searches.

Besides source code, they include configuration, e.g. YAML manifests, Helm templates and Terraform.
"""

DOCUMENTATION_FILENAMES = frozenset({"LICENSE", "COPYING", "NOTICE", "AUTHORS"})
"""The names of files without an extension that are indexed as documentation."""

CODE_FILENAMES = frozenset({"Makefile", "Dockerfile", "Procfile", "CODEOWNERS", ".gitignore", ".dockerignore"})
"""The names of files without a known extension that are indexed as code."""

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
"""The folders whose files are never indexed, at any depth: vendored packages, builds and caches."""

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
"""
Generated, vendored and lock files, which match many searches and answer none.

Each pattern is matched against both a file's path and its name, with :func:`fnmatch.fnmatchcase`.
"""

RST_UNDERLINE = re.compile(r"^([=\-~^\"'`#*+:.])\1{2,}\s*$")
"""A reStructuredText heading's underline or overline: three or more of one punctuation character, e.g. ``===``."""

MARKDOWN_HEADING = re.compile(r"^#{1,3}\s+(.+?)\s*#*\s*$")
"""A Markdown heading of level 1 to 3, e.g. ``# Title``.

Its group 1 is the heading's text.
"""

RST_IMAGE_DIRECTIVE = re.compile(r"^(?P<indent>\s*)\.\. (?P<directive>image|figure)::\s*(?P<target>\S*)\s*$")
"""
A reStructuredText ``image`` or ``figure`` directive, e.g. ``.. image:: /_static/x.png``.

Its groups are the directive's ``indent``, its name, ``directive``, and its argument, ``target``,
which is empty when the argument is on the next line.
"""

RST_OPTION = re.compile(r"^\s*:(?P<name>[\w-]+):\s*(?P<value>.*)$")
"""An option of a reStructuredText directive, e.g. ``:alt: The console``, with its ``name`` and ``value``."""

WHITESPACE = re.compile(r"\s+")
"""A run of whitespace, which a Markdown image's description collapses to one space."""

BADGE_HOSTS = frozenset({"img.shields.io"})
"""Hosts of status badges, which are images, but illustrate nothing."""

MAX_IMAGE_LINE_LENGTH = MAX_LINE_LENGTH
"""The maximum length of a line with a Markdown image: the longest line that a search's passage shows whole."""


class ArchiveFile(BaseModel):
    """
    A text file read from a repository's archive, before it is stored as a :class:`~smarter.apps.mcpserver.models.RepositoryFile`.

    :func:`read_archive` makes one for each file that is indexed, :func:`link_documentation_images`
    may change its content, and :func:`store_files` saves it. The blog's indexer,
    :mod:`smarter.apps.mcpserver.index.blog`, makes one for each post.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    """The file's path in the repository, without the archive's top-level folder, e.g. ``docs/source/index.rst``."""

    kind: RepositoryFileKind
    """Whether the file is documentation or code, from :func:`file_kind`."""

    title: str
    """A document's first heading, from :func:`document_title`, or an empty string for code."""

    content: str
    """The file's text."""

    size: int
    """The size of the file's text, in bytes, when encoded as UTF-8."""

    line_count: int
    """The number of lines of the file, from :func:`count_lines`."""


def count_lines(content: str) -> int:
    """
    Count the lines of a file's text, as an editor numbers them.

    A last line without a newline counts as a line, so ``"a\\nb"`` and ``"a\\nb\\n"`` both have two.

    :param content: The text.
    :returns: The number of lines.
    """
    newlines = content.count("\n")
    if content.endswith("\n"):
        return newlines
    return newlines + 1


def is_excluded(path: str) -> bool:
    """
    Check whether a file is in an excluded folder, or matches an excluded pattern.

    :param path: The file's path in the repository.
    :returns: True if the file is one of :data:`EXCLUDED_DIRECTORIES` or :data:`EXCLUDED_PATTERNS`,
        which are never indexed.
    """
    parts = path.split("/")
    folders = parts[:-1]
    filename = parts[-1]
    for folder in folders:
        if folder in EXCLUDED_DIRECTORIES:
            return True
    for pattern in EXCLUDED_PATTERNS:
        if fnmatch.fnmatchcase(path, pattern):
            return True
        if fnmatch.fnmatchcase(filename, pattern):
            return True
    return False


def file_kind(path: str) -> Optional[RepositoryFileKind]:
    """
    Return what a file of a repository is, or None if it is not indexed.

    A file is documentation or code by its extension or its name (see :data:`DOCUMENTATION_EXTENSIONS`
    and :data:`CODE_EXTENSIONS`). A file in an excluded folder, or that matches an excluded pattern,
    is not indexed, whatever its extension.

    :param path: The file's path in the repository.
    :returns: Documentation, code, or None.
    """
    if is_excluded(path):
        return None
    filename = posixpath.basename(path)
    extension = posixpath.splitext(filename)[1].lower()
    if extension in DOCUMENTATION_EXTENSIONS:
        return RepositoryFileKind.DOCUMENTATION
    if filename in DOCUMENTATION_FILENAMES:
        return RepositoryFileKind.DOCUMENTATION
    if extension in CODE_EXTENSIONS:
        return RepositoryFileKind.CODE
    if filename in CODE_FILENAMES:
        return RepositoryFileKind.CODE
    return None


def is_rst_title(lines: list[str], i: int) -> bool:
    """
    Check whether a line is a reStructuredText title: text, underlined by a line at least as long.

    :param lines: The document's lines.
    :param i: The index of the line to check.
    :returns: True if the line has text, is not itself an underline, and the next line underlines it.
    """
    line = lines[i]
    text = line.strip()
    if not text:
        return False
    if RST_UNDERLINE.match(line):
        return False
    next_index = i + 1
    if next_index >= len(lines):
        return False
    underline = lines[next_index]
    if not RST_UNDERLINE.match(underline):
        return False
    return len(underline.strip()) >= len(text)


def document_title(content: str) -> str:
    """
    Return a document's first heading, in reStructuredText or Markdown.

    Only the first 60 lines are read: a heading further down is a section's, not the document's.
    The title is stored with the file, and a search ranks a file whose title matches a term higher.

    :param content: The document.
    :returns: The heading, cut at :data:`MAX_TITLE_LENGTH` characters, or an empty string if it has none.
    """
    lines = content.splitlines()[:60]
    for i, line in enumerate(lines):
        match = MARKDOWN_HEADING.match(line)
        if match:
            heading = match.group(1)
            return heading[:MAX_TITLE_LENGTH]
        if is_rst_title(lines, i):
            heading = line.strip()
            return heading[:MAX_TITLE_LENGTH]
    return ""


def markdown_image(description: str, url: str, prefix_length: int = 0) -> tuple[str, bool]:
    """
    Return a Markdown image, ``![description](url)``, that fits on one line of a search's passage.

    The LLM cannot see an image, so its description, e.g. its alt text, is what tells the LLM
    what it shows, and Smarter Chat displays the image when the LLM includes it in an answer.
    A search clips a line longer than :data:`MAX_IMAGE_LINE_LENGTH`, which would break the image's
    Markdown, so a long description is shortened at a word, rather than the line clipped.

    :param description: What the image shows. Brackets become parentheses, which Markdown allows.
        An empty description becomes ``Illustration``.
    :param url: The image's url.
    :param prefix_length: The length of the text before the image on its line.
    :returns: The image, and whether its description is complete. A description that does not
        fit within :data:`MAX_IMAGE_LINE_LENGTH` is shortened, and ends with an ellipsis. If fewer
        than 20 characters are left for it, it is replaced by ``Illustration``.
    """
    collapsed = WHITESPACE.sub(" ", description).strip()
    text = collapsed.replace("[", "(").replace("]", ")")
    if not text:
        text = "Illustration"
    budget = MAX_IMAGE_LINE_LENGTH - prefix_length - len(url) - len("![](…)")
    if len(text) <= budget:
        image = f"![{text}]({url})"
        return image, True

    short = ""
    if budget >= 20:
        cut = text[:budget]
        whole_words = cut.rsplit(" ", 1)[0]
        short = whole_words.rstrip(",;:.")
    if short:
        image = f"![{short}…]({url})"
    else:
        image = f"![Illustration]({url})"
    return image, False


def documentation_image_url(repository: ProjectRepository, target: str) -> Optional[str]:
    """
    Return the published url of an image of a repository's Sphinx documentation.

    Sphinx copies a local image to the ``_images/`` folder of the built site, by its file name.
    A target that is already a url is kept, unless it is a status badge.

    :param repository: The repository.
    :param target: The image directive's argument, e.g. ``/_static/api-key-claude.png``, or a url.
    :returns: The url, or None for a status badge, an empty target, a target with characters that
        would break a Markdown image, ``()<>``, or a local image of a repository without published
        documentation.
    """
    if target.startswith(("http://", "https://")):
        host = urlparse(target).hostname
        if host in BADGE_HOSTS:
            return None
        return target
    if not target:
        return None
    if not repository.docs_url:
        return None
    for character in "()<>":
        if character in target:
            return None
    filename = posixpath.basename(target)
    url = f"{repository.docs_url}_images/{filename}"
    return url


def is_published_rst(repository: ProjectRepository, file: ArchiveFile) -> bool:
    """
    Check whether a file is a reStructuredText source of a repository's published Sphinx documentation.

    :param repository: The repository, whose :attr:`~ProjectRepository.docs_root` is where its Sphinx
        sources are, e.g. ``docs/source``, or None if it publishes none.
    :param file: The file.
    :returns: True if the file is an ``.rst`` file under the repository's ``docs_root``.
    """
    if not repository.docs_root:
        return False
    docs_folder = repository.docs_root.rstrip("/") + "/"
    if not file.path.startswith(docs_folder):
        return False
    return file.path.endswith(".rst")


def image_description(lines: list[str], start: int, indent: int, is_figure: bool) -> str:
    """
    Read the description of an image from its directive's options, or a figure's caption.

    The directive's body is the lines after it that are blank or indented more than it. Its options,
    e.g. ``:alt: The console``, come first, and a figure's caption is the first line of text after
    a blank line.

    :param lines: The file's lines.
    :param start: The index of the first line after the directive and its target.
    :param indent: The directive's indentation, in characters.
    :param is_figure: Whether the directive is a ``figure``, which may have a caption.
    :returns: The ``:alt:`` option's value, or else the caption, or an empty string if there is neither.
    """
    alt = ""
    caption = ""
    blank = False
    j = start
    while j < len(lines):
        line = lines[j]
        text = line.strip()
        if text and indentation(line) <= indent:
            break
        option = RST_OPTION.match(line)
        if not text:
            blank = True
        elif option and not blank:
            if option.group("name") == "alt":
                alt = option.group("value")
        elif blank and not caption and is_figure:
            caption = text
        j += 1
    if alt:
        return alt
    return caption


def link_documentation_images(repository: ProjectRepository, file: ArchiveFile) -> ArchiveFile:
    """
    Append a Markdown image to each ``image`` and ``figure`` directive of a Sphinx source file.

    An LLM cannot turn ``.. image:: /_static/x.png`` into a link, so the line that names the
    image gets its published url, as a Markdown image whose description is the directive's
    ``:alt:``, or else a figure's caption. The image is appended to the line, rather than added on a
    line of its own, so that line numbers still match the file on GitHub.

    :param repository: The repository.
    :param file: The file.
    :returns: A copy of the file, with its images linked, or the file unchanged if it is not a
        reStructuredText file of the repository's published documentation, or has no image to link.
    """
    if not is_published_rst(repository, file):
        return file
    lines = file.content.split("\n")
    changed = False
    for i, line in enumerate(lines):
        match = RST_IMAGE_DIRECTIVE.match(line)
        if not match:
            continue
        indent = len(match.group("indent"))
        is_figure = match.group("directive") == "figure"

        # The directive's argument is on its own line, or else on the next, indented line.
        target = match.group("target")
        target_line = i
        body_start = i + 1
        if not target and body_start < len(lines):
            next_line = lines[body_start]
            if indentation(next_line) > indent and not RST_OPTION.match(next_line):
                target = next_line.strip()
                target_line = body_start
                body_start = body_start + 1

        url = documentation_image_url(repository, target)
        if url is None:
            continue
        description = image_description(lines, body_start, indent, is_figure)
        prefix = lines[target_line].rstrip() + "  "
        image, _ = markdown_image(description, url, prefix_length=len(prefix))
        lines[target_line] = prefix + image
        changed = True

    if not changed:
        return file
    content = "\n".join(lines)
    size = len(content.encode())
    linked = file.model_copy(update={"content": content, "size": size})
    return linked


def indentation(line: str) -> int:
    """
    Return the number of whitespace characters before a line's text.

    :param line: The line.
    :returns: The indentation. A blank line's is its length.
    """
    return len(line) - len(line.lstrip())


def decode_text(data: bytes) -> Optional[str]:
    """
    Return a file's bytes as text, or None if it is binary.

    A file with a NUL byte, or that is not valid UTF-8, is taken to be binary, e.g. an image.

    :param data: The file's content.
    :returns: The text, or None.
    """
    if b"\x00" in data:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text


def read_archive(archive: IO[bytes]) -> Iterator[ArchiveFile]:
    """
    Read the indexable text files of a repository's gzipped tar archive.

    GitHub's archives contain one top-level folder, ``<repository>-<commit>/``, which is
    removed from the paths. Only regular files are read: links, which could point outside
    the repository, are skipped. Nothing is extracted to disk. A file is skipped if
    :func:`file_kind` does not index it, it is larger than :data:`MAX_FILE_BYTES`, it is binary,
    or it is blank.

    :param archive: The archive, positioned at its start.
    :returns: The files, in the archive's order.
    :raises SmarterMCPServerIndexError: If the archive cannot be read.
    """
    try:
        with tarfile.open(fileobj=archive, mode="r:gz") as tar:
            for member in tar:
                if not member.isfile():
                    continue
                if "/" not in member.name:
                    continue
                path = member.name.split("/", 1)[1]
                kind = file_kind(path)
                if kind is None:
                    continue
                if member.size > MAX_FILE_BYTES:
                    continue
                extracted = tar.extractfile(member)
                if extracted is None:
                    continue
                data = extracted.read(MAX_FILE_BYTES + 1)
                content = decode_text(data)
                if content is None:
                    continue
                if not content.strip():
                    continue
                title = ""
                if kind == RepositoryFileKind.DOCUMENTATION:
                    title = document_title(content)
                yield ArchiveFile(
                    path=path,
                    kind=kind,
                    title=title,
                    content=content,
                    size=member.size,
                    line_count=count_lines(content),
                )
    except (tarfile.TarError, OSError, EOFError) as e:
        raise SmarterMCPServerIndexError(f"the archive could not be read: {e}") from e


def latest_commit_sha(repository: ProjectRepository) -> str:
    """
    Return the latest commit of a repository's branch, from the GitHub api.

    The request asks for the ``application/vnd.github.sha`` media type, so that GitHub answers with
    the 40 characters of the sha alone, not the commit's JSON.

    Side effects: one unauthenticated HTTP request to the GitHub api.

    :param repository: The repository.
    :returns: The commit's sha.
    :raises SmarterMCPServerIndexError: If GitHub cannot be reached, or does not answer with a commit.
    """
    headers = {"Accept": "application/vnd.github.sha", "User-Agent": USER_AGENT}
    try:
        response = requests.get(repository.commit_api_url, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.RequestException as e:
        raise SmarterMCPServerIndexError(f"GitHub could not be reached: {type(e).__name__}") from e
    sha = response.text.strip()
    is_ok = response.status_code == 200
    is_sha = re.fullmatch(r"[0-9a-f]{40}", sha) is not None
    if not is_ok or not is_sha:
        raise SmarterMCPServerIndexError(
            f"GitHub responded with HTTP {response.status_code} for the latest commit of {repository.full_name}"
        )
    return sha


def download_archive(repository: ProjectRepository, commit_sha: str, destination: IO[bytes]) -> int:
    """
    Download a repository's gzipped tar archive at a commit.

    The archive is streamed, a chunk at a time, so that it is never wholly in memory, and the
    download stops as soon as it is larger than :data:`MAX_ARCHIVE_BYTES`.

    Side effects: one HTTP request to GitHub's codeload service, and writes to ``destination``.

    :param repository: The repository.
    :param commit_sha: The commit.
    :param destination: A binary file to write the archive to. It is left positioned at its start,
        ready for :func:`read_archive`.
    :returns: The archive's size, in bytes.
    :raises SmarterMCPServerIndexError: If the download fails, or the archive is larger than :data:`MAX_ARCHIVE_BYTES`.
    """
    url = repository.archive_url(commit_sha)
    headers = {"User-Agent": USER_AGENT}
    size = 0
    try:
        with requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True) as response:
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

    The limits keep one very large repository from filling the database. The files are read in the
    archive's order, and the first file that would exceed a limit ends the list.

    :param archive: The archive.
    :returns: The files. Files beyond the limits are left out, and a warning is logged.
    :raises SmarterMCPServerIndexError: If the archive cannot be read.
    """
    files: list[ArchiveFile] = []
    total = 0
    for file in read_archive(archive):
        too_many = len(files) >= MAX_FILES
        too_large = total + file.size > MAX_INDEX_BYTES
        if too_many or too_large:
            logger.warning(
                "%s.collect_files() the index limit was reached at %s files and %s bytes: the remaining files are not indexed.",
                logger_prefix,
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

    The old files are deleted and the new ones inserted, in batches of :data:`BATCH_SIZE`, and the
    index is marked ready, at the commit, with its counts, and with no error. Since it is one
    transaction, a search sees either the old files or the new ones, never a mix.

    Side effects: database writes: deletes and inserts of
    :class:`~smarter.apps.mcpserver.models.RepositoryFile` rows, and an update of the index.

    :param index: The repository's index.
    :param commit_sha: The commit that the files are of. The blog's indexer passes a fingerprint
        of its posts instead.
    :param files: The files.
    :returns: The index, ready to search.
    """
    rows = []
    total_bytes = 0
    for file in files:
        row = RepositoryFile(
            index=index,
            path=file.path,
            kind=file.kind,
            title=file.title,
            content=file.content,
            size=file.size,
            line_count=file.line_count,
        )
        rows.append(row)
        total_bytes += file.size

    with transaction.atomic():
        RepositoryFile.objects.filter(index=index).delete()
        RepositoryFile.objects.bulk_create(rows, batch_size=BATCH_SIZE)
        index.commit_sha = commit_sha
        index.status = RepositoryIndexStatus.READY
        index.indexed_at = timezone.now()
        index.file_count = len(files)
        index.total_bytes = total_bytes
        index.error = None
        index.save()
    return index


def index_repository(name: str, force: bool = False) -> RepositoryIndex:
    """
    Bring a repository's index up to date with the latest commit of its branch.

    If the latest commit is already indexed, only a previous error is cleared. Otherwise the
    archive is downloaded to a temporary file, which is deleted afterwards, and its files replace
    the index's (see the module's description for the steps).

    A failure never raises: the index keeps its files, and stays ready if it was, so that the tools
    can go on answering from the previous commit, and the failure is recorded in its ``error``.

    Side effects: HTTP requests to GitHub (see :func:`latest_commit_sha` and :func:`download_archive`),
    a temporary file, database writes (the index's row is created if it does not exist, and see
    :func:`store_files`), and a signal: ``mcpserver_repository_indexed`` when the files are replaced,
    whose receiver makes the cached tool results stale, or ``mcpserver_repository_index_failed``.

    :param name: The repository's name, e.g. ``smarter-cli``.
    :param force: Index the repository even if its latest commit is already indexed.
    :returns: The repository's index. If indexing fails, its ``error`` says why, and an
        existing index is kept.
    :raises SmarterMCPServerIndexError: If there is no such repository.

    **Example usage**::

        index = index_repository("smarter-cli")
        index.status  # 'ready'
    """
    repository = get_repository(name)
    if repository is None:
        raise SmarterMCPServerIndexError(f"{name} is not a repository of The Smarter Project.")
    index, _ = RepositoryIndex.objects.get_or_create(repository=repository.name)
    try:
        commit_sha = latest_commit_sha(repository)
        is_up_to_date = index.is_ready and index.commit_sha == commit_sha
        if is_up_to_date and not force:
            logger.info("%s.index_repository() %s is up to date at %s.", logger_prefix, repository.name, commit_sha)
            if index.error:
                RepositoryIndex.objects.filter(pk=index.pk).update(error=None)
                index.error = None
            return index
        with tempfile.TemporaryFile() as archive:
            size = download_archive(repository, commit_sha, archive)
            logger.info(
                "%s.index_repository() downloaded %s at %s: %s bytes.",
                logger_prefix,
                repository.full_name,
                commit_sha,
                size,
            )
            archive_files = collect_files(archive)
            files = [link_documentation_images(repository, file) for file in archive_files]
        index = store_files(index, commit_sha, files)
    except SmarterMCPServerIndexError as e:
        # Keep a ready index ready, so that its files are still searched.
        if index.is_ready:
            status = RepositoryIndexStatus.READY
        else:
            status = RepositoryIndexStatus.FAILED
        RepositoryIndex.objects.filter(pk=index.pk).update(status=status, error=e.message)
        index.refresh_from_db()
        mcpserver_repository_index_failed.send(sender=index_repository, repository=repository.name, error=e.message)
        return index
    mcpserver_repository_indexed.send(sender=index_repository, index=index)
    return index


__all__ = [
    "ArchiveFile",
    "collect_files",
    "count_lines",
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
