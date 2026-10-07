"""
Extract the text of a document, so that it can be split, embedded, and loaded into a vectorstore.

PDFs are read with `pypdf <https://pypdf.readthedocs.io/>`__, one page at a time, and their pages
are joined with :data:`~smarter.apps.vectorstore.models.PAGE_BREAK`, so that each chunk records
its page. Text, Markdown, CSV, JSON and YAML are decoded as they are, and HTML has its markup
removed. Other formats, e.g. Word documents, are refused: convert them to PDF first.
"""

import html
import io
import mimetypes
import os
import re
from html.parser import HTMLParser
from typing import Optional

from smarter.common.exceptions import SmarterValueError

from .models.document import PAGE_BREAK

MAX_DOCUMENT_BYTES = 50 * 1024 * 1024
"""The largest document that may be added, 50 MiB."""

PDF = "application/pdf"
HTML = "text/html"
TEXT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "text/csv",
    "application/json",
    "application/x-yaml",
    "text/yaml",
    "application/yaml",
}
EXTENSIONS = {
    ".pdf": PDF,
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".html": HTML,
    ".htm": HTML,
}
SUPPORTED_TYPES = {PDF, HTML, *TEXT_TYPES}


class VectorstoreExtractionError(SmarterValueError):
    """The document cannot be read."""


class _TextExtractor(HTMLParser):
    """The visible text of an HTML document, without scripts and styles."""

    SKIP = {"script", "style", "noscript", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skipping += 1
        elif tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section", "article"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skipping:
            self._skipping -= 1

    def handle_data(self, data):
        if not self._skipping:
            self.parts.append(data)

    @property
    def text(self) -> str:
        text = html.unescape("".join(self.parts))
        return re.sub(r"\n\s*\n+", "\n\n", re.sub(r"[ \t]+", " ", text)).strip()


def content_type_for(name: str, content_type: Optional[str] = None) -> str:
    """The media type of a document, from its declared type, else from its name's extension."""
    declared = (content_type or "").split(";", 1)[0].strip().lower()
    if declared in SUPPORTED_TYPES:
        return declared
    extension = os.path.splitext(name.lower().split("?", 1)[0])[1]
    if extension in EXTENSIONS:
        return EXTENSIONS[extension]
    guessed, _ = mimetypes.guess_type(name)
    return guessed or declared or "application/octet-stream"


def extract_text(name: str, data: bytes, content_type: Optional[str] = None) -> tuple[str, str]:
    """
    The text of a document.

    :param name: e.g. its file name, which determines its type if content_type does not.
    :param data: its bytes.
    :param content_type: its declared media type, if any.
    :returns: its text, with pages separated by PAGE_BREAK, and its media type.
    :raises VectorstoreExtractionError: if it is too large, of an unsupported type, or has no text.
    """
    if len(data) > MAX_DOCUMENT_BYTES:
        raise VectorstoreExtractionError(f"{name} is larger than {MAX_DOCUMENT_BYTES // (1024 * 1024)} MiB.")
    media_type = content_type_for(name, content_type)
    if media_type == PDF:
        text = _pdf_text(name, data)
    elif media_type == HTML:
        parser = _TextExtractor()
        parser.feed(_decode(data))
        text = parser.text
    elif media_type in TEXT_TYPES:
        text = _decode(data)
    else:
        raise VectorstoreExtractionError(
            f"{name}: {media_type} documents are not supported. Use PDF, text, Markdown, CSV, JSON, YAML or HTML."
        )
    if not text.replace(PAGE_BREAK, "").strip():
        raise VectorstoreExtractionError(f"{name} has no text. A scanned PDF needs OCR first.")
    return text, media_type


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _pdf_text(name: str, data: bytes) -> str:
    # pylint: disable=import-outside-toplevel
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise VectorstoreExtractionError(f"{name} is encrypted.")
        return PAGE_BREAK.join((page.extract_text() or "").strip() for page in reader.pages)
    except PdfReadError as e:
        raise VectorstoreExtractionError(f"{name} is not a readable PDF: {e}") from e


__all__ = ["MAX_DOCUMENT_BYTES", "VectorstoreExtractionError", "content_type_for", "extract_text"]
