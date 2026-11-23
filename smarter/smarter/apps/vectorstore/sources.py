"""
The documents of a request: uploaded files, text, or a public url, and their metadata.

The REST api's documents view (``POST /api/v1/vectorstores/<id>/documents/``) and the cli api's
``documents`` command (``POST /api/v1/cli/documents/Vectorstore/?name=<name>``) both read them with
:func:`request_sources` and :func:`request_metadata`, and add them with
:meth:`smarter.apps.vectorstore.service.VectorstoreService.add_documents`.

A request may carry, in any combination:

- files, as multipart/form-data, in the field ``files`` (repeated), or ``file``;
- ``text``, with an optional ``name``;
- ``url``, a public http or https url, fetched with
  :func:`smarter.apps.llmtool.plugin.safe_http.fetch`, which refuses private addresses;
- ``metadata``, a JSON object, stored with every chunk of every document. In a multipart form, it
  is the object's JSON text.
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Optional

from django.core.files.uploadedfile import UploadedFile
from django.utils.datastructures import MultiValueDict

from smarter.apps.llmtool.plugin.safe_http import fetch
from smarter.apps.vectorstore.extract import MAX_DOCUMENT_BYTES
from smarter.apps.vectorstore.models import VectorstoreDocumentSource
from smarter.lib import json
from smarter.lib.typing import SmarterDictType

FILE_FIELDS = ("files", "file")
"""The multipart fields of uploaded files, in the order that they are read."""


@dataclass(frozen=True)
class DocumentSource:
    """One document of a request, before its text is extracted."""

    name: str
    data: Optional[bytes]
    text: Optional[str]
    content_type: Optional[str]
    source: str


def request_files(files: MultiValueDict) -> list[UploadedFile]:
    """
    Return a request's uploaded files.

    :param files: The request's ``FILES``, a Django ``MultiValueDict``.
    :returns: The files of the first of :data:`FILE_FIELDS` that has any.
    """
    for field in FILE_FIELDS:
        uploads = files.getlist(field)
        if uploads:
            return list(uploads)
    return []


def request_sources(files: MultiValueDict, data: Mapping[str, Any]) -> Iterator[DocumentSource]:
    """
    Read the documents of a request: its uploaded files, then its text, then its url.

    :param files: The request's ``FILES``.
    :param data: The request's data: a JSON object, or a multipart form.
    :returns: The documents, one at a time. A url is fetched when its document is read.
    :raises ValueError: If a file is larger than :data:`~smarter.apps.vectorstore.extract.MAX_DOCUMENT_BYTES`.
    :raises smarter.apps.llmtool.plugin.safe_http.SafeHttpError: If the url can't be fetched safely.
    """
    for upload in request_files(files):
        size = upload.size or 0
        if size > MAX_DOCUMENT_BYTES:
            raise ValueError(f"{upload.name} is larger than {MAX_DOCUMENT_BYTES // (1024 * 1024)} MiB.")
        yield DocumentSource(
            name=str(upload.name),
            data=upload.read(),
            text=None,
            content_type=upload.content_type,
            source=VectorstoreDocumentSource.UPLOAD,
        )
    text = data.get("text")
    if text:
        name = data.get("name") or "text"
        yield DocumentSource(
            name=str(name), data=None, text=str(text), content_type="text/plain", source=VectorstoreDocumentSource.TEXT
        )
    url = data.get("url")
    if url:
        response = fetch(str(url), max_bytes=MAX_DOCUMENT_BYTES)
        yield DocumentSource(
            name=response.url,
            data=response.content,
            text=None,
            content_type=response.content_type,
            source=VectorstoreDocumentSource.URL,
        )


def request_metadata(data: Mapping[str, Any]) -> Optional[SmarterDictType]:
    """
    Return the metadata of a request's documents.

    :param data: The request's data. Its ``metadata`` is a JSON object, or, in a multipart form, its text.
    :returns: The metadata, or None if there is none.
    :raises ValueError: If the metadata is not a JSON object.
    """
    metadata = data.get("metadata")
    if metadata is None or metadata == "":
        return None
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except ValueError as e:
            raise ValueError("metadata must be a JSON object.") from e
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a JSON object.")
    return metadata


__all__ = ["FILE_FIELDS", "DocumentSource", "request_files", "request_metadata", "request_sources"]
