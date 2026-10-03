# pylint: disable=wrong-import-position
"""
Test SAMGuardrailBroker.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import os

from smarter.apps.guardrail.manifest.brokers.guardrail import SAMGuardrailBroker
from smarter.apps.guardrail.manifest.models.guardrail.model import SAMGuardrail
from smarter.apps.guardrail.models import Guardrail, GuardrailEvent
from smarter.apps.llmclient.manifest.brokers.llmclient import SAMLLMClientBroker
from smarter.apps.llmclient.models import LLMClient, LLMClientGuardrails
from smarter.lib import json, logging
from smarter.lib.manifest.broker import (
    SAMBrokerError,
    SAMBrokerErrorDependencies,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

logger = logging.getLogger(__name__)

GUARDRAIL_NAME = "test_guardrail"


# pylint: disable=too-many-public-methods
class TestSmarterGuardrailBroker(TestSAMBrokerBaseClass):
    """Test the Smarter SAMGuardrailBroker."""

    @classmethod
    def tearDownClass(cls):
        Guardrail.objects.filter(user_profile__account=cls.account).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("guardrail.yaml")
        self.addCleanup(Guardrail.objects.filter(user_profile=self.user_profile).delete)

    @property
    def SAMBrokerClass(self) -> type[SAMGuardrailBroker]:
        return SAMGuardrailBroker

    @property
    def broker(self) -> SAMGuardrailBroker:
        return super().broker  # type: ignore

    def broker_for(self, filename: str) -> SAMGuardrailBroker:
        """Return a broker for a manifest in ./data."""
        with open(self.get_data_full_filepath(filename), encoding="utf-8") as f:
            return SAMGuardrailBroker(request=self.request, loader=SAMLoader(manifest=f.read()))

    def guardrail(self, name: str = GUARDRAIL_NAME) -> Guardrail:
        """Return the user's Guardrail."""
        return Guardrail.objects.get(user_profile=self.user_profile, name=name)

    def test_broker_initialization(self):
        """Test the broker's kind and model classes, and that it creates nothing lazily."""
        self.assertTrue(self.ready)
        self.assertEqual(self.broker.kind, "Guardrail")
        self.assertIs(self.broker.ORMModelClass, Guardrail)
        self.assertIsInstance(self.broker.manifest, SAMGuardrail)
        self.assertIsNone(self.broker.guardrail)

    def test_example_manifest(self):
        """Test that example_manifest() returns a valid manifest."""
        response = self.broker.example_manifest(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        SAMGuardrail(**json.loads(response.content)["data"])

    def test_apply(self):
        """Test that apply() creates the Guardrail, with the strategy's fields in its config."""
        response = self.broker.apply(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        g = self.guardrail()
        self.assertEqual(
            (g.stage, g.category, g.strategy, g.action, g.mode), ("both", "pii", "detector", "redact", "enforce")
        )
        self.assertEqual(g.config, {"detectors": ["credit_card", "email"]})
        self.assertEqual(g.replacement, "[REDACTED {label}]")
        self.assertEqual((g.severity, g.priority), (4, 10))
        self.assertEqual(sorted(g.tags_list), ["pii", "test"])

    def test_apply_llm_judge(self):
        """Test that apply() stores the llm_judge fields, and failClosed."""
        self.broker_for("guardrail-llm-judge.yaml").apply(self.request, **self.kwargs)
        g = self.guardrail("test_guardrail_llm_judge")
        self.assertEqual(sorted(g.config), ["judgePrompt", "model", "provider"])
        self.assertIn("{text}", g.config["judgePrompt"])
        self.assertTrue(g.fail_closed)
        self.assertEqual(g.threshold, 0.8)

    def test_apply_updates(self):
        """Test that applying again updates the Guardrail, rather than creating another."""
        self.broker.apply(self.request, **self.kwargs)
        pk = self.guardrail().pk
        self.broker_for("guardrail.yaml").apply(self.request, **self.kwargs)
        self.assertEqual(Guardrail.objects.filter(user_profile=self.user_profile, name=GUARDRAIL_NAME).count(), 1)
        self.assertEqual(self.guardrail().pk, pk)

    def test_describe(self):
        """Test that describe() round trips the manifest, and reports the status."""
        self.broker.apply(self.request, **self.kwargs)
        g = self.guardrail()
        GuardrailEvent.objects.create(
            guardrail=g,
            guardrail_name=g.name,
            stage="input",
            category="pii",
            strategy="detector",
            action="redact",
            mode="enforce",
            disposition="redacted",
        )
        response = self.broker_for("guardrail.yaml").describe(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        data = json.loads(response.content)["data"]
        config = data["spec"]["config"]
        self.assertEqual(config["detectors"], ["credit_card", "email"])
        self.assertEqual(config["replacement"], "[REDACTED {label}]")
        self.assertEqual(data["status"]["triggered"], 1)
        self.assertEqual(data["status"]["blocked"], 0)
        self.assertEqual(data["status"]["dependencies"], [])
        SAMGuardrail(**data)

    def test_describe_not_found(self):
        """Test that describe() fails for a Guardrail that does not exist."""
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker.describe(self.request, **self.kwargs)

    def test_get(self):
        """Test that get() lists the user's Guardrails, and the built-in ones."""
        self.broker.apply(self.request, **self.kwargs)
        response = self.broker.get(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        names = [item["name"] for item in json.loads(response.content)["data"]["data"]["items"]]
        self.assertIn(GUARDRAIL_NAME, names)

    def test_delete(self):
        """Test that delete() deletes the Guardrail."""
        self.broker.apply(self.request, **self.kwargs)
        response = self.broker_for("guardrail.yaml").delete(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertFalse(Guardrail.objects.filter(user_profile=self.user_profile, name=GUARDRAIL_NAME).exists())
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker_for("guardrail.yaml").delete(self.request, **self.kwargs)

    def attach_to_llmclient(self, name: str = "test_guardrail_dependency") -> LLMClient:
        """Return a new LLMClient that uses the Guardrail."""
        llmclient = LLMClient.objects.create(name=name, user_profile=self.user_profile)
        self.addCleanup(llmclient.delete)
        LLMClientGuardrails.objects.create(llmclient=llmclient, guardrail=self.guardrail())
        return llmclient

    def test_dependencies_none(self):
        """Test that dependencies() is empty for a Guardrail that no LLMClient uses."""
        self.broker.apply(self.request, **self.kwargs)
        self.assertEqual(self.broker_for("guardrail.yaml").dependencies(), [])

    def test_dependencies(self):
        """Test that dependencies() returns a broker for each LLMClient that uses the Guardrail."""
        self.broker.apply(self.request, **self.kwargs)
        llmclient = self.attach_to_llmclient()
        dependencies = self.broker_for("guardrail.yaml").dependencies()
        self.assertEqual(len(dependencies), 1)
        self.assertIsInstance(dependencies[0], SAMLLMClientBroker)
        self.assertEqual(dependencies[0].name, llmclient.name)
        self.assertEqual(dependencies[0].llmclient, llmclient)

    def test_dependencies_memoized(self):
        """Test that dependencies() queries once per broker instance."""
        self.broker.apply(self.request, **self.kwargs)
        broker = self.broker_for("guardrail.yaml")
        dependencies = broker.dependencies()
        self.attach_to_llmclient()
        self.assertIs(broker.dependencies(), dependencies)
        self.assertEqual(len(self.broker_for("guardrail.yaml").dependencies()), 1)

    def test_delete_ignores_memoized_dependencies(self):
        """Test that delete() checks the current dependencies, not those memoized before an LLMClient used it."""
        self.broker.apply(self.request, **self.kwargs)
        broker = self.broker_for("guardrail.yaml")
        self.assertEqual(broker.dependencies(), [])
        self.attach_to_llmclient()
        with self.assertRaises(SAMBrokerErrorDependencies):
            broker.delete(self.request, **self.kwargs)

    def test_describe_dependencies(self):
        """Test that describe() reports the LLMClients that use the Guardrail in status.dependencies."""
        self.broker.apply(self.request, **self.kwargs)
        response = self.broker_for("guardrail.yaml").describe(self.request, **self.kwargs)
        self.assertEqual(json.loads(response.content)["data"]["status"]["dependencies"], [])
        llmclient = self.attach_to_llmclient()
        response = self.broker_for("guardrail.yaml").describe(self.request, **self.kwargs)
        data = json.loads(response.content)["data"]
        self.assertEqual(data["status"]["dependencies"], [{"kind": "LLMClient", "name": llmclient.name}])
        SAMGuardrail(**data)

    def test_delete_refused_while_used(self):
        """Test that delete() refuses to delete a Guardrail that an LLMClient uses, and names the LLMClient."""
        self.broker.apply(self.request, **self.kwargs)
        llmclient = self.attach_to_llmclient()
        with self.assertRaises(SAMBrokerErrorDependencies) as context:
            self.broker_for("guardrail.yaml").delete(self.request, **self.kwargs)
        self.assertIn(f"LLMClient {llmclient.name}", str(context.exception))
        self.assertTrue(Guardrail.objects.filter(user_profile=self.user_profile, name=GUARDRAIL_NAME).exists())

    def test_not_implemented(self):
        """Test that deploy, undeploy and prompt are not implemented."""
        for method in (self.broker.deploy, self.broker.undeploy, self.broker.prompt):
            with (
                self.subTest(method=method.__name__),
                self.assertRaises((SAMBrokerErrorNotImplemented, SAMBrokerError)),
            ):
                method(self.request, **self.kwargs)
