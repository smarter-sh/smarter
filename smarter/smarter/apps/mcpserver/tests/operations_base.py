"""
Test harness of the Smarter Operations MCP server.

:class:`OperationsTestBase` installs an in-memory log service, with the lines of
./data/pod-logs.yaml, timed relative to now, so that nothing reaches Loki. Its staff user is the
account mixin's admin user, and every audit row that a test writes is deleted afterwards.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import os
from datetime import datetime, timedelta, timezone

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.infrastructure.services import (
    InMemoryLogService,
    LogLine,
    configure_logs,
)
from smarter.apps.mcpserver.models import OperationsToolCall
from smarter.common.utils import get_readonly_yaml_file

HERE = os.path.abspath(os.path.dirname(__file__))
POD_LOGS = os.path.join(HERE, "data", "pod-logs.yaml")
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


class OperationsTestBase(TestAccountMixin):
    """An in-memory log service with the test pod logs, and the audit rows cleaned up."""

    def setUp(self):
        super().setUp()
        self.now = datetime.now(timezone.utc)
        self.logs = InMemoryLogService()
        self.logs.lines = pod_logs(self.now)
        configure_logs(lambda: self.logs)
        self.addCleanup(configure_logs, None)
        last_id = OperationsToolCall.objects.order_by("-id").values_list("id", flat=True).first() or 0
        self.addCleanup(lambda: OperationsToolCall.objects.filter(id__gt=last_id).delete())

    def audit_rows(self):
        """The audit rows of this test's staff user, newest first."""
        return OperationsToolCall.objects.filter(user=self.admin_user).order_by("-id")
