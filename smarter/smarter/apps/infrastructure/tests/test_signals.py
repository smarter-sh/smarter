"""Test the service base class, the signals' receivers, and the ledger they keep, InfrastructureResource."""

from unittest.mock import patch

from django.test import RequestFactory

from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.apps.infrastructure.admin import InfrastructureResourceAdmin
from smarter.apps.infrastructure.exceptions import (
    InfrastructureConfigurationError,
    InfrastructureNotReadyError,
    SmarterInfrastructureError,
)
from smarter.apps.infrastructure.models import InfrastructureResource
from smarter.apps.infrastructure.services import refuse_in_unit_tests
from smarter.apps.infrastructure.services.base import InfrastructureService
from smarter.apps.infrastructure.signals import (
    billable_resource_created,
    billable_resource_creating,
    billable_resource_destroyed,
    billable_resource_destroying,
    email_failed,
    email_sent,
    infrastructure_authenticated,
    infrastructure_authentication_failed,
    infrastructure_connected,
    infrastructure_connection_failed,
    infrastructure_operation_failed,
    resource_applied,
    resource_created,
    resource_destroyed,
)
from smarter.lib.unittest import running_unit_tests

from .base import InfrastructureTestBase

RECEIVERS = "smarter.apps.infrastructure.receivers"


class FakeService(InfrastructureService):
    service_name = "fake"

    def __init__(self, ready: bool = True):
        super().__init__(provider_name="test")
        self._ready = ready

    @property
    def ready(self) -> bool:
        return self._ready


class TestInfrastructureService(InfrastructureTestBase):
    """Test the service base class: the unit test guard, readiness, signals and error translation."""

    def test_refuse_in_unit_tests(self):
        self.assertTrue(running_unit_tests())
        with self.assertRaises(InfrastructureConfigurationError):
            refuse_in_unit_tests("the moon")
        refuse_in_unit_tests("the moon", allow_in_tests=True)

    def test_require_ready(self):
        FakeService().require_ready()
        with self.assertRaises(InfrastructureNotReadyError):
            FakeService(ready=False).require_ready()
        self.assertEqual(str(FakeService()), "test.fake")

    def test_connection_state(self):
        events = self.capture(infrastructure_connected, infrastructure_connection_failed)
        service = FakeService()
        for connected in (True, True, False, False, True):
            service.connection_state(connected, error="down")
        self.assertEqual(
            [signal for signal, _ in events],
            [infrastructure_connected, infrastructure_connection_failed, infrastructure_connected],
        )
        self.assertEqual(self.sent(events, infrastructure_connection_failed)[0]["error"], "down")

    def test_resource_lifecycle_signals(self):
        """Billable resources have a signal before and after; others only after."""
        events = self.capture(
            billable_resource_creating, billable_resource_created, resource_created,
            billable_resource_destroying, billable_resource_destroyed, resource_destroyed,
        )  # fmt: skip
        service = FakeService()
        for billable in (True, False):
            resource = service.creating_resource("thing", f"name-{billable}", billable=billable)
            service.created_resource(resource, resource_id="id-1")
            resource = service.destroying_resource("thing", f"name-{billable}", "id-1", billable=billable)
            service.destroyed_resource(resource)
        self.assertEqual(
            [signal for signal, _ in events],
            [
                billable_resource_creating,
                billable_resource_created,
                billable_resource_destroying,
                billable_resource_destroyed,
                resource_created,
                resource_destroyed,
            ],
        )
        for _, kwargs in events:
            self.assertEqual((kwargs["service"], kwargs["provider"], kwargs["sender"]), ("fake", "test", FakeService))

    def test_operation(self):
        events = self.capture(infrastructure_operation_failed)
        service = FakeService()
        with service.operation("ok"):
            pass
        with self.assertRaises(SmarterInfrastructureError) as context:
            with service.operation("boom"):
                raise ValueError("sdk error")
        self.assertIsInstance(context.exception.__cause__, ValueError)
        with self.assertRaises(InfrastructureNotReadyError):
            with service.operation("not_ready"):
                raise InfrastructureNotReadyError("not ready")
        self.assertEqual(
            [e["operation"] for e in self.sent(events, infrastructure_operation_failed)], ["boom", "not_ready"]
        )


