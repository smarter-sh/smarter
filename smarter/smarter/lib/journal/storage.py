"""
Content-addressed storage of the Smarter Journal's request and response documents.

The journal is written far more often than it is read. Most of what it writes is the response of an
LLMClient's prompt, whose ``messages`` hold the whole conversation: each turn's response repeats every
message of the turns before it, and adds one or two. Stored as plain JSON, a conversation of n turns
costs O(n²) bytes. This module stores it in O(n), without knowing anything about conversations, so
that every other kind of journal entry, e.g. a manifest's ``apply`` or ``describe``, gets the same
savings wherever its documents repeat.

A document is encoded, by :class:`JournalDocumentEncoder`, into a small skeleton and a set of blobs:

- A dict or a string whose JSON is at least :data:`BLOB_MIN_BYTES` long is stored once, as a blob
  whose id is the SHA-256 of its JSON, and replaced in the skeleton by ``{"$journal:ref": <digest>}``.
  The same tool definitions, system prompt, or LLMClient configuration, sent with every turn of every
  conversation, is stored one time.
- A list whose JSON is at least :data:`LIST_MIN_BYTES` long is stored as a chain, a persistent linked
  list: each item is a node ``{"parent": <the previous node's digest>, "value": <the item>}``, and the
  skeleton keeps only the last node's digest, as ``{"$journal:list": <digest>, "$journal:length": n}``.
  A node's digest covers its parent's, so the two lists that share their first k items share their
  first k nodes. A turn of a conversation stores only its new messages, and a branch of a conversation,
  e.g. a message edited and sent again, shares the messages before it.

Blobs are never updated nor deleted, and two writers that store the same blob store the same bytes,
so entries may be written in any order, by any number of Celery workers, with no locking. The skeleton
and every blob are compressed with zlib.

A dict of the document whose keys begin with :data:`RESERVED_PREFIX` is wrapped in
``{"$journal:escape": ...}``, so that no document can be mistaken for a reference.

This module is pure: it neither reads nor writes the database. See
:class:`smarter.lib.journal.models.SAMJournalBlob`, which stores the blobs.
"""

import hashlib
import json
import zlib
from collections.abc import Callable
from typing import Optional, Union

from pydantic import JsonValue

from smarter.common.exceptions import SmarterException

RESERVED_PREFIX = "$journal:"
"""The prefix of the keys that the encoding adds to a document."""

REF_KEY = RESERVED_PREFIX + "ref"
"""The key of a reference to a blob: ``{"$journal:ref": <digest>}``."""

LIST_KEY = RESERVED_PREFIX + "list"
"""The key of a reference to a chain's last node: ``{"$journal:list": <digest>, "$journal:length": n}``."""

LENGTH_KEY = RESERVED_PREFIX + "length"
"""The number of items of a chain, beside :data:`LIST_KEY`."""

ESCAPE_KEY = RESERVED_PREFIX + "escape"
"""The key that wraps a document's own dict whose keys begin with :data:`RESERVED_PREFIX`."""

PARENT_KEY = "parent"
"""A chain node's key of its parent's digest, or None for the first node."""

VALUE_KEY = "value"
"""A chain node's key of its item."""

BLOB_MIN_BYTES = 1024
"""A dict or string whose JSON is this long, or longer, is stored as a blob."""

LIST_MIN_BYTES = 256
"""A list whose JSON is this long, or longer, is stored as a chain."""

COMPRESSION_LEVEL = 6
"""The zlib compression level of the skeletons and the blobs."""

DIGEST_LENGTH = 64
"""The length of a blob's id: a SHA-256, as hexadecimal."""

BlobReader = Callable[[str], bytes]
"""Returns the compressed bytes of a blob, by its digest."""


class JournalStorageError(SmarterException):
    """A journal document could not be decoded, e.g. because a blob that it references is missing."""

    @property
    def get_formatted_err_message(self):
        """The error message prefix of these errors."""
        return "Smarter Journal Storage Error"


