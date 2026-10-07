"""Test the text extraction of documents: :mod:`smarter.apps.vectorstore.extract`."""

import io

from pypdf import PdfWriter

from smarter.apps.vectorstore.extract import (
    MAX_DOCUMENT_BYTES,
    VectorstoreExtractionError,
    content_type_for,
    extract_text,
)
from smarter.apps.vectorstore.models import PAGE_BREAK
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import DATA_PATH


class TestExtract(SmarterTestBase):
    """Test extract_text() and content_type_for()."""

    def test_content_type(self):
        self.assertEqual(content_type_for("a.pdf"), "application/pdf")
        self.assertEqual(content_type_for("notes.MD"), "text/markdown")
        self.assertEqual(content_type_for("x", "text/html; charset=utf-8"), "text/html")
        self.assertEqual(content_type_for("https://example.com/page.html?x=1"), "text/html")

    def test_pdf(self):
        """Test that a PDF's pages are extracted, separated by PAGE_BREAK."""
        with open(f"{DATA_PATH}/two-pages.pdf", "rb") as f:
            text, media_type = extract_text("two-pages.pdf", f.read())
        self.assertEqual(media_type, "application/pdf")
        pages = text.split(PAGE_BREAK)
        self.assertEqual(len(pages), 2)
        self.assertIn("Smarter", pages[0])
        self.assertIn("Qdrant", pages[1])

    def test_text_and_html(self):
        text, _ = extract_text("notes.md", b"# Title\n\nSome *markdown*.")
        self.assertIn("Some *markdown*.", text)
        html = b"<html><head><style>p{}</style><script>alert(1)</script></head><body><p>Hello &amp; welcome</p></body></html>"
        text, media_type = extract_text("page.html", html)
        self.assertEqual(media_type, "text/html")
        self.assertEqual(text, "Hello & welcome")

    def test_refused(self):
        """Test that unsupported, empty, unreadable and oversized documents are refused."""
        for name, data in (
            ("a.docx", b"PK\x03\x04"),
            ("empty.txt", b"   "),
            ("bad.pdf", b"not a pdf"),
            ("big.txt", b"x" * (MAX_DOCUMENT_BYTES + 1)),
        ):
            with self.subTest(name=name), self.assertRaises(VectorstoreExtractionError):
                extract_text(name, data)

    def test_scanned_pdf(self):
        """Test that a PDF without text, e.g. a scanned one, is refused."""
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        buffer = io.BytesIO()
        writer.write(buffer)
        with self.assertRaisesRegex(VectorstoreExtractionError, "no text"):
            extract_text("scan.pdf", buffer.getvalue())
