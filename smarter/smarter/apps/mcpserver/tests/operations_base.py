"""
Test harness of the Smarter Operations MCP server.

:class:`OperationsTestBase` installs fakes of everything that the operations tools read, so that
nothing reaches real infrastructure:

- an in-memory log service, with the lines of ./data/pod-logs.yaml, timed relative to now, in place of Loki,
- an in-memory Kubernetes cluster, with the resources of ./data/cluster.yaml, in the environment's
  namespace, whose warning events happened a few minutes ago, in place of kubectl,
- the in-memory cloud provider, in place of AWS.

Its staff user is the account mixin's admin user, and every audit row that a test writes is deleted
afterwards.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import copy
import os
from datetime import datetime, timedelta, timezone

from smarter.apps.account.tests.factories import platform_staff_profile_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.infrastructure.providers import configure_provider
from smarter.apps.infrastructure.providers.memory import InMemoryProvider
from smarter.apps.infrastructure.services import (
    InMemoryKubernetesService,
    InMemoryLogService,
    LogLine,
    configure_kubernetes,
    configure_logs,
)
from smarter.apps.mcpserver.models import OperationsToolCall
from smarter.common.conf import smarter_settings
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.typing import SmarterDictType

HERE = os.path.abspath(os.path.dirname(__file__))
POD_LOGS = os.path.join(HERE, "data", "pod-logs.yaml")
CLUSTER = os.path.join(HERE, "data", "cluster.yaml")
EVENT_MINUTES_AGO = 5
"""How long before the test the test cluster's warning events last happened."""
TICKET = "HD-1234 user reports errors"


def pod_logs(now: datetime) -> list[LogLine]:
    """
    Return the test pod logs, from ./data/pod-logs.yaml.

    :param now: The time that each line's ``minutes_ago`` counts back from.
    """
    return [
        LogLine(
            timestamp=now - timedelta(minutes=line["minutes_ago"]),
            component=line["component"],
            pod=line["pod"],
            container=line["component"],
            line=line["line"],
        )
        for line in get_readonly_yaml_file(POD_LOGS)["lines"]
    ]


def cluster_items(now: datetime) -> dict[str, list[SmarterDictType]]:
    """
    Return the test cluster's resources, from ./data/cluster.yaml, keyed by kind.

    Each namespaced resource is moved into the environment's namespace, and each event's
    ``lastTimestamp`` is set to :data:`EVENT_MINUTES_AGO` minutes before ``now``.

    :param now: The time of the test.
    """
    items = copy.deepcopy(get_readonly_yaml_file(CLUSTER))
    namespace = smarter_settings.environment_namespace
    last_seen = now - timedelta(minutes=EVENT_MINUTES_AGO)
    for resources in items.values():
        for resource in resources:
            metadata = resource["metadata"]
            if "namespace" in metadata:
                metadata["namespace"] = namespace
    for event in items["event"]:
        event["lastTimestamp"] = last_seen.strftime("%Y-%m-%dT%H:%M:%SZ")
    return items


class OperationsTestBase(TestAccountMixin):
    """
    The in-memory logs, cluster and cloud provider, and the audit rows cleaned up.

    The account mixin's admin user is staff of its own test account. A profile in the Smarter
    account makes them one of the platform's staff, as the server requires.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.platform_staff_profile = platform_staff_profile_factory(cls.admin_user)

    @classmethod
    def tearDownClass(cls):
        cls.platform_staff_profile.delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.now = datetime.now(timezone.utc)
        self.logs = InMemoryLogService()
        self.logs.lines = pod_logs(self.now)
        configure_logs(lambda: self.logs)
        self.addCleanup(configure_logs, None)
        self.cluster = InMemoryKubernetesService()
        self.cluster.items = cluster_items(self.now)
        configure_kubernetes(lambda: self.cluster)
        self.addCleanup(configure_kubernetes, None)
        self.provider = InMemoryProvider()
        configure_provider(lambda: self.provider)
        self.addCleanup(configure_provider, None)
        last_id = OperationsToolCall.objects.order_by("-id").values_list("id", flat=True).first() or 0
        self.addCleanup(lambda: OperationsToolCall.objects.filter(id__gt=last_id).delete())

    def audit_rows(self):
        """The audit rows of this test's staff user, newest first."""
        return OperationsToolCall.objects.filter(user=self.admin_user).order_by("-id")