def to_json_bytes(value: JsonValue) -> bytes:
    """
    Return a value's JSON, compact and in UTF-8, as the encoding hashes and stores it.

    Keys keep their order: two documents built by the same code have the same JSON, and a decoded
    document has the same order as the original.

    :param value: The value.
    :returns: Its JSON.
    """
    text = json.dumps(value, separators=(",", ":"), ensure_ascii=False, default=str)
    return text.encode("utf-8")


def pack(value: JsonValue) -> bytes:
    """
    Return a value's JSON, compressed: the stored form of a skeleton and of a blob.

    :param value: The value.
    :returns: The compressed JSON.
    """
    data = to_json_bytes(value)
    return zlib.compress(data, COMPRESSION_LEVEL)


def unpack(data: Union[bytes, bytearray, memoryview]) -> JsonValue:
    """
    Return the value of what :func:`pack` stored.

    :param data: The compressed JSON. Some database drivers return a ``memoryview``.
    :returns: The value.
    """
    compressed = bytes(data)
    text = zlib.decompress(compressed)
    value = json.loads(text)
    return value


def is_reference(value: JsonValue, key: str, size: int) -> bool:
    """
    Return whether a value of a skeleton is one of the encoding's markers.

    :param value: The value.
    :param key: The marker's key, e.g. :data:`REF_KEY`.
    :param size: The number of keys of the marker.
    :returns: True if the value is a dict of ``size`` keys, one of them ``key``.
    """
    if not isinstance(value, dict):
        return False
    if len(value) != size:
        return False
    return key in value


class JournalDocumentEncoder:
    """
    Encodes documents into skeletons and blobs.

    One encoder may encode several documents, e.g. an entry's request and response, which then share
    their blobs. After encoding, :attr:`blobs` holds each blob's compressed bytes, by digest: every
    blob of the documents, of which the database may already have some.

    **Example**::

        encoder = JournalDocumentEncoder()
        skeleton = encoder.encode(response)
        SAMJournalBlob.objects.save_blobs(encoder.blobs)
        stored = pack(skeleton)
    """

    def __init__(self):
        self.blobs: dict[str, bytes] = {}

    def encode(self, document: JsonValue) -> JsonValue:
        """
        Return a document's skeleton, adding its blobs to :attr:`blobs`.

        The document itself is never a blob: it is unique to its entry, so the skeleton stays in the
        entry's row.

        :param document: The document, as JSON.
        :returns: The skeleton.
        """
        skeleton = self._encode_item(document)
        return skeleton

    def store(self, value: JsonValue) -> str:
        """
        Add a value to :attr:`blobs`, and return its digest.

        :param value: The value, already encoded.
        :returns: The SHA-256 of its JSON, as hexadecimal.
        """
        data = to_json_bytes(value)
        digest = hashlib.sha256(data).hexdigest()
        if digest not in self.blobs:
            self.blobs[digest] = zlib.compress(data, COMPRESSION_LEVEL)
        return digest

    def _encode_value(self, value: JsonValue) -> JsonValue:
        """Return a value encoded, as a reference to a blob if it is large."""
        if isinstance(value, list):
            return self._encode_list(value)
        if isinstance(value, dict):
            encoded = self._encode_dict(value)
        elif isinstance(value, str):
            encoded = value
        else:
            return value
        size = len(to_json_bytes(encoded))
        if size < BLOB_MIN_BYTES:
            return encoded
        digest = self.store(encoded)
        return {REF_KEY: digest}

    def _encode_item(self, value: JsonValue) -> JsonValue:
        """Return a value encoded, without making the value itself a blob: a document, or a chain's item."""
        if isinstance(value, dict):
            return self._encode_dict(value)
        if isinstance(value, list):
            return self._encode_list(value)
        return value

    def _encode_dict(self, value: dict) -> JsonValue:
        """Return a dict whose values are encoded, escaped if it has a reserved key."""
        encoded: dict[str, JsonValue] = {}
        has_reserved_key = False
        for key, item in value.items():
            if str(key).startswith(RESERVED_PREFIX):
                has_reserved_key = True
            encoded[key] = self._encode_value(item)
        if has_reserved_key:
            return {ESCAPE_KEY: encoded}
        return encoded

    def _encode_list(self, value: list) -> JsonValue:
        """Return a list encoded: inline if it is short, or as a chain of nodes."""
        items = []
        for item in value:
            encoded_item = self._encode_item(item)
            items.append(encoded_item)
        size = len(to_json_bytes(items))
        if size < LIST_MIN_BYTES:
            return items
        parent: Optional[str] = None
        for item in items:
            node = {PARENT_KEY: parent, VALUE_KEY: item}
            parent = self.store(node)
        return {LIST_KEY: parent, LENGTH_KEY: len(items)}


