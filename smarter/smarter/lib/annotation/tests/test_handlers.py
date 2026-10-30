"""Test annotation handlers and the annotations_changed signal."""

from decimal import Decimal
from unittest.mock import patch

from smarter.apps.account.models import Budget
from smarter.lib.annotation import handlers
from smarter.lib.annotation.contract import AnnotationChange
from smarter.lib.annotation.handlers import (
    AnnotationEvent,
    annotation_handler,
    handlers_for_key,
    register_annotation_handler,
    unregister_annotation_handler,
)
from smarter.lib.annotation.signals import annotations_changed
from smarter.lib.annotation.validation import SmarterAnnotationError
from smarter.lib.unittest.base_classes import SmarterTestBase


def outside_handler(event: AnnotationEvent) -> None:
    """A handler that pretends to live outside Smarter."""


outside_handler.__module__ = "acme_integration.handlers"


class TestAnnotationHandlers(SmarterTestBase):
    """Test that handlers see their own prefix's changes, after commit, and can't break a save."""

    def setUp(self):
        super().setUp()
        self.domain = f"acme-{self.hash_suffix}.com"
        self.events: list[AnnotationEvent] = []
        register_annotation_handler(self.domain, self.events.append)
        self.addCleanup(unregister_annotation_handler, self.domain, self.events.append)

    def budget(self, **annotations) -> Budget:
        """A throwaway Budget."""
        budget = Budget.objects.create(
            name=f"test_handlers_{self.hash_suffix}_{Budget.objects.count()}",
            periodic_limit=Decimal("1"),
            annotations=annotations,
        )
        self.addCleanup(lambda: Budget.objects.filter(pk=budget.pk).delete())
        return budget

    def test_handler_sees_its_prefix_and_subdomains(self):
        """Test that a handler is called for its domain and subdomains, once per change, and not for others."""
        budget = self.budget(**{f"{self.domain}/a": "1", f"crm.{self.domain}/b": "2", "other.com/c": "3"})
        self.assertEqual(
            [(e.change.key, e.change.action, e.object_id, e.model_label) for e in self.events],
            [
                (f"{self.domain}/a", "added", budget.pk, "account.Budget"),
                (f"crm.{self.domain}/b", "added", budget.pk, "account.Budget"),
            ],
        )
        self.assertTrue(all(e.instance is budget and not e.resource_deleted for e in self.events))

    def test_handler_sees_deletion(self):
        """Test that deleting a resource reports its annotations as removed, with resource_deleted."""
        budget = self.budget(**{f"{self.domain}/a": "1"})
        pk = budget.pk
        self.events.clear()
        budget.delete()
        self.assertEqual(len(self.events), 1)
        self.assertEqual((self.events[0].change.action, self.events[0].object_id), ("removed", pk))
        self.assertTrue(self.events[0].resource_deleted)

    def test_failing_handler_is_isolated(self):
        """Test that a handler's exception is logged, and the other handlers and the save go on."""

        def broken(event: AnnotationEvent) -> None:
            raise RuntimeError("legacy system is down")

        register_annotation_handler(self.domain, broken)
        self.addCleanup(unregister_annotation_handler, self.domain, broken)
        with patch.object(handlers.logger, "exception") as logged:
            budget = self.budget(**{f"{self.domain}/a": "1"})
        logged.assert_called_once()
        self.assertEqual(len(self.events), 1)
        self.assertEqual(budget.annotations, {f"{self.domain}/a": "1"})

    def test_signal(self):
        """Test that annotations_changed is sent with every change, and a failing receiver is logged."""
        received = []

        def receiver(sender, **kwargs):
            received.append((sender, kwargs["changes"], kwargs["resource_deleted"]))
            raise RuntimeError("receiver failed")

        annotations_changed.connect(receiver)
        self.addCleanup(annotations_changed.disconnect, receiver)
        with patch.object(handlers.logger, "error") as logged:
            self.budget(**{"other.com/c": "3"})
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0], Budget)
        self.assertEqual([c.key for c in received[0][1]], ["other.com/c"])
        self.assertFalse(received[0][2])
        logged.assert_called_once()

    def test_register(self):
        """Test the decorator, duplicate registrations and unregistering."""
        domain = f"crm-{self.hash_suffix}.com"

        @annotation_handler(domain)
        def handler(event: AnnotationEvent) -> None:
            pass

        register_annotation_handler(domain, handler)
        self.assertEqual(handlers_for_key(f"{domain}/x"), [handler])
        self.assertEqual(handlers_for_key("no-prefix"), [])
        unregister_annotation_handler(domain, handler)
        unregister_annotation_handler(domain, handler)
        self.assertEqual(handlers_for_key(f"{domain}/x"), [])

    def test_register_errors(self):
        """Test that a prefix must be a domain, and that only Smarter handles smarter.sh."""
        with self.assertRaises(SmarterAnnotationError):
            register_annotation_handler("Not A Domain", outside_handler)
        for prefix in ("smarter.sh", "llmclient.smarter.sh"):
            with self.subTest(prefix=prefix), self.assertRaises(SmarterAnnotationError):
                register_annotation_handler(prefix, outside_handler)

        def smarter_handler(event: AnnotationEvent) -> None:
            pass

        register_annotation_handler("smarter.sh", smarter_handler)
        self.addCleanup(unregister_annotation_handler, "smarter.sh", smarter_handler)
        self.assertIn(smarter_handler, handlers_for_key("smarter.sh/x"))

    def test_no_changes_no_dispatch(self):
        """Test that nothing is sent without changes, or for an unsaved resource."""
        change = AnnotationChange(key=f"{self.domain}/a", old_value=None, new_value="1")
        handlers.dispatch_annotation_changes(Budget(), [])
        handlers.dispatch_annotation_changes(Budget(), [change])
        self.assertEqual(self.events, [])
