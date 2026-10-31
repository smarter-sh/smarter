"""
Tests for smarter.apps.mcpserver.index.indexer.

GitHub is never contacted: ``requests.get`` is replaced, and serves archives built by
:func:`.base_classes.build_archive`.
"""

import io
import tarfile
from unittest import mock

import requests

from smarter.apps.mcpserver.exceptions import SmarterMCPServerIndexError
from smarter.apps.mcpserver.index import indexer
from smarter.apps.mcpserver.index.indexer import (
    ArchiveFile,
    collect_files,
    decode_text,
    document_title,
    download_archive,
    file_kind,
    index_repository,
    latest_commit_sha,
    link_documentation_images,
    markdown_image,
    read_archive,
)
from smarter.apps.mcpserver.models import (
    RepositoryFile,
    RepositoryFileKind,
    RepositoryIndex,
    RepositoryIndexStatus,
)
from smarter.apps.mcpserver.signals import (
    mcpserver_repository_index_failed,
    mcpserver_repository_indexed,
)

from .base_classes import (
    COMMIT_SHA,
    DOCS_URL,
    NEW_COMMIT_SHA,
    MCPServerTestBase,
    build_archive,
)

REQUESTS_PATCH = "smarter.apps.mcpserver.index.indexer.requests.get"


class FakeResponse:
    """A requests response, for a fake GitHub."""

    def __init__(self, status_code: int = 200, text: str = "", content: bytes = b""):
        self.status_code = status_code
        self.text = text
        self.content = content

    def iter_content(self, chunk_size: int):
        for start in range(0, len(self.content), chunk_size):
            yield self.content[start : start + chunk_size]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_github(commit_sha: str, archive: bytes, commit_status: int = 200, archive_status: int = 200):
    """Return a replacement of requests.get that answers like GitHub's api and codeload."""

    def get(url, **kwargs):
        if url.startswith("https://api.github.com/"):
            return FakeResponse(commit_status, text=commit_sha + "\n")
        if url.startswith("https://codeload.github.com/"):
            return FakeResponse(archive_status, content=archive)
        raise AssertionError(f"unexpected url {url}")

    return get


ARCHIVE_FILES = {
    "README.md": b"# Fresh Readme\n\nThe new version.\n",
    "docs/source/index.rst": b"Fresh Index\n===========\n\nIndexed again.\n",
    "src/main.py": b"def main():\n    return 'apply'\n",
    "Makefile": b"build:\n\techo build\n",
    "LICENSE": b"A license.\n",
    "node_modules/library/index.js": b"module.exports = 1;\n",
    "static/app.min.js": b"var a=1;\n",
    "smarter/static/assets/plugins/bundle.js": b"var vendored=1;\n",
    "package-lock.json": b"{}\n",
    "image.png": b"\x89PNG\r\n\x1a\n",
    "binary.py": b"\x00\x01\x02",
    "latin1.txt": b"r\xe9sum\xe9",
    "empty.py": b"   \n",
    "big.py": b"x" * (indexer.MAX_FILE_BYTES + 1),
}
"""Files of a fresh archive: the first five are indexed, and the others are skipped."""
INDEXED_PATHS = {"README.md", "docs/source/index.rst", "src/main.py", "Makefile", "LICENSE"}


