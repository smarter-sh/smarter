"""
Tests for smarter.apps.mcpserver.manifests.schemas.

They read the committed JSON Schemas and examples of the api contract, which a test of
:mod:`smarter.apps.api.v1.contract` keeps current, and small schemas of their own.
"""

from unittest import mock

import yaml

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.manifests.schemas import (
    MAX_MANIFEST_LENGTH,
    field_description,
    find_kind,
    manifest_example,
    manifest_fields,
    manifest_kinds,
    manifest_schema,
    parse_manifest,
    validate_manifest_text,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestManifests(SmarterTestBase):
    """Test the manifests of the platform, and the flattening of their schemas."""

    def test_kinds(self):
        """Every committed schema is a kind, and a kind is found ignoring case."""
        kinds = manifest_kinds()
        self.assertIn("LLMClient", kinds)
        self.assertIn("Secret", kinds)
        self.assertEqual(kinds, sorted(kinds))
        self.assertEqual(find_kind(" llmclient "), "LLMClient")
        self.assertIsNone(find_kind("NotAKind"))

    def test_every_kind_flattens(self):
        """Every kind's schema flattens, without its read-only status, and its example has its kind."""
        for kind in manifest_kinds():
            with self.subTest(kind=kind):
                fields = manifest_fields(manifest_schema(kind))
                paths = [field.path for field in fields]
                self.assertEqual(paths[:3], ["apiVersion", "kind", "metadata"])
                self.assertIn("metadata.name", paths)
                self.assertIn("spec", paths)
                self.assertFalse(any(path.startswith("status") for path in paths))
                self.assertEqual(len(paths), len(set(paths)))
                self.assertEqual(manifest_example(kind)["kind"], kind)

    def test_secret(self):
        """A field has its path, type, required flag and description, without a redundant prefix."""
        fields = {field.path: field for field in manifest_fields(manifest_schema("Secret"))}
        value = fields["spec.config.value"]
        self.assertEqual(value.type, "string")
        self.assertTrue(value.required)
        self.assertEqual(value.description, "The unencrypted value of the Secret.")
        expiration = fields["spec.config.expiration_date"]
        self.assertEqual(expiration.type, "string (date-time)")
        self.assertFalse(expiration.required)
        self.assertEqual(fields["metadata.tags"].type, "list of string")

    def test_flattening(self):
        """References, lists and maps of objects, enums, defaults and cycles are flattened."""
        schema = {
            "$defs": {
                "Item": {
                    "properties": {
                        "mode": {"enum": ["a", "b"], "default": "a"},
                        "next": {"anyOf": [{"$ref": "#/$defs/Item"}, {"type": "null"}]},
                    },
                    "required": ["mode"],
                    "type": "object",
                },
            },
            "properties": {
                "items": {"items": {"$ref": "#/$defs/Item"}, "type": "array"},
                "byName": {"additionalProperties": {"$ref": "#/$defs/Item"}, "type": "object"},
                "labels": {"additionalProperties": {"type": "string"}, "type": "object"},
                "anything": {"type": "object"},
                "count": {"anyOf": [{"type": "integer"}, {"type": "string"}], "default": 3},
                "status": {"type": "object", "properties": {"x": {"type": "string"}}},
            },
            "required": ["items"],
            "type": "object",
        }
        fields = {field.path: field for field in manifest_fields(schema)}
        self.assertEqual(fields["items"].type, "list of object")
        self.assertTrue(fields["items"].required)
        self.assertEqual(fields["items[].mode"].type, "one of: a, b")
        self.assertEqual(fields["items[].mode"].default, "a")
        self.assertTrue(fields["items[].mode"].required)
        self.assertEqual(fields["items[].next"].type, "object")
        self.assertIn("items[].next.next.next.mode", fields)
        self.assertIn("byName.<key>.mode", fields)
        self.assertEqual(fields["labels"].type, "map of string to string")
        self.assertEqual(fields["anything"].type, "object")
        self.assertEqual(fields["count"].type, "integer or string")
        self.assertEqual(fields["count"].default, 3)
        self.assertNotIn("status", fields)
        self.assertLess(max(path.count(".") for path in fields), 12)

    def test_field_description(self):
        """The path, type and required flag at the start of a description are removed."""
        cases = {
            "LLMClient.spec.config.prompt.appName[str]. Optional. The name.": "The name.",
            "apiVersion[String]: Required. The API version.": "The API version.",
            "Secret.spec.configuration.value[list[str]]. Required. the value.": "The value.",
            "Required, the LLMClient metadata.": "The LLMClient metadata.",
            "A plain   description.": "A plain description.",
            "": "",
        }
        for description, expected in cases.items():
            with self.subTest(description=description):
                self.assertEqual(field_description(description), expected)
        self.assertTrue(field_description("word " * 100).endswith("…"))

    # -------------------------------------------------------------------------
    # parse_manifest, validate_manifest_text
    # -------------------------------------------------------------------------
    def test_parse_manifest(self):
        """YAML and JSON are parsed."""
        self.assertEqual(parse_manifest("kind: Secret\nspec:\n  a: 1\n"), {"kind": "Secret", "spec": {"a": 1}})
        self.assertEqual(parse_manifest('{"kind": "Secret"}'), {"kind": "Secret"})

    def test_parse_manifest_refuses_aliases(self):
        """A YAML alias, whose expansion could be enormous, is refused; an anchor alone is not."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "aliases are not allowed"):
            parse_manifest("a: &x [1, 2]\nb: *x\n")
        self.assertEqual(parse_manifest("a: &x 1\n"), {"a": 1})

    def test_parse_manifest_errors(self):
        """Text that is not YAML, or is too long, is an error."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "not valid YAML"):
            parse_manifest("a: [1, 2\n")
        with self.assertRaisesRegex(SmarterMCPServerToolError, "longer than"):
            parse_manifest("a" * (MAX_MANIFEST_LENGTH + 1))

    def test_validate_manifest_text(self):
        """Every kind's example is valid, and a missing field is an error with its path."""
        for kind in ("Secret", "Guardrail", "LLMClient"):
            with self.subTest(kind=kind):
                example = manifest_example(kind)
                self.assertEqual(validate_manifest_text(yaml.safe_dump(example)).errors, [])
                del example["metadata"]["name"]
                errors = validate_manifest_text(yaml.safe_dump(example)).errors
                self.assertIn(["metadata", "name"], [error.loc for error in errors])

    def test_validate_manifest_text_skips_external_checks(self):
        """The checks that make requests, e.g. that an image url responds, are never run."""
        with mock.patch("smarter.apps.api.v1.cli.validation.validate_manifest") as validate:
            validate_manifest_text("kind: Secret\n")
        validate.assert_called_once_with({"kind": "Secret"}, external_checks=False)
