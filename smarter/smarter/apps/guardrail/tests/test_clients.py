"""
Test :mod:`smarter.apps.guardrail.services.strategies.clients`, with a mocked OpenAI SDK.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from types import SimpleNamespace
from unittest import mock

import openai

from smarter.apps.guardrail.services.exceptions import (
    GuardrailConfigError,
    GuardrailProviderError,
)
from smarter.apps.guardrail.services.strategies.clients import (
    JUDGE_SYSTEM_MESSAGE,
    OpenAIGuardrailClient,
    default_client_for,
)

from .base_classes import GuardrailTestBase


class Scores(SimpleNamespace):
    """A stand-in for the SDK's moderation categories and scores models."""

    def model_dump(self, by_alias=False):  # pylint: disable=unused-argument
        return dict(self.__dict__)


class TestGuardrailClients(GuardrailTestBase):
    """Test OpenAIGuardrailClient and default_client_for."""

    def client(self) -> tuple[OpenAIGuardrailClient, mock.MagicMock]:
        """Return a client whose OpenAI SDK client is a mock."""
        client = OpenAIGuardrailClient(api_key="sk-test")
        sdk = mock.MagicMock()
        client._client = sdk  # pylint: disable=protected-access
        return client, sdk

    def test_embed(self):
        """Test that embed returns the vectors in the order of the texts."""
        client, sdk = self.client()
        sdk.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(index=1, embedding=[0.0, 1.0]), SimpleNamespace(index=0, embedding=[1.0, 0.0])]
        )
        self.assertEqual(client.embed(["a", "b"], model="m"), [[1.0, 0.0], [0.0, 1.0]])
        sdk.embeddings.create.assert_called_once_with(model="m", input=["a", "b"])

    def test_moderate(self):
        """Test that moderate returns the scores and flagged categories, by their API names."""
        client, sdk = self.client()
        result = SimpleNamespace(
            category_scores=Scores(**{"hate": 0.1, "self-harm/intent": 0.8}),
            categories=Scores(**{"hate": False, "self-harm/intent": True}),
        )
        sdk.moderations.create.return_value = SimpleNamespace(results=[result])
        moderation = client.moderate("text", model="omni-moderation-latest")
        self.assertEqual(moderation.scores, {"hate": 0.1, "self-harm/intent": 0.8})
        self.assertEqual(moderation.flagged, ["self-harm/intent"])

    def test_judge(self):
        """Test that judge asks for a JSON object, and parses the verdict."""
        client, sdk = self.client()
        message = SimpleNamespace(content='{"triggered": true, "confidence": 0.9, "rationale": "r"}')
        sdk.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=message)])
        verdict = client.judge("prompt", model="gpt-4o-mini")
        self.assertTrue(verdict.triggered)
        kwargs = sdk.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["response_format"], {"type": "json_object"})
        self.assertEqual(kwargs["temperature"], 0.0)
        # the text under judgement may try to instruct the judge, so the system message forbids it
        self.assertEqual(kwargs["messages"][0], {"role": "system", "content": JUDGE_SYSTEM_MESSAGE})
        self.assertEqual(kwargs["messages"][1], {"role": "user", "content": "prompt"})

    def test_errors(self):
        """Test that the SDK's errors are raised as GuardrailProviderError."""
        client, sdk = self.client()
        error = openai.APIConnectionError(request=mock.MagicMock())
        sdk.embeddings.create.side_effect = error
        sdk.moderations.create.side_effect = error
        sdk.chat.completions.create.side_effect = error
        for call in (
            lambda: client.embed(["a"], model="m"),
            lambda: client.moderate("a", model="m"),
            lambda: client.judge("a", model="m"),
        ):
            with self.assertRaises(GuardrailProviderError):
                call()

    def test_default_client_for(self):
        """Test that default_client_for requires a provider that the guardrail's owner may read."""
        g = self.new_guardrail("test_clients_provider", strategy="moderation", config={"provider": "no_such_provider"})
        with self.assertRaises(GuardrailConfigError):
            default_client_for(g)

    def test_default_client_for_openai(self):
        """Test that default_client_for returns a cached client for the platform's openai provider, if it has a key."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.provider.models import Provider

        provider = Provider.objects.filter(name="openai", is_active=True).first()
        if provider is None or not provider.api_key:
            self.skipTest("the platform's openai Provider does not exist, or has no API key.")
        g = self.new_guardrail("test_clients_openai", strategy="moderation", config={})
        client = default_client_for(g)
        self.assertIsInstance(client, OpenAIGuardrailClient)
        self.assertIs(default_client_for(g), client)
