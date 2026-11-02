"""
Tests for smarter.apps.mcpserver.protocol.views: the MCP server over HTTP.

:class:`TestMCPClientEndToEnd` connects Smarter's own MCPClient, with the MCP Python SDK's
Streamable HTTP client, to the view, through an httpx2 transport that hands each request to
Django's test client. The network is never used.
"""

import json
from unittest import mock

import anyio.to_thread
import httpx2
from django.test import Client, RequestFactory
from django.urls import reverse

from smarter.apps.account.models import User
from smarter.apps.mcpclient.connection import MCPServerConnection
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.mcpserver.github.issues import GitHubIssue
from smarter.apps.mcpserver.protocol.views import api_key, bearer_token
from smarter.apps.mcpserver.urls import MCPServerReverseNames
from smarter.lib.drf.models import SmarterAuthToken

from .base_classes import TOKEN, MCPServerTestBase
from .operations_base import TICKET, OperationsTestBase

CONNECTION = "smarter.apps.mcpclient.connection"
HEADERS = {"HTTP_ACCEPT": "application/json, text/event-stream"}
CREATE_ISSUE = "smarter.apps.mcpserver.github.issues.create_issue"


def url(repository=None) -> str:
    """Return the url of the MCP server of a repository, or of all of them."""
    names = MCPServerReverseNames
    if repository is None:
        return reverse(f"{names.namespace}:{names.smarter_project}")
    return reverse(f"{names.namespace}:{names.repository}", kwargs={"repository": repository})


