"""Test the journal's sources: :mod:`smarter.lib.journal.sources`."""

from pydantic import JsonValue

from smarter.lib.journal.sources import (
    UNRESOLVED_KEY,
    JournalSourceGone,
    JournalSourceLookup,
    JournalSourceNotReady,
    SAMJournalSource,
    attach_sources,
    detach_sources,
    get_at_path,
    register_journal_source,
    replace_at_path,
    value_digest,
)
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.narrowing import json_object

THREAD: JsonValue = [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
ROWS: dict[int, JsonValue] = {1: THREAD}
"""The rows of the test source, by id: the database, for these tests."""


def resolve_test_thread(lookup: JournalSourceLookup) -> JsonValue:
    """A test source: ROWS[id], not ready while missing, gone for a negative id."""
    row_id = int(lookup["id"])
    if row_id < 0:
        raise JournalSourceGone("deleted")
    if row_id not in ROWS:
        raise JournalSourceNotReady("not written yet")
    return ROWS[row_id]


register_journal_source("test.thread", resolve_test_thread)


def source(row_id: int = 1, path=("data", "thread")) -> SAMJournalSource:
    """The test source of a row."""
    return SAMJournalSource(name="test.thread", path=path, lookup={"id": row_id})


class TestJournalSources(SmarterTestBase):
    """Test that sources are detached from a response, and attached again from the database."""

    def test_paths(self):
        """Test reading and replacing values by path, through dicts and lists, without changing the original."""
        document: JsonValue = {"a": [{"b": 1}, {"b": 2}]}
        self.assertEqual(get_at_path(document, ("a", 1, "b")), 2)
        replaced = replace_at_path(document, ("a", 1, "b"), 3)
        self.assertEqual(replaced, {"a": [{"b": 1}, {"b": 3}]})
        self.assertEqual(document, {"a": [{"b": 1}, {"b": 2}]})
        self.assertEqual(replace_at_path([1, 2], (0,), 9), [9, 2])
        for path in (("x",), ("a", 5), ("a", "b"), ("a", 0, "b", "c")):
            with self.subTest(path=path):
                with self.assertRaises(KeyError):
                    get_at_path(document, path)
                with self.assertRaises(KeyError):
                    replace_at_path(document, path, None)

    def test_detach_and_attach(self):
        """Test that a detached document has None at the source's path, and is attached back unchanged."""
        document: JsonValue = {"data": {"thread": THREAD, "other": 1}}
        detached, references = detach_sources(document, [source()])
        self.assertEqual(detached, {"data": {"thread": None, "other": 1}})
        self.assertEqual(get_at_path(document, ("data", "thread")), THREAD)
        self.assertEqual(references[0].digest, value_digest(THREAD))
        self.assertEqual(attach_sources(detached, references), document)

    def test_missing_path_stays(self):
        """Test that a source whose path the response doesn't have gets no reference."""
        document: JsonValue = {"data": {}}
        detached, references = detach_sources(document, [source()])
        self.assertEqual(detached, document)
        self.assertEqual(references, [])

    def test_not_ready(self):
        """Test that a row that is not written yet raises JournalSourceNotReady, until it is written."""
        document: JsonValue = {"data": {"thread": THREAD}}
        _, references = detach_sources(document, [source(row_id=2)])
        with self.assertRaises(JournalSourceNotReady):
            attach_sources({"data": {"thread": None}}, references)
        ROWS[2] = THREAD
        self.addCleanup(ROWS.pop, 2)
        self.assertEqual(attach_sources({"data": {"thread": None}}, references), document)

    def test_unresolved(self):
        """Test that a gone, changed or unregistered source is journaled as its reference."""
        changed: JsonValue = {"data": {"thread": [{"role": "user", "content": "something else"}]}}
        unregistered = SAMJournalSource(name="test.unregistered", path=("data", "thread"), lookup={"id": 1})
        cases: list[tuple[str, JsonValue, list[SAMJournalSource]]] = [
            ("gone", {"data": {"thread": THREAD}}, [source(row_id=-1)]),
            ("changed", changed, [source()]),
            ("unregistered", {"data": {"thread": THREAD}}, [unregistered]),
        ]
        for name, document, sources in cases:
            with self.subTest(name=name):
                detached, references = detach_sources(document, sources)
                attached = attach_sources(detached, references)
                marker = json_object(get_at_path(attached, ("data", "thread")), "marker")
                self.assertEqual(list(marker), [UNRESOLVED_KEY])
                unresolved = json_object(marker[UNRESOLVED_KEY], UNRESOLVED_KEY)
                self.assertEqual(unresolved["digest"], references[0].digest)

    def test_error_messages(self):
        """Test the sources' error message prefixes."""
        self.assertIn("Not Ready", JournalSourceNotReady("x").get_formatted_err_message)
        self.assertIn("Gone", JournalSourceGone("x").get_formatted_err_message)
