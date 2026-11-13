"""
Tests for smarter.apps.mcpserver.protocol.views: the MCPServer's endpoints over HTTP.

:class:`TestMCPClientEndToEnd` and :class:`TestOperationsMCPClientEndToEnd` connect Smarter's own
MCPClient, with the MCP Python SDK's Streamable HTTP client, to the views, through an httpx2
transport that hands each request to Django's test client, :func:`forward_to_django`. The network
is never used.
"""

import json
from unittest import mock

import anyio.to_thread
import httpx2
from django.test import Client
from django.urls import reverse

from smarter.apps.account.models import User
from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.mcpclient.connection import MCPServerConnection
from smarter.apps.mcpclient.exceptions import SmarterMCPClientConnectionError
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.mcpserver.models import OperationsToolCall
from smarter.apps.mcpserver.services.acting_user import (
    ACTING_USER_HEADER,
    acting_user,
    sign_acting_user,
    staff_endpoint_url,
)
from smarter.apps.mcpserver.services.github.issues import GitHubIssue
from smarter.apps.mcpserver.urls import MCPServerReverseNames
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.typing import SmarterDictType, required

from .base_classes import TOKEN, MCPServerTestBase
from .operations_base import TICKET, OperationsTestBase

CONNECTION = "smarter.apps.mcpclient.connection"
HEADERS: SmarterDictType = {"HTTP_ACCEPT": "application/json, text/event-stream"}
"""The WSGI environ of every request; RequestFactory's extra environ may hold values of any type."""
CREATE_ISSUE = "smarter.apps.mcpserver.services.github.issues.create_issue"


def forward_to_django(test) -> None:
    """
    Make an MCPClient's http requests go to Django's test client, for the rest of a test.

    Every request header is forwarded, e.g. ``Authorization`` and ``X-Smarter-Acting-User``.

    :param test: The test case, whose cleanups stop the patches.
    """
    django_client = Client()

    async def handler(request: httpx2.Request) -> httpx2.Response:
        def forward():
            extra: SmarterDictType = {}
            for name, value in request.headers.items():
                # the test client sets its own host, and the content's type and length.
                if name.lower() in ("host", "content-type", "content-length"):
                    continue
                meta_name = "HTTP_" + name.upper().replace("-", "_")
                extra[meta_name] = value
            return django_client.generic(
                request.method,
                request.url.raw_path.decode(),
                data=request.content,
                content_type=request.headers.get("content-type", ""),
                **extra,
            )

        response = await anyio.to_thread.run_sync(forward)
        return httpx2.Response(
            response.status_code,
            headers={"content-type": response.get("Content-Type", "application/json")},
            content=response.content,
        )

    def http_client(headers=None, timeout=None, auth=None):
        return httpx2.AsyncClient(transport=httpx2.MockTransport(handler), headers=headers, timeout=timeout, auth=auth)

    for patcher in (
        mock.patch(f"{CONNECTION}.validate_public_url"),
        mock.patch(f"{CONNECTION}.guarded_http_client", http_client),
    ):
        patcher.start()
        test.addCleanup(patcher.stop)


def url(repository=None) -> str:
    """Return the url of the MCP server of a repository, or of all of them."""
    names = MCPServerReverseNames
    if repository is None:
        return reverse(f"{names.namespace}:{names.public}")
    return reverse(f"{names.namespace}:{names.public_repository}", kwargs={"repository": repository})


class TestPublicEndpointView(MCPServerTestBase):
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
        """The endpoint of every repository answers too, without a csrf token."""
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            url(), data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["result"]["tools"]), 11)

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
        forward_to_django(self)

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
        self.assertIn(self.docs_repository.full_name, required(catalog.instructions, "catalog.instructions"))

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
            instructions = required(catalog.instructions, "catalog.instructions")
            self.assertIn("create_issue opens a public GitHub issue", instructions)
            self.assertFalse(tools["comment_on_issue"].read_only)
            self.assertTrue(tools["search_issues"].read_only)
            with mock.patch(CREATE_ISSUE, return_value=issue) as create_issue:
                result = connection.call_tool("create_issue", {"title": "t", "body": "b"})
        self.assertFalse(result.is_error)
        self.assertIn(issue.html_url, result.text)
        self.assertEqual(create_issue.call_args.args[3].get_secret_value(), TOKEN)


