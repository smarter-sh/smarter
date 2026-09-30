# pylint: disable=wrong-import-position
"""
Test SAMMCPClientBroker.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import os
from unittest import mock

from django.http import HttpRequest

from smarter.apps.connection.tests.factories import secret_factory
from smarter.apps.mcpclient.manifest.brokers.mcpclient import SAMMCPClientBroker
from smarter.apps.mcpclient.manifest.models.mcpclient.model import SAMMCPClient
from smarter.apps.mcpclient.models import MCPClient, MCPConnectionStatus
from smarter.lib import json, logging
from smarter.lib.manifest.broker import (
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

logger = logging.getLogger(__name__)

TOKEN_SECRET_NAME = "test_mcpclient_token"
"""The credentials Secret named by ./data/mcpclient-bearer.yaml."""
TOKEN_VALUE = "test-mcpclient-token-value"
REFRESH_PATCH = "smarter.apps.mcpclient.receivers.refresh_mcpclient"


# pylint: disable=too-many-public-methods
class TestSmarterMCPClientBroker(TestSAMBrokerBaseClass):
    """
    Test the Smarter SAMMCPClientBroker.

    Saving an MCPClient queues a Celery refresh task. It is mocked, so that the
    tests do not depend on the Celery worker, nor contact the MCP server.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.token_secret = secret_factory(user_profile=cls.user_profile, name=TOKEN_SECRET_NAME, value=TOKEN_VALUE)

    @classmethod
    def tearDownClass(cls):
        try:
            MCPClient.objects.filter(user_profile__account=cls.account).delete()
            cls.token_secret.delete()
        # pylint: disable=W0718
        except Exception:
            pass
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._broker_class = SAMMCPClientBroker
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("mcpclient.yaml")
        patcher = mock.patch(REFRESH_PATCH)
        self.refresh = patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(MCPClient.objects.filter(user_profile=self.user_profile).delete)

    @property
    def SAMBrokerClass(self) -> type[SAMMCPClientBroker]:
        return SAMMCPClientBroker

    @property
    def broker(self) -> SAMMCPClientBroker:
        return super().broker  # type: ignore

    def broker_for(self, filename: str) -> SAMMCPClientBroker:
        """Return a broker for a manifest in ./data."""
        with open(self.get_data_full_filepath(filename), encoding="utf-8") as f:
            loader = SAMLoader(manifest=f.read())
        return SAMMCPClientBroker(request=self.request, loader=loader)

    def test_setup(self):
        """Test that the test setup is correct."""
        self.assertTrue(self.ready)
        self.assertIsInstance(self.request, HttpRequest)
        self.assertIsInstance(self.broker, SAMMCPClientBroker)

    def test_broker_initialization(self):
        """Test the broker's kind and model classes."""
        self.assertEqual(self.broker.kind, "MCPClient")
        self.assertIs(self.broker.ORMModelClass, MCPClient)
        self.assertIsInstance(self.broker.manifest, SAMMCPClient)
        self.assertTrue(self.broker.ready)

    def test_mcpclient_is_not_created_lazily(self):
        """Test that reading the broker's mcpclient property does not create an MCPClient."""
        self.assertIsNone(self.broker.mcpclient)
        self.assertFalse(MCPClient.objects.filter(user_profile=self.user_profile, name="test_mcpclient").exists())

    def test_example_manifest(self):
        """Test that example_manifest() returns a valid manifest."""
        response = self.broker.example_manifest(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        data = json.loads(response.content)["data"]
        manifest = SAMMCPClient(**data)
        self.assertEqual(manifest.spec.config.authType, "bearer_token")

    def test_apply(self):
        """Test that apply() creates the MCPClient, and queues a refresh."""
        response = self.broker.apply(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        mcpclient = MCPClient.objects.get(user_profile=self.user_profile, name="test_mcpclient")
        self.assertEqual(mcpclient.transport, "http")
        self.assertEqual(mcpclient.endpoint_url, "https://mcp.example.com/mcp")
        self.assertEqual(mcpclient.headers, {"X-Client-Id": "smarter-tests"})
        self.assertEqual(mcpclient.allowed_tools, ["echo", "add_*", "fail"])
        self.assertEqual(mcpclient.allowed_resources, ["docs://test/*"])
        self.assertEqual(mcpclient.priority, 10)
        self.assertEqual(mcpclient.status, MCPConnectionStatus.UNCONFIGURED)
        self.assertEqual(sorted(mcpclient.tags_list), ["mcpclient", "test"])
        self.refresh.delay.assert_called_once_with(mcpclient.pk)

    def test_apply_updates(self):
        """Test that applying again updates the MCPClient, rather than creating another."""
        self.broker.apply(self.request, **self.kwargs)
        first = MCPClient.objects.get(user_profile=self.user_profile, name="test_mcpclient")
        self.broker_for("mcpclient.yaml").apply(self.request, **self.kwargs)
        self.assertEqual(MCPClient.objects.filter(user_profile=self.user_profile, name="test_mcpclient").count(), 1)
        self.assertEqual(MCPClient.objects.get(user_profile=self.user_profile, name="test_mcpclient").pk, first.pk)

    def test_apply_credentials(self):
        """Test that apply() resolves the credentials Secret by name."""
        broker = self.broker_for("mcpclient-bearer.yaml")
        broker.apply(self.request, **self.kwargs)
        mcpclient = MCPClient.objects.get(user_profile=self.user_profile, name="test_mcpclient_bearer")
        self.assertEqual(mcpclient.auth_type, "bearer_token")
        self.assertEqual(mcpclient.credentials, self.token_secret)

    def test_apply_missing_secret(self):
        """Test that apply() fails if the credentials Secret does not exist."""
        broker = self.broker_for("mcpclient-bearer.yaml")
        with mock.patch("smarter.apps.mcpclient.manifest.brokers.mcpclient.Secret.objects.filter") as secret_filter:
            secret_filter.return_value.first.return_value = None
            secret_filter.return_value.with_read_permission_for.return_value.order_by.return_value.first.return_value = (
                None
            )
            with self.assertRaises(SAMBrokerErrorNotFound):
                broker.apply(self.request, **self.kwargs)
        self.assertFalse(MCPClient.objects.filter(name="test_mcpclient_bearer").exists())

    def test_describe(self):
        """Test that describe() renders the MCPClient, with the credentials Secret's name, never its value."""
        self.broker_for("mcpclient-bearer.yaml").apply(self.request, **self.kwargs)
        broker = self.broker_for("mcpclient-bearer.yaml")
        response = broker.describe(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        data = json.loads(response.content)["data"]
        self.assertEqual(data["spec"]["config"]["credentials"], TOKEN_SECRET_NAME)
        self.assertEqual(data["status"]["connectionStatus"], MCPConnectionStatus.UNCONFIGURED)
        self.assertNotIn(TOKEN_VALUE, response.content.decode())
        # the description is a valid manifest
        SAMMCPClient(**data)

    def test_describe_status(self):
        """Test that describe() reports the last connection."""
        self.broker.apply(self.request, **self.kwargs)
        MCPClient.objects.filter(user_profile=self.user_profile, name="test_mcpclient").update(
            status=MCPConnectionStatus.CONNECTED,
            server_name="test-server",
            tools=["echo"],
            protocol_version="2025-11-25",
        )
        response = self.broker_for("mcpclient.yaml").describe(self.request, **self.kwargs)
        status = json.loads(response.content)["data"]["status"]
        self.assertEqual(status["connectionStatus"], MCPConnectionStatus.CONNECTED)
        self.assertEqual(status["serverName"], "test-server")
        self.assertEqual(status["tools"], ["echo"])

    def test_describe_not_found(self):
        """Test that describe() fails for an MCPClient that does not exist."""
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker.describe(self.request, **self.kwargs)

    def test_get(self):
        """Test that get() lists the MCPClient, with its credentials as a name."""
        self.broker_for("mcpclient-bearer.yaml").apply(self.request, **self.kwargs)
        response = self.broker.get(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        items = json.loads(response.content)["data"]["data"]["items"]
        item = next(item for item in items if item["name"] == "test_mcpclient_bearer")
        self.assertEqual(item["credentials"], TOKEN_SECRET_NAME)
        self.assertNotIn(TOKEN_VALUE, response.content.decode())

    def test_delete(self):
        """Test that delete() deletes the MCPClient."""
        self.broker.apply(self.request, **self.kwargs)
        response = self.broker_for("mcpclient.yaml").delete(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertFalse(MCPClient.objects.filter(user_profile=self.user_profile, name="test_mcpclient").exists())

    def test_delete_not_found(self):
        """Test that delete() fails for an MCPClient that does not exist."""
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker.delete(self.request, **self.kwargs)

    def test_not_implemented(self):
        """Test that deploy, undeploy and prompt are not implemented."""
        for method in (self.broker.deploy, self.broker.undeploy, self.broker.prompt):
            with self.subTest(method=method.__name__):
                with self.assertRaises((SAMBrokerErrorNotImplemented, SAMBrokerError)):
                    method(self.request, **self.kwargs)