class TestSmarterProjectMCPServerView(MCPServerTestBase):
    """Test the HTTP endpoint."""

    def setUp(self):
        super().setUp()
        self.client = Client()

    def post(self, path: str, body, **extra):
        data = body if isinstance(body, (str, bytes)) else json.dumps(body)
        return self.client.post(path, data=data, content_type="application/json", **HEADERS, **extra)

    def test_urls(self):
        """The server is mounted under /api/v1/mcp/."""
        self.assertEqual(url(), "/api/v1/mcp/smarter-project/")
        self.assertEqual(url("smarter-cli"), "/api/v1/mcp/smarter-project/smarter-cli/")

    def test_post(self):
        """A request is answered with JSON, and is never cached."""
        response = self.post(url(self.docs_repository.name), {"jsonrpc": "2.0", "id": 1, "method": "ping"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("no-cache", response["Cache-Control"])
        self.assertEqual(response.json(), {"jsonrpc": "2.0", "id": 1, "result": {}})
        self.assertNotIn("Mcp-Session-Id", response)

    def test_all_repositories(self):
        """The server of all of the repositories answers too, without a csrf token."""
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            url(), data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["result"]["tools"]), 11)

    def test_bearer_token(self):
        """The token of an Authorization: Bearer header is read, and nothing else."""
        factory = RequestFactory()
        cases = [
            ({}, None),
            ({"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}, TOKEN),
            ({"HTTP_AUTHORIZATION": f"  bearer   {TOKEN}  "}, TOKEN),
            ({"HTTP_AUTHORIZATION": "Bearer "}, None),
            ({"HTTP_AUTHORIZATION": f"Token {TOKEN}"}, None),
            ({"HTTP_AUTHORIZATION": f"Basic {TOKEN}"}, None),
        ]
        for headers, expected in cases:
            with self.subTest(headers=headers):
                token = bearer_token(factory.post("/", **headers))
                self.assertEqual(token.get_secret_value() if token else None, expected)
                if token:
                    self.assertNotIn(TOKEN, repr(token))

    def test_github_token_serves_create_issue(self):
        """A request with a GitHub token is also served the tools that write: issues, comments and pull requests."""
        body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        tools = self.post(url(), body, HTTP_AUTHORIZATION=f"Bearer {TOKEN}").json()["result"]["tools"]
        self.assertEqual(len(tools), 15)
        self.assertEqual(
            [tool["name"] for tool in tools[-4:]],
            ["create_issue", "comment_on_issue", "close_issue", "create_pull_request"],
        )
        self.assertFalse(tools[-1]["annotations"]["readOnlyHint"])

    def test_notification(self):
        """A notification is accepted, with no body."""
        response = self.post(url(self.docs_repository.name), {"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, b"")

    def test_batch(self):
        """A batch is answered with a JSON array."""
        batch = [{"jsonrpc": "2.0", "id": 1, "method": "ping"}, {"jsonrpc": "2.0", "id": 2, "method": "ping"}]
        response = self.post(url(self.docs_repository.name), batch)
        self.assertEqual([item["id"] for item in response.json()], [1, 2])

    def test_not_json(self):
        """A body that is not JSON is a parse error."""
        response = self.post(url(self.docs_repository.name), "{not json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], -32700)
        self.assertIsNone(response.json()["id"])

    def test_unknown_repository(self):
        """A repository that is not The Smarter Project's is not found."""
        response = self.post(url("not-a-repository"), {"jsonrpc": "2.0", "id": 1, "method": "ping"})
        self.assertEqual(response.status_code, 404)
        self.assertIn(self.docs_repository.name, response.json()["detail"])

    def test_get_and_delete_are_not_allowed(self):
        """The server offers no GET stream, and no session to delete."""
        for method in (self.client.get, self.client.delete):
            with self.subTest(method=method.__name__):
                response = method(url(self.docs_repository.name))
                self.assertEqual(response.status_code, 405)
                self.assertIn("POST", response["Allow"])


class TestMCPClientEndToEnd(MCPServerTestBase):
    """Connect Smarter's MCPClient to the MCP server, with the MCP Python SDK's client."""

    def setUp(self):
        super().setUp()
        django_client = Client()

        async def handler(request: httpx2.Request) -> httpx2.Response:
            def forward():
                return django_client.generic(
                    request.method,
                    request.url.raw_path.decode(),
                    data=request.content,
                    content_type=request.headers.get("content-type", ""),
                    HTTP_ACCEPT=request.headers.get("accept", ""),
                    **(
                        {"HTTP_AUTHORIZATION": request.headers["authorization"]}
                        if "authorization" in request.headers
                        else {}
                    ),
                )

            response = await anyio.to_thread.run_sync(forward)
            return httpx2.Response(
                response.status_code,
                headers={"content-type": response.get("Content-Type", "application/json")},
                content=response.content,
            )

        def http_client(headers=None, timeout=None, auth=None):
            return httpx2.AsyncClient(
                transport=httpx2.MockTransport(handler), headers=headers, timeout=timeout, auth=auth
            )

        for patcher in (
            mock.patch(f"{CONNECTION}.validate_public_url"),
            mock.patch(f"{CONNECTION}.guarded_http_client", http_client),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def connection(self, repository=None, auth_type="none") -> MCPServerConnection:
        mcpclient = MCPClient(
            name="test_mcpserver_end_to_end",
            endpoint_url=f"https://platform.example.com{url(repository)}",
            transport="http",
            auth_type=auth_type,
            timeout=30,
            allowed_tools=[],
        )
        return MCPServerConnection(mcpclient)

    def test_discover(self):
        """The MCPClient performs the handshake, and lists the tools."""
        catalog = self.connection(self.docs_repository.name).discover()
        self.assertEqual(catalog.server_name, f"smarter-project-{self.docs_repository.name}")
        self.assertTrue(catalog.has_tools)
        self.assertFalse(catalog.has_resources)
        self.assertIn("search_code", [tool.name for tool in catalog.tools])
        self.assertTrue(all(tool.read_only for tool in catalog.tools))
        self.assertIn(self.docs_repository.full_name, catalog.instructions)

    def test_call_tool(self):
        """The MCPClient calls a tool, and gets its text."""
        result = self.connection(self.docs_repository.name).call_tool(
            "read_file", {"path": "platform/apps/domains/verification.py", "start_line": 4, "end_line": 4}
        )
        self.assertFalse(result.is_error)
        self.assertIn("def verify_custom_domain", result.text)

    def test_tool_error(self):
        """A tool's error reaches the MCPClient as an error result."""
        result = self.connection().call_tool("read_file", {"path": "README.md"})
        self.assertTrue(result.is_error)
        self.assertIn("repository is required", result.text)

    def test_create_issue_with_a_bearer_token(self):
        """An MCPClient whose bearer token is a GitHub token discovers create_issue, as a tool that writes, and calls it."""
        issue = GitHubIssue(number=9, title="t", html_url="https://github.com/smarter-sh/x/issues/9", author="octocat")
        with mock.patch.object(MCPServerConnection, "credential", return_value=TOKEN):
            connection = self.connection(self.docs_repository.name, auth_type="bearer_token")
            catalog = connection.discover()
            tools = {tool.name: tool for tool in catalog.tools}
            self.assertFalse(tools["create_issue"].read_only)
            self.assertIn("create_issue opens a public GitHub issue", catalog.instructions)
            self.assertFalse(tools["comment_on_issue"].read_only)
            self.assertTrue(tools["search_issues"].read_only)
            with mock.patch(CREATE_ISSUE, return_value=issue) as create_issue:
                result = connection.call_tool("create_issue", {"title": "t", "body": "b"})
        self.assertFalse(result.is_error)
        self.assertIn(issue.html_url, result.text)
        self.assertEqual(create_issue.call_args.args[3].get_secret_value(), TOKEN)


class TestSmarterOperationsMCPServerView(OperationsTestBase):
    """Test the staff-only endpoint of the Smarter Operations MCP server, with real api keys."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.staff_token, cls.staff_key = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=cls.user_profile, name="test_operations_staff", user=cls.admin_user, description="test"
        )
        cls.inactive_token, cls.inactive_key = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=cls.user_profile,
            name="test_operations_inactive",
            user=cls.admin_user,
            description="test",
            is_active=False,
        )

    @classmethod
    def tearDownClass(cls):
        SmarterAuthToken.objects.filter(pk__in=[cls.staff_token.pk, cls.inactive_token.pk]).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client = Client(enforce_csrf_checks=True)
        self.url = reverse(f"{MCPServerReverseNames.namespace}:{MCPServerReverseNames.smarter_operations}")

    def post(self, body, key=None, **extra):
        if key is not None:
            extra["HTTP_AUTHORIZATION"] = f"Token {key}"
        return self.client.post(self.url, data=json.dumps(body), content_type="application/json", **HEADERS, **extra)

    def test_url(self):
        self.assertEqual(self.url, "/api/v1/mcp/smarter-operations/")

    def test_api_key(self):
        """The key of an Authorization: Token header is read, and nothing else."""
        factory = RequestFactory()
        cases = [
            ({}, None),
            ({"HTTP_AUTHORIZATION": "Token abc123"}, "abc123"),
            ({"HTTP_AUTHORIZATION": "  token   abc123  "}, "abc123"),
            ({"HTTP_AUTHORIZATION": "Token "}, None),
            ({"HTTP_AUTHORIZATION": "Bearer abc123"}, None),
        ]
        for headers, expected in cases:
            with self.subTest(headers=headers):
                self.assertEqual(api_key(factory.post("/", **headers)), expected)

    def test_staff(self):
        """A staff user's api key is served the operations tools, and nothing else."""
        response = self.post({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, key=self.staff_key)
        self.assertEqual(response.status_code, 200)
        names = [tool["name"] for tool in response.json()["result"]["tools"]]
        self.assertEqual(
            names, ["platform_status", "eks_status", "summarize_log_errors", "search_logs", "list_log_sources"]
        )

    def test_tool_call_is_audited(self):
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "search_logs", "arguments": {"ticket": TICKET, "contains": ["timeout"]}},
        }
        response = self.post(body, key=self.staff_key)
        self.assertIn("timeout talking to provider", response.json()["result"]["content"][0]["text"])
        self.assertEqual(self.audit_rows().first().ticket, TICKET)

    def test_refused(self):
        """Without a valid, active key of an active staff user, nothing is read, and nothing is answered."""
        ping = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        cases = [
            ({}, 401),
            ({"key": "not-a-real-key"}, 401),
            ({"key": self.inactive_key}, 401),
            ({"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}, 401),
        ]
        for kwargs, status in cases:
            with self.subTest(kwargs=kwargs):
                response = self.post(ping, **kwargs)
                self.assertEqual(response.status_code, status)
                self.assertNotIn(b'"result"', response.content)
        # without a key, the view refuses; an invalid key is refused by the platform's token
        # middleware before the view, with a 401 of its own.
        response = self.post(ping)
        self.assertEqual(response.json()["error"]["code"], -32001)
        self.assertEqual(response["WWW-Authenticate"], "Token")
        self.assertFalse(self.audit_rows().exists())

    def test_user_who_is_not_staff(self):
        """An api key outlives its user's staff status: such a user is forbidden."""
        User.objects.filter(pk=self.admin_user.pk).update(is_staff=False)
        try:
            response = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, key=self.staff_key)
        finally:
            User.objects.filter(pk=self.admin_user.pk).update(is_staff=True)
        self.assertEqual(response.status_code, 403)
        self.assertIn("staff only", response.json()["error"]["message"])

    def test_inactive_staff_user(self):
        self.admin_user.is_active = False
        self.admin_user.save(update_fields=["is_active"])
        try:
            response = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, key=self.staff_key)
            self.assertIn(response.status_code, (401, 403))
        finally:
            self.admin_user.is_active = True
            self.admin_user.save(update_fields=["is_active"])

    def test_not_json(self):
        response = self.client.post(
            self.url, data="{not json", content_type="application/json", HTTP_AUTHORIZATION=f"Token {self.staff_key}"
        )
        self.assertEqual(response.status_code, 400)

    def test_rate_limited(self):
        with mock.patch("smarter.apps.mcpserver.protocol.views.is_rate_limited", return_value=True):
            response = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, key=self.staff_key)
        self.assertEqual(response.status_code, 429)
        self.assertIn("Retry-After", response)
