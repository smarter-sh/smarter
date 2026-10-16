"""
Test :mod:`smarter.apps.llmclient.tasks.delete_orphan_dns_records`, and its management command.

The task is called directly, which runs it synchronously. The DNS service is mocked, and so are the
querysets of LLMClients and LLMHosts, so nothing reaches Route53.
"""

import importlib
import io
from unittest.mock import MagicMock, patch

from django.core.management import call_command

from smarter.apps.infrastructure.services.dns import DNSRecord, DNSZone
from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.llmclient.tasks.delete_orphan_dns_records"
# the tasks package exports the task with the module's name, so the module is imported by its path.
task_module = importlib.import_module(MODULE)
delete_orphan_dns_records = task_module.delete_orphan_dns_records

DOMAIN = "api.example.com"
ACCOUNT = "3141-5926-5359"
LIVE = f"live.{ACCOUNT}.{DOMAIN}"
ORPHAN = f"deleted.{ACCOUNT}.{DOMAIN}"
ZONE = DNSZone(id="Z0000000000TEST", name=DOMAIN)


def a_record(name: str, record_type: str = "A") -> DNSRecord:
    return DNSRecord(name=name, type=record_type, values=["192.0.2.1"])


class TestDeleteOrphanDNSRecords(SmarterTestBase):
    """Test that only the A records of LLMClient-shaped hosts that nothing uses are deleted."""

    def setUp(self):
        super().setUp()
        self.infrastructure = MagicMock()
        dns = self.infrastructure.dns
        dns.get_zone.return_value = ZONE
        dns.delete_record.return_value = True
        dns.list_records.return_value = [
            a_record(LIVE),
            a_record(ORPHAN),
            a_record(DOMAIN),  # the API domain's own record
            a_record(f"*.{ACCOUNT}.{DOMAIN}"),  # a wildcard
            a_record(f"deleted.{ACCOUNT}.alpha.{DOMAIN}"),  # another environment's host
            a_record(f"_acme-challenge.deleted.{ACCOUNT}.{DOMAIN}", "TXT"),
            a_record(f"deleted.{ACCOUNT}.{DOMAIN}", "TXT"),
            a_record(f"deleted.not-an-account.{DOMAIN}"),
        ]
        self.dns = dns
        settings = MagicMock(
            environment=SmarterEnvironments.PROD,
            environment_api_domain=DOMAIN,
            infrastructure_tasks_celery_task_queue=smarter_settings.infrastructure_tasks_celery_task_queue,
        )
        for target, value in (
            ("infrastructure", self.infrastructure),
            ("is_taskable", MagicMock(return_value=True)),
            ("live_hosts", MagicMock(return_value={LIVE})),
            ("smarter_settings", settings),
        ):
            patcher = patch(f"{MODULE}.{target}", value)
            setattr(self, target, patcher.start())
            self.addCleanup(patcher.stop)

    def test_is_a_celery_task(self):
        """Test that Celery Beat can queue it on the infrastructure queue."""
        self.assertTrue(callable(delete_orphan_dns_records.delay))
        self.assertEqual(delete_orphan_dns_records.queue, smarter_settings.infrastructure_tasks_celery_task_queue)

    def test_deletes_only_orphans(self):
        """Test that the only orphan is deleted, and nothing else in the zone is touched."""
        self.assertEqual(delete_orphan_dns_records(), [ORPHAN])
        self.dns.get_zone.assert_called_once_with(DOMAIN)
        self.dns.delete_record.assert_called_once_with(ZONE.id, ORPHAN, "A")

    def test_dry_run(self):
        """Test that a dry run returns the orphans, and deletes nothing."""
        self.assertEqual(delete_orphan_dns_records(dry_run=True), [ORPHAN])
        self.dns.delete_record.assert_not_called()

    def test_local_environment(self):
        """Test that it never runs where the API domain's zone is shared, e.g. in local development."""
        for environment in (SmarterEnvironments.LOCAL, "staging"):
            self.smarter_settings.environment = environment
            self.assertEqual(delete_orphan_dns_records(), [])
        self.dns.get_zone.assert_not_called()

    def test_not_taskable(self):
        self.is_taskable.return_value = False
        self.assertEqual(delete_orphan_dns_records(), [])
        self.dns.get_zone.assert_not_called()

    def test_no_zone(self):
        self.dns.get_zone.return_value = None
        self.assertEqual(delete_orphan_dns_records(), [])
        self.dns.list_records.assert_not_called()

    def test_live_hosts_unknown(self):
        """Test that nothing is deleted when the live hosts cannot be determined."""
        self.live_hosts.side_effect = task_module.OrphanDNSRecordsError("the database has no LLMClients.")
        with patch(f"{MODULE}.logger") as logger:
            self.assertEqual(delete_orphan_dns_records(), [])
        logger.error.assert_called_once()
        self.dns.list_records.assert_not_called()

    def test_deletions_are_capped(self):
        """Test that one run deletes at most MAX_DELETIONS_PER_RUN records."""
        self.dns.list_records.return_value = [a_record(f"deleted{i}.{ACCOUNT}.{DOMAIN}") for i in range(60)]
        deleted = delete_orphan_dns_records()
        self.assertEqual(len(deleted), task_module.MAX_DELETIONS_PER_RUN)
        self.assertEqual(self.dns.delete_record.call_count, task_module.MAX_DELETIONS_PER_RUN)

    def test_failed_deletion_continues(self):
        """Test that a record that cannot be deleted is logged, and the others are still deleted."""
        other = f"other.{ACCOUNT}.{DOMAIN}"
        self.dns.list_records.return_value = [a_record(ORPHAN), a_record(other)]
        self.dns.delete_record.side_effect = [RuntimeError("throttled"), True]
        with patch(f"{MODULE}.logger") as logger:
            self.assertEqual(delete_orphan_dns_records(), [other])
        logger.error.assert_called_once()

    def test_already_deleted(self):
        """Test that a record that is already gone is not reported as deleted."""
        self.dns.delete_record.return_value = False
        self.assertEqual(delete_orphan_dns_records(), [])

    def test_command(self):
        """Test that the command lists what a dry run would delete, and what a real run deleted."""
        output = io.StringIO()
        call_command("delete_orphan_dns_records", "--dry-run", stdout=output, stderr=io.StringIO())
        self.assertIn(f"Would delete the orphaned A record {ORPHAN}", output.getvalue())
        self.dns.delete_record.assert_not_called()
        output = io.StringIO()
        call_command("delete_orphan_dns_records", stdout=output, stderr=io.StringIO())
        self.assertIn("Deleted 1 orphaned A records.", output.getvalue())


