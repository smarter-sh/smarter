"""Tests for smarter.apps.mcpserver.protocol.operations_tools: arguments, the audit trail and errors."""

from unittest import mock

from smarter.apps.infrastructure.exceptions import LogServiceError
from smarter.apps.mcpserver.exceptions import SmarterMCPServerToolError
from smarter.apps.mcpserver.logs.tools import SearchLogsTool
from smarter.apps.mcpserver.models import OperationsToolCall
from smarter.apps.mcpserver.protocol.operations_tools import (
    MAX_RESULT_CHARACTERS,
    truncate,
)

from .operations_base import TICKET, OperationsTestBase


class TestSmarterOperationsTool(OperationsTestBase):
    """Test SmarterOperationsTool.call(), with search_logs."""

    def setUp(self):
        super().setUp()
        self.tool = SearchLogsTool(self.admin_user)

    def test_ticket_is_required(self):
        for arguments in ({}, {"ticket": ""}, {"ticket": "x" * 201}, None):
            with self.assertRaisesRegex(SmarterMCPServerToolError, "invalid arguments for search_logs: ticket"):
                self.tool.call(arguments)
        self.assertFalse(self.audit_rows().exists(), "a call with invalid arguments reads nothing, and is not recorded")

    def test_input_schema(self):
        schema = self.tool.input_schema()
        self.assertIn("ticket", schema["required"])
        self.assertFalse(schema["additionalProperties"])
        self.assertTrue(self.tool.definition().annotations.read_only_hint)

    def test_audit(self):
        text = self.tool.call({"ticket": TICKET, "contains": ["timeout"], "limit": 5})
        row = self.audit_rows().first()
        self.assertEqual(row.tool, "search_logs")
        self.assertEqual(row.ticket, TICKET)
        self.assertEqual(row.username, self.admin_user.get_username())
        self.assertEqual(row.arguments["contains"], ["timeout"])
        self.assertNotIn("ticket", row.arguments)
        self.assertFalse(row.is_error)
        self.assertEqual(row.characters, len(text))
        self.assertIn(TICKET, str(row))

    def test_audit_of_errors(self):
        with self.assertRaises(SmarterMCPServerToolError):
            self.tool.call({"ticket": TICKET, "pattern": "("})
        with mock.patch.object(self.logs, "query", side_effect=LogServiceError("Loki answered HTTP 500")):
            with self.assertRaisesRegex(SmarterMCPServerToolError, "search_logs failed: .*Loki answered HTTP 500"):
                self.tool.call({"ticket": TICKET})
        self.assertEqual(self.audit_rows().filter(is_error=True).count(), 2)

    def test_audit_outlives_the_user(self):
        """The user's deletion empties the row's user, and keeps its username."""
        self.tool.call({"ticket": TICKET})
        row = self.audit_rows().first()
        OperationsToolCall.objects.filter(pk=row.pk).update(user=None)
        row.refresh_from_db()
        self.assertIsNone(row.user)
        self.assertEqual(row.username, self.admin_user.get_username())

    def test_result_is_truncated(self):
        with mock.patch.object(SearchLogsTool, "run", return_value="line\n" * MAX_RESULT_CHARACTERS):
            text = self.tool.call({"ticket": TICKET})
        self.assertLessEqual(len(text), MAX_RESULT_CHARACTERS)
        self.assertEqual(self.audit_rows().first().characters, len(text))


class TestTruncate(OperationsTestBase):
    """Test truncate()."""

    def test_truncate(self):
        self.assertEqual(truncate("short"), "short")
        text = truncate("abcdefghij\n" * 100, limit=500)
        self.assertLessEqual(len(text), 500)
        self.assertTrue(text.endswith("Narrow the query to see the rest._"))
        self.assertIn("abcdefghij\n\n_The result", text, "cut at a line")
