"""Test the documents of a request: :mod:`smarter.apps.vectorstore.sources`."""

from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.datastructures import MultiValueDict

from smarter.apps.llmtool.plugin.safe_http import SafeResponse
from smarter.apps.vectorstore.extract import MAX_DOCUMENT_BYTES
from smarter.apps.vectorstore.sources import (
    DocumentSource,
    request_files,
    request_metadata,
    request_sources,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


def files(field: str, *uploads: SimpleUploadedFile) -> MultiValueDict:
    """A request's FILES, with the uploads in one field."""
    return MultiValueDict({field: list(uploads)})


class TestRequestSources(SmarterTestBase):
    """The documents that a request carries, and their metadata."""

    def test_files_then_text_then_url(self):
        """Uploaded files come first, then text, then the page at a url, which is fetched safely."""
        uploads = files(
            "files",
            SimpleUploadedFile("a.md", b"# A", content_type="text/markdown"),
            SimpleUploadedFile("b.txt", b"B", content_type="text/plain"),
        )
        page = SafeResponse(
            url="https://example.com/faq.html",
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b"<p>FAQ</p>",
        )
        data = {"text": "Refunds within 30 days.", "name": "refunds", "url": "https://example.com/faq.html"}
        with patch("smarter.apps.vectorstore.sources.fetch", return_value=page) as fetch:
            sources = list(request_sources(uploads, data))
        fetch.assert_called_once_with("https://example.com/faq.html", max_bytes=MAX_DOCUMENT_BYTES)
        self.assertEqual(
            sources,
            [
                DocumentSource("a.md", b"# A", None, "text/markdown", "upload"),
                DocumentSource("b.txt", b"B", None, "text/plain", "upload"),
                DocumentSource("refunds", None, "Refunds within 30 days.", "text/plain", "text"),
                DocumentSource("https://example.com/faq.html", b"<p>FAQ</p>", None, "text/html", "url"),
            ],
        )

    def test_the_file_field_and_unnamed_text(self):
        """A single upload may be in the field file, and text without a name is named text."""
        uploads = files("file", SimpleUploadedFile("a.md", b"# A"))
        self.assertEqual([f.name for f in request_files(uploads)], ["a.md"])
        sources = list(request_sources(MultiValueDict(), {"text": "Hello."}))
        self.assertEqual([(s.name, s.source) for s in sources], [("text", "text")])
        self.assertEqual(list(request_sources(MultiValueDict(), {})), [])

    def test_a_file_that_is_too_large(self):
        """A file larger than the limit is refused before it is read."""
        upload = SimpleUploadedFile("huge.pdf", b"x")
        upload.size = MAX_DOCUMENT_BYTES + 1
        with self.assertRaisesRegex(ValueError, "huge.pdf is larger than 50 MiB"):
            list(request_sources(files("files", upload), {}))

    def test_metadata(self):
        """Metadata is a JSON object, or its text in a multipart form."""
        self.assertEqual(request_metadata({"metadata": {"source": "faq"}}), {"source": "faq"})
        self.assertEqual(request_metadata({"metadata": '{"source": "faq"}'}), {"source": "faq"})
        self.assertIsNone(request_metadata({}))
        self.assertIsNone(request_metadata({"metadata": ""}))
        for invalid in ("[1, 2]", "{not json", 7):
            with self.subTest(metadata=invalid), self.assertRaisesRegex(ValueError, "must be a JSON object"):
                request_metadata({"metadata": invalid})
