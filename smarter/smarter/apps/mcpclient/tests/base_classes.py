"""
Test harness for the mcpclient app.

The tests never contact a real MCP server. :func:`build_test_server` builds an in-process
MCP server, with the MCP Python SDK, and :func:`mock_mcp_server` connects every MCPClient
to it, by replacing :meth:`MCPServerConnection.server_target`. The MCP protocol itself,
from the handshake to tool calls, is real.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import copy
import os
from contextlib import contextmanager
from typing import Any, Optional
from unittest import mock

from mcp.server import MCPServer

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.connection.tests.factories import secret_factory
from smarter.apps.mcpclient.caching import invalidate_cached_catalog
from smarter.apps.mcpclient.connection import MCPServerConnection
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.secret.models import Secret
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import logging

logger = logging.getLogger(__name__)

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(HERE, "data")

MCPCLIENT_NAME = "test_mcpclient"
"""The name of the MCPClient in ./data/mcpclient.yaml."""
TOKEN_SECRET_NAME = "test_mcpclient_token"
TOKEN_VALUE = "test-mcpclient-token-value"
TEST_SERVER_NAME = "smarter-test-server"
TEST_SERVER_VERSION = "1.2.3"
TEST_SERVER_INSTRUCTIONS = "Use echo to repeat text, and add_numbers to add numbers."
README_URI = "docs://test/readme"
README_TEXT = "Hello from the test readme."

GUARD_PATCH = "smarter.apps.mcpclient.connection.validate_public_url"


def get_data_path(filename: str) -> str:
    """Return the full path of a file in ./data."""
    return os.path.join(DATA_PATH, filename)


def get_test_data(filename: str) -> Any:
    """Return the parsed contents of a yaml file in ./data."""
    return get_readonly_yaml_file(get_data_path(filename))


def build_test_server(instructions: Optional[str] = TEST_SERVER_INSTRUCTIONS) -> MCPServer:
    """
    Build an in-process MCP server with tools and a resource.

    - ``echo(text)``: returns the text.
    - ``add_numbers(a, b)``: returns a + b.
    - ``fail()``: raises, so the tool call returns an error result.
    - ``secret_admin_tool()``: a tool that the test MCPClient does not allow.
    - ``docs://test/readme``: a text resource.

    :param instructions: The server's instructions.
    :returns: The server.
    """
    server = MCPServer(name=TEST_SERVER_NAME, version=TEST_SERVER_VERSION, instructions=instructions)

    @server.tool(description="Repeat the text.")
    def echo(text: str) -> str:
        return text

    @server.tool(description="Add two numbers.")
    def add_numbers(a: int, b: int) -> int:
        return a + b

    @server.tool(description="Always fails.")
    def fail() -> str:
        raise ValueError("this tool always fails")

    @server.tool(description="A tool that the test MCPClient does not allow.")
    def secret_admin_tool() -> str:
        return "should never be called"

    @server.resource(README_URI, description="The test readme.")
    def readme() -> str:
        return README_TEXT

    # pylint: disable=W0104
    echo, add_numbers, fail, secret_admin_tool, readme
    return server


@contextmanager
def mock_mcp_server(server: Optional[MCPServer] = None):
    """
    Connect every MCPClient to an in-process MCP server, for the duration of the context.

    The public-URL guard is also replaced, because the MCPClients' endpoint URLs are
    never contacted.

    :param server: The server. Defaults to :func:`build_test_server`.
    :yields: A mock of the guard, to inspect the URLs it was called with.
    """
    server = server or build_test_server()
    with (
        mock.patch(GUARD_PATCH) as guard,
        mock.patch.object(MCPServerConnection, "server_target", lambda self, http_client: server),
    ):
        yield guard


class MCPClientTestBase(TestAccountMixin):
    """
    Base class for the mcpclient app's tests.

    In addition to the TestAccountMixin account, admin user and non-admin user, it
    creates ``mcpclient``, an MCPClient owned by the admin user from ./data/mcpclient.yaml,
    and ``token_secret``, a Secret for bearer token authentication. Every MCPClient
    owned by the account is deleted in tearDownClass().
    """

    mcpclient_yaml: dict
    mcpclient: MCPClient
    token_secret: Secret

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mcpclient_yaml = get_test_data("mcpclient.yaml")
        cls.token_secret = secret_factory(user_profile=cls.user_profile, name=TOKEN_SECRET_NAME, value=TOKEN_VALUE)
        cls.mcpclient = cls.create_mcpclient(MCPCLIENT_NAME)

    @classmethod
    def tearDownClass(cls):
        try:
            MCPClient.objects.filter(user_profile__account=cls.account).delete()
            cls.token_secret.delete()
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("%s.tearDownClass() cleanup failed: %s", cls.__name__, e)
        finally:
            super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.mcpclient.refresh_from_db()
        invalidate_cached_catalog(self.mcpclient)
        self.addCleanup(invalidate_cached_catalog, self.mcpclient)

    @classmethod
    def create_mcpclient(cls, name: str, user_profile=None, **fields) -> MCPClient:
        """
        Create an MCPClient with the configuration of ./data/mcpclient.yaml.

        Saving an MCPClient queues a Celery refresh task, which is mocked here, so that
        the tests do not depend on the Celery worker.

        :param name: The MCPClient's name.
        :param user_profile: The owner. Defaults to the admin user's profile.
        :param fields: MCPClient fields that override the manifest's configuration.
        """
        config = copy.deepcopy(cls.mcpclient_yaml["spec"]["config"])
        data = {
            "name": name,
            "description": "An MCPClient for unit testing.",
            "version": "1.0.0",
            "user_profile": user_profile or cls.user_profile,
            "transport": config["transport"],
            "endpoint_url": config["endpointUrl"],
            "headers": config["headers"],
            "timeout": config["timeout"],
            "auth_type": config["authType"],
            "allowed_tools": config["allowedTools"],
            "allowed_resources": config["allowedResources"],
            "include_instructions": config["includeInstructions"],
            "cache_ttl": config["cacheTtl"],
            "priority": config["priority"],
            **fields,
        }
        with mock.patch("smarter.apps.mcpclient.receivers.refresh_mcpclient"):
            return MCPClient.objects.create(**data)

    def new_mcpclient(self, name: str, user_profile=None, **fields) -> MCPClient:
        """Create a throwaway MCPClient, which is deleted when the test ends."""
        mcpclient = self.create_mcpclient(name, user_profile=user_profile, **fields)
        self.addCleanup(MCPClient.objects.filter(pk=mcpclient.pk).delete)
        self.addCleanup(invalidate_cached_catalog, mcpclient)
        return mcpclient