class TestReceivers(InfrastructureTestBase):
    """Test that the receivers log every signal, and record resources in the ledger."""

    def send(self, signal, **kwargs):
        signal.send(sender=FakeService, service="dns", provider="test", **kwargs)

    def test_ledger(self):
        resource = {"resource_type": "dns.zone", "resource_name": "ledger.example.com"}
        self.send(billable_resource_creating, **resource)
        self.send(billable_resource_created, resource_id="Z1", **resource)
        row = InfrastructureResource.objects.get(provider="test", **resource)
        self.assertEqual((row.status, row.billable, row.resource_id, row.service), ("active", True, "Z1", "dns"))
        self.assertIn("ledger.example.com", str(row))

        # created again, e.g. an update, is the same row.
        self.send(billable_resource_created, resource_id="Z1", **resource)
        self.assertEqual(InfrastructureResource.objects.filter(provider="test", **resource).count(), 1)

        self.send(billable_resource_destroying, resource_id="Z1", **resource)
        self.send(billable_resource_destroyed, resource_id="Z1", **resource)
        row.refresh_from_db()
        self.assertEqual(row.status, InfrastructureResource.Status.DESTROYED)
        self.assertIsNotNone(row.destroyed_at)

        # re-created after it was destroyed, it is a new row.
        self.send(billable_resource_created, resource_id="Z2", **resource)
        self.assertEqual(InfrastructureResource.objects.filter(provider="test", **resource).count(), 2)

    def test_ledger_of_unbillable_resources(self):
        resource = {"resource_type": "dns.record", "resource_name": "www.ledger.example.com A"}
        self.send(resource_created, resource_id="Z1", **resource)
        self.assertFalse(InfrastructureResource.objects.get(provider="test", **resource).billable)
        self.send(resource_destroyed, resource_id="Z1", **resource)
        self.assertEqual(InfrastructureResource.objects.get(provider="test", **resource).status, "destroyed")

    def test_destroyed_resource_that_the_ledger_does_not_know(self):
        """E.g.

        a resource created before the ledger existed.
        """
        resource = {"resource_type": "dns.record", "resource_name": "old.ledger.example.com A"}
        self.send(resource_destroyed, resource_id=None, **resource)
        row = InfrastructureResource.objects.get(provider="test", **resource)
        self.assertEqual((row.status, row.resource_id), ("destroyed", ""))

    def test_ledger_failure_does_not_fail_the_operation(self):
        with patch.object(InfrastructureResource, "record_created", side_effect=RuntimeError("database down")):
            with patch(f"{RECEIVERS}.logger") as logger:
                self.send(resource_created, resource_type="dns.record", resource_name="x", resource_id="Z1")
        logger.error.assert_called_once()

    def test_logged(self):
        """Every signal is logged: billable resources as warnings, and failures as errors."""
        with patch(f"{RECEIVERS}.logger") as logger:
            self.send(infrastructure_authenticated, identity={"Account": "1"})
            self.send(infrastructure_connected)
            self.send(resource_applied, kinds=["Ingress"])
            self.send(email_sent, subject="s", recipients=["a@example.com"])
            self.assertEqual(logger.info.call_count, 4)
            self.send(billable_resource_creating, resource_type="t", resource_name="n")
            self.assertEqual(logger.warning.call_count, 1)
            self.send(infrastructure_authentication_failed, error="e")
            self.send(infrastructure_connection_failed, error="e")
            self.send(infrastructure_operation_failed, operation="o", error="e")
            self.send(email_failed, subject="s", recipients=["a@example.com"], error="e")
            self.assertEqual(logger.error.call_count, 4)


class TestAdmin(InfrastructureTestBase):
    """Test that the ledger is in the admin, read-only."""

    def test_admin(self):
        self.assertIn(
            InfrastructureResource, smarter_restricted_admin_site._registry
        )  # pylint: disable=protected-access
        admin = InfrastructureResourceAdmin(InfrastructureResource, smarter_restricted_admin_site)
        request = RequestFactory().get("/")
        self.assertFalse(admin.has_add_permission(request))
        self.assertFalse(admin.has_change_permission(request))
        self.assertIn("resource_name", admin.readonly_fields)
