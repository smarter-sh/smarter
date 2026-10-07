# pylint: disable=too-many-public-methods
"""
Unit tests for :py:mod:`smarter.apps.plugin.plugin.websearch_fetch`, which reads web pages for the WebsearchPlugin.

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from unittest import mock

from django.core.cache import cache

from smarter.apps.plugin.manifest.models.websearch_plugin.policy import DomainPolicy
from smarter.apps.plugin.plugin.websearch_fetch import (
    TRUNCATION_MARKER,
    USER_AGENT_TOKEN,
    WebFetchError,
    fetch_page,
    html_to_markdown,
    normalize_url,
    robots_permit,
    truncate,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import SAFE_HTTP_DNS_PATCH, FakeWebHost, mock_web_host

ARTICLE = """<!doctype html>
<html>
<head>
  <title> The  Title </title>
  <style>body { color: red; }</style>
  <script>alert("tracking")</script>
</head>
<body>
  <nav><a href="/home">Home</a> | <a href="/about">About</a></nav>
  <header>Site header</header>
  <main>
    <h1>Main heading</h1>
    <p>A paragraph with <strong>bold</strong>, <em>italic</em>, <code>code</code> and
       <a href="/docs/page">a relative link</a>, <a href="https://other.example/x">an absolute link</a>,
       <a href="#section">an anchor</a> and <a href="javascript:alert(1)">a script link</a>.</p>
    <h2>Lists</h2>
    <ul><li>First</li><li>Second <ol><li>Nested</li></ol></li></ul>
    <pre>def hello():
    return "world"</pre>
    <blockquote>A quotation.</blockquote>
    <table>
      <tr><th>Name</th><th>Value</th></tr>
      <tr><td>a</td><td>1 | 2</td></tr>
    </table>
    <img src="/diagram.png" alt="A diagram">
    <form><input name="q"><button>Search</button></form>
    <!-- a comment -->
  </main>
  <footer>Copyright</footer>
