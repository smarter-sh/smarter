# pylint: disable=too-many-lines,too-many-public-methods
"""
Unit tests for the SkillPlugin manifest models, and for the parsing and validation of.

SKILL.md documents and skill source URLs, per the Agent Skills specification.

These tests do not use the database.

.. seealso::

    - :py:mod:`smarter.apps.plugin.manifest.models.skill_plugin.document`
    - :py:mod:`smarter.apps.plugin.manifest.models.skill_plugin.source`
    - :py:mod:`smarter.apps.plugin.manifest.models.skill_plugin.spec`
    - Agent Skills specification: https://agentskills.io/specification
"""

import copy
import glob
import os

from smarter.apps.plugin.manifest.models.skill_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.skill_plugin.document import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    MAX_RESOURCE_LENGTH,
    MAX_RESOURCES,
    MAX_SKILL_DOCUMENT_LENGTH,
    SkillDocumentError,
    find_resource_references,
    normalize_resource_path,
    normalize_resources,
    parse_allowed_tools,
    parse_skill_document,
)
from smarter.apps.plugin.manifest.models.skill_plugin.model import SAMSkillPlugin
from smarter.apps.plugin.manifest.models.skill_plugin.source import (
    SkillSourceError,
    parse_source_url,
)
from smarter.apps.plugin.manifest.models.skill_plugin.spec import (
    SAMSkillPluginSpec,
    SkillData,
    SkillSource,
)
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.unittest.base_classes import SmarterTestBase

HERE = os.path.abspath(os.path.dirname(__file__))
SAMPLE_PLUGINS_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "..", "data", "sample-plugins"))
TEST_DATA_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "..", "plugin", "tests", "data"))

MINIMAL_SKILL = """---
name: minimal-skill
description: A minimal skill. Use when testing.
---
"""

FULL_SKILL = """---
name: pdf-processing
description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
license: Apache-2.0
compatibility: Requires Python 3.14+ and uv
allowed-tools: Bash(git:*) Bash(jq:*) Read
metadata:
  author: example-org
  version: "1.0"
---

# PDF processing

See [the reference guide](references/REFERENCE.md) for details.

Run the extraction script:
scripts/extract.py
"""


def skill_with(**frontmatter) -> str:
    """Return a SKILL.md document with the given frontmatter lines, and a short body."""
    fields = {"name": "test-skill", "description": "A test skill. Use when testing.", **frontmatter}
    lines = [f"{key}: {value}" for key, value in fields.items() if value is not None]
    return "---\n" + "\n".join(lines) + "\n---\n\n# Test skill\n"


