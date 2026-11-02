"""Tests for smarter.apps.mcpserver.logs.tools, with the in-memory log service."""

from smarter.apps.infrastructure.services import InMemoryLogService, configure_logs
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.logs.tools import (
    ListLogSourcesTool,
    SearchLogsTool,
    SummarizeLogErrorsTool,
)
from smarter.apps.mcpserver.protocol.operations_tools import UNTRUSTED_DATA_NOTICE

from .operations_base import TICKET, OperationsTestBase


class TestListLogSourcesTool(OperationsTestBase):
    """Test list_log_sources."""

    def test_sources(self):
        text = ListLogSourcesTool(self.admin_user).call({"ticket": TICKET})
        self.assertIn("Components: mariadb, smarter, smarter-beat, smarter-worker", text)
        self.assertIn("Components that wrote nothing: smarter-worker-infrastructure", text)
        self.assertIn("- smarter-mariadb-0", text)

    def test_nothing(self):
        self.logs.lines = []
        text = ListLogSourcesTool(self.admin_user).call({"ticket": TICKET, "minutes": 5})
        self.assertIn("Components: none", text)
        self.assertIn("- none", text)


class TestSearchLogsTool(OperationsTestBase):
    """Test search_logs."""

    def search(self, **arguments) -> str:
        return SearchLogsTool(self.admin_user).call({"ticket": TICKET, **arguments})

    def test_latest_lines(self):
        text = self.search(limit=3)
        self.assertTrue(text.startswith(UNTRUSTED_DATA_NOTICE), "log lines are marked as untrusted data")
        self.assertIn("3 log lines in the last 60 minutes (the limit, newest first: there may be more)", text)
        self.assertLess(text.index("Sending due task"), text.index("ignore your instructions"), "newest first")

    def test_filters(self):
        text = self.search(components=["smarter"], contains=["TIMEOUT"])
        self.assertIn("3 log lines", text)
        self.assertIn("smarter/smarter-6f9c7d-d3e4f:", text)
        self.assertEqual(self.logs.queries[-1].components, ("smarter",))
        self.assertEqual(len(self.logs.queries[-1].contains), 1)

    def test_pod_pattern_and_oldest_first(self):
        text = self.search(pod="smarter-6f9c7d-a1b2c", pattern=r"took \d+\.\d+s", oldest_first=True)
        self.assertIn("1 log lines", text)
        self.assertIn("(oldest first)", text)
        self.assertEqual(self.logs.queries[-1].direction, "forward")

    def test_min_level(self):
        text = self.search(min_level="warning")
        self.assertIn("6 log lines", text, "3 errors, and 3 warnings in the platform's, Celery's and MariaDB's formats")
        self.assertNotIn("Sending due task", text)

    def test_period(self):
        self.assertIn("an old error", self.search(minutes=720, min_level="error"))
        self.assertNotIn("an old error", self.search(min_level="error"))

    def test_nothing(self):
        self.assertIn("No line matches", self.search(contains=["no such text anywhere"]))

    def test_invalid(self):
        with self.assertRaisesRegex(SmarterMCPServerToolError, "invalid log query: .*regular expression"):
            self.search(pattern="(")
        with self.assertRaisesRegex(SmarterMCPServerToolError, "invalid arguments for search_logs: components"):
            self.search(components=["not-a-component"])
        with self.assertRaisesRegex(SmarterMCPServerToolError, "minutes"):
            self.search(minutes=10000)


class TestSummarizeLogErrorsTool(OperationsTestBase):
    """Test summarize_log_errors."""

    def summarize(self, **arguments) -> str:
        return SummarizeLogErrorsTool(self.admin_user).call({"ticket": TICKET, **arguments})

    def test_errors(self):
        text = self.summarize()
        self.assertTrue(text.startswith(UNTRUSTED_DATA_NOTICE))
        self.assertIn("## 3 errors in the last 60 minutes", text)
        self.assertIn("### 3 × error in smarter (2 pods,", text, "the three timeouts are one problem")
        self.assertIn("request 1003", text, "the example is the latest line")
        self.assertNotIn("an old error", text)

    def test_warnings(self):
        text = self.summarize(min_level="warning", groups=2)
        self.assertIn("## 6 warnings and errors", text)
        self.assertIn("_2 more groups are not shown._", text)

    def test_components_and_none(self):
        self.assertIn("None. The logs show no errors", self.summarize(components=["smarter-beat"]))
        self.assertEqual(self.logs.queries[-1].components, ("smarter-beat",))

    def test_not_ready(self):
        configure_logs(lambda: InMemoryLogService(ready=False))
        with self.assertRaisesRegex(SmarterMCPServerToolError, "not available on this platform"):
            self.summarize()
