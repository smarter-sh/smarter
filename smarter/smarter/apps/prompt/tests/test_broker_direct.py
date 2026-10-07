"""
Test the Prompt manifest broker, :class:`smarter.apps.prompt.manifest.brokers.prompt.SAMPromptBroker`, directly.

:mod:`smarter.apps.prompt.tests.test_broker` covers the api/v1/cli/ commands. This module covers
the broker methods that those commands don't reach.
"""

import os

from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.manifest.brokers.prompt import (
    PromptSerializer,
    SAMPromptBroker,
    SAMPromptBrokerError,
)
from smarter.apps.prompt.manifest.models.prompt.model import SAMPrompt
from smarter.apps.prompt.models import Prompt
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib import json
from smarter.lib.manifest.broker import SAMBrokerErrorNotReady, SAMBrokerReadOnlyError
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

HERE = os.path.abspath(os.path.dirname(__file__))


class TestSAMPromptBrokerDirect(TestSAMBrokerBaseClass):
    """Test SAMPromptBroker's methods directly."""

    def setUp(self):
        super().setUp()
        self._here = HERE
        self._broker_class = SAMPromptBroker
        self._manifest_filespec = os.path.join(HERE, "data", "prompt.yaml")
        self.session_key = self.loader.manifest_spec["sessionKey"]  # type: ignore[index]
        self.addCleanup(Prompt.objects.filter(session_key=self.session_key).delete)

    @property
    def broker(self) -> SAMPromptBroker:
        return super().broker  # type: ignore[return-value]

    def create_prompt(self) -> Prompt:
        """Create the Prompt that the manifest's session key identifies."""
        llmclient = LLMClient.objects.create(
            name=f"test_prompt_broker_direct_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(llmclient.delete)
        return Prompt.objects.create(
            name="test_prompt_broker_direct",
            session_key=self.session_key,
            llmclient=llmclient,
            user_profile=self.user_profile,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            url="https://www.example.com/",
        )

    def test_properties(self):
        """Test the broker's manifest, serializer and class name."""
        self.assertIsInstance(self.broker.manifest, SAMPrompt)
        self.assertIs(self.broker.manifest, self.broker.manifest)
        self.assertIs(self.broker.SerializerClass, PromptSerializer)
        self.assertIn("SAMPromptBroker", self.broker.formatted_class_name)
        self.assertEqual(self.broker.dependencies(), [])

    def test_manifest_to_django_orm(self):
        """Test that the manifest's metadata and spec merge into one snake_case dict."""
        orm = self.broker.manifest_to_django_orm()
        self.assertEqual(orm["name"], "test_prompt_broker_direct")  # type: ignore[index]
        self.assertEqual(orm["session_key"], self.session_key)  # type: ignore[index]
        self.assertEqual(orm["ip_address"], "192.168.1.1")  # type: ignore[index]

    def test_invalid_manifest_type(self):
        """Test that a manifest of the wrong type is refused."""
        self.broker._manifest = {"kind": "Prompt"}  # type: ignore[assignment]  # pylint: disable=protected-access
        with self.assertRaises(SAMPromptBrokerError):
            _ = self.broker.manifest

    def test_chat_object_by_session_key(self):
        """Test that the manifest's session key identifies its Prompt."""
        prompt = self.create_prompt()
        self.assertEqual(self.broker.chat_object, prompt)

    def test_get_by_session_key(self):
        """Test that get() with a session key returns that one Prompt."""
        prompt = self.create_prompt()
        response = self.broker.get(self.request, **{SMARTER_CHAT_SESSION_KEY_NAME: self.session_key})
        data = json.loads(response.content.decode())["data"]
        items = data["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], str(prompt.id))

    def test_describe(self):
        """Test that describe() returns the Prompt's manifest, and refuses when there is none."""
        with self.assertRaises(SAMBrokerErrorNotReady):
            self.broker.describe(self.request)

        self.create_prompt()
        broker = SAMPromptBroker(request=self.request, loader=self.loader)
        response = broker.describe(self.request)
        data = json.loads(response.content.decode())["data"]
        self.assertEqual(data["spec"]["sessionKey"], self.session_key)

    def test_apply_is_refused(self):
        """Test that apply() refuses, because a Prompt is read-only."""
        with self.assertRaises(SAMBrokerReadOnlyError):
            self.broker.apply(self.request)

    def test_prompt(self):
        """Test that prompt() echoes the prompt."""
        response = self.broker.prompt(self.request, prompt="hello")
        data = json.loads(response.content.decode())["data"]
        self.assertEqual(data["prompt"], "hello")
