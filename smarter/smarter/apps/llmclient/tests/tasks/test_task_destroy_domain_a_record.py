"""
Test :mod:`smarter.apps.llmclient.tasks.destroy_domain_a_record`.

The task is called directly, which runs it synchronously. The DNS service is mocked.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.infrastructure.services.dns import DNSZone
from smarter.apps.llmclient.tasks.destroy_domain_a_record import (
    destroy_domain_A_record,
)
from smarter.common.conf import smarter_settings
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.llmclient.tasks.destroy_domain_a_record"
HOSTNAME = "test-llmclient.api.example.com"
API_HOST_DOMAIN = "api.example.com"


class TestDestroyDomainARecord(SmarterTestBase):
    """Test that the A record of a hostname is destroyed."""

    def setUp(self):
        super().setUp()
        self.infrastructure = MagicMock()
        self.infrastructure.dns.resolve_domain.side_effect = lambda domain: domain
        self.infrastructure.dns.get_zone.return_value = DNSZone(id="Z0000000000TEST", name=API_HOST_DOMAIN)
        self.infrastructure.dns.delete_record.return_value = True
        for target, value in (("is_taskable", MagicMock(return_value=True)), ("infrastructure", self.infrastructure)):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)

    def test_is_a_celery_task(self):
        """It is queued with delay(), e.g. by llmhost, on the infrastructure queue."""
        self.assertTrue(callable(destroy_domain_A_record.delay))
        self.assertEqual(destroy_domain_A_record.queue, smarter_settings.infrastructure_tasks_celery_task_queue)

    def test_not_taskable(self):
        self.is_taskable.return_value = False
        destroy_domain_A_record(HOSTNAME, API_HOST_DOMAIN)
        self.infrastructure.dns.get_zone.assert_not_called()

    def test_zone_not_found(self):
        """Test that a missing zone is not created, and nothing is destroyed."""
        self.infrastructure.dns.get_zone.return_value = None
        destroy_domain_A_record(HOSTNAME, API_HOST_DOMAIN)
        self.infrastructure.dns.get_or_create_zone.assert_not_called()
        self.infrastructure.dns.delete_record.assert_not_called()

    def test_record_not_found(self):
        """Test that a hostname without an A record is not an error."""
        self.infrastructure.dns.delete_record.return_value = False
        self.assertIsNone(destroy_domain_A_record(HOSTNAME, API_HOST_DOMAIN))

    def test_record_destroyed(self):
        """Test that the hostname's A record is deleted from the parent domain's zone."""
        destroy_domain_A_record(HOSTNAME, API_HOST_DOMAIN, task_id="test-task")
        self.infrastructure.dns.get_zone.assert_called_once_with(API_HOST_DOMAIN)
        self.infrastructure.dns.delete_record.assert_called_once_with("Z0000000000TEST", HOSTNAME, "A")
