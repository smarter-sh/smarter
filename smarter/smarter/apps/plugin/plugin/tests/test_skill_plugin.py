# pylint: disable=too-many-lines,protected-access
"""
Unit tests for :py:class:`smarter.apps.plugin.plugin.skill.SkillPlugin`, and for the.

:py:class:`smarter.apps.plugin.models.PluginDataSkill` model that stores its skill.

The shared fixtures are two SkillPlugins: one whose SKILL.md and bundled files are
contained verbatim in its manifest (``./data/skill-plugin.yaml``), and one that refers
to a skill on GitHub (``./data/skill-plugin-remote.yaml``), which is served by
:class:`FakeSkillHost` from ``./data/skill-remote``.
"""

import copy
import glob
import os
from unittest import mock

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.manifest.controller import (
    PLUGIN_MAP,
    PLUGIN_META_CLASS_MAP,
    SAM_MAP,
    PluginController,
)
from smarter.apps.plugin.manifest.enum import SAMPluginCommonMetadataClass
from smarter.apps.plugin.manifest.models.skill_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.skill_plugin.document import (
    parse_skill_document,
)
from smarter.apps.plugin.manifest.models.skill_plugin.model import SAMSkillPlugin
from smarter.apps.plugin.models import PLUGIN_DATA_MAP, PluginDataSkill, PluginMeta
from smarter.apps.plugin.plugin.skill import (
    SkillPlugin,
    SmarterSkillPluginError,
)
from smarter.apps.plugin.plugin.skill_sources import retrieve_skill
from smarter.apps.plugin.serializers import PluginSkillSerializer
from smarter.apps.plugin.signals import plugin_called, plugin_responded
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import json

from .base_classes import (
    SKILL_PLUGIN_NAME,
    SKILL_REMOTE_PLUGIN_NAME,
    SKILL_REMOTE_RAW_URL,
    SKILL_REMOTE_URL,
    SKILL_SOURCES_REQUESTS_PATCH,
    FakeSkillHost,
    PluginTestBase,
    capture_signal,
    mock_skill_host,
)

HERE = os.path.abspath(os.path.dirname(__file__))
SAMPLE_PLUGINS_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "data", "sample-plugins"))

INLINE_RESOURCES = ["assets/logo.png", "references/forms.md", "references/policy.md", "scripts/fill_form.py"]
REMOTE_RESOURCES = ["LICENSE.txt", "assets/logo.png", "forms.md", "reference.md", "scripts/fill_form.py"]

MINIMAL_SKILL = """---
name: minimal-skill
description: A minimal skill. Use when testing.
---

Do the thing.
"""


