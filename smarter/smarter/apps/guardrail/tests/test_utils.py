"""
Test :mod:`smarter.apps.guardrail.utils` and the add_builtin_guardrails management command.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from unittest import mock

from django.core.management import call_command

from smarter.apps.guardrail.utils import GuardrailExamples, add_builtin_guardrails
from smarter.common.exceptions import SmarterValueError

from .base_classes import GuardrailTestBase


class TestGuardrailUtils(GuardrailTestBase):
    """Test the built-in guardrails' loading and installation."""

    def test_examples(self):
        """Test that the built-in guardrails are loaded, with their names."""
        examples = GuardrailExamples()
        self.assertEqual(examples.count(), 18)
        names = [example.name for example in examples.guardrails]
        self.assertIn("pii_redaction_input", names)
        self.assertIn("prompt_injection_llm_judge_input", names)

    def test_add_builtin_guardrails(self):
        """Test that add_builtin_guardrails applies every built-in manifest for the user."""
        with mock.patch("smarter.apps.guardrail.utils.call_command") as command:
            self.assertTrue(add_builtin_guardrails(user_profile=self.user_profile))
        self.assertEqual(command.call_count, 18)
        for call in command.call_args_list:
            self.assertEqual(call.args[0], "apply_manifest")
            self.assertEqual(call.kwargs["username"], self.admin_user.username)

    def test_add_builtin_guardrails_applies(self):
        """Test that the built-in guardrails really apply, for a test user."""
        call_command("add_builtin_guardrails", username=self.admin_user.username)
        from smarter.apps.guardrail.models import (
            Guardrail,  # pylint: disable=import-outside-toplevel
        )

        self.assertEqual(Guardrail.objects.filter(user_profile=self.user_profile).count(), 18)

    def test_requires_user_profile(self):
        """Test that add_builtin_guardrails requires a UserProfile."""
        with self.assertRaises(SmarterValueError):
            add_builtin_guardrails(user_profile=None)
