"""
Test :mod:`smarter.apps.guardrail.models`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.db import IntegrityError, transaction

from smarter.apps.guardrail.manifest.enum import (
    SAMGuardrailAction,
    SAMGuardrailCategory,
    SAMGuardrailMode,
    SAMGuardrailStage,
    SAMGuardrailStrategy,
)
from smarter.apps.guardrail.manifest.models.guardrail.const import (
    DEFAULT_MESSAGE,
    DEFAULT_REPLACEMENT,
)
from smarter.apps.guardrail.models import (
    Guardrail,
    GuardrailAction,
    GuardrailCategory,
    GuardrailMode,
    GuardrailStage,
    GuardrailStrategy,
)
from smarter.apps.guardrail.serializers import GuardrailSerializer

from .base_classes import GuardrailTestBase


class TestGuardrailModels(GuardrailTestBase):
    """Test the Guardrail model."""

    def test_choices_match_the_manifest(self):
        """Test that the model's choices match the manifest's enums."""
        for choices, enum in (
            (GuardrailStage, SAMGuardrailStage),
            (GuardrailCategory, SAMGuardrailCategory),
            (GuardrailStrategy, SAMGuardrailStrategy),
            (GuardrailAction, SAMGuardrailAction),
            (GuardrailMode, SAMGuardrailMode),
        ):
            self.assertEqual(sorted(choices.values), sorted(enum.all()), choices)

    def test_helpers(self):
        """Test settings, effective_replacement, effective_message and runs_on."""
        g = Guardrail(stage="both", config=None)
        self.assertEqual(g.settings, {})
        self.assertEqual(g.effective_replacement, DEFAULT_REPLACEMENT)
        self.assertEqual(g.effective_message, DEFAULT_MESSAGE)
        self.assertTrue(g.runs_on("input") and g.runs_on("output"))
        g = Guardrail(stage="output", replacement="", message="No.")
        self.assertEqual(g.effective_replacement, "")
        self.assertEqual(g.effective_message, "No.")
        self.assertFalse(g.runs_on("input"))

    def test_unique_name_per_user_profile(self):
        """Test that a user may not have two Guardrails with the same name."""
        self.new_guardrail("test_models_unique")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_guardrail("test_models_unique")

    def test_serializer(self):
        """Test the serializer."""
        data = GuardrailSerializer(self.new_guardrail("test_models_serializer")).data
        self.assertEqual(data["name"], "test_models_serializer")
        self.assertEqual(data["strategy"], "keyword")
