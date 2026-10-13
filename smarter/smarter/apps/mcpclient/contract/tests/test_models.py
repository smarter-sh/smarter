"""Test :mod:`smarter.apps.mcpclient.contract.models`."""

import json
from typing import get_args

from smarter.apps.account.serializers import user_can_delete
from smarter.apps.mcpclient.connection import (
    MCPServerCatalog,
    MCPToolInfo,
    MCPToolResult,
)
from smarter.apps.mcpclient.contract.models import (
    MCPClientApiAuthType,
    MCPClientApiConnectionStatus,
    MCPClientApiMCPClient,
    MCPClientApiStatus,
    MCPClientApiToolResult,
    MCPClientApiTools,
    MCPClientApiTransport,
)
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.mcpclient.serializers import MCPClientSerializer
from smarter.apps.mcpclient.tests.base_classes import MCPClientTestBase


class TestMCPClientContractModels(MCPClientTestBase):
    """Test the MCPClient contract's models against the serializer and views whose output they replace."""

    def test_choices(self):
        cases = [
            (MCPClientApiTransport, "transport"),
            (MCPClientApiAuthType, "auth_type"),
            (MCPClientApiConnectionStatus, "status"),
        ]
        for literal, field in cases:
            with self.subTest(field=field):
                self.assertEqual(
                    list(get_args(literal)), [value for value, _ in MCPClient._meta.get_field(field).choices]
                )

    def test_mcpclient_is_the_serializers_output(self):
        model = MCPClientApiMCPClient.from_model(self.mcpclient)
        self.assertEqual(
            model.model_dump(mode="json"), json.loads(json.dumps(MCPClientSerializer(self.mcpclient).data, default=str))
        )

    def test_can_delete_is_the_users(self):
        self.assertIs(MCPClientApiMCPClient.from_model(self.mcpclient).can_delete, False)
        self.assertEqual(
            MCPClientApiMCPClient.from_model(self.mcpclient, self.admin_user).can_delete,
            user_can_delete(self.mcpclient, "MCPClient", self.admin_user),
        )

    def test_status(self):
        """The status's keys are the ones that the views returned."""
        data = MCPClientApiStatus.from_model(self.mcpclient).model_dump(mode="json")
        self.assertEqual(
            sorted(data),
            sorted(
                [
                    "name",
                    "status",
                    "protocolVersion",
                    "serverName",
                    "serverVersion",
                    "lastConnected",
                    "lastError",
                    "tools",
                ]
            ),
        )
        self.assertEqual(data["tools"], self.mcpclient.tools or [])

    def test_tools_and_result(self):
        tool = MCPToolInfo(name="echo", description="Echo.", input_schema={"type": "object"}, read_only=True)
        catalog = MCPServerCatalog(server_name="test", instructions="Use echo.", tools=[tool])
        data = MCPClientApiTools.from_catalog(self.mcpclient, catalog, [tool]).model_dump(mode="json")
        self.assertEqual(data["instructions"], "Use echo.")
        self.assertEqual(data["tools"][0]["inputSchema"], {"type": "object"})
        self.assertTrue(data["tools"][0]["readOnly"])
        result = MCPClientApiToolResult.from_result(self.mcpclient, "echo", MCPToolResult(text="hi"))
        self.assertEqual(
            result.model_dump(mode="json"),
            {"name": self.mcpclient.name, "tool": "echo", "isError": False, "content": "hi"},
        )
