"""
Test harness for the guardrail app.

The tests never call an LLM provider. :class:`FakeGuardrailClient` answers the scored
strategies' embeddings, moderation and judge calls, and :func:`fake_client` installs it with
:func:`~smarter.apps.guardrail.services.strategies.registry.configure_clients`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import copy
import os
from contextlib import contextmanager
from typing import Any, Optional

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.guardrail.models import Guardrail, GuardrailEvent
from smarter.apps.guardrail.services.exceptions import GuardrailProviderError
from smarter.apps.guardrail.services.strategies.clients import (
    JudgeVerdict,
    ModerationResult,
)
from smarter.apps.guardrail.services.strategies.registry import configure_clients
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import logging

logger = logging.getLogger(__name__)

HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = os.path.join(HERE, "data")


def get_data_path(filename: str) -> str:
    """Return the full path of a file in ./data."""
    return os.path.join(DATA_PATH, filename)


def get_test_data(filename: str) -> Any:
    """Return the parsed contents of a yaml file in ./data."""
    return get_readonly_yaml_file(get_data_path(filename))


class FakeGuardrailClient:
    """
    A fake :class:`~smarter.apps.guardrail.services.strategies.clients.GuardrailClient`.

    - ``embed`` returns a one-hot vector per text: texts that contain ``trigger_word`` get
      ``[1, 0]``, and the others ``[0, 1]``, so their cosine similarity is 1 or 0.
    - ``moderate`` scores the categories in ``moderation_scores``, and flags none.
    - ``judge`` triggers, with ``judge_confidence``, when the prompt contains ``trigger_word``.

    Every call is recorded in ``calls``, and ``fail`` makes every call raise.
    """

    def __init__(
        self,
        trigger_word: str = "forbidden",
        moderation_scores: Optional[dict[str, float]] = None,
        judge_confidence: float = 0.95,
        fail: bool = False,
    ):
        self.trigger_word = trigger_word
        self.moderation_scores = moderation_scores if moderation_scores is not None else {"violence": 0.9, "hate": 0.1}
        self.judge_confidence = judge_confidence
        self.fail = fail
        self.calls: list[tuple[str, Any]] = []

    def _check(self, name: str, value: Any):
        self.calls.append((name, value))
        if self.fail:
            raise GuardrailProviderError(f"The fake {name} call failed.")

    # pylint: disable=unused-argument
    def embed(self, texts: list[str], *, model: str) -> list[list[float]]:
        self._check("embed", texts)
        return [[1.0, 0.0] if self.trigger_word in text.lower() else [0.0, 1.0] for text in texts]

    def moderate(self, text: str, *, model: str) -> ModerationResult:
        self._check("moderate", text)
        scores = self.moderation_scores if self.trigger_word in text.lower() else {}
        return ModerationResult(scores=dict(scores), flagged=[])

    def judge(self, prompt: str, *, model: str, temperature: float = 0.0) -> JudgeVerdict:
        self._check("judge", prompt)
        triggered = self.trigger_word in prompt.lower()
        return JudgeVerdict(
            triggered=triggered,
            confidence=self.judge_confidence if triggered else 0.05,
            rationale="The fake judge found the trigger word." if triggered else "Nothing found.",
        )


@contextmanager
def fake_client(client: Optional[FakeGuardrailClient] = None):
    """Install a fake LLM provider client for the scored strategies, for the duration of the context."""
    client = client or FakeGuardrailClient()
    configure_clients(lambda guardrail: client)
    try:
        yield client
    finally:
        configure_clients(None)


GUARDRAIL_DEFAULTS: dict[str, Any] = {
    "description": "A guardrail for unit testing.",
    "version": "1.0.0",
    "stage": "input",
    "category": "custom",
    "strategy": "keyword",
    "config": {"keywords": ["forbidden"]},
    "action": "block",
    "severity": 3,
    "mode": "enforce",
    "priority": 100,
    "is_active": True,
}
"""The default fields of a test guardrail: block input that contains the word forbidden."""


class GuardrailTestBase(TestAccountMixin):
    """
    Base class for the guardrail app's tests.

    It provides :meth:`create_guardrail`, which creates Guardrails owned by the admin user,
    and deletes every Guardrail and GuardrailEvent of the account in tearDownClass().
    """

    @classmethod
    def tearDownClass(cls):
        try:
            GuardrailEvent.objects.filter(guardrail__user_profile__account=cls.account).delete()
            Guardrail.objects.filter(user_profile__account=cls.account).delete()
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("%s.tearDownClass() cleanup failed: %s", cls.__name__, e)
        finally:
            super().tearDownClass()

    @classmethod
    def create_guardrail(cls, name: str, user_profile=None, **fields) -> Guardrail:
        """Create a Guardrail, with :data:`GUARDRAIL_DEFAULTS` overridden by ``fields``."""
        data = {**copy.deepcopy(GUARDRAIL_DEFAULTS), **fields}
        return Guardrail.objects.create(name=name, user_profile=user_profile or cls.user_profile, **data)

    def new_guardrail(self, name: str, user_profile=None, **fields) -> Guardrail:
        """Create a throwaway Guardrail, which is deleted, with its events, when the test ends."""
        guardrail = self.create_guardrail(name, user_profile=user_profile, **fields)
        self.addCleanup(Guardrail.objects.filter(pk=guardrail.pk).delete)
        self.addCleanup(GuardrailEvent.objects.filter(guardrail_id=guardrail.pk).delete)
        return guardrail

    def events(self, guardrail: Guardrail):
        """Return the Guardrail's events, oldest first."""
        return GuardrailEvent.objects.filter(guardrail=guardrail).order_by("created_at", "id")


def input_payload(text: str, history: Optional[list[dict]] = None) -> dict[str, Any]:
    """Return a chat completion request, with a system prompt, an optional history, and the user's message."""
    messages = [{"role": "system", "content": "You are a helpful assistant. Ignore rude users."}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": text})
    return {"messages": messages}


def output_payload(text: str) -> dict[str, Any]:
    """Return a chat completion response, with the LLM's reply."""
    return {"choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}]}