class TestStaffEndpointView(OperationsTestBase):
    """Test the MCPServer's staff-only endpoint, with real api keys."""

    staff_token: SmarterAuthToken
    staff_key: str
    inactive_token: SmarterAuthToken
    inactive_key: str

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
        self.url = reverse(f"{MCPServerReverseNames.namespace}:{MCPServerReverseNames.staff}")

    def post(self, body, key=None, **extra):
        if key is not None:
            extra["HTTP_AUTHORIZATION"] = f"Token {key}"
        return self.client.post(self.url, data=json.dumps(body), content_type="application/json", **HEADERS, **extra)

    def test_url(self):
        self.assertEqual(self.url, "/api/v1/mcp/smarter-operations/")

    def test_staff(self):
        """A staff user's api key is served the operations tools, and nothing else."""
        response = self.post({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, key=self.staff_key)
        self.assertEqual(response.status_code, 200)
        names = [tool["name"] for tool in response.json()["result"]["tools"]]
        self.assertEqual(
            names,
            [
                "platform_status",
                "eks_status",
                "summarize_log_errors",
                "search_logs",
                "list_log_sources",
                "user_support_snapshot",
                "check_reply",
                "create_bug_report",
            ],
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

    def test_admin_of_another_account(self):
        """The admin of a customer's account is staff of that account only, even as a superuser: forbidden."""
        customer_admin, customer_account, customer_profile = admin_user_factory()
        _, customer_key = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=customer_profile, name="test_operations_customer", user=customer_admin, description="test"
        )
        try:
            self.assertTrue(customer_admin.is_staff)
            self.assertTrue(customer_admin.is_superuser)
            response = self.post({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, key=customer_key)
        finally:
            # not factory_account_teardown(), which deletes every test user, including this class's.
            SmarterAuthToken.objects.filter(user=customer_admin).delete()
            customer_profile.delete()
            customer_admin.delete()
            customer_account.delete()
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b'"result"', response.content)

    def post_as(self, body, value: str):
        """Post with a signed acting user, and no api key."""
        header = "HTTP_" + ACTING_USER_HEADER.upper().replace("-", "_")
        return self.post(body, **{header: value})

    def test_acting_user(self):
        """A tool call that the platform signed for a staff user is served, and recorded under them."""
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "search_logs", "arguments": {"ticket": TICKET, "contains": ["timeout"]}},
        }
        response = self.post_as(body, sign_acting_user(self.admin_user))
        self.assertEqual(response.status_code, 200)
        self.assertIn("timeout talking to provider", response.json()["result"]["content"][0]["text"])
        self.assertEqual(self.audit_rows().first().ticket, TICKET)

    def test_acting_user_for_nobody(self):
        """The platform's own request for nobody may list the tools, but not call one, and nothing is recorded."""
        signed = sign_acting_user(None)
        listed = self.post_as({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, signed)
        self.assertEqual(listed.status_code, 200)
        self.assertIn("search_logs", [tool["name"] for tool in listed.json()["result"]["tools"]])
        last_id = OperationsToolCall.objects.order_by("-id").values_list("id", flat=True).first() or 0
        body = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "search_logs", "arguments": {"ticket": TICKET}},
        }
        called = self.post_as(body, signed)
        result = called.json()["result"]
        self.assertTrue(result["isError"])
        self.assertIn("requires a staff user", result["content"][0]["text"])
        self.assertFalse(OperationsToolCall.objects.filter(id__gt=last_id).exists())

    def test_acting_user_refused(self):
        """A value that the platform didn't sign is 401; one for a user who isn't platform staff is 403."""
        ping = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        unsigned = self.post_as(ping, f"{self.admin_user.pk}")
        self.assertEqual(unsigned.status_code, 401)
        not_staff = self.post_as(ping, sign_acting_user(self.non_admin_user))
        self.assertEqual(not_staff.status_code, 403)
        missing = User(pk=10**9, username="nobody")
        deleted = self.post_as(ping, sign_acting_user(missing))
        self.assertEqual(deleted.status_code, 403)

    def test_acting_user_wins_over_an_api_key(self):
        """A signed acting user is checked, not an api key beside it: an unsigned value is refused, whatever the key."""
        header = "HTTP_" + ACTING_USER_HEADER.upper().replace("-", "_")
        response = self.post({"jsonrpc": "2.0", "id": 1, "method": "ping"}, key=self.staff_key, **{header: "forged"})
        self.assertEqual(response.status_code, 401)


class TestStaffMCPClientEndToEnd(OperationsTestBase):
    """An MCPClient of the platform's staff-only endpoint calls it for the user who is chatting."""

    def setUp(self):
        super().setUp()
        forward_to_django(self)
        self.mcpclient = MCPClient(
            name="test_operations_end_to_end",
            endpoint_url=staff_endpoint_url(),
            transport="http",
            auth_type="none",
            timeout=30,
            allowed_tools=[],
        )

    def test_discover_for_nobody(self):
        """The catalog, e.g. of the background refresh, is read for nobody in particular."""
        catalog = MCPServerConnection(self.mcpclient).discover()
        self.assertEqual(catalog.server_name, "smarter-operations")
        self.assertIn("platform_status", [tool.name for tool in catalog.tools])

    def test_call_tool_as_staff(self):
        with acting_user(self.admin_user):
            connection = MCPServerConnection(self.mcpclient)
        result = connection.call_tool("search_logs", {"ticket": TICKET, "contains": ["timeout"]})
        self.assertFalse(result.is_error)
        self.assertIn("timeout talking to provider", result.text)
        self.assertEqual(self.audit_rows().first().ticket, TICKET)

    def test_call_tool_as_someone_else(self):
        """A user who is not platform staff gets an error, and the tool never runs."""
        with acting_user(self.non_admin_user):
            connection = MCPServerConnection(self.mcpclient)
        last_id = OperationsToolCall.objects.order_by("-id").values_list("id", flat=True).first() or 0
        with self.assertRaises(SmarterMCPClientConnectionError):
            connection.call_tool("search_logs", {"ticket": TICKET})
        self.assertFalse(OperationsToolCall.objects.filter(id__gt=last_id).exists())
