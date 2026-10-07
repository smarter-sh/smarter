"""
Test the LLMClient manifest's ``spec.guardrails``, and the LLMClientGuardrails model.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import copy
import os

import yaml

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.llmclient.manifest.brokers.llmclient import SAMLLMClientBroker
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientFunctions,
    LLMClientGuardrails,
)
from smarter.lib import json
from smarter.lib.manifest.broker import SAMBrokerErrorNotFound
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

from .base_classes import GuardrailTestBase, get_test_data

LLMCLIENT_NAME = "test_guardrail_llmclient"
BUILTIN = "pii_redaction_input"


class TestLLMClientGuardrails(TestSAMBrokerBaseClass, GuardrailTestBase):
    """Test that applying an LLMClient manifest attaches, detaches and describes its Guardrails."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guardrail = cls.create_guardrail("test_guardrail")

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

    def apply(self, guardrails=None) -> SAMLLMClientBroker:
        """Apply ./data/llmclient.yaml, with spec.guardrails replaced by ``guardrails`` if given."""
        data = copy.deepcopy(get_test_data("llmclient.yaml"))
        if guardrails is not None:
            data["spec"]["guardrails"] = guardrails
        broker = SAMLLMClientBroker(request=self.request, loader=SAMLoader(manifest=yaml.safe_dump(data)))
        broker.apply(self.request, **self.kwargs)
        return broker

    def llmclient(self) -> LLMClient:
        return LLMClient.objects.get(user_profile=self.user_profile, name=LLMCLIENT_NAME)

    def linked(self) -> list[str]:
        """Return the names of the LLMClient's Guardrails."""
        return sorted(link.guardrail.name for link in LLMClientGuardrails.objects.filter(llmclient=self.llmclient()))

    def test_apply_attaches(self):
        """Test that applying the LLMClient attaches its Guardrails, and not as Functions."""
        self.apply()
        self.assertEqual(self.linked(), ["test_guardrail"])
        self.assertFalse(LLMClientFunctions.objects.filter(llmclient=self.llmclient(), name="test_guardrail").exists())

    def test_apply_is_idempotent(self):
        """Test that applying the same manifest again keeps the Guardrails attached."""
        self.apply()
        self.apply()
        self.assertEqual(self.linked(), ["test_guardrail"])

    def test_apply_builtin(self):
        """Test that an LLMClient may use a built-in guardrail of the Smarter admin user."""
        from smarter.apps.guardrail.models import (
            Guardrail,  # pylint: disable=import-outside-toplevel
        )

        if not Guardrail.objects.filter(
            name=BUILTIN, user_profile=smarter_cached_objects.smarter_admin_user_profile
        ).exists():
            self.skipTest("the built-in guardrails are not installed.")
        self.apply(["test_guardrail", BUILTIN])
        self.assertEqual(self.linked(), sorted(["test_guardrail", BUILTIN]))

    def test_apply_detaches(self):
        """Test that removing a Guardrail from spec.guardrails detaches it."""
        second = self.new_guardrail("test_guardrail_second")
        self.apply(["test_guardrail", second.name])
        self.assertEqual(self.linked(), sorted(["test_guardrail", second.name]))
        self.apply([second.name])
        self.assertEqual(self.linked(), [second.name])
        self.apply([])
        self.assertEqual(self.linked(), [])

    def test_apply_unknown_guardrail(self):
        """Test that applying an LLMClient with an unknown Guardrail fails."""
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.apply(["no_such_guardrail"])

    def test_resolve_own_first(self):
        """Test that the user's own Guardrail takes precedence over a shared one of the same name."""
        broker = self.apply()
        self.assertEqual(broker.resolve_guardrail("test_guardrail"), self.guardrail)
        self.assertIsNone(broker.resolve_guardrail("no_such_guardrail"))

    def test_describe(self):
        """Test that describe() renders spec.guardrails."""
        self.apply()
        response = SAMLLMClientBroker(request=self.request, loader=self.loader).describe(self.request, **self.kwargs)
        self.assertEqual(json.loads(response.content)["data"]["spec"]["guardrails"], ["test_guardrail"])

    def test_delete_guardrail_detaches(self):
        """Test that deleting a Guardrail detaches it from the LLMClient."""
        second = self.new_guardrail("test_guardrail_deleted")
        self.apply(["test_guardrail", second.name])
        second.delete()
        self.assertEqual(self.linked(), ["test_guardrail"])
