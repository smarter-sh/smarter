"""
Test the Guardrail Pydantic manifest: :mod:`smarter.apps.guardrail.manifest.models.guardrail`.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import glob
import os

from pydantic import ValidationError

from smarter.apps.guardrail.const import DATA_PATH
from smarter.apps.guardrail.manifest.enum import (
    SAMGuardrailAction,
    SAMGuardrailStrategy,
)
from smarter.apps.guardrail.manifest.models.guardrail.model import SAMGuardrail
from smarter.apps.guardrail.manifest.models.guardrail.spec import (
    SAMGuardrailSpecConfig,
)
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import get_test_data

BUILTINS_PATH = os.path.join(DATA_PATH, "guardrails")
INVALID = (SAMValidationError, ValidationError, ValueError)


class TestGuardrailManifest(SmarterTestBase):
    """Test SAMGuardrail and SAMGuardrailSpecConfig."""

    def config(self, **fields) -> SAMGuardrailSpecConfig:
        """Return a spec.config: a keyword guardrail that blocks input, with fields overridden."""
        data = {"stage": "input", "strategy": "keyword", "keywords": ["forbidden"], "action": "block", **fields}
        return SAMGuardrailSpecConfig(**data)

    def assertInvalid(self, **fields):
        """Assert that a spec.config with these fields is rejected."""
        with self.assertRaises(INVALID):
            self.config(**fields)

    def test_builtin_manifests(self):
        """Test that every built-in guardrail manifest is valid, and that their names are unique."""
        filespecs = sorted(glob.glob(os.path.join(BUILTINS_PATH, "*.yaml")))
        self.assertGreaterEqual(len(filespecs), 18)
        names = []
        strategies = set()
        actions = set()
        for filespec in filespecs:
            with self.subTest(filespec=os.path.basename(filespec)):
                manifest = SAMGuardrail(**get_readonly_yaml_file(filespec))
                names.append(manifest.metadata.name)
                strategies.add(manifest.spec.config.strategy)
                actions.add(manifest.spec.config.action)
        self.assertEqual(len(names), len(set(names)))
        # the built-ins demonstrate every strategy, and every action but log
        self.assertEqual(strategies, set(SAMGuardrailStrategy.all()))
        self.assertEqual(actions, set(SAMGuardrailAction.all()) - {"log"})

    def test_test_manifests(self):
        """Test the test manifests."""
        manifest = SAMGuardrail(**get_test_data("guardrail.yaml"))
        self.assertEqual(manifest.spec.config.detectors, ["credit_card", "email"])
        judge = SAMGuardrail(**get_test_data("guardrail-llm-judge.yaml"))
        self.assertTrue(judge.spec.config.failClosed)

    def test_defaults(self):
        """Test the defaults of spec.config."""
        config = self.config()
        self.assertEqual(config.category, "custom")
        self.assertEqual(config.mode, "enforce")
        self.assertEqual(config.severity, 3)
        self.assertEqual(config.priority, 100)
        self.assertFalse(config.failClosed)
        self.assertTrue(config.isActive)
        self.assertEqual(config.flags, ["IGNORECASE"])

    def test_enums(self):
        """Test that the enumerated fields are validated, case insensitively."""
        self.assertEqual(self.config(stage="OUTPUT").stage, "output")
        self.assertEqual(self.config(action="Flag").action, "flag")
        for field in ("stage", "category", "strategy", "action", "mode"):
            with self.subTest(field=field):
                self.assertInvalid(**{field: "nonsense"})

    def test_regex(self):
        """Test that the regex strategy requires a valid pattern, that does not match empty text."""
        self.assertEqual(self.config(strategy="regex", pattern=r"\d+").pattern, r"\d+")
        self.assertInvalid(strategy="regex")
        self.assertInvalid(strategy="regex", pattern="([unclosed")
        self.assertInvalid(strategy="regex", pattern=r"\d*")
        self.assertInvalid(strategy="regex", pattern="x", flags=["VERBOSE"])

    def test_keyword(self):
        """Test that the keyword strategy requires keywords, which are deduplicated."""
        self.assertEqual(self.config(keywords=["a b", " a b ", "c"]).keywords, ["a b", "c"])
        self.assertInvalid(keywords=[])
        self.assertInvalid(keywords=["  "])

    def test_detector(self):
        """Test that the detector strategy requires known detectors."""
        self.assertEqual(self.config(strategy="detector", detectors=["IBAN"]).detectors, ["iban"])
        self.assertInvalid(strategy="detector")
        self.assertInvalid(strategy="detector", detectors=["passport"])

    def test_semantic(self):
        """Test that the semantic strategy requires reference texts."""
        self.config(strategy="semantic", referenceTexts=["an example"], threshold=0.9, action="flag")
        self.assertInvalid(strategy="semantic", action="flag")

    def test_moderation(self):
        """Test that the moderation strategy's categories are validated, and optional."""
        self.config(strategy="moderation", action="block")
        self.config(strategy="moderation", categories=["self-harm/intent"], action="escalate")
        self.assertInvalid(strategy="moderation", categories=["rudeness"])

    def test_llm_judge(self):
        """Test that the llm_judge strategy requires a prompt with {text}, and no other placeholder."""
        self.config(strategy="llm_judge", judgePrompt='Judge """{text}""" as JSON: {{"triggered": true}}')
        self.assertInvalid(strategy="llm_judge")
        self.assertInvalid(strategy="llm_judge", judgePrompt="Judge this.")
        self.assertInvalid(strategy="llm_judge", judgePrompt='Judge {text} as JSON: {"triggered": true}')
        self.assertInvalid(strategy="llm_judge", judgePrompt="Judge {text} for {user}.")

    def test_threshold(self):
        """Test that threshold is from 0 to 1, and only for the scored strategies."""
        self.config(strategy="moderation", threshold=0.0)
        self.assertInvalid(strategy="moderation", threshold=1.5)
        self.assertInvalid(threshold=0.5)

    def test_redact_and_transform(self):
        """Test that redact and transform require a strategy that locates matches, and transform a replacement."""
        self.config(action="redact")
        self.config(strategy="regex", pattern="x", action="transform", replacement="y")
        self.assertInvalid(strategy="moderation", action="redact")
        self.assertInvalid(strategy="llm_judge", judgePrompt="{text}", action="transform", replacement="y")
        self.assertInvalid(strategy="regex", pattern="x", action="transform")

    def test_bounds(self):
        """Test the bounds of severity, priority and message."""
        self.assertInvalid(severity=0)
        self.assertInvalid(severity=6)
        self.assertInvalid(priority=-1)
        self.assertInvalid(message="x" * 1001)

    def test_immutable(self):
        """Test that the manifest is immutable."""
        manifest = SAMGuardrail(**get_test_data("guardrail.yaml"))
        with self.assertRaises(ValidationError):
            manifest.spec.config.action = "block"
