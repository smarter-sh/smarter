"""Tests for smarter.apps.mcpserver.protocol.tools.markdown."""

from smarter.apps.mcpserver.protocol.tools.markdown import (
    code_fence_language,
    numbered_excerpt,
)
from smarter.apps.mcpserver.services.search import SearchLine
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestMarkdown(SmarterTestBase):
    """Test the Markdown helpers of the public tools."""

    def test_code_fence_language(self):
        """A file's extension names its language, case insensitively, and others are text."""
        self.assertEqual(code_fence_language("a/b/models.py"), "python")
        self.assertEqual(code_fence_language("values.YAML"), "yaml")
        self.assertEqual(code_fence_language("Makefile"), "text")

    def test_numbered_excerpt(self):
        """Line numbers are right-aligned to the widest one."""
        lines = [SearchLine(number=9, text="nine"), SearchLine(number=10, text="ten")]
        self.assertEqual(numbered_excerpt(lines), " 9  nine\n10  ten")
        self.assertEqual(numbered_excerpt([]), "")