class TestIndexerHelpers(MCPServerTestBase):
    """Test what the indexer keeps, and how it reads an archive."""

    def test_file_kind(self):
        """Documentation and code are indexed.

        Vendored, generated, lock and binary files are not.
        """
        documentation, code = RepositoryFileKind.DOCUMENTATION, RepositoryFileKind.CODE
        cases = {
            "README.md": documentation,
            "docs/source/index.rst": documentation,
            "notes.txt": documentation,
            "LICENSE": documentation,
            "smarter/apps/models.py": code,
            "cmd/apply.go": code,
            "Makefile": code,
            "Dockerfile": code,
            "helm/templates/_helpers.tpl": code,
            "main.tf": code,
            "image.png": None,
            "node_modules/x/index.js": None,
            "a/__pycache__/x.py": None,
            "app.min.js": None,
            "site/plugins.bundle.css": None,
            "smarter/static/assets/x.js": None,
            "package-lock.json": None,
            "go.sum": None,
            "poetry.lock": None,
        }
        for path, kind in cases.items():
            with self.subTest(path=path):
                self.assertEqual(file_kind(path), kind)

    def test_document_title(self):
        """The first reStructuredText or Markdown heading is a document's title."""
        self.assertEqual(document_title("Custom Domains\n==============\n\ntext"), "Custom Domains")
        self.assertEqual(document_title(".. comment\n\nTitle\n-----\n"), "Title")
        self.assertEqual(document_title("====\nOver\n====\n"), "Over")
        self.assertEqual(document_title("# Getting Started\n\ntext"), "Getting Started")
        self.assertEqual(document_title("## Second ##\n"), "Second")
        self.assertEqual(document_title("Too long\n===\n"), "")
        self.assertEqual(document_title("no heading here\n"), "")

    def test_decode_text(self):
        """Only utf-8 text without NUL bytes is text."""
        self.assertEqual(decode_text("héllo".encode()), "héllo")
        self.assertIsNone(decode_text(b"a\x00b"))
        self.assertIsNone(decode_text(b"r\xe9sum\xe9"))

    def test_read_archive(self):
        """The indexable text files are read, without the archive's top-level folder."""
        archive = io.BytesIO(build_archive("repo", COMMIT_SHA, ARCHIVE_FILES))
        files = {file.path: file for file in read_archive(archive)}
        self.assertEqual(set(files), INDEXED_PATHS)
        self.assertEqual(files["README.md"].title, "Fresh Readme")
        self.assertEqual(files["README.md"].kind, RepositoryFileKind.DOCUMENTATION)
        self.assertEqual(files["src/main.py"].title, "")
        self.assertEqual(files["src/main.py"].line_count, 2)
        self.assertEqual(files["src/main.py"].size, len(ARCHIVE_FILES["src/main.py"]))

    def test_read_archive_skips_links(self):
        """Symbolic links, which could point outside the repository, are not read."""
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            link = tarfile.TarInfo(f"repo-{COMMIT_SHA}/passwd.txt")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            tar.addfile(link)
            info = tarfile.TarInfo("top-level.md")
            content = b"# outside the root folder\n"
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
        buffer.seek(0)
        self.assertEqual(list(read_archive(buffer)), [])

    def test_read_archive_rejects_a_corrupt_archive(self):
        """An archive that is not a gzipped tar file fails."""
        with self.assertRaises(SmarterMCPServerIndexError):
            list(read_archive(io.BytesIO(b"not an archive")))

    def test_collect_files_limits(self):
        """Files beyond the maximum number, or the maximum total size, are left out."""
        archive = build_archive("repo", COMMIT_SHA, ARCHIVE_FILES)
        with mock.patch.object(indexer, "MAX_FILES", 2):
            self.assertEqual(len(collect_files(io.BytesIO(archive))), 2)
        with mock.patch.object(indexer, "MAX_INDEX_BYTES", len(ARCHIVE_FILES["README.md"])):
            self.assertEqual([file.path for file in collect_files(io.BytesIO(archive))], ["README.md"])

    def test_latest_commit_sha(self):
        """The GitHub api answers with the sha of the branch's latest commit."""
        with mock.patch(REQUESTS_PATCH, side_effect=fake_github(NEW_COMMIT_SHA, b"")) as get:
            self.assertEqual(latest_commit_sha(self.docs_repository), NEW_COMMIT_SHA)
        self.assertEqual(get.call_args.kwargs["headers"]["Accept"], "application/vnd.github.sha")
        for status, sha in ((404, NEW_COMMIT_SHA), (200, "<html>rate limited</html>")):
            with self.subTest(status=status), mock.patch(REQUESTS_PATCH, side_effect=fake_github(sha, b"", status)):
                with self.assertRaises(SmarterMCPServerIndexError):
                    latest_commit_sha(self.docs_repository)
        with mock.patch(REQUESTS_PATCH, side_effect=requests.exceptions.ConnectionError("down")):
            with self.assertRaises(SmarterMCPServerIndexError):
                latest_commit_sha(self.docs_repository)

    def test_download_archive(self):
        """The archive is streamed to a file, and refused when it is too large or GitHub fails."""
        archive = build_archive("repo", NEW_COMMIT_SHA, ARCHIVE_FILES)
        destination = io.BytesIO()
        with mock.patch(REQUESTS_PATCH, side_effect=fake_github(NEW_COMMIT_SHA, archive)):
            self.assertEqual(download_archive(self.docs_repository, NEW_COMMIT_SHA, destination), len(archive))
        self.assertEqual(destination.read(), archive)
        with (
            mock.patch(REQUESTS_PATCH, side_effect=fake_github(NEW_COMMIT_SHA, archive)),
            mock.patch.object(indexer, "MAX_ARCHIVE_BYTES", 10),
        ):
            with self.assertRaises(SmarterMCPServerIndexError):
                download_archive(self.docs_repository, NEW_COMMIT_SHA, io.BytesIO())
        with mock.patch(REQUESTS_PATCH, side_effect=fake_github(NEW_COMMIT_SHA, archive, archive_status=404)):
            with self.assertRaises(SmarterMCPServerIndexError):
                download_archive(self.docs_repository, NEW_COMMIT_SHA, io.BytesIO())
        with mock.patch(REQUESTS_PATCH, side_effect=requests.exceptions.ReadTimeout("slow")):
            with self.assertRaises(SmarterMCPServerIndexError):
                download_archive(self.docs_repository, NEW_COMMIT_SHA, io.BytesIO())


