"""Test :class:`smarter.apps.llmclient.serializers.LLMClientSerializer`'s tools of an LLMClient."""

from smarter.apps.guardrail.tests.base_classes import GuardrailTestBase
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientExtensions,
    LLMClientGuardrails,
    LLMClientMCPClients,
    LLMClientPlugin,
)
from smarter.apps.llmclient.serializers import LLMClientSerializer
from smarter.apps.llmtool.models import Extension, PluginMeta
from smarter.apps.mcpclient.tests.base_classes import MCPClientTestBase


class TestLLMClientSerializer(MCPClientTestBase, GuardrailTestBase):
    """
    Test the extensions, plugins, mcpclients, guardrails and tools of a serialized LLMClient.

    The class fixture is an LLMClient with one extension, one plugin, the MCPClientTestBase
    MCPClient and one guardrail.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmclient = LLMClient.objects.create(name="test_serializers_llmclient", user_profile=cls.user_profile)
        cls.plugin_meta = PluginMeta.objects.create(
            name="test_serializers_plugin", plugin_class="static", version="1.0.0", user_profile=cls.user_profile
        )
        cls.guardrail = cls.create_guardrail("test_serializers_guardrail")
        cls.extension = Extension.objects.create(slug="test-serializers", display_name="Test Serializers")
        cls.extension_link = LLMClientExtensions.objects.create(llmclient=cls.llmclient, extension=cls.extension)
        cls.plugin = LLMClientPlugin.objects.create(llmclient=cls.llmclient, plugin_meta=cls.plugin_meta)
        cls.mcpclient_link = LLMClientMCPClients.objects.create(llmclient=cls.llmclient, mcpclient=cls.mcpclient)
        cls.guardrail_link = LLMClientGuardrails.objects.create(llmclient=cls.llmclient, guardrail=cls.guardrail)

    @classmethod
    def tearDownClass(cls):
        cls.llmclient.delete()
        cls.plugin_meta.delete()
        cls.extension.delete()
        super().tearDownClass()

    def test_mcpclients(self):
        data = LLMClientSerializer(self.llmclient).data
        self.assertEqual(data["mcpclients"], [{"id": self.mcpclient_link.id, "name": self.mcpclient.name}])

    def test_extensions(self):
        data = LLMClientSerializer(self.llmclient).data
        self.assertEqual(
            [(item["id"], item["name"]) for item in data["extensions"]], [(self.extension_link.id, "test-serializers")]
        )

    def test_guardrails(self):
        data = LLMClientSerializer(self.llmclient).data
        self.assertEqual(data["guardrails"], [{"id": self.guardrail_link.id, "name": self.guardrail.name}])

    def test_tools(self):
        """Test that the tools are the extensions, plugins, mcpclients and guardrails, in that order."""
        data = LLMClientSerializer(self.llmclient).data
        self.assertEqual(
            data["tools"],
            [
                {"id": self.extension_link.id, "name": "test-serializers", "kind": "Extension"},
                {"id": self.plugin.id, "name": self.plugin_meta.name, "kind": "Plugin"},
                {"id": self.mcpclient_link.id, "name": self.mcpclient.name, "kind": "MCPClient"},
                {"id": self.guardrail_link.id, "name": self.guardrail.name, "kind": "Guardrail"},
            ],
        )

    def test_no_tools(self):
        llmclient = LLMClient.objects.create(name="test_serializers_no_tools", user_profile=self.user_profile)
        self.addCleanup(llmclient.delete)
        data = LLMClientSerializer(llmclient).data
        self.assertEqual(data["mcpclients"], [])
        self.assertEqual(data["guardrails"], [])
        self.assertEqual(data["tools"], [])