class TestLiveHosts(SmarterTestBase):
    """Test that every LLMClient's and LLMHost's host is live, and that an unknown one stops the sweep."""

    def setUp(self):
        super().setUp()
        llmclient = MagicMock(default_host=f"Live.{ACCOUNT}.{DOMAIN}.")
        llmhost = MagicMock(pk=7, user_profile=MagicMock(account=MagicMock(account_number=ACCOUNT)))
        llmhost.name = "llama"
        self.llmclients = patch(f"{MODULE}.LLMClient")
        self.llmclients.start().objects.select_related.return_value = [llmclient]
        self.addCleanup(self.llmclients.stop)
        self.llmhosts = patch("smarter.apps.llmhost.models.LLMHost")
        self.llmhosts.start().objects.select_related.return_value = [llmhost]
        self.addCleanup(self.llmhosts.stop)
        self.llmhost = llmhost

    def test_live_hosts(self):
        from smarter.apps.llmhost.services.service import LLMHostService

        llmhost_host = LLMHostService.default_hostname(self.llmhost, LLMHostService.base_name(self.llmhost))
        self.assertEqual(task_module.live_hosts(), {f"live.{ACCOUNT}.{DOMAIN}", llmhost_host.lower()})

    def test_no_llmclients(self):
        """Test that an empty database is refused, because every record would look orphaned."""
        with patch(f"{MODULE}.LLMClient") as llmclients:
            llmclients.objects.select_related.return_value = []
            with self.assertRaises(task_module.OrphanDNSRecordsError):
                task_module.live_hosts()

    def test_host_cannot_be_computed(self):
        """Test that a host that cannot be computed is refused, because its record would look orphaned."""
        self.llmhost.pk = None  # LLMHostService.base_name() refuses an unsaved LLMHost
        with self.assertRaises(task_module.OrphanDNSRecordsError):
            task_module.live_hosts()

    def test_host_pattern(self):
        pattern = task_module.host_pattern(DOMAIN)
        self.assertTrue(pattern.match(ORPHAN))
        for name in (f"*.{ACCOUNT}.{DOMAIN}", f"x.{ACCOUNT}.alpha.{DOMAIN}", f"x.{ACCOUNT}.{DOMAIN}.evil.com", DOMAIN):
            self.assertIsNone(pattern.match(name), name)
