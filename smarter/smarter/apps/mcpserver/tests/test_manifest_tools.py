"""Tests for smarter.apps.mcpserver.manifests.tools."""

from unittest import mock

import yaml

from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.manifests import schemas
from smarter.apps.mcpserver.manifests import tools as manifest_tools
from smarter.apps.mcpserver.manifests.tools import (
    GetManifestSchemaTool,
    ValidateManifestTool,
)

from .base_classes import MCPServerTestBase


class TestManifestTools(MCPServerTestBase):
    """Test get_manifest_schema and validate_manifest."""

    # -------------------------------------------------------------------------
    # get_manifest_schema
    # -------------------------------------------------------------------------
    def test_manifest_schema_is_served_everywhere(self):
        """Every MCP server serves get_manifest_schema, without a repository argument."""
        self.assertTrue(GetManifestSchemaTool.serves(self.single()))
        self.assertTrue(GetManifestSchemaTool.serves(self.all()))
        self.assertNotIn("repository", GetManifestSchemaTool(self.all()).input_schema()["properties"])

    def test_manifest_kinds(self):
        """Without a kind, the kinds are listed."""
        text = GetManifestSchemaTool(self.single()).call({})
        self.assertIn("# Smarter resource kinds", text)
        self.assertIn("- LLMClient", text)
        self.assertIn("- Secret", text)

    def test_manifest_schema(self):
        """A kind's result has its example in YAML, its schema's url and its fields, without status."""
        text = GetManifestSchemaTool(self.all()).call({"kind": "secret", "repository": "ignored"})
        self.assertIn("# Secret manifest", text)
        self.assertIn("```yaml\napiVersion: smarter.sh/v1\nkind: Secret\n", text)
        self.assertIn(
            "Full JSON Schema: https://github.com/smarter-sh/smarter/blob/main/"
            "smarter/smarter/apps/api/v1/contract/sam/Secret.schema.json",
            text,
        )
        self.assertIn("- `spec.config.value` (string, required): The unencrypted value of the Secret.", text)
        self.assertNotIn("`status", text)
        self.assertNotIn("more fields", text)

    def test_manifest_schema_defaults(self):
        """A field's default is shown, as JSON."""
        text = GetManifestSchemaTool(self.single()).call({"kind": "MCPClient"})
        self.assertRegex(text, r"`spec\.config\.timeout` \(integer, optional, default \d+\)")

    def test_manifest_schema_is_truncated(self):
        """Fields beyond MAX_READ_CHARACTERS are left out, and the result says where they are."""
        with mock.patch.object(manifest_tools, "MAX_READ_CHARACTERS", 3000):
            text = GetManifestSchemaTool(self.single()).call({"kind": "LLMClient"})
        self.assertRegex(text, r"\[\d+ more fields: see the full JSON Schema, https://github\.com/")

    def test_manifest_schema_url_without_the_smarter_repository(self):
        """The schema's url is the smarter repository's, even when the tests replace the repositories."""
        self.assertTrue(GetManifestSchemaTool.schema_url("Secret").startswith("https://github.com/smarter-sh/smarter/"))

    def test_unknown_kind(self):
        """An unknown kind is an error that lists the kinds."""
        with self.assertRaisesRegex(SmarterMCPServerToolError, "is not a resource kind. It is one of: .*LLMClient"):
            GetManifestSchemaTool(self.single()).call({"kind": "Chatbot"})

    # -------------------------------------------------------------------------
    # validate_manifest
    # -------------------------------------------------------------------------
    def test_validate_manifest_is_served_everywhere(self):
        """Validate_manifest takes no repository, on every server."""
        self.assertNotIn("repository", ValidateManifestTool(self.all()).input_schema()["properties"])

    def test_validate_manifest(self):
        """A valid manifest says so, and an invalid one lists its errors with their paths."""
        example = schemas.manifest_example("Secret")
        valid = ValidateManifestTool(self.single()).call({"manifest": yaml.safe_dump(example)})
        self.assertTrue(valid.startswith("The manifest is valid."))
        del example["metadata"]["name"]
        invalid = ValidateManifestTool(self.single()).call({"manifest": yaml.safe_dump(example)})
        self.assertIn("errors:", invalid)
        self.assertIn("- `metadata.name`:", invalid)

    def test_validate_manifest_of_unknown_kind_and_bad_yaml(self):
        """An unknown kind is an error of the whole manifest's kind; text that is not YAML is a tool error."""
        text = ValidateManifestTool(self.single()).call({"manifest": "kind: Chatbot\n"})
        self.assertIn("- `kind`: kind must be one of", text)
        text = ValidateManifestTool(self.single()).call({"manifest": "- a list\n"})
        self.assertIn("- `(manifest)`: The manifest is not a JSON or YAML object.", text)
        with self.assertRaisesRegex(SmarterMCPServerToolError, "not valid YAML"):
            ValidateManifestTool(self.single()).call({"manifest": "a: [1\n"})
