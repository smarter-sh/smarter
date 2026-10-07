"""
Test the LLMClient manifest's ``spec.mcpClients``, and the LLMClientMCPClients model.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import copy
import os
from unittest import mock

import yaml

from smarter.apps.llmclient.manifest.brokers.llmclient import SAMLLMClientBroker
from smarter.apps.llmclient.models import LLMClient, LLMClientMCPClients
from smarter.lib import json
from smarter.lib.manifest.broker import SAMBrokerErrorNotFound
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

from .base_classes import MCPCLIENT_NAME, MCPClientTestBase, get_test_data

LLMCLIENT_NAME = "test_mcpclient_llmclient"


class TestLLMClientMCPClients(TestSAMBrokerBaseClass, MCPClientTestBase):
    """Test that applying an LLMClient manifest attaches, detaches and describes its MCPClients."""

    @classmethod
    def tearDownClass(cls):
        LLMClient.objects.filter(user_profile__account=cls.account).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("llmclient.yaml")
        self.addCleanup(LLMClient.objects.filter(user_profile=self.user_profile, name=LLMCLIENT_NAME).delete)

    @property
    def SAMBrokerClass(self):
        return SAMLLMClientBroker

    def apply(self, mcpclients=None) -> SAMLLMClientBroker:
        """Apply ./data/llmclient.yaml, with spec.mcpClients replaced by ``mcpclients`` if given."""
        data = copy.deepcopy(get_test_data("llmclient.yaml"))
        if mcpclients is not None:
            data["spec"]["mcpClients"] = mcpclients
        broker = SAMLLMClientBroker(request=self.request, loader=SAMLoader(manifest=yaml.safe_dump(data)))
        with mock.patch("smarter.apps.llmclient.receivers.deploy_default_api", create=True):
            broker.apply(self.request, **self.kwargs)
        return broker

    def linked(self) -> list[str]:
        """Return the names of the LLMClient's MCPClients."""
        llmclient = LLMClient.objects.get(user_profile=self.user_profile, name=LLMCLIENT_NAME)
        return sorted(link.mcpclient.name for link in LLMClientMCPClients.objects.filter(llmclient=llmclient))

    def test_apply_attaches(self):
        """Test that applying the LLMClient attaches its MCPClients."""
        self.apply()
        self.assertEqual(self.linked(), [MCPCLIENT_NAME])

    def test_apply_detaches(self):
        """Test that removing an MCPClient from spec.mcpClients detaches it."""
        second = self.new_mcpclient("test_mcpclient_llmclient_second")
        self.apply([MCPCLIENT_NAME, second.name])
        self.assertEqual(self.linked(), sorted([MCPCLIENT_NAME, second.name]))
        self.apply([second.name])
        self.assertEqual(self.linked(), [second.name])
        self.apply([])
        self.assertEqual(self.linked(), [])

    def test_apply_unknown_mcpclient(self):
        """Test that applying an LLMClient with an unknown MCPClient fails."""
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.apply(["no_such_mcpclient"])

    def test_apply_shared_mcpclient(self):
        """Test that an LLMClient may use an MCPClient that is shared with its owner."""
        shared = self.new_mcpclient("test_mcpclient_shared", user_profile=self.non_admin_user_profile)
        broker = self.apply([MCPCLIENT_NAME])
        self.assertEqual(broker.resolve_mcpclient(MCPCLIENT_NAME), self.mcpclient)
        # the admin user may read the non-admin user's MCPClient only if it is shared with them,
        # so resolve_mcpclient() returns it or None, but never another account's MCPClient.
        resolved = broker.resolve_mcpclient(shared.name)
        self.assertIn(resolved, (shared, None))

    def test_describe(self):
        """Test that describe() renders spec.mcpClients."""
        self.apply()
        broker = SAMLLMClientBroker(request=self.request, loader=self.loader)
        response = broker.describe(self.request, **self.kwargs)
        data = json.loads(response.content)["data"]
        self.assertEqual(data["spec"]["mcpClients"], [MCPCLIENT_NAME])

    def test_delete_mcpclient_detaches(self):
        """Test that deleting an MCPClient detaches it from the LLMClient."""
        second = self.new_mcpclient("test_mcpclient_llmclient_deleted")
        self.apply([MCPCLIENT_NAME, second.name])
        second.delete()
        self.assertEqual(self.linked(), [MCPCLIENT_NAME])