class JournalDocumentDecoder:
    """
    Decodes the skeletons of :class:`JournalDocumentEncoder` back into their documents.

    Each blob is read once per decoder, with ``read_blob``.

    :param read_blob: Returns a blob's compressed bytes, by its digest. It raises ``KeyError`` if there
        is no such blob.
    """

    def __init__(self, read_blob: BlobReader):
        self.read_blob = read_blob
        self.loaded: dict[str, JsonValue] = {}

    def decode(self, skeleton: JsonValue) -> JsonValue:
        """
        Return the document of a skeleton.

        :param skeleton: The skeleton, as :meth:`JournalDocumentEncoder.encode` returned it.
        :returns: The document.
        :raises JournalStorageError: If a blob that the skeleton references is missing.
        """
        document = self._decode_value(skeleton)
        return document

    def load(self, digest: str) -> JsonValue:
        """
        Return a blob's value, still encoded.

        :param digest: The blob's digest.
        :returns: Its value.
        :raises JournalStorageError: If there is no such blob.
        """
        if digest in self.loaded:
            return self.loaded[digest]
        try:
            data = self.read_blob(digest)
        except KeyError as e:
            raise JournalStorageError(f"The journal blob {digest} is missing.") from e
        value = unpack(data)
        self.loaded[digest] = value
        return value

    def _decode_value(self, value: JsonValue) -> JsonValue:
        """Return a value decoded."""
        if isinstance(value, list):
            return [self._decode_value(item) for item in value]
        if not isinstance(value, dict):
            return value
        if is_reference(value, ESCAPE_KEY, 1):
            escaped = value[ESCAPE_KEY]
            return self._decode_dict(escaped)  # type: ignore[arg-type]
        if is_reference(value, REF_KEY, 1):
            blob = self.load(str(value[REF_KEY]))
            return self._decode_value(blob)
        if is_reference(value, LIST_KEY, 2) and LENGTH_KEY in value:
            return self._decode_list(str(value[LIST_KEY]))
        return self._decode_dict(value)

    def _decode_dict(self, value: dict) -> JsonValue:
        """Return a dict whose values are decoded."""
        decoded = {}
        for key, item in value.items():
            decoded[key] = self._decode_value(item)
        return decoded

    def _decode_list(self, tail: str) -> JsonValue:
        """Return the items of a chain, from its first node to ``tail``."""
        items = []
        digest: Optional[str] = tail
        while digest is not None:
            node = self.load(digest)
            if not isinstance(node, dict):
                raise JournalStorageError(f"The journal blob {digest} is not a list's node.")
            items.append(node.get(VALUE_KEY))
            parent = node.get(PARENT_KEY)
            digest = str(parent) if parent is not None else None
        items.reverse()
        decoded = []
        for item in items:
            decoded_item = self._decode_value(item)
            decoded.append(decoded_item)
        return decoded


__all__ = [
    "BLOB_MIN_BYTES",
    "BlobReader",
    "JournalDocumentDecoder",
    "JournalDocumentEncoder",
    "JournalStorageError",
    "LIST_MIN_BYTES",
    "pack",
    "unpack",
]