# pylint: disable=too-many-public-methods
class TestSkillPlugin(PluginTestBase):
    """Test SkillPlugin, using the shared SkillPlugin fixtures."""

    sql_fixtures = False
    api_fixtures = False
    skill_fixtures = True

    @property
    def inline_skill(self) -> str:
        """The SKILL.md of ./data/skill-plugin.yaml."""
        return self.skill_plugin_yaml["spec"]["skillData"]["skill"]

    def ask(self, function_args=None, remote: bool = False):
        """Run a tool call against a freshly loaded shared plugin."""
        return self.load_skill_plugin(remote=remote).tool_call_fetch_plugin_response(function_args)

    # =========================================================================
    # fixtures
    # =========================================================================
    def test_000_fixtures(self):
        """Test the class fixtures themselves, lest we get ahead of ourselves."""
        self.assertTrue(self.ready)
        for plugin in (self.skill_plugin, self.skill_remote_plugin):
            self.assertIsInstance(plugin, SkillPlugin)
            self.assertTrue(plugin.ready)
        self.assertEqual(self.skill_plugin.name, SKILL_PLUGIN_NAME)
        self.assertEqual(self.skill_remote_plugin.name, SKILL_REMOTE_PLUGIN_NAME)

    def test_001_fixture_plugins_persisted(self):
        """Test that the shared plugins exist in the database."""
        for plugin in (self.skill_plugin, self.skill_remote_plugin):
            self.assertTrue(PluginMeta.objects.filter(id=plugin.id, plugin_class="skill").exists())
            self.assertTrue(PluginDataSkill.objects.filter(plugin_id=plugin.id).exists())

    # =========================================================================
    # class structure and registration
    # =========================================================================
    def test_class_attributes(self):
        """Test the SkillPlugin class attributes."""
        self.assertIs(SkillPlugin.SAMPluginType, SAMSkillPlugin)
        self.assertEqual(self.skill_plugin.kind, MANIFEST_KIND)
        self.assertEqual(MANIFEST_KIND, "SkillPlugin")
        self.assertIs(self.skill_plugin.plugin_data_class, PluginDataSkill)
        self.assertIs(self.skill_plugin.plugin_data_serializer_class, PluginSkillSerializer)

    def test_metadata_class(self):
        """Test that the plugin class is skill."""
        self.assertEqual(self.load_skill_plugin().metadata_class, SAMPluginCommonMetadataClass.SKILL.value)

    def test_has_no_orm_model_class(self):
        """Test that the misnamed ORMModelClass property, which returned a Pydantic class, has been removed."""
        self.assertFalse(hasattr(SkillPlugin, "ORMModelClass"))

    def test_plugin_meta_kind(self):
        """Test that a skill PluginMeta is of kind SkillPlugin."""
        self.assertEqual(self.load_skill_plugin().plugin_meta.kind, SAMKinds.SKILL_PLUGIN)  # type: ignore[union-attr]

    def test_registered_in_maps(self):
        """Test that SkillPlugin is registered with the plugin controller and the plugin data map."""
        self.assertIs(PLUGIN_MAP[SAMKinds.SKILL_PLUGIN.value], SkillPlugin)
        self.assertIs(PLUGIN_META_CLASS_MAP["skill"], SkillPlugin)
        self.assertIs(SAM_MAP[SAMKinds.SKILL_PLUGIN.value], SAMSkillPlugin)
        self.assertIs(PLUGIN_DATA_MAP[SAMKinds.SKILL_PLUGIN.value], PluginDataSkill)

    def test_plugin_controller(self):
        """Test that the plugin controller instantiates a SkillPlugin from its PluginMeta, as the chat providers do."""
        plugin_meta = PluginMeta.objects.get(id=self.skill_plugin.id)
        controller = PluginController(user_profile=self.user_profile, plugin_meta=plugin_meta)
        self.assertIsInstance(controller.plugin, SkillPlugin)
        self.assertTrue(controller.plugin.ready)  # type: ignore[union-attr]

    def test_plugin_controller_plugin_class_from_manifest(self):
        """Test that the plugin controller maps a SkillPlugin manifest to the skill plugin class."""
        controller = PluginController(user_profile=self.user_profile, manifest=self.skill_manifest("controller_test"))
        self.assertEqual(controller.plugin_class, "skill")

    # =========================================================================
    # plugin data: verbatim skill
    # =========================================================================
    def test_plugin_data(self):
        """Test the PluginDataSkill of the verbatim skill."""
        plugin_data = self.load_skill_plugin().plugin_data
        self.assertIsInstance(plugin_data, PluginDataSkill)
        self.assertEqual(plugin_data.skill_document, self.inline_skill)  # type: ignore[union-attr]
        self.assertIsNone(plugin_data.source_url)  # type: ignore[union-attr]
        self.assertIsNone(plugin_data.source_retrieved_at)  # type: ignore[union-attr]

    def test_plugin_data_derived_fields(self):
        """Test that the frontmatter, allowed-tools and description are derived from the SKILL.md."""
        plugin_data = self.load_skill_plugin().plugin_data
        self.assertEqual(plugin_data.metadata["name"], "expense-reports")  # type: ignore[union-attr,index]
        self.assertEqual(plugin_data.metadata["metadata"], {"author": "smarter", "version": "1.0"})  # type: ignore[union-attr,index]
        self.assertEqual(plugin_data.allowed_tools, ["Read", "Bash(python scripts/fill_form.py:*)"])  # type: ignore[union-attr]
        self.assertEqual(plugin_data.description, parse_skill_document(self.inline_skill).description)  # type: ignore[union-attr]

    def test_plugin_data_resources(self):
        """Test the bundled files of the verbatim skill, including a binary file without contents."""
        plugin_data = self.load_skill_plugin().plugin_data
        self.assertEqual(plugin_data.resource_paths, INLINE_RESOURCES)  # type: ignore[union-attr]
        self.assertIsNone(plugin_data.resources["assets/logo.png"])  # type: ignore[union-attr,index]
        self.assertEqual(plugin_data.resources["scripts/fill_form.py"], 'print("filled")\n')  # type: ignore[union-attr,index]
        self.assertEqual(plugin_data.return_data_keys, INLINE_RESOURCES)  # type: ignore[union-attr]

    def test_plugin_data_instructions(self):
        """Test that the instructions are the SKILL.md body."""
        instructions = self.load_skill_plugin().plugin_data.instructions  # type: ignore[union-attr]
        self.assertTrue(instructions.startswith("# Expense reports"))
        self.assertNotIn("name: expense-reports", instructions)

    def test_plugin_data_data(self):
        """Test the structured data() representation."""
        data = self.load_skill_plugin().plugin_data.data()  # type: ignore[union-attr]
        self.assertEqual(data["frontmatter"]["name"], "expense-reports")  # type: ignore[index]
        self.assertEqual(list(data["resources"]), INLINE_RESOURCES)  # type: ignore[index]

    def test_plugin_data_not_ready(self):
        """Test that plugin_data is None for a plugin without a PluginMeta."""
        self.assertIsNone(SkillPlugin().plugin_data)

    def test_plugin_data_serializer(self):
        """Test the PluginDataSkill serializer."""
        data = self.load_skill_plugin(remote=True).plugin_data_serializer.data  # type: ignore[union-attr]
        self.assertEqual(data["sourceUrl"], SKILL_REMOTE_URL)
        self.assertEqual(list(data["resources"]), REMOTE_RESOURCES)
        self.assertEqual(data["allowedTools"], [])

    # =========================================================================
    # plugin data: remote skill
    # =========================================================================
    def test_remote_plugin_data(self):
        """Test that a snapshot of the remote skill, its source and its retrieval time are stored."""
        plugin_data = self.load_skill_plugin(remote=True).plugin_data
        with open(os.path.join(HERE, "data", "skill-remote", "SKILL.md"), encoding="utf-8") as file:
            self.assertEqual(plugin_data.skill_document, file.read())  # type: ignore[union-attr]
        self.assertEqual(plugin_data.source_url, SKILL_REMOTE_URL)  # type: ignore[union-attr]
        self.assertIsNotNone(plugin_data.source_retrieved_at)  # type: ignore[union-attr]
        self.assertEqual(plugin_data.resource_paths, REMOTE_RESOURCES)  # type: ignore[union-attr]

    def test_remote_plugin_does_not_use_the_network_after_apply(self):
        """Test that tool calls on a remote skill use the stored snapshot, and never the network."""
        with mock.patch(SKILL_SOURCES_REQUESTS_PATCH, side_effect=AssertionError("network used")):
            plugin = self.load_skill_plugin(remote=True)
            self.assertEqual(plugin.tool_call_fetch_plugin_response(None)["name"], "test-skill")  # type: ignore[index]
            self.assertTrue(plugin.tool_call_fetch_plugin_response({"resource": "forms.md"})["content"])  # type: ignore[index]
            self.assertTrue(plugin.to_json())

    # =========================================================================
    # PluginDataSkill.find_resource()
    # =========================================================================
    def test_find_resource_exact(self):
        """Test finding a bundled file by its exact path."""
        plugin_data = self.load_skill_plugin().plugin_data
        self.assertEqual(plugin_data.find_resource("references/forms.md")[0], "references/forms.md")  # type: ignore[union-attr]

    def test_find_resource_normalized(self):
        """Test finding a bundled file by an equivalent relative path."""
        plugin_data = self.load_skill_plugin().plugin_data
        self.assertEqual(plugin_data.find_resource("./references//policy.md")[0], "references/policy.md")  # type: ignore[union-attr]

    def test_find_resource_ignoring_case(self):
        """Test finding a bundled file whose case differs from the requested path."""
        plugin_data = self.load_skill_plugin().plugin_data
        self.assertEqual(plugin_data.find_resource("References/FORMS.md")[0], "references/forms.md")  # type: ignore[union-attr]

    def test_find_resource_by_file_name(self):
        """Test finding a bundled file by its file name, as Anthropic's pdf skill refers to FORMS.md."""
        plugin_data = self.load_skill_plugin().plugin_data
        self.assertEqual(plugin_data.find_resource("FORMS.md")[0], "references/forms.md")  # type: ignore[union-attr]
        self.assertEqual(plugin_data.find_resource("fill_form.py")[0], "scripts/fill_form.py")  # type: ignore[union-attr]

    def test_find_resource_ambiguous(self):
        """Test that a file name matching more than one bundled file raises."""
        plugin_data = self.load_skill_plugin().plugin_data
        plugin_data.resources = {"a/notes.md": "a", "b/notes.md": "b"}  # type: ignore[union-attr]
        with self.assertRaises(SmarterValueError) as context:
            plugin_data.find_resource("notes.md")  # type: ignore[union-attr]
        self.assertIn("ambiguous", str(context.exception))

    def test_find_resource_not_found(self):
        """Test that a missing bundled file raises, listing the available files."""
        plugin_data = self.load_skill_plugin().plugin_data
        with self.assertRaises(SmarterValueError) as context:
            plugin_data.find_resource("references/missing.md")  # type: ignore[union-attr]
        self.assertIn("references/forms.md", str(context.exception))

    def test_find_resource_invalid_path(self):
        """Test that a path that escapes the skill root raises, rather than being resolved."""
        plugin_data = self.load_skill_plugin().plugin_data
        for path in ("../secrets.md", "/etc/passwd", "https://example.com/a.md", ""):
            with self.assertRaises(SmarterValueError, msg=f"path={path!r}"):
                plugin_data.find_resource(path)  # type: ignore[union-attr]

    # =========================================================================
    # PluginDataSkill.save()
    # =========================================================================
    def test_save_rejects_invalid_skill_document(self):
        """Test that an invalid SKILL.md cannot be saved."""
        plugin = self.new_skill_plugin("skill_save_invalid")
        plugin_data = PluginDataSkill.objects.get(plugin_id=plugin.id)
        for document in ("# no frontmatter", "---\nname: Bad Name\ndescription: d\n---\n", ""):
            plugin_data.skill_document = document
            with self.assertRaises(SmarterValueError, msg=f"document={document!r}"):
                plugin_data.save()
        self.assertEqual(PluginDataSkill.objects.get(plugin_id=plugin.id).skill_document, self.inline_skill)

    def test_save_rejects_invalid_resources(self):
        """Test that invalid bundled file paths cannot be saved."""
        plugin = self.new_skill_plugin("skill_save_invalid_resources")
        plugin_data = PluginDataSkill.objects.get(plugin_id=plugin.id)
        plugin_data.resources = {"../escape.md": "x"}
        with self.assertRaises(SmarterValueError):
            plugin_data.save()

    def test_save_derives_fields(self):
        """Test that the derived fields are recomputed from the SKILL.md on every save."""
        plugin = self.new_skill_plugin("skill_save_derives")
        plugin_data = PluginDataSkill.objects.get(plugin_id=plugin.id)
        plugin_data.skill_document = MINIMAL_SKILL.replace("\n", "\r\n")
        plugin_data.metadata = {"tampered": True}
        plugin_data.allowed_tools = ["Tampered"]
        plugin_data.description = ""
        plugin_data.save()
        plugin_data.refresh_from_db()
        self.assertEqual(plugin_data.skill_document, MINIMAL_SKILL)
        self.assertEqual(plugin_data.metadata["name"], "minimal-skill")
        self.assertEqual(plugin_data.allowed_tools, [])
        self.assertEqual(plugin_data.description, "A minimal skill. Use when testing.")

    # =========================================================================
    # sanitized_return_data()
    # =========================================================================
    def test_return_data_instructions(self):
        """Test the response to a tool call without a resource: the instructions, and the bundled file paths."""
        retval = self.load_skill_plugin().plugin_data.sanitized_return_data()  # type: ignore[union-attr]
        self.assertEqual(retval["name"], "expense-reports")
        self.assertEqual(retval["instructions"], parse_skill_document(self.inline_skill).body)
        self.assertEqual(retval["license"], "Apache-2.0")
        self.assertEqual(retval["compatibility"], "Requires access to the company expense system.")
        self.assertEqual(retval["allowed_tools"], ["Read", "Bash(python scripts/fill_form.py:*)"])
        self.assertEqual(retval["metadata"], {"author": "smarter", "version": "1.0"})
        self.assertEqual(retval["resources"], INLINE_RESOURCES)
        self.assertIn("resource", retval["note"])

    def test_return_data_minimal_skill(self):
        """Test that optional fields are omitted from the response of a minimal skill without bundled files."""
        plugin = self.new_skill_plugin("skill_minimal", skill=MINIMAL_SKILL, resources=None)
        retval = plugin.plugin_data.sanitized_return_data()  # type: ignore[union-attr]
        self.assertEqual(
            retval,
            {
                "name": "minimal-skill",
                "description": "A minimal skill. Use when testing.",
                "instructions": "Do the thing.",
            },
        )

    def test_return_data_resource(self):
        """Test the response to a tool call for a bundled file."""
        retval = self.load_skill_plugin().plugin_data.sanitized_return_data({"resource": "references/policy.md"})  # type: ignore[union-attr]
        self.assertEqual(
            retval,
            {
                "name": "expense-reports",
                "resource": "references/policy.md",
                "content": "# Travel policy\n## Meals\nAt most $75 per day.\n",
            },
        )

    def test_return_data_binary_resource(self):
        """Test the response to a tool call for a bundled file whose contents are unavailable."""
        retval = self.load_skill_plugin().plugin_data.sanitized_return_data({"resource": "assets/logo.png"})  # type: ignore[union-attr]
        self.assertIsNone(retval["content"])
        self.assertIn("not a text file", retval["note"])

    # =========================================================================
    # custom tool
    # =========================================================================
    def test_custom_tool(self):
        """Test the OpenAI function calling tool definition."""
        plugin = self.load_skill_plugin()
        tool = plugin.custom_tool
        function = tool["function"]  # type: ignore[index]
        self.assertEqual(tool["type"], "function")  # type: ignore[index]
        self.assertEqual(function["name"], plugin.function_calling_identifier)
        self.assertEqual(function["description"], parse_skill_document(self.inline_skill).description)
        self.assertEqual(function["parameters"]["type"], "object")
        self.assertEqual(function["parameters"]["required"], [])
        resource = function["parameters"]["properties"]["resource"]
        self.assertEqual(resource["type"], "string")
        self.assertEqual(resource["enum"], INLINE_RESOURCES)

    def test_custom_tool_without_resources(self):
        """Test that the tool takes no parameters when the skill has no bundled files."""
        tool = self.new_skill_plugin("skill_tool_no_resources", skill=MINIMAL_SKILL, resources=None).custom_tool
        self.assertEqual(tool["function"]["parameters"]["properties"], {})  # type: ignore[index]

    def test_custom_tool_remote(self):
        """Test the tool definition of a remote skill."""
        tool = self.load_skill_plugin(remote=True).custom_tool
        self.assertEqual(tool["function"]["parameters"]["properties"]["resource"]["enum"], REMOTE_RESOURCES)  # type: ignore[index]

    def test_custom_tool_is_json_serializable(self):
        """Test that the tool can be sent to the OpenAI api as JSON."""
        tool = self.load_skill_plugin().custom_tool
        self.assertEqual(json.loads(json.dumps(tool)), tool)

    def test_custom_tool_not_ready(self):
        """Test that the tool is None for a plugin that is not ready."""
        self.assertIsNone(SkillPlugin().custom_tool)

    def test_every_advertised_resource_resolves(self):
        """Test that every bundled file offered to the LLM in the tool's enum can be requested without error."""
        for remote in (False, True):
            plugin = self.load_skill_plugin(remote=remote)
            enum = plugin.custom_tool["function"]["parameters"]["properties"]["resource"]["enum"]  # type: ignore[index]
            for resource in enum:
                retval = plugin.tool_call_fetch_plugin_response({"resource": resource})
                self.assertEqual(retval["resource"], resource, f"remote={remote}")  # type: ignore[index]

    # =========================================================================
    # tool calls
    # =========================================================================
    def test_tool_call_without_arguments(self):
        """Test that a tool call without arguments returns the instructions."""
        for function_args in (None, {}, "", "{}", "  "):
            retval = self.ask(function_args)
            self.assertEqual(retval["name"], "expense-reports", f"function_args={function_args!r}")  # type: ignore[index]
            self.assertIn("instructions", retval, f"function_args={function_args!r}")

    def test_tool_call_with_null_resource(self):
        """Test that a null resource returns the instructions."""
        self.assertIn("instructions", self.ask({"resource": None}))  # type: ignore[arg-type]

    def test_tool_call_resource(self):
        """Test a tool call for a bundled file."""
        retval = self.ask({"resource": "scripts/fill_form.py"})
        self.assertEqual(retval["content"], 'print("filled")\n')  # type: ignore[index]

    def test_tool_call_json_string_args(self):
        """Test a tool call with a JSON string of arguments, as sent by OpenAI."""
        retval = self.ask('{"resource": "references/forms.md"}')
        self.assertEqual(retval["resource"], "references/forms.md")  # type: ignore[index]

    def test_tool_call_resource_as_the_instructions_refer_to_it(self):
        """Test requesting a bundled file by the name the instructions use, whose case differs from its path."""
        self.assertEqual(self.ask({"resource": "FORMS.md"})["resource"], "references/forms.md")  # type: ignore[index]
        self.assertEqual(self.ask({"resource": "REFERENCE.md"}, remote=True)["resource"], "reference.md")  # type: ignore[index]

    def test_tool_call_extra_args_are_ignored(self):
        """Test that arguments other than resource are ignored."""
        self.assertIn("instructions", self.ask({"unexpected": "value"}))  # type: ignore[arg-type]

    def test_tool_call_unknown_resource(self):
        """Test that an unknown bundled file raises, listing the available files."""
        with self.assertRaises(SmarterSkillPluginError) as context:
            self.ask({"resource": "references/missing.md"})
        self.assertIn("references/forms.md", str(context.exception))

    def test_tool_call_invalid_resource(self):
        """Test that a resource that is not a string, or escapes the skill root, raises."""
        for resource in (1, ["a.md"], {"a": 1}, "../SKILL.md", "/etc/passwd"):
            with self.assertRaises(SmarterSkillPluginError, msg=f"resource={resource!r}"):
                self.ask({"resource": resource})

    def test_tool_call_invalid_args(self):
        """Test that malformed arguments raise."""
        for function_args in ("{not json", 42, ["a"], '["a"]'):
            with self.assertRaises(SmarterSkillPluginError, msg=f"function_args={function_args!r}"):
                self.ask(function_args)

    def test_tool_call_not_ready(self):
        """Test that a tool call on a plugin that is not ready raises."""
        with self.assertRaises(SmarterSkillPluginError):
            SkillPlugin().tool_call_fetch_plugin_response({})

    def test_tool_call_no_plugin_data(self):
        """Test that a tool call without plugin data raises."""
        plugin = self.load_skill_plugin()
        with mock.patch.object(SkillPlugin, "plugin_data", new_callable=mock.PropertyMock, return_value=None):
            with self.assertRaises(SmarterSkillPluginError):
                plugin.tool_call_fetch_plugin_response({})

    def test_tool_call_sends_signals(self):
        """Test that a tool call sends plugin_called and plugin_responded."""
        with capture_signal(plugin_called) as called, capture_signal(plugin_responded) as responded:
            retval = self.ask({"resource": "references/forms.md"})
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0]["inquiry_type"], "references/forms.md")
        self.assertEqual(len(responded), 1)
        self.assertEqual(responded[0]["response"], retval)

    def test_tool_call_failure_sends_no_response_signal(self):
        """Test that a failed tool call sends plugin_called, but not plugin_responded."""
        with capture_signal(plugin_called) as called, capture_signal(plugin_responded) as responded:
            with self.assertRaises(SmarterSkillPluginError):
                self.ask({"resource": "missing.md"})
        self.assertEqual(len(called), 1)
        self.assertEqual(responded, [])

    # =========================================================================
    # manifest and serialization
    # =========================================================================
    def test_to_json_verbatim(self):
        """Test that to_json renders the verbatim skill as the manifest author wrote it."""
        data = self.load_skill_plugin().to_json()
        self.assertEqual(data["kind"], MANIFEST_KIND)  # type: ignore[index]
        skill_data = data["spec"]["skillData"]  # type: ignore[index]
        self.assertEqual(skill_data["skill"], self.inline_skill)
        self.assertEqual(list(skill_data["resources"]), INLINE_RESOURCES)
        self.assertNotIn("data", data["spec"])  # type: ignore[index]

    def test_to_json_remote(self):
        """Test that to_json renders a remote skill by its source, as the manifest author wrote it."""
        skill_data = self.load_skill_plugin(remote=True).to_json()["spec"]["skillData"]  # type: ignore[index]
        self.assertEqual(skill_data, {"source": {"url": SKILL_REMOTE_URL}})

    def test_to_json_status(self):
        """Test the status section of to_json()."""
        plugin = self.load_skill_plugin()
        status = plugin.to_json()["status"]  # type: ignore[index]
        self.assertEqual(status["recordLocator"], plugin.plugin_meta.record_locator)  # type: ignore[union-attr]
        self.assertEqual(status["accountNumber"], self.account.account_number)

    def test_to_json_invalid_version(self):
        """Test that to_json() rejects unsupported versions."""
        with self.assertRaises(Exception):
            self.load_skill_plugin().to_json(version="v2")

    def test_to_json_not_ready(self):
        """Test that to_json() returns None for a plugin that is not ready."""
        self.assertIsNone(SkillPlugin().to_json())

    def test_manifest_from_database(self):
        """Test that the manifest is reconstructed from the database when not provided."""
        for remote in (False, True):
            plugin = self.load_skill_plugin(remote=remote)
            self.assertIsNone(plugin._manifest)
            manifest = plugin.manifest
            self.assertIsInstance(manifest, SAMSkillPlugin)
            if remote:
                self.assertEqual(manifest.spec.skillData.source.url, SKILL_REMOTE_URL)  # type: ignore[union-attr]
            else:
                self.assertEqual(manifest.spec.skillData.skill, self.inline_skill)  # type: ignore[union-attr]

    def test_manifest_from_database_recreates_plugin(self):
        """Test that a manifest reconstructed from the database creates an identical plugin."""
        name = "skill_recreated"
        self.addCleanup(self.delete_plugin_by_name, name)
        data = json.loads(self.load_skill_plugin().manifest.model_dump_json())  # type: ignore[union-attr]
        data["metadata"]["name"] = name
        data.pop("status", None)
        plugin = SkillPlugin(manifest=SAMSkillPlugin(**data), user_profile=self.user_profile)
        original = self.load_skill_plugin().plugin_data
        self.assertEqual(plugin.plugin_data.skill_document, original.skill_document)  # type: ignore[union-attr]
        self.assertEqual(plugin.plugin_data.resources, original.resources)  # type: ignore[union-attr]
        self.assertEqual(plugin.custom_tool["function"]["parameters"], self.load_skill_plugin().custom_tool["function"]["parameters"])  # type: ignore[index]

    def test_manifest_verbatim_skill_is_yaml_readable(self):
        """Test that a manifest rendered from the database presents the SKILL.md as a single multi-line string."""
        skill = self.load_skill_plugin().manifest.spec.skillData.skill  # type: ignore[union-attr]
        self.assertIn("\n# Expense reports\n", skill)  # type: ignore[operator]

    # =========================================================================
    # lifecycle
    # =========================================================================
    def test_create_description_is_the_skill_description(self):
        """Test that the tool description is the skill's description, which says when to use it."""
        plugin = self.new_skill_plugin("skill_create", skill=MINIMAL_SKILL, resources=None)
        self.assertEqual(
            PluginDataSkill.objects.get(plugin_id=plugin.id).description, "A minimal skill. Use when testing."
        )

    def test_update_replaces_skill(self):
        """Test that re-applying a manifest replaces the skill, and that reloaded plugins see the change."""
        name = "skill_update"
        plugin = self.new_skill_plugin(name)
        _ = SkillPlugin(plugin_id=plugin.id, user_profile=self.user_profile).plugin_data  # populate the cache
        SkillPlugin(
            manifest=self.skill_manifest(name, skill=MINIMAL_SKILL, resources={"a.md": "a"}),
            user_profile=self.user_profile,
        )
        reloaded = SkillPlugin(plugin_id=plugin.id, user_profile=self.user_profile)
        self.assertEqual(reloaded.plugin_data.skill_document, MINIMAL_SKILL)  # type: ignore[union-attr]
        self.assertEqual(reloaded.plugin_data.resources, {"a.md": "a"})  # type: ignore[union-attr]
        self.assertEqual(reloaded.plugin_data.description, "A minimal skill. Use when testing.")  # type: ignore[union-attr]
        self.assertEqual(PluginMeta.objects.filter(user_profile__account=self.account, name=name).count(), 1)

    def test_update_remote_retrieves_again(self):
        """Test that re-applying a remote manifest retrieves the latest version of the skill."""
        name = "skill_update_remote"
        plugin = self.new_skill_plugin(name, remote=True)
        first_retrieved_at = PluginDataSkill.objects.get(plugin_id=plugin.id).source_retrieved_at
        host = FakeSkillHost()
        host.add(
            SKILL_REMOTE_RAW_URL + "SKILL.md",
            b"---\nname: test-skill\ndescription: Version two. Use when testing.\n---\nNew instructions.\n",
        )
        with mock_skill_host(host):
            SkillPlugin(manifest=self.skill_manifest(name, remote=True), user_profile=self.user_profile)
        plugin_data = PluginDataSkill.objects.get(plugin_id=plugin.id)
        self.assertEqual(plugin_data.description, "Version two. Use when testing.")
        self.assertIn("New instructions.", plugin_data.skill_document)
        self.assertGreater(plugin_data.source_retrieved_at, first_retrieved_at)  # type: ignore[operator]

    def test_update_verbatim_to_remote_and_back(self):
        """Test switching a plugin between a verbatim and a remote skill."""
        name = "skill_switch_source"
        plugin = self.new_skill_plugin(name)
        with mock_skill_host():
            SkillPlugin(manifest=self.skill_manifest(name, remote=True), user_profile=self.user_profile)
        plugin_data = PluginDataSkill.objects.get(plugin_id=plugin.id)
        self.assertEqual(plugin_data.source_url, SKILL_REMOTE_URL)
        self.assertEqual(plugin_data.resource_paths, REMOTE_RESOURCES)

        SkillPlugin(manifest=self.skill_manifest(name), user_profile=self.user_profile)
        plugin_data = PluginDataSkill.objects.get(plugin_id=plugin.id)
        self.assertIsNone(plugin_data.source_url)
        self.assertIsNone(plugin_data.source_retrieved_at)
        self.assertEqual(plugin_data.resource_paths, INLINE_RESOURCES)

    def test_create_remote_retrieval_failure(self):
        """Test that a remote skill that cannot be retrieved raises, and leaves nothing behind."""
        name = "skill_remote_failure"
        self.addCleanup(self.delete_plugin_by_name, name)
        host = FakeSkillHost()
        host.remove(SKILL_REMOTE_RAW_URL + "SKILL.md")
        with self.assertRaises(SmarterSkillPluginError) as context:
            self.new_skill_plugin(name, host=host, remote=True)
        self.assertIn(SKILL_REMOTE_URL, str(context.exception))
        self.assertFalse(PluginMeta.objects.filter(user_profile__account=self.account, name=name).exists())

    def test_create_remote_retrieves_once(self):
        """Test that creating a remote skill plugin retrieves the skill only once."""
        with mock_skill_host() as host:
            self.addCleanup(self.delete_plugin_by_name, "skill_retrieve_once")
            SkillPlugin(
                manifest=self.skill_manifest("skill_retrieve_once", remote=True), user_profile=self.user_profile
            )
        self.assertEqual(host.requested.count(SKILL_REMOTE_RAW_URL + "SKILL.md"), 1)

    def test_clone(self):
        """Test that cloning a plugin copies its skill, and leaves the original intact."""
        plugin = self.new_skill_plugin("skill_clone_source")
        clone_id = plugin.clone(new_name="skill_clone_target")
        self.addCleanup(self.delete_plugin_by_id, clone_id)
        clone = PluginDataSkill.objects.get(plugin_id=clone_id)
        original = PluginDataSkill.objects.get(plugin_id=plugin.id)
        self.assertNotEqual(clone.pk, original.pk)
        self.assertEqual(clone.skill_document, original.skill_document)
        self.assertEqual(clone.resources, original.resources)

    def test_delete(self):
        """Test that deleting a plugin removes its skill."""
        plugin = self.new_skill_plugin("skill_delete")
        plugin_id = plugin.id
        self.assertTrue(plugin.delete())
        self.assertFalse(PluginMeta.objects.filter(id=plugin_id).exists())
        self.assertFalse(PluginDataSkill.objects.filter(plugin_id=plugin_id).exists())

    # =========================================================================
    # example and sample manifests
    # =========================================================================
    def test_example_manifest(self):
        """Test that the example manifest is valid, and creates a working plugin."""
        name = "skill_from_example"
        self.addCleanup(self.delete_plugin_by_name, name)
        example = SkillPlugin.example_manifest()
        self.assertEqual(example["kind"], MANIFEST_KIND)  # type: ignore[index]
        example["metadata"]["name"] = name  # type: ignore[index]
        example.pop("status", None)  # type: ignore[union-attr]
        plugin = SkillPlugin(manifest=SAMSkillPlugin(**example), user_profile=self.user_profile)  # type: ignore[arg-type]
        self.assertEqual(plugin.plugin_data.resource_paths, ["assets/template.md"])  # type: ignore[union-attr]
        self.assertIn("Meeting notes", plugin.tool_call_fetch_plugin_response({})["instructions"])  # type: ignore[index]

    def test_sample_manifests_create_working_plugins(self):
        """
        Test that every sample SkillPlugin manifest creates a working plugin.

        Remote samples refer to Anthropic's skills repository. Their retrieval is replaced
        by the test skill, since unit tests must not depend on GitHub.
        """
        paths = sorted(glob.glob(os.path.join(SAMPLE_PLUGINS_PATH, "skill-*.yaml")))
        self.assertGreaterEqual(len(paths), 7)
        with mock_skill_host():
            test_skill = retrieve_skill(SKILL_REMOTE_URL)
        for i, path in enumerate(paths):
            manifest = copy.deepcopy(get_readonly_yaml_file(path))
            name = f"skill_sample_{i}"
            manifest["metadata"]["name"] = name
            self.addCleanup(self.delete_plugin_by_name, name)
            with mock.patch("smarter.apps.plugin.plugin.skill.retrieve_skill", return_value=test_skill):
                plugin = SkillPlugin(manifest=SAMSkillPlugin(**manifest), user_profile=self.user_profile)
            self.assertTrue(plugin.ready, path)
            self.assertIn("instructions", plugin.tool_call_fetch_plugin_response({}), path)
            for resource in plugin.plugin_data.resource_paths:  # type: ignore[union-attr]
                plugin.tool_call_fetch_plugin_response({"resource": resource})
