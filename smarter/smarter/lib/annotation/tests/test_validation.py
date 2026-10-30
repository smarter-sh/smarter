"""Test the validation and normalization of annotations."""

import datetime
import decimal
import uuid

from smarter.lib.annotation.const import (
    ANNOTATION_KEY_MAX_LENGTH,
    ANNOTATIONS_TOTAL_MAX_BYTES,
)
from smarter.lib.annotation.validation import (
    SmarterAnnotationError,
    annotations_size,
    coerce_annotation_value,
    is_reserved_annotation_key,
    normalize_annotations,
    prefix_matches,
    split_annotation_key,
    validate_annotation_key,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

VALID_KEYS = (
    "owner",
    "acme.com/crm-account-id",
    "smarter.sh/llmclient/use-case",
    "smarter.sh/created_by",
    "app.kubernetes.io/name",
    "a/b.c_d-e",
    "x" * 63,
    "a" * 253 + "/" + "b" * 63,
)
INVALID_KEYS = (
    "",
    "/name",
    "acme.com/",
    "Acme.com/name",
    "acme_corp.com/name",
    "acme.com/-name",
    "acme.com/name-",
    "acme.com/a//b",
    "acme.com/has space",
    "acme.com/" + "x" * 64,
    "a" * 254 + "/name",
    "x" * (ANNOTATION_KEY_MAX_LENGTH + 1),
)


class TestAnnotationValidation(SmarterTestBase):
    """Test that keys and values follow Kubernetes' rules, extended for multi-segment names."""

    def test_valid_keys(self):
        """Test that every Kubernetes key, and Smarter's multi-segment keys, are valid."""
        for key in VALID_KEYS:
            with self.subTest(key=key):
                self.assertEqual(validate_annotation_key(key), key)

    def test_invalid_keys(self):
        """Test that malformed prefixes, segments and lengths are rejected."""
        for key in INVALID_KEYS:
            with self.subTest(key=key), self.assertRaises(SmarterAnnotationError):
                validate_annotation_key(key)

    def test_non_string_key(self):
        """Test that a key that isn't a string is rejected."""
        with self.assertRaises(SmarterAnnotationError):
            validate_annotation_key(42)  # type: ignore[arg-type]

    def test_split_annotation_key(self):
        """Test that the prefix is everything before the first slash."""
        self.assertEqual(split_annotation_key("acme.com/crm/id"), ("acme.com", "crm/id"))
        self.assertEqual(split_annotation_key("owner"), (None, "owner"))

    def test_coerce_scalars(self):
        """Test that YAML's unquoted scalars become the strings that were written."""
        cases = (
            ("text", "text"),
            (True, "true"),
            (False, "false"),
            (42, "42"),
            (1.5, "1.5"),
            (decimal.Decimal("4.00"), "4.00"),
            (datetime.date(2026, 10, 28), "2026-10-28"),
            (datetime.datetime(2026, 10, 28, 12, 30), "2026-10-28T12:30:00"),
            (uuid.UUID(int=1), "00000000-0000-0000-0000-000000000001"),
            (b"bytes", "bytes"),
            (None, ""),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(coerce_annotation_value("k", value), expected)

    def test_coerce_rejects_structures(self):
        """Test that lists, dicts and non-UTF-8 bytes are rejected, unless lenient."""
        for value in ([1, 2], {"a": 1}, b"\xff"):
            with self.subTest(value=value), self.assertRaises(SmarterAnnotationError):
                coerce_annotation_value("k", value)
        self.assertEqual(coerce_annotation_value("k", [1, 2], lenient=True), "[1, 2]")
        self.assertEqual(coerce_annotation_value("k", {"a": 1}, lenient=True), '{"a": 1}')

    def test_normalize_shapes(self):
        """Test that a map, the legacy list of one-key maps, and their JSON are the same annotations."""
        expected = {"acme.com/id": "A-1", "acme.com/active": "true"}
        for value in (
            {"acme.com/id": "A-1", "acme.com/active": True},
            [{"acme.com/id": "A-1"}, {"acme.com/active": True}],
            [{"acme.com/id": "A-1", "acme.com/active": True}],
            '{"acme.com/id": "A-1", "acme.com/active": true}',
            '[{"acme.com/id": "A-1"}, {"acme.com/active": true}]',
        ):
            with self.subTest(value=value):
                self.assertEqual(normalize_annotations(value), expected)

    def test_normalize_empty(self):
        """Test that None, an empty string, list and map are no annotations."""
        for value in (None, "", [], {}):
            with self.subTest(value=value):
                self.assertEqual(normalize_annotations(value), {})

    def test_normalize_errors(self):
        """Test that bad JSON, shapes, keys, duplicates and values are rejected."""
        for value in (
            "not json",
            42,
            ["not a map"],
            {"Bad Key": "x"},
            [{"acme.com/id": "1"}, {"acme.com/id": "2"}],
            {"acme.com/id": ["a", "list"]},
        ):
            with self.subTest(value=value), self.assertRaises(SmarterAnnotationError):
                normalize_annotations(value)  # type: ignore[arg-type]

    def test_normalize_lenient(self):
        """Test that legacy rows keep what they can: valid keys, the last duplicate, structures as JSON."""
        value = [{"acme.com/id": "1"}, {"acme.com/id": "2"}, {"Bad Key": "x"}, "junk", {"acme.com/list": [1]}]
        self.assertEqual(normalize_annotations(value, lenient=True), {"acme.com/id": "2", "acme.com/list": "[1]"})

    def test_size_limit(self):
        """Test that all annotations together are limited to 256 KiB, as in Kubernetes."""
        value = {"acme.com/big": "x" * ANNOTATIONS_TOTAL_MAX_BYTES}
        with self.assertRaises(SmarterAnnotationError):
            normalize_annotations(value)
        self.assertEqual(annotations_size({"ab": "cd"}), 4)
        self.assertEqual(len(normalize_annotations(value, lenient=True)["acme.com/big"]), ANNOTATIONS_TOTAL_MAX_BYTES)

    def test_prefix_matches(self):
        """Test that a prefix matches its domain and subdomains, and nothing else."""
        self.assertTrue(prefix_matches("acme.com", "acme.com"))
        self.assertTrue(prefix_matches("crm.acme.com", "acme.com"))
        self.assertFalse(prefix_matches("notacme.com", "acme.com"))
        self.assertFalse(prefix_matches(None, "acme.com"))

    def test_reserved_keys(self):
        """Test that smarter.sh and its subdomains are reserved."""
        self.assertTrue(is_reserved_annotation_key("smarter.sh/llmclient/use-case"))
        self.assertTrue(is_reserved_annotation_key("llmclient.smarter.sh/x"))
        self.assertFalse(is_reserved_annotation_key("acme.com/x"))
        self.assertFalse(is_reserved_annotation_key("smarter.sh"))