RST_WITH_IMAGES = """\
Guide
=====

.. image:: /_static/api-key-claude.png
   :alt: The [API keys] page

.. figure::
   https://cdn.example.com/pre-commit.png
   :alt: pre-commit output

   pre-commit output

.. figure:: https://cdn.example.com/naming.png
  :align: center

  How resources are named.

.. image:: https://img.shields.io/badge/x-y-blue
   :alt: A badge

.. image:: _static/diagram.svg

    .. image:: https://cdn.example.com/indented.png
       :alt: Indented
Text after."""


class TestDocumentationImages(MCPServerTestBase):
    """Test the Markdown images of the Sphinx documentation's image directives."""

    def rst_file(self, path: str = "docs/source/guide.rst", content: str = RST_WITH_IMAGES) -> ArchiveFile:
        return ArchiveFile(
            path=path,
            kind=RepositoryFileKind.DOCUMENTATION,
            title="Guide",
            content=content,
            size=len(content.encode()),
            line_count=content.count("\n") + 1,
        )

    def test_markdown_image(self):
        """A description that does not fit on the line is shortened, and one that cannot fit is an Illustration."""
        self.assertEqual(markdown_image("A [b]  c", "https://x/y.png"), ("![A (b) c](https://x/y.png)", True))
        self.assertEqual(markdown_image("", "https://x/y.png"), ("![Illustration](https://x/y.png)", True))
        image, complete = markdown_image("word " * 100, "https://x/y.png")
        self.assertFalse(complete)
        self.assertTrue(image.endswith("…](https://x/y.png)"))
        self.assertLessEqual(len(image), indexer.MAX_IMAGE_LINE_LENGTH)
        self.assertEqual(
            markdown_image("word " * 10, "https://x/y.png", prefix_length=220),
            ("![Illustration](https://x/y.png)", False),
        )

    def test_link_documentation_images(self):
        """Each image gets its published url on the line that names it, so line numbers do not change."""
        file = link_documentation_images(self.docs_repository, self.rst_file())
        lines = file.content.split("\n")
        self.assertEqual(len(lines), len(RST_WITH_IMAGES.split("\n")))
        self.assertEqual(file.size, len(file.content.encode()))
        self.assertEqual(
            lines[3],
            f".. image:: /_static/api-key-claude.png  ![The (API keys) page]({DOCS_URL}_images/api-key-claude.png)",
        )
        self.assertEqual(
            lines[7],
            "   https://cdn.example.com/pre-commit.png  ![pre-commit output](https://cdn.example.com/pre-commit.png)",
        )
        self.assertTrue(lines[12].endswith("![How resources are named.](https://cdn.example.com/naming.png)"))
        self.assertNotIn("![", lines[17])
        self.assertTrue(lines[20].endswith(f"![Illustration]({DOCS_URL}_images/diagram.svg)"))
        self.assertTrue(lines[22].endswith("![Indented](https://cdn.example.com/indented.png)"))

    def test_files_that_are_not_published_documentation(self):
        """Files outside docs_root, files that are not reStructuredText, and repositories without docs are unchanged."""
        for repository, file in (
            (self.code_repository, self.rst_file()),
            (self.docs_repository, self.rst_file(path="README.rst")),
            (self.docs_repository, self.rst_file(path="docs/source/guide.md")),
            (self.docs_repository, self.rst_file(content="No images here.")),
        ):
            with self.subTest(repository=repository.name, path=file.path):
                self.assertIs(link_documentation_images(repository, file), file)

    def test_local_images_of_a_repository_without_published_documentation(self):
        """A local image has no url without published documentation, and a remote one keeps its own."""
        repository = self.code_repository.model_copy(update={"docs_root": "docs/source"})
        lines = link_documentation_images(repository, self.rst_file()).content.split("\n")
        self.assertNotIn("![", lines[3])
        self.assertIn("![pre-commit output](https://cdn.example.com/pre-commit.png)", lines[7])


