"""Test the built-in LLMClient manifests, in smarter/apps/llmclient/data/llm-clients."""

import glob
import os
import re

from smarter.apps.llmclient.const import DATA_PATH
from smarter.apps.llmtool.extension.toolkit import FUNCTION_NAME_PREFIX
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.unittest.base_classes import SmarterTestBase

LLMCLIENTS_PATH = os.path.join(DATA_PATH, "llm-clients")
EXTENSION_TOOL = re.compile(rf"\b{FUNCTION_NAME_PREFIX}[a-z0-9_]+\b")
"""The name of an extension tool, as the LLM sees it: ext_<slug>_<tool name>."""


class TestBuiltinLLMClients(SmarterTestBase):
    """Test that the built-in LLMClients' system prompts name the tools that the LLM is offered."""

    def test_extension_tools_in_system_prompts(self):
        """Every ext_<slug>_<tool> that a system prompt names is a tool of an extension that the manifest lists."""
        manifests = sorted(glob.glob(os.path.join(LLMCLIENTS_PATH, "*.yaml")))
        self.assertTrue(manifests)
        named = 0
        for path in manifests:
            manifest = get_readonly_yaml_file(path)
            system_role = manifest["spec"]["config"]["prompt"].get("defaultSystemRole") or ""
            prefixes = [
                f"{FUNCTION_NAME_PREFIX}{slug.replace('-', '_')}_" for slug in manifest["spec"].get("extensions") or []
            ]
            for tool in EXTENSION_TOOL.findall(system_role):
                named += 1
                with self.subTest(manifest=os.path.basename(path), tool=tool):
                    self.assertTrue(
                        any(tool.startswith(prefix) for prefix in prefixes),
                        f"{tool} is not a tool of the extensions that the manifest lists: {manifest['spec'].get('extensions')}",
                    )
        self.assertGreater(named, 0, "no built-in system prompt names an extension tool")

    def test_no_removed_function_names(self):
        """No system prompt names a built-in function that Extensions replaced."""
        for path in sorted(glob.glob(os.path.join(LLMCLIENTS_PATH, "*.yaml"))):
            system_role = get_readonly_yaml_file(path)["spec"]["config"]["prompt"].get("defaultSystemRole") or ""
            with self.subTest(manifest=os.path.basename(path)):
                self.assertNotIn("get_current_weather", system_role)
                self.assertIsNone(re.search(r"(?<!ext_)(?<!_)\bdate_calculator\b", system_role))
