"""Test the content-addressed storage of the journal's documents: :mod:`smarter.lib.journal.storage`."""

from pydantic import JsonValue

from smarter.lib.journal.storage import (
    BLOB_MIN_BYTES,
    ESCAPE_KEY,
    LENGTH_KEY,
    LIST_KEY,
    REF_KEY,
    JournalDocumentDecoder,
    JournalDocumentEncoder,
    JournalStorageError,
    blob_references,
    node_references,
    pack,
    unpack,
)
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.narrowing import json_list, json_object


def conversation(turns: int) -> SmarterDictType:
    """The response of an LLMClient's prompt after a number of turns: every message so far, and the tools."""
    messages = [{"role": "system", "content": "You are a helpful assistant. " * 40}]
    for turn in range(turns):
        messages.append({"role": "user", "content": f"question {turn}: what is {turn} times {turn}?"})
        messages.append({"role": "assistant", "content": f"{turn} times {turn} is {turn * turn}. " * 5})
    tools = [{"type": "function", "function": {"name": f"tool_{i}", "description": "d" * 300}} for i in range(5)]
    return {"data": {"messages": messages, "tools": tools, "completion": {"id": f"chatcmpl-{turns}"}}}


class TestJournalStorage(SmarterTestBase):
    """Test that documents are encoded into skeletons and blobs, and decoded back unchanged."""

    def round_trip(self, document, encoder=None):
        """Encode and decode a document, through pack() and unpack(), as the database stores it."""
        encoder = encoder or JournalDocumentEncoder()
        skeleton = unpack(pack(encoder.encode(document)))
        decoder = JournalDocumentDecoder(encoder.blobs.__getitem__)
        return decoder.decode(skeleton), skeleton, encoder

    def test_round_trip(self):
        """Test that documents of every shape decode to themselves."""
        documents = [
            None,
            True,
            42,
            1.5,
            "short",
            "long " * 1000,
            [],
            {},
            [1, "two", None, {"three": 3}],
            {"nested": {"list": [[1, 2], [3, 4]] * 100, "text": "t" * 5000}},
            [{"item": i, "padding": "p" * 50} for i in range(50)],
            {"unicode": "héllo ☃ " * 300},
        ]
        for document in documents:
            with self.subTest(document=str(document)[:40]):
                decoded, _, _ = self.round_trip(document)
                self.assertEqual(decoded, document)

    def test_key_order_is_kept(self):
        """Test that a decoded document has its keys in their original order."""
        document = {"z": 1, "a": "a" * 2000, "m": [{"y": 1, "b": 2}] * 40}
        decoded, _, _ = self.round_trip(document)
        decoded_object = json_object(decoded, "decoded")
        self.assertEqual(list(decoded_object), ["z", "a", "m"])
        first_item = json_object(json_list(decoded_object["m"], "m")[0], "m[0]")
        self.assertEqual(list(first_item), ["y", "b"])

    def test_small_document_has_no_blobs(self):
        """Test that a small document is stored inline, in its skeleton."""
        document = {"data": {"a": 1}, "metadata": {"command": "get"}}
        _, skeleton, encoder = self.round_trip(document)
        self.assertEqual(skeleton, document)
        self.assertEqual(encoder.blobs, {})

    def test_large_values_are_references(self):
        """Test that a large string or dict, and a long list, are references in the skeleton."""
        document = {"text": "t" * BLOB_MIN_BYTES, "list": list(range(200)), "small": "s"}
        _, skeleton, _ = self.round_trip(document)
        skeleton_object = json_object(skeleton, "skeleton")
        text = json_object(skeleton_object["text"], "text")
        chain = json_object(skeleton_object["list"], "list")
        self.assertEqual(list(text), [REF_KEY])
        self.assertEqual(chain[LENGTH_KEY], 200)
        self.assertIn(LIST_KEY, chain)
        self.assertEqual(skeleton_object["small"], "s")

    def test_reserved_keys_are_escaped(self):
        """Test that a document's own keys that look like references are escaped, and decoded back."""
        documents = [
            {REF_KEY: "0" * 64},
            {LIST_KEY: "0" * 64, LENGTH_KEY: 3},
            {"outer": {ESCAPE_KEY: {"x": 1}}},
            [{REF_KEY: "a" * 2000}] * 10,
        ]
        for document in documents:
            with self.subTest(document=str(document)[:40]):
                decoded, _, _ = self.round_trip(document)
                self.assertEqual(decoded, document)

    def test_identical_values_are_stored_once(self):
        """Test that a value repeated in a document, or in two documents of one encoder, is one blob."""
        text = "repeated " * 500
        encoder = JournalDocumentEncoder()
        encoder.encode({"a": text, "b": text})
        count = len(encoder.blobs)
        encoder.encode({"c": text})
        self.assertEqual(count, 1)
        self.assertEqual(len(encoder.blobs), 1)

    def test_conversation_stores_only_new_messages(self):
        """Test that each turn of a conversation adds only its own messages' blobs, and shares the rest."""
        stored: dict[str, bytes] = {}
        new_blobs_per_turn = []
        for turns in range(1, 21):
            encoder = JournalDocumentEncoder()
            skeleton = encoder.encode(conversation(turns))
            new = 0
            for digest, data in encoder.blobs.items():
                if digest not in stored:
                    stored[digest] = data
                    new += 1
            new_blobs_per_turn.append(new)
            decoder = JournalDocumentDecoder(stored.__getitem__)
            self.assertEqual(decoder.decode(skeleton), conversation(turns))
        # after the first turn, each turn stores its two messages, and nothing else.
        self.assertEqual(set(new_blobs_per_turn[1:]), {2})

    def test_conversation_storage_is_linear(self):
        """Test that a conversation of n turns costs O(n) bytes, not the O(n²) of storing every response."""
        stored: dict[str, bytes] = {}
        stored_bytes = 0
        plain_bytes = 0
        for turns in range(1, 51):
            document = conversation(turns)
            encoder = JournalDocumentEncoder()
            skeleton = encoder.encode(document)
            stored_bytes += len(pack(skeleton))
            for digest, data in encoder.blobs.items():
                if digest not in stored:
                    stored[digest] = data
                    stored_bytes += len(data)
            plain_bytes += len(str(document))
        self.assertLess(stored_bytes * 10, plain_bytes)

    def test_branches_share_their_prefix(self):
        """Test that two lists that share their first items share those items' nodes."""
        first: list[JsonValue] = [{"content": f"message {i} " * 10} for i in range(10)]
        second: list[JsonValue] = first[:8] + [{"content": "a different ending " * 10}]
        encoder = JournalDocumentEncoder()
        encoder.encode(first)
        count = len(encoder.blobs)
        encoder.encode(second)
        self.assertEqual(len(encoder.blobs), count + 1)

    def test_missing_blob(self):
        """Test that a skeleton whose blob is missing raises JournalStorageError."""
        encoder = JournalDocumentEncoder()
        skeleton = encoder.encode({"text": "t" * 5000, "list": list(range(500))})
        no_blobs: dict[str, bytes] = {}
        decoder = JournalDocumentDecoder(no_blobs.__getitem__)
        with self.assertRaises(JournalStorageError):
            decoder.decode(skeleton)

    def test_chain_node_that_is_not_a_node(self):
        """Test that a list whose node is not a dict raises JournalStorageError."""
        encoder = JournalDocumentEncoder()
        digest = encoder.store("not a node")
        decoder = JournalDocumentDecoder(encoder.blobs.__getitem__)
        with self.assertRaises(JournalStorageError):
            decoder.decode({LIST_KEY: digest, LENGTH_KEY: 1})

    def test_blobs_are_read_once(self):
        """Test that a decoder reads a blob once, however often it is referenced."""
        encoder = JournalDocumentEncoder()
        text = "t" * 5000
        skeleton = encoder.encode({"a": text, "b": text, "c": text})
        reads = []

        def read_blob(digest: str) -> bytes:
            reads.append(digest)
            return encoder.blobs[digest]

        decoded = JournalDocumentDecoder(read_blob).decode(skeleton)
        self.assertEqual(decoded, {"a": text, "b": text, "c": text})
        self.assertEqual(len(reads), 1)

    def test_unpack_memoryview(self):
        """Test that unpack() reads the memoryview that some database drivers return."""
        self.assertEqual(unpack(memoryview(pack({"a": [1, 2]}))), {"a": [1, 2]})

    def test_error_message(self):
        """Test the storage error's message prefix."""
        self.assertIn("Journal Storage", JournalStorageError("x").get_formatted_err_message)

    def test_blob_references(self):
        """Test that the references of a skeleton, a blob and a chain's node reach every blob of a document."""
        document: JsonValue = {
            "text": "t" * 2000,
            "list": [{"item": i, "long": f"{i} " + "l" * 2000} for i in range(3)],
            "escaped": {REF_KEY: "x" * 2000},
        }
        encoder = JournalDocumentEncoder()
        skeleton = encoder.encode(document)
        found = set()
        pending = blob_references(skeleton)
        while pending:
            digest, is_node = pending.pop()
            if (digest, is_node) in found:
                continue
            found.add((digest, is_node))
            value = unpack(encoder.blobs[digest])
            if is_node:
                pending.extend(node_references(value))
            else:
                pending.extend(blob_references(value))
        self.assertEqual({digest for digest, _ in found}, set(encoder.blobs))
        self.assertEqual(node_references("not a node"), [])

    def test_blob_references_of_lists_and_look_alikes(self):
        """Test that a reference inside a list is found, and that a dict with a reference key and others is not one."""
        digest = "a" * 64
        reference: JsonValue = {REF_KEY: digest}
        look_alike: JsonValue = {REF_KEY: "b" * 64, "other": 1}
        skeleton: JsonValue = [[reference], look_alike]
        self.assertEqual(blob_references(skeleton), [(digest, False)])
