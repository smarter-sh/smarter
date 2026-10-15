"""Tests of smarter.apps.llmtool.extension.docs."""

from unittest.mock import patch

from smarter.apps.llmtool.extension import docs
from smarter.apps.llmtool.extension.docs import render_markdown, render_page, render_rst
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestExtensionDocs(SmarterTestBase):
    """Test rendering extension documentation safely."""

    def test_render_rst(self):
        """ReStructuredText is rendered as HTML, and empty text as nothing."""
        html = render_rst("Title\n=====\n\nSome *emphasis*.")
        self.assertIn("<em>emphasis</em>", html)
        self.assertEqual(render_rst("  "), "")

    def test_rst_is_safe(self):
        """Raw HTML and file inclusion are disabled."""
        html = render_rst(".. raw:: html\n\n   <script>alert(1)</script>\n\n.. include:: /etc/passwd\n")
        self.assertNotIn("<script>", html)
        self.assertNotIn("root:", html)

    def test_rst_failure(self):
        """Text that docutils cannot render is shown as preformatted text."""
        with patch.object(docs, "publish_parts", side_effect=RuntimeError("boom")):
            self.assertEqual(render_rst("<b>x</b>"), "<pre>&lt;b&gt;x&lt;/b&gt;</pre>")

    def test_render_markdown_is_safe(self):
        """Markdown is rendered, with raw HTML escaped."""
        html = render_markdown("# Usage\n\n<script>alert(1)</script>")
        self.assertIn("<h1>Usage</h1>", html)
        self.assertNotIn("<script>", html)

    def test_render_page(self):
        """Pages are rendered by their file extension."""
        self.assertIn("<h1>", render_page("usage.md", "# Usage"))
        self.assertIn("<em>", render_page("usage.rst", "*x*"))