class TestIndexRepository(MCPServerTestBase):
    """Test index_repository(), on the unindexed test repository."""

    def setUp(self):
        super().setUp()
        self.addCleanup(RepositoryIndex.objects.filter(repository=self.unindexed_repository.name).delete)
        self.archive = build_archive(self.unindexed_repository.name, NEW_COMMIT_SHA, ARCHIVE_FILES)

    def index(self, commit_sha: str = NEW_COMMIT_SHA, force: bool = False, **github) -> RepositoryIndex:
        with mock.patch(REQUESTS_PATCH, side_effect=fake_github(commit_sha, self.archive, **github)) as get:
            index = index_repository(self.unindexed_repository.name, force=force)
        self.requested_urls = [call.args[0] for call in get.call_args_list]
        return index

    def test_index_repository(self):
        """A new repository is indexed, and the signal is sent."""
        received = []

        def receiver(sender, index, **kwargs):
            received.append(index)

        mcpserver_repository_indexed.connect(receiver)
        self.addCleanup(mcpserver_repository_indexed.disconnect, receiver)
        index = self.index()
        self.assertEqual(index.status, RepositoryIndexStatus.READY)
        self.assertEqual(index.commit_sha, NEW_COMMIT_SHA)
        self.assertEqual(index.file_count, len(INDEXED_PATHS))
        self.assertEqual(index.total_bytes, sum(len(ARCHIVE_FILES[path]) for path in INDEXED_PATHS))
        self.assertIsNotNone(index.indexed_at)
        self.assertIsNone(index.error)
        self.assertEqual(set(RepositoryFile.objects.filter(index=index).values_list("path", flat=True)), INDEXED_PATHS)
        self.assertEqual(received, [index])
        self.assertTrue(index.is_ready)
        self.assertIn(self.unindexed_repository.name, str(index))

    def test_up_to_date_repository_is_not_downloaded(self):
        """A repository whose branch has not moved costs one request to the GitHub api."""
        self.index()
        RepositoryIndex.objects.filter(repository=self.unindexed_repository.name).update(error="an old error")
        index = self.index()
        self.assertEqual(len(self.requested_urls), 1)
        self.assertTrue(self.requested_urls[0].startswith("https://api.github.com/"))
        self.assertIsNone(index.error)
        self.assertIsNone(RepositoryIndex.objects.get(pk=index.pk).error)

    def test_force(self):
        """Force downloads the archive again."""
        self.index()
        self.index(force=True)
        self.assertEqual(len(self.requested_urls), 2)

    def test_new_commit_replaces_the_files(self):
        """A new commit replaces every file of the index."""
        self.index()
        self.archive = build_archive(self.unindexed_repository.name, COMMIT_SHA, {"only.md": b"# Only\n"})
        index = self.index(commit_sha=COMMIT_SHA)
        self.assertEqual(index.commit_sha, COMMIT_SHA)
        self.assertEqual(list(RepositoryFile.objects.filter(index=index).values_list("path", flat=True)), ["only.md"])

    def test_failure_of_a_new_repository(self):
        """A repository that cannot be indexed, and has no index, fails, and the signal is sent."""
        received = []

        def receiver(sender, repository, error, **kwargs):
            received.append((repository, error))

        mcpserver_repository_index_failed.connect(receiver)
        self.addCleanup(mcpserver_repository_index_failed.disconnect, receiver)
        index = self.index(commit_status=500)
        self.assertEqual(index.status, RepositoryIndexStatus.FAILED)
        self.assertIn("HTTP 500", index.error)
        self.assertEqual(received, [(self.unindexed_repository.name, index.error)])
        self.assertFalse(index.is_ready)

    def test_failure_keeps_an_existing_index(self):
        """A failed refresh keeps the existing index, and records why it failed."""
        self.index()
        index = self.index(commit_sha=COMMIT_SHA, archive_status=502)
        self.assertEqual(index.status, RepositoryIndexStatus.READY)
        self.assertEqual(index.commit_sha, NEW_COMMIT_SHA)
        self.assertIn("HTTP 502", index.error)
        self.assertEqual(RepositoryFile.objects.filter(index=index).count(), len(INDEXED_PATHS))

    def test_unknown_repository(self):
        """Only The Smarter Project's repositories are indexed."""
        with self.assertRaises(SmarterMCPServerIndexError):
            index_repository("not-a-repository")