class TestSkillPluginManifest(SmarterTestBase):
    """Test SKILL.md parsing, skill source URLs, and the SkillPlugin manifest models."""

    # =========================================================================
    # SKILL.md frontmatter
    # =========================================================================
    def test_parse_minimal_skill(self):
        """Test the minimal example from the specification, which has an empty body."""
        document = parse_skill_document(MINIMAL_SKILL)
        self.assertEqual(document.name, "minimal-skill")
        self.assertEqual(document.description, "A minimal skill. Use when testing.")
        self.assertEqual(document.body, "")
        self.assertIsNone(document.license)
        self.assertIsNone(document.compatibility)
        self.assertEqual(document.metadata, {})
        self.assertEqual(document.allowed_tools, [])

    def test_parse_full_skill(self):
        """Test a skill that uses every standard frontmatter field."""
        document = parse_skill_document(FULL_SKILL)
        self.assertEqual(document.name, "pdf-processing")
        self.assertEqual(document.license, "Apache-2.0")
        self.assertEqual(document.compatibility, "Requires Python 3.14+ and uv")
        self.assertEqual(document.metadata, {"author": "example-org", "version": "1.0"})
        self.assertEqual(document.allowed_tools, ["Bash(git:*)", "Bash(jq:*)", "Read"])
        self.assertTrue(document.body.startswith("# PDF processing"))

    def test_parse_preserves_document(self):
        """Test that the verbatim document is preserved."""
        self.assertEqual(parse_skill_document(FULL_SKILL).document, FULL_SKILL)

    def test_parse_preserves_unknown_frontmatter_keys(self):
        """Test that frontmatter extensions, such as those of Claude Code, are preserved."""
        document = parse_skill_document(skill_with(model="claude-opus-4", **{"disable-model-invocation": "true"}))
        self.assertEqual(document.frontmatter["model"], "claude-opus-4")
        self.assertIs(document.frontmatter["disable-model-invocation"], True)

    def test_parse_body_preserves_markdown(self):
        """Test that the Markdown body, including code blocks and trailing whitespace inside them, is preserved."""
        body = "# Title\n\n```python\nprint('---')\n```\n\n| a | b |\n| - | - |\n"
        document = parse_skill_document(f"---\nname: t\ndescription: d\n---\n{body}")
        self.assertEqual(document.body, body.rstrip("\n"))

    def test_parse_body_containing_frontmatter_delimiter(self):
        """Test that a '---' horizontal rule in the body does not end the frontmatter early."""
        document = parse_skill_document("---\nname: t\ndescription: d\n---\n\nabove\n\n---\n\nbelow\n")
        self.assertIn("above", document.body)
        self.assertIn("below", document.body)

    def test_parse_windows_line_endings(self):
        """Test that CRLF line endings are normalized."""
        document = parse_skill_document(FULL_SKILL.replace("\n", "\r\n"))
        self.assertEqual(document.name, "pdf-processing")
        self.assertNotIn("\r", document.document)

    def test_parse_byte_order_mark(self):
        """Test that a leading UTF-8 byte order mark is ignored."""
        self.assertEqual(parse_skill_document("﻿" + MINIMAL_SKILL).name, "minimal-skill")

    def test_parse_frontmatter_delimiter_trailing_whitespace(self):
        """Test that trailing whitespace on the '---' delimiters is tolerated."""
        self.assertEqual(parse_skill_document("---  \nname: t\ndescription: d\n--- \nbody").body, "body")

    def test_parse_frontmatter_dates_are_json_serializable(self):
        """Test that YAML dates in the frontmatter are converted to strings."""
        document = parse_skill_document(skill_with(metadata="{released: 2025-10-16}"))
        self.assertEqual(document.metadata, {"released": "2025-10-16"})

    def test_parse_multiline_description(self):
        """Test a folded multi-line description."""
        document = parse_skill_document("---\nname: t\ndescription: >\n  line one\n  line two\n---\n")
        self.assertEqual(document.description, "line one line two\n")

    def test_parse_unicode(self):
        """Test unicode in the description and body."""
        document = parse_skill_document("---\nname: t\ndescription: Café ☕\n---\nüñï\n")
        self.assertEqual(document.description, "Café ☕")
        self.assertEqual(document.body, "üñï")

    # =========================================================================
    # SKILL.md structure errors
    # =========================================================================
    def test_parse_empty(self):
        """Test that an empty document is rejected."""
        for document in ("", "   \n", None, 42):
            with self.assertRaises(SkillDocumentError, msg=f"document={document!r}"):
                parse_skill_document(document)  # type: ignore[arg-type]

    def test_parse_without_frontmatter(self):
        """Test that a document without frontmatter is rejected."""
        with self.assertRaises(SkillDocumentError):
            parse_skill_document("# Just markdown\n")

    def test_parse_unterminated_frontmatter(self):
        """Test that frontmatter without a closing delimiter is rejected."""
        with self.assertRaises(SkillDocumentError):
            parse_skill_document("---\nname: t\ndescription: d\n")

    def test_parse_frontmatter_not_at_start(self):
        """Test that frontmatter must be at the very start of the document."""
        with self.assertRaises(SkillDocumentError):
            parse_skill_document("\n---\nname: t\ndescription: d\n---\n")

    def test_parse_invalid_yaml(self):
        """Test that invalid YAML frontmatter is rejected."""
        with self.assertRaises(SkillDocumentError):
            parse_skill_document("---\nname: [unclosed\ndescription: d\n---\n")

    def test_parse_frontmatter_not_a_mapping(self):
        """Test that frontmatter must be a mapping."""
        for frontmatter in ("- a\n- b", "just a string", ""):
            with self.assertRaises(SkillDocumentError, msg=f"frontmatter={frontmatter!r}"):
                parse_skill_document(f"---\n{frontmatter}\n---\n")

    def test_parse_too_long(self):
        """Test that an overly long document is rejected."""
        with self.assertRaises(SkillDocumentError):
            parse_skill_document(MINIMAL_SKILL + "x" * MAX_SKILL_DOCUMENT_LENGTH)

    def test_skill_document_error_is_a_value_error(self):
        """Test that SkillDocumentError is a SmarterValueError, which the ORM layer expects."""
        self.assertTrue(issubclass(SkillDocumentError, SmarterValueError))

    # =========================================================================
    # frontmatter: name
    # =========================================================================
    def test_name_valid(self):
        """Test the valid names from the specification, and others."""
        for name in ("pdf-processing", "data-analysis", "code-review", "a", "a1", "1-2-3", "x" * MAX_NAME_LENGTH):
            self.assertEqual(parse_skill_document(skill_with(name=name)).name, name)

    def test_name_invalid(self):
        """Test the invalid names from the specification, and others."""
        for name in (
            "PDF-Processing",
            "-pdf",
            "pdf-",
            "pdf--processing",
            "pdf_processing",
            "pdf processing",
            "pdf.processing",
            "x" * (MAX_NAME_LENGTH + 1),
        ):
            with self.assertRaises(SkillDocumentError, msg=f"name={name!r}"):
                parse_skill_document(skill_with(name=name))

    def test_name_required(self):
        """Test that name is required, and must be a string."""
        for name in (None, "''", "123"):
            with self.assertRaises(SkillDocumentError, msg=f"name={name!r}"):
                parse_skill_document(skill_with(name=name))

    # =========================================================================
    # frontmatter: description
    # =========================================================================
    def test_description_required(self):
        """Test that description is required, and must not be empty."""
        for description in (None, "''", "'   '"):
            with self.assertRaises(SkillDocumentError, msg=f"description={description!r}"):
                parse_skill_document(skill_with(description=description))

    def test_description_length(self):
        """Test the maximum description length."""
        parse_skill_document(skill_with(description="x" * MAX_DESCRIPTION_LENGTH))
        with self.assertRaises(SkillDocumentError):
            parse_skill_document(skill_with(description="x" * (MAX_DESCRIPTION_LENGTH + 1)))

    def test_description_must_be_a_string(self):
        """Test that a non-string description is rejected."""
        with self.assertRaises(SkillDocumentError):
            parse_skill_document(skill_with(description="[a, b]"))

    # =========================================================================
    # frontmatter: optional fields
    # =========================================================================
    def test_license(self):
        """Test the license field, which may refer to a bundled license file."""
        document = parse_skill_document(skill_with(license="Proprietary. LICENSE.txt has complete terms"))
        self.assertEqual(document.license, "Proprietary. LICENSE.txt has complete terms")
        with self.assertRaises(SkillDocumentError):
            parse_skill_document(skill_with(license="[MIT]"))

    def test_compatibility(self):
        """Test the compatibility field, which is limited to 500 characters."""
        parse_skill_document(skill_with(compatibility="x" * 500))
        for compatibility in ("x" * 501, "''", "[a]"):
            with self.assertRaises(SkillDocumentError, msg=f"compatibility={compatibility!r}"):
                parse_skill_document(skill_with(compatibility=compatibility))

    def test_metadata(self):
        """Test the metadata field, which must be a mapping."""
        self.assertEqual(parse_skill_document(skill_with(metadata="{a: b}")).metadata, {"a": "b"})
        for metadata in ("[a, b]", "just a string"):
            with self.assertRaises(SkillDocumentError, msg=f"metadata={metadata!r}"):
                parse_skill_document(skill_with(metadata=metadata))

    # =========================================================================
    # frontmatter: allowed-tools
    # =========================================================================
    def test_allowed_tools_space_separated(self):
        """Test the space-separated string format of the specification."""
        self.assertEqual(parse_allowed_tools("Bash(git:*) Bash(jq:*) Read"), ["Bash(git:*)", "Bash(jq:*)", "Read"])

    def test_allowed_tools_with_spaces_inside_parentheses(self):
        """Test that a tool pattern containing spaces is a single tool."""
        self.assertEqual(
            parse_allowed_tools("Bash(git status:*) Bash(npm run test:*) Read"),
            ["Bash(git status:*)", "Bash(npm run test:*)", "Read"],
        )

    def test_allowed_tools_comma_separated(self):
        """Test the comma-separated string format, which is common in practice."""
        self.assertEqual(parse_allowed_tools("Read, Grep,Glob"), ["Read", "Grep", "Glob"])

    def test_allowed_tools_list(self):
        """Test the YAML list format, which is common in practice."""
        self.assertEqual(parse_allowed_tools(["Read", " Grep "]), ["Read", "Grep"])

    def test_allowed_tools_empty(self):
        """Test empty values."""
        for value in (None, "", "   ", []):
            self.assertEqual(parse_allowed_tools(value), [], f"value={value!r}")

    def test_allowed_tools_invalid(self):
        """Test values that are neither a string nor a list of strings."""
        for value in (42, {"a": "b"}, ["Read", 1], ["Read", ""]):
            with self.assertRaises(SkillDocumentError, msg=f"value={value!r}"):
                parse_allowed_tools(value)

    def test_allowed_tools_in_frontmatter(self):
        """Test that allowed-tools is normalized when parsing a document, in each format."""
        for value, expected in (
            ("Read Grep", ["Read", "Grep"]),
            ("'Read, Grep'", ["Read", "Grep"]),
            ("[Read, Grep]", ["Read", "Grep"]),
        ):
            document = parse_skill_document(skill_with(**{"allowed-tools": value}))
            self.assertEqual(document.allowed_tools, expected, f"value={value!r}")

    def test_allowed_tools_invalid_in_frontmatter(self):
        """Test that an invalid allowed-tools value is rejected when parsing a document."""
        with self.assertRaises(SkillDocumentError):
            parse_skill_document(skill_with(**{"allowed-tools": "42"}))

    # =========================================================================
    # bundled file paths
    # =========================================================================
    def test_normalize_resource_path(self):
        """Test the normalization of bundled file paths."""
        for path, expected in (
            ("references/REFERENCE.md", "references/REFERENCE.md"),
            ("./references/REFERENCE.md", "references/REFERENCE.md"),
            ("references//REFERENCE.md", "references/REFERENCE.md"),
            ("references/./REFERENCE.md", "references/REFERENCE.md"),
            ("scripts/../references/a.md", "references/a.md"),
            (" FORMS.md ", "FORMS.md"),
        ):
            self.assertEqual(normalize_resource_path(path), expected, f"path={path!r}")

    def test_normalize_resource_path_invalid(self):
        """Test that paths that are empty, absolute, URLs, or escape the skill root are rejected."""
        for path in (
            "",
            "   ",
            None,
            "/etc/passwd",
            "../secrets.md",
            "references/../../secrets.md",
            "..",
            ".",
            "references\\a.md",
            "https://example.com/a.md",
            "file:///etc/passwd",
            "a\x00.md",
            "a" * 600,
        ):
            with self.assertRaises(SkillDocumentError, msg=f"path={path!r}"):
                normalize_resource_path(path)  # type: ignore[arg-type]

    def test_normalize_resources(self):
        """Test that bundled files are normalized, sorted, and may be unavailable (None)."""
        resources = normalize_resources({"./scripts/b.py": "print(1)\r\n", "assets/logo.png": None, "a.md": "a"})
        self.assertEqual(resources, {"a.md": "a", "assets/logo.png": None, "scripts/b.py": "print(1)\n"})
        self.assertEqual(list(resources), ["a.md", "assets/logo.png", "scripts/b.py"])

    def test_normalize_resources_empty(self):
        """Test empty resources."""
        for resources in (None, {}):
            self.assertEqual(normalize_resources(resources), {})

    def test_normalize_resources_invalid(self):
        """Test invalid resources."""
        for resources in (
            ["a.md"],
            {"../a.md": "a"},
            {"SKILL.md": "---"},
            {"./SKILL.md": "---"},
            {"a.md": "a", "./a.md": "b"},
            {"a.md": 42},
            {"a.md": "x" * (MAX_RESOURCE_LENGTH + 1)},
            {f"{i}.md": "" for i in range(MAX_RESOURCES + 1)},
        ):
            with self.assertRaises(SkillDocumentError, msg=f"resources={str(resources)[:60]}"):
                normalize_resources(resources)  # type: ignore[arg-type]

    def test_find_resource_references(self):
        """Test finding the bundled files that a SKILL.md body refers to."""
        body = (
            "See [the guide](./reference/guide.md) and [forms](FORMS.md#section).\n"
            'Also [titled](references/a.md "Title"), and run `scripts/fill_form.py`.\n'
            "Ignore [site](https://example.com/a.md), [anchor](#top), [abs](/etc/passwd), "
            "[escape](../secret.md), [mail](mailto:a@b.c) and `not a path`.\n"
            "Repeat [the guide](reference/guide.md), and see [skill](SKILL.md).\n"
        )
        self.assertEqual(
            find_resource_references(body),
            ["reference/guide.md", "FORMS.md", "references/a.md", "scripts/fill_form.py"],
        )

    def test_find_resource_references_none(self):
        """Test a body without references."""
        self.assertEqual(find_resource_references("# Nothing to see here\n"), [])

    # =========================================================================
    # skill source urls
    # =========================================================================
    def test_source_github_tree(self):
        """Test the GitHub URL of a skill directory."""
        location = parse_source_url("https://github.com/anthropics/skills/tree/main/skills/pdf")
        self.assertTrue(location.is_github)
        self.assertEqual(
            (location.owner, location.repo, location.ref, location.path), ("anthropics", "skills", "main", "skills/pdf")
        )
        self.assertEqual(
            location.skill_url, "https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/SKILL.md"
        )
        self.assertEqual(location.base_url, "https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/")
        self.assertEqual(location.skill_directory_name, "pdf")

    def test_source_github_tree_trailing_slash(self):
        """Test a GitHub directory URL with a trailing slash."""
        location = parse_source_url("https://github.com/anthropics/skills/tree/main/skills/pdf/")
        self.assertEqual(location.path, "skills/pdf")

    def test_source_github_blob(self):
        """Test the GitHub URL of a SKILL.md file."""
        location = parse_source_url("https://github.com/anthropics/skills/blob/main/skills/pdf/SKILL.md")
        self.assertEqual(location.path, "skills/pdf")
        self.assertEqual(
            location.skill_url, "https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/SKILL.md"
        )

    def test_source_github_raw(self):
        """Test the raw.githubusercontent.com URL of a SKILL.md file."""
        location = parse_source_url("https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/SKILL.md")
        self.assertTrue(location.is_github)
        self.assertEqual((location.owner, location.ref, location.path), ("anthropics", "main", "skills/pdf"))

    def test_source_github_repository_root(self):
        """Test a GitHub repository whose root is the skill, which uses the default branch."""
        location = parse_source_url("https://github.com/example-org/my-skill")
        self.assertEqual((location.ref, location.path), ("HEAD", ""))
        self.assertEqual(location.skill_url, "https://raw.githubusercontent.com/example-org/my-skill/HEAD/SKILL.md")
        self.assertEqual(location.skill_directory_name, "my-skill")

    def test_source_github_repository_git_suffix(self):
        """Test a GitHub repository URL with a .git suffix."""
        self.assertEqual(parse_source_url("https://github.com/example-org/my-skill.git").repo, "my-skill")

    def test_source_github_commit_sha(self):
        """Test pinning a skill to a commit."""
        location = parse_source_url("https://github.com/anthropics/skills/tree/0123abc/skills/pdf")
        self.assertEqual(location.ref, "0123abc")

    def test_source_github_repository_root_tree(self):
        """Test the GitHub URL of a repository root at a ref."""
        location = parse_source_url("https://github.com/example-org/my-skill/tree/v1.0")
        self.assertEqual((location.ref, location.path), ("v1.0", ""))

    def test_source_github_url_encoding(self):
        """Test that path segments are URL encoded."""
        location = parse_source_url("https://github.com/o/r/tree/main/my skills/a")
        self.assertEqual(location.base_url, "https://raw.githubusercontent.com/o/r/main/my%20skills/a/")
        self.assertEqual(location.resource_url("references/a b.md"), location.base_url + "references/a%20b.md")

    def test_source_generic(self):
        """Test any other https URL of a SKILL.md file."""
        location = parse_source_url("https://example.com/skills/my-skill/SKILL.md?download=1#top")
        self.assertFalse(location.is_github)
        self.assertEqual(location.skill_url, "https://example.com/skills/my-skill/SKILL.md")
        self.assertEqual(location.base_url, "https://example.com/skills/my-skill/")
        self.assertEqual(location.skill_directory_name, "my-skill")

    def test_source_invalid(self):
        """Test unsupported URLs."""
        for url in (
            "",
            "   ",
            None,
            "http://github.com/anthropics/skills/tree/main/skills/pdf",
            "ftp://example.com/SKILL.md",
            "file:///skills/SKILL.md",
            "github.com/anthropics/skills",
            "https://github.com/anthropics",
            "https://github.com/anthropics/skills/issues/1",
            "https://github.com/anthropics/skills/tree",
            "https://github.com/anthropics/skills/blob/main/skills/pdf/forms.md",
            "https://raw.githubusercontent.com/anthropics/skills/main/skills/pdf/forms.md",
            "https://raw.githubusercontent.com/anthropics/SKILL.md",
            "https://example.com/skills/my-skill/",
            "https://example.com/skills/my-skill/README.md",
            "https://user:password@example.com/SKILL.md",
            "https:///SKILL.md",
            "https://example.com/" + "a" * 2048 + "/SKILL.md",
        ):
            with self.assertRaises(SkillSourceError, msg=f"url={url!r}"):
                parse_source_url(url)  # type: ignore[arg-type]

    def test_source_error_is_a_value_error(self):
        """Test that SkillSourceError is a SmarterValueError."""
        self.assertTrue(issubclass(SkillSourceError, SmarterValueError))

    # =========================================================================
    # SkillData and SkillSource
    # =========================================================================
    def test_skill_data_verbatim(self):
        """Test a SkillData containing a SKILL.md verbatim."""
        skill_data = SkillData(skill=FULL_SKILL, resources={"references/REFERENCE.md": "# Reference"})
        self.assertEqual(skill_data.document.name, "pdf-processing")  # type: ignore[union-attr]
        self.assertIsNone(skill_data.source)

    def test_skill_data_source(self):
        """Test a SkillData referring to a remote skill."""
        skill_data = SkillData(source=SkillSource(url="https://github.com/anthropics/skills/tree/main/skills/pdf"))
        self.assertIsNone(skill_data.document)
        self.assertEqual(skill_data.source.location.path, "skills/pdf")  # type: ignore[union-attr]

    def test_skill_data_source_from_dict(self):
        """Test a SkillData whose source is a dict, as parsed from YAML."""
        skill_data = SkillData(**{"source": {"url": " https://github.com/anthropics/skills/tree/main/skills/pdf "}})
        self.assertEqual(skill_data.source.url, "https://github.com/anthropics/skills/tree/main/skills/pdf")  # type: ignore[union-attr]

    def test_skill_data_requires_exactly_one_of_skill_or_source(self):
        """Test that exactly one of skill or source is required."""
        source = SkillSource(url="https://github.com/anthropics/skills/tree/main/skills/pdf")
        for kwargs in ({}, {"skill": ""}, {"skill": FULL_SKILL, "source": source}):
            with self.assertRaises(SAMValidationError, msg=f"kwargs={list(kwargs)}"):
                SkillData(**kwargs)

    def test_skill_data_resources_require_skill(self):
        """Test that resources cannot be combined with a remote source."""
        with self.assertRaises(SAMValidationError):
            SkillData(
                source=SkillSource(url="https://github.com/anthropics/skills/tree/main/skills/pdf"),
                resources={"a.md": "a"},
            )

    def test_skill_data_invalid_skill(self):
        """Test that an invalid SKILL.md is rejected as a SAMValidationError."""
        with self.assertRaises(SAMValidationError) as context:
            SkillData(skill="# no frontmatter")
        self.assertIn("frontmatter", str(context.exception))

    def test_skill_data_invalid_resources(self):
        """Test that invalid bundled file paths are rejected as a SAMValidationError."""
        with self.assertRaises(SAMValidationError):
            SkillData(skill=FULL_SKILL, resources={"../escape.md": "a"})

    def test_skill_source_invalid_url(self):
        """Test that an unsupported source URL is rejected as a SAMValidationError."""
        with self.assertRaises(SAMValidationError):
            SkillSource(url="http://github.com/anthropics/skills/tree/main/skills/pdf")

    # =========================================================================
    # SAMSkillPlugin manifests
    # =========================================================================
    def test_test_data_manifests(self):
        """Test that the plugin unit test data manifests are valid."""
        for filename in ("skill-plugin.yaml", "skill-plugin-remote.yaml"):
            manifest = SAMSkillPlugin(**get_readonly_yaml_file(os.path.join(TEST_DATA_PATH, filename)))
            self.assertEqual(manifest.kind, MANIFEST_KIND, filename)

    def test_sample_manifests(self):
        """Test that every sample SkillPlugin manifest is valid."""
        paths = sorted(glob.glob(os.path.join(SAMPLE_PLUGINS_PATH, "skill-*.yaml")))
        self.assertGreaterEqual(len(paths), 7)
        for path in paths:
            manifest = SAMSkillPlugin(**get_readonly_yaml_file(path))
            self.assertEqual(manifest.kind, MANIFEST_KIND, path)
            self.assertEqual(manifest.metadata.pluginClass, "skill", path)

    def test_sample_manifests_cover_verbatim_and_remote_skills(self):
        """Test that the samples illustrate verbatim skills, bundled files, and each form of remote source url."""
        skill_data = [
            SAMSkillPlugin(**get_readonly_yaml_file(path)).spec.skillData
            for path in glob.glob(os.path.join(SAMPLE_PLUGINS_PATH, "skill-*.yaml"))
        ]
        self.assertTrue(any(data.skill and data.resources for data in skill_data))
        urls = [data.source.url for data in skill_data if data.source]
        self.assertTrue(any("/tree/" in url for url in urls))
        self.assertTrue(any("/blob/" in url for url in urls))
        self.assertTrue(any("raw.githubusercontent.com" in url for url in urls))

    def test_manifest_skill_is_verbatim(self):
        """Test that a SKILL.md pasted into a YAML literal block scalar is preserved exactly."""
        manifest = get_readonly_yaml_file(os.path.join(TEST_DATA_PATH, "skill-plugin.yaml"))
        skill = SAMSkillPlugin(**manifest).spec.skillData.skill
        self.assertTrue(skill.startswith("---\nname: expense-reports\n"))  # type: ignore[union-attr]
        self.assertIn("\n## Instructions\n\n1. Collect the receipts", skill)  # type: ignore[operator]

    def test_manifest_requires_skill_data(self):
        """Test that spec.skillData is required."""
        manifest = get_readonly_yaml_file(os.path.join(TEST_DATA_PATH, "skill-plugin.yaml"))
        spec = copy.deepcopy(manifest["spec"])
        spec.pop("skillData")
        with self.assertRaises(Exception):
            SAMSkillPluginSpec(**spec)
