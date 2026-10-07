"""Test the LLMHost models: :mod:`smarter.apps.llmhost.models`."""

import datetime
from decimal import Decimal

from django.utils import timezone

from smarter.apps.llmhost.models import LLMHost, LLMHostEvent

from .base_classes import LLMHostTestBase


class TestLLMHostModels(LLMHostTestBase):
    """Test LLMHost and LLMHostEvent."""

    def test_fields_from_spec(self):
        """Test that the queried fields are copied from the spec, which is stored as it is."""
        llmhost = self.new_llmhost("test_models_fields")
        self.assertEqual(str(llmhost), "test_models_fields")
        self.assertEqual(
            (llmhost.model_source, llmhost.model_repository), ("huggingface", "meta-llama/Llama-3.1-8B-Instruct")
        )
        self.assertEqual((llmhost.inference_engine, llmhost.gpu_count, llmhost.replicas), ("vllm", 1, 1))
        self.assertEqual(llmhost.served_model_name, "llama-3.1-8b-instruct")
        self.assertTrue(llmhost.supports_function_calling)
        self.assertEqual(llmhost.cost_per_hour, Decimal("1.212"))
        self.assertEqual(llmhost.spec["engine"]["contextLength"], 16384)
        self.assertEqual(llmhost.status, "inactive")
        self.assertFalse(llmhost.is_deployed)

    def test_uptime_and_cost(self):
        """Test that uptime and estimated cost accrue only while the LLMHost is deployed."""
        llmhost = self.new_llmhost("test_models_cost")
        self.assertIsNone(llmhost.uptime)
        self.assertIsNone(llmhost.estimated_cost)
        llmhost.status = "active"
        llmhost.deployed_at = timezone.now() - datetime.timedelta(hours=10)
        self.assertTrue(llmhost.is_deployed)
        self.assertAlmostEqual(llmhost.uptime_hours, 10, places=2)
        self.assertAlmostEqual(float(llmhost.estimated_cost), 12.12, places=2)
        # cost_per_hour is per replica.
        llmhost.replicas = 2
        self.assertAlmostEqual(float(llmhost.estimated_cost), 24.24, places=2)
        llmhost.cost_per_hour = None
        self.assertIsNone(llmhost.estimated_cost)
        llmhost.status = "inactive"
        self.assertIsNone(llmhost.uptime_hours)

    def test_events(self):
        """Test that events record the status, and survive the LLMHost's deletion."""
        llmhost = self.new_llmhost("test_models_events")
        event = llmhost.record_event("launched", "Applied", {"resources": ["Deployment/x"]})
        self.assertEqual(
            (event.status, event.llmhost_name, event.details["resources"]), ("inactive", llmhost.name, ["Deployment/x"])
        )
        self.assertIn("launched", str(event))
        self.assertEqual(list(llmhost.events.all()), [event])  # type: ignore[attr-defined]
        LLMHost.objects.filter(pk=llmhost.pk).delete()
        event.refresh_from_db()
        self.assertIsNone(event.llmhost)
        self.assertEqual(LLMHostEvent.objects.filter(llmhost_name="test_models_events").count(), 1)