</body>
</html>"""


class TestWebsearchFetch(SmarterTestBase):
    """Test reading web pages."""

    def setUp(self):
        super().setUp()
        # robots.txt files are cached.
        cache.clear()

    def host(self, **pages) -> FakeWebHost:
        """Return a FakeWebHost serving HTML pages at https://example.com/<name>, with no robots.txt."""
        host = FakeWebHost()
        for name, html in pages.items():
            host.add_html(f"https://example.com/{name}", html)
        return host

    # =========================================================================
    # normalize_url()
    # =========================================================================
    def test_normalize_url(self):
        """Test that http is upgraded to https, and fragments are removed."""
        for url, expected in (
            ("https://example.com/a?b=1", "https://example.com/a?b=1"),
            ("http://example.com/a", "https://example.com/a"),
            ("  https://example.com/a#section  ", "https://example.com/a"),
            ("HTTP://Example.com/", "https://Example.com/"),
        ):
            self.assertEqual(normalize_url(url), expected, f"url={url!r}")

    def test_normalize_url_invalid(self):
        """Test that non-http(s) URLs, and URLs without a host, are rejected."""
        for url in (
            "",
            "   ",
            None,
            "ftp://example.com/",
            "file:///etc/passwd",
            "example.com/page",
            "https://",
            "https://" + "a" * 2048,
        ):
            with self.assertRaises(WebFetchError, msg=f"url={url!r}"):
                normalize_url(url)  # type: ignore[arg-type]

    # =========================================================================
    # html_to_markdown()
    # =========================================================================
    def test_html_to_markdown(self):
        """Test the conversion of a typical article to Markdown."""
        title, markdown = html_to_markdown(ARTICLE.encode("utf-8"), "https://example.com/blog/post")
        self.assertEqual(title, "The Title")
        self.assertTrue(markdown.startswith("# Main heading"))
        self.assertIn("**bold**", markdown)
        self.assertIn("*italic*", markdown)
        self.assertIn("`code`", markdown)
        self.assertIn("[a relative link](https://example.com/docs/page)", markdown)
        self.assertIn("[an absolute link](https://other.example/x)", markdown)
        self.assertIn("an anchor", markdown)
        self.assertNotIn("#section", markdown)
        self.assertNotIn("javascript:", markdown)
        self.assertIn("## Lists", markdown)
        self.assertIn("- First", markdown)
        self.assertIn("1. Nested", markdown)
        self.assertIn('```\ndef hello():\n    return "world"\n```', markdown)
        self.assertIn("> A quotation.", markdown)
        self.assertIn("| Name | Value |", markdown)
        self.assertIn("| a | 1 \\| 2 |", markdown)
        self.assertIn("[image: A diagram]", markdown)

    def test_html_to_markdown_removes_boilerplate(self):
        """Test that scripts, styles, forms, comments, navigation, headers and footers are removed."""
        _, markdown = html_to_markdown(ARTICLE.encode("utf-8"), "https://example.com/")
        for text in ("tracking", "color: red", "Search", "a comment", "Home", "Site header", "Copyright"):
            self.assertNotIn(text, markdown, text)

    def test_html_to_markdown_without_main(self):
        """Test a page without <main> or <article>: navigation, headers, footers and sidebars are removed."""
        html = "<html><body><nav>Menu</nav><header>Header</header><aside>Ads</aside><div><p>Content</p></div><footer>Foot</footer></body></html>"
        title, markdown = html_to_markdown(html.encode("utf-8"), "https://example.com/")
        self.assertIsNone(title)
        self.assertEqual(markdown, "Content")

    def test_html_to_markdown_prefers_article(self):
        """Test that <article> is read when there is no <main>."""
        html = "<body><div>Other</div><article><p>The article</p></article></body>"
        _, markdown = html_to_markdown(html.encode("utf-8"), "https://example.com/")
        self.assertEqual(markdown, "The article")

    def test_html_to_markdown_base_href(self):
        """Test that relative links are resolved against <base href>."""
        html = '<html><head><base href="https://cdn.example.com/docs/"></head><body><p><a href="page">Page</a></p></body></html>'
        _, markdown = html_to_markdown(html.encode("utf-8"), "https://example.com/")
        self.assertIn("[Page](https://cdn.example.com/docs/page)", markdown)

    def test_html_to_markdown_whitespace(self):
        """Test that whitespace is collapsed, and blank lines are limited."""
        html = "<body><p>a\n\n   b</p><p></p><div></div><p>c</p></body>"
        _, markdown = html_to_markdown(html.encode("utf-8"), "https://example.com/")
        self.assertEqual(markdown, "a b\n\nc")

    def test_html_to_markdown_encoding(self):
        """Test that the server's declared encoding is used."""
        html = "<body><p>Café</p></body>".encode("iso-8859-1")
        _, markdown = html_to_markdown(html, "https://example.com/", "iso-8859-1")
        self.assertEqual(markdown, "Café")

    def test_html_to_markdown_link_without_text(self):
        """Test that a link without text is rendered as its URL."""
        _, markdown = html_to_markdown(b'<body><p><a href="https://a.com/"></a></p></body>', "https://example.com/")
        self.assertEqual(markdown, "[https://a.com/](https://a.com/)")

    # =========================================================================
    # truncate()
    # =========================================================================
    def test_truncate(self):
        """Test truncation at a word boundary."""
        self.assertEqual(truncate("short", 100), ("short", False))
        content, truncated = truncate("word " * 100, 102)
        self.assertTrue(truncated)
        self.assertTrue(content.endswith(TRUNCATION_MARKER))
        self.assertLessEqual(len(content) - len(TRUNCATION_MARKER), 102)
        self.assertTrue(content[: -len(TRUNCATION_MARKER)].endswith("word"))

    def test_truncate_without_boundary(self):
        """Test truncation of text without a word boundary."""
        content, truncated = truncate("x" * 200, 100)
        self.assertTrue(truncated)
        self.assertEqual(content, "x" * 100 + TRUNCATION_MARKER)

    # =========================================================================
    # robots.txt
    # =========================================================================
    def test_robots_missing(self):
        """Test that a missing robots.txt (4xx) permits everything."""
        with mock_web_host(FakeWebHost()):
            self.assertTrue(robots_permit("https://example.com/private", 5))

    def test_robots_unreachable(self):
        """Test that an unreachable robots.txt (5xx) permits nothing."""
        host = FakeWebHost()
        host.add("https://example.com/robots.txt", b"", status_code=503)
        with mock_web_host(host):
            self.assertFalse(robots_permit("https://example.com/page", 5))

    def test_robots_rules(self):
        """Test that robots.txt rules are obeyed, for all user agents and for Smarter's."""
        host = FakeWebHost()
        host.add(
            "https://example.com/robots.txt",
            f"User-agent: *\nDisallow: /private/\n\nUser-agent: {USER_AGENT_TOKEN}\nDisallow: /no-smarter/\n".encode(),
        )
        with mock_web_host(host):
            self.assertTrue(robots_permit("https://example.com/public/page", 5))
            self.assertFalse(robots_permit("https://example.com/no-smarter/page", 5))

    def test_robots_is_cached(self):
        """Test that robots.txt is requested once per website."""
        host = FakeWebHost()
        host.add("https://example.com/robots.txt", b"User-agent: *\nDisallow:\n")
        with mock_web_host(host):
            robots_permit("https://example.com/a", 5)
            robots_permit("https://example.com/b", 5)
        self.assertEqual(host.requested.count("https://example.com/robots.txt"), 1)

    # =========================================================================
    # fetch_page()
    # =========================================================================
    def test_fetch_page(self):
        """Test reading an HTML page."""
        with mock_web_host(self.host(post=ARTICLE)):
            page = fetch_page("http://example.com/post#top")
        self.assertEqual(page.url, "https://example.com/post")
        self.assertEqual(page.final_url, "https://example.com/post")
        self.assertEqual(page.title, "The Title")
        self.assertEqual(page.content_type, "text/html")
        self.assertTrue(page.content.startswith("# Main heading"))
        self.assertFalse(page.truncated)
        self.assertIsNotNone(page.retrieved_at)

    def test_fetch_page_request_headers(self):
        """Test that pages are requested with Smarter's user agent, and an Accept header."""
        with mock_web_host(self.host(post=ARTICLE)) as host:
            fetch_page("https://example.com/post")
        headers = host.calls[-1]["headers"]
        self.assertIn(USER_AGENT_TOKEN, headers["User-Agent"])
        self.assertIn("text/html", headers["Accept"])

    def test_fetch_page_truncated(self):
        """Test that long pages are truncated."""
        with mock_web_host(self.host(long="<p>" + "word " * 1000 + "</p>")):
            page = fetch_page("https://example.com/long", max_characters=1000)
        self.assertTrue(page.truncated)
        self.assertLessEqual(len(page.content), 1000 + len(TRUNCATION_MARKER))

    def test_fetch_page_text_formats(self):
        """Test reading plain text, Markdown, JSON and XML."""
        host = FakeWebHost()
        host.add("https://example.com/a.txt", b"plain text", headers={"Content-Type": "text/plain"})
        host.add("https://example.com/a.md", b"# Markdown", headers={"Content-Type": "text/markdown"})
        host.add("https://example.com/a.json", b'{"a":[1,2]}', headers={"Content-Type": "application/json"})
        host.add("https://example.com/bad.json", b"{not json", headers={"Content-Type": "application/json"})
        host.add("https://example.com/feed", b"<rss><item/></rss>", headers={"Content-Type": "application/rss+xml"})
        with mock_web_host(host):
            self.assertEqual(fetch_page("https://example.com/a.txt").content, "plain text")
            self.assertEqual(fetch_page("https://example.com/a.md").content, "# Markdown")
            self.assertEqual(fetch_page("https://example.com/a.json").content, '{\n  "a": [\n    1,\n    2\n  ]\n}')
            self.assertEqual(fetch_page("https://example.com/bad.json").content, "{not json")
            self.assertEqual(fetch_page("https://example.com/feed").content, "<rss><item/></rss>")

    def test_fetch_page_unsupported_type(self):
        """Test that binary formats, e.g. PDF and images, are rejected."""
        host = FakeWebHost()
        host.add("https://example.com/a.pdf", b"%PDF-1.7", headers={"Content-Type": "application/pdf"})
        host.add("https://example.com/a.png", b"\x89PNG", headers={"Content-Type": "image/png"})
        with mock_web_host(host):
            for url in ("https://example.com/a.pdf", "https://example.com/a.png"):
                with self.assertRaises(WebFetchError, msg=url) as context:
                    fetch_page(url)
                self.assertIn("cannot be read", str(context.exception))

    def test_fetch_page_without_content_type(self):
        """Test that a page without a Content-Type is read as HTML."""
        host = FakeWebHost()
        host.add("https://example.com/", b"<p>Untyped</p>")
        with mock_web_host(host):
            self.assertEqual(fetch_page("https://example.com/").content, "Untyped")

    def test_fetch_page_not_found(self):
        """Test that an HTTP error is reported with its status code."""
        with mock_web_host(FakeWebHost()):
            with self.assertRaises(WebFetchError) as context:
                fetch_page("https://example.com/missing")
        self.assertIn("HTTP 404", str(context.exception))

    def test_fetch_page_domain_policy(self):
        """Test that the domain policy is enforced, without any request."""
        with mock_web_host(self.host(post=ARTICLE)) as host:
            with self.assertRaises(WebFetchError) as context:
                fetch_page("https://example.com/post", policy=DomainPolicy.create(allowed=["docs.example.org"]))
        self.assertIn("not permitted", str(context.exception))
        self.assertEqual(host.requested, [])

    def test_fetch_page_redirect_to_blocked_domain(self):
        """Test that a redirect to a blocked domain is refused."""
        host = self.host()
        host.add("https://example.com/go", status_code=302, headers={"Location": "https://blocked.example/"})
        host.add_html("https://blocked.example/", "<p>Blocked</p>")
        with mock_web_host(host):
            with self.assertRaises(WebFetchError):
                fetch_page("https://example.com/go", policy=DomainPolicy.create(blocked=["blocked.example"]))
        self.assertNotIn("https://blocked.example/", host.requested)

    def test_fetch_page_redirect(self):
        """Test that a permitted redirect is followed, and reported as the final URL."""
        host = self.host(new="<p>New</p>")
        host.add("https://example.com/old", status_code=301, headers={"Location": "/new"})
        with mock_web_host(host):
            page = fetch_page("https://example.com/old")
        self.assertEqual(page.final_url, "https://example.com/new")
        self.assertEqual(page.content, "New")

    def test_fetch_page_robots_disallowed(self):
        """Test that a page disallowed by robots.txt is not read."""
        host = self.host(private="<p>Private</p>")
        host.add("https://example.com/robots.txt", b"User-agent: *\nDisallow: /private\n")
        with mock_web_host(host):
            with self.assertRaises(WebFetchError) as context:
                fetch_page("https://example.com/private")
            self.assertIn("robots.txt", str(context.exception))
            self.assertNotIn("https://example.com/private", host.requested)
            self.assertEqual(fetch_page("https://example.com/private", respect_robots_txt=False).content, "Private")

    def test_fetch_page_redirect_to_robots_disallowed(self):
        """Test that robots.txt is obeyed on redirects to another website."""
        host = self.host()
        host.add("https://example.com/go", status_code=302, headers={"Location": "https://other.example/private"})
        host.add("https://other.example/robots.txt", b"User-agent: *\nDisallow: /\n")
        host.add_html("https://other.example/private", "<p>Private</p>")
        with mock_web_host(host):
            with self.assertRaises(WebFetchError):
                fetch_page("https://example.com/go")
        self.assertNotIn("https://other.example/private", host.requested)

    def test_fetch_page_private_address(self):
        """Test that a page whose host has a private address is not read."""

        # pylint: disable=unused-argument
        def private(host, port, *args, **kwargs):
            return [(2, 1, 6, "", ("10.0.0.1", port))]

        with mock_web_host(self.host(post=ARTICLE)) as host, mock.patch(SAFE_HTTP_DNS_PATCH, side_effect=private):
            with self.assertRaises(WebFetchError):
                fetch_page("https://example.com/post", respect_robots_txt=False)
        self.assertEqual(host.requested, [])
