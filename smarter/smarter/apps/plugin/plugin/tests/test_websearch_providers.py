"""
Unit tests for :py:mod:`smarter.apps.plugin.plugin.websearch_providers`, the web search APIs.

of the WebsearchPlugin.

The Brave Search and Tavily APIs are simulated by a :class:`FakeWebHost`, using responses
in the documented format of each API.

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.plugin.manifest.models.websearch_plugin.policy import DomainPolicy
from smarter.apps.plugin.plugin.websearch_providers import (
    PROVIDERS,
    BraveSearchProvider,
    SearchProvider,
    SearchRequest,
    SearchResult,
    TavilySearchProvider,
    WebsearchError,
    clean_text,
    get_provider,
    post_filter,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import FakeWebHost, mock_web_host

BRAVE_URL = BraveSearchProvider.url
TAVILY_URL = TavilySearchProvider.url


def brave_response(*urls: str) -> dict:
    """Return a Brave Search API response with a result for each URL."""
    return {
        "type": "search",
        "query": {"original": "q", "more_results_available": True},
        "web": {
            "type": "search",
            "results": [
                {
                    "title": f"Title {i}",
                    "url": url,
                    "description": f"Description {i} with <strong>markup</strong>",
                    "page_age": "2026-09-01T00:00:00",
                    "age": "September 1, 2026",
                }
                for i, url in enumerate(urls)
            ],
        },
    }


def tavily_response(*urls: str) -> dict:
    """Return a Tavily Search API response with a result for each URL."""
    return {
        "query": "q",
        "answer": None,
        "results": [
            {"title": f"Title {i}", "url": url, "content": f"Content {i}", "score": 0.9, "published_date": "2026-09-01"}
            for i, url in enumerate(urls)
        ],
        "response_time": 0.5,
    }


class TestWebsearchProviders(SmarterTestBase):
    """Test the web search APIs."""

    def search(self, provider: SearchProvider, response: dict, status_code: int = 200, **request_kwargs):
        """Search with a provider whose API returns a response."""
        host = FakeWebHost()
        host.add_json(provider.url, response, status_code)  # type: ignore[attr-defined]
        request = SearchRequest(**{"query": "django release", "max_results": 3, **request_kwargs})
        with mock_web_host(host):
            results = provider.search(request, "the-api-key")
        return results, host.calls[0]

    # =========================================================================
    # registry and helpers
    # =========================================================================
    def test_providers(self):
        """Test the provider registry."""
        self.assertEqual(set(PROVIDERS), {"brave", "tavily"})
        self.assertIsInstance(get_provider("brave"), BraveSearchProvider)
        self.assertIsInstance(get_provider("tavily"), TavilySearchProvider)
        with self.assertRaises(WebsearchError):
            get_provider("google")

    def test_clean_text(self):
        """Test that text is collapsed to a single line and truncated."""
        self.assertEqual(clean_text("  a\n\tb  ", 100), "a b")
        self.assertEqual(clean_text(None, 100), "")
        self.assertEqual(clean_text("abcdefghij", 5), "abcd…")

    def test_search_result(self):
        """Test a search result."""
        result = SearchResult(title="T", url="https://Docs.Example.com/a", snippet="S")
        self.assertEqual(result.domain, "docs.example.com")
        self.assertEqual(result.to_dict(), {"title": "T", "url": "https://Docs.Example.com/a", "snippet": "S"})
        self.assertEqual(SearchResult("T", "https://a.com", "S", "2026").to_dict()["published"], "2026")

    def test_post_filter(self):
        """Test that results are filtered by policy, deduplicated, restricted to http(s), and limited."""
        results = [
            SearchResult("1", "https://a.com/1", ""),
            SearchResult("dup", "https://a.com/1/", ""),
            SearchResult("blocked", "https://blocked.example/", ""),
            SearchResult("ftp", "ftp://a.com/file", ""),
            SearchResult("js", "javascript:alert(1)", ""),
            SearchResult("2", "https://b.com/2", ""),
            SearchResult("3", "http://c.com/3", ""),
            SearchResult("4", "https://d.com/4", ""),
        ]
        request = SearchRequest(query="q", max_results=3, policy=DomainPolicy.create(blocked=["blocked.example"]))
        self.assertEqual([result.title for result in post_filter(results, request)], ["1", "2", "3"])

    def test_site_operators(self):
        """Test the search operators that apply a domain policy."""
        self.assertEqual(SearchProvider.site_operators(DomainPolicy()), "")
        self.assertEqual(SearchProvider.site_operators(DomainPolicy.create(allowed=["a.com"])), "site:a.com")
        self.assertEqual(
            SearchProvider.site_operators(DomainPolicy.create(allowed=["a.com", "b.com"], blocked=["c.a.com"])),
            "(site:a.com OR site:b.com) -site:c.a.com",
        )

    # =========================================================================
    # Brave Search
    # =========================================================================
    def test_brave_request(self):
        """Test the Brave Search API request."""
        _, call = self.search(
            BraveSearchProvider(),
            brave_response(),
            country="us",
            language="en",
            freshness="week",
            safe_search="strict",
            timeout=9,
        )
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["url"], BRAVE_URL)
        self.assertEqual(call["headers"]["X-Subscription-Token"], "the-api-key")
        self.assertEqual(
            call["params"],
            {
                "q": "django release",
                "count": 6,
                "safesearch": "strict",
                "country": "US",
                "search_lang": "en",
                "freshness": "pw",
            },
        )
        self.assertEqual(call["timeout"], 9)

    def test_brave_request_domain_policy(self):
        """Test that Brave is asked to apply the domain policy with site operators."""
        policy = DomainPolicy.create(allowed=["docs.python.org"], blocked=["wiki.python.org"])
        _, call = self.search(BraveSearchProvider(), brave_response(), policy=policy)
        self.assertEqual(call["params"]["q"], "django release site:docs.python.org -site:wiki.python.org")

    def test_brave_request_freshness(self):
        """Test the mapping of freshness to Brave's codes."""
        for freshness, code in (("day", "pd"), ("week", "pw"), ("month", "pm"), ("year", "py")):
            _, call = self.search(BraveSearchProvider(), brave_response(), freshness=freshness)
            self.assertEqual(call["params"]["freshness"], code)

    def test_brave_request_count_is_capped(self):
        """Test that the number of results requested from Brave is at most 20."""
        _, call = self.search(BraveSearchProvider(), brave_response(), max_results=20)
        self.assertEqual(call["params"]["count"], 20)

    def test_brave_results(self):
        """Test parsing Brave Search API results."""
        results, _ = self.search(BraveSearchProvider(), brave_response("https://a.com/", "https://b.com/"))
        self.assertEqual(
            [result.to_dict() for result in results],
            [
                {
                    "title": "Title 0",
                    "url": "https://a.com/",
                    "snippet": "Description 0 with <strong>markup</strong>",
                    "published": "2026-09-01T00:00:00",
                },
                {
                    "title": "Title 1",
                    "url": "https://b.com/",
                    "snippet": "Description 1 with <strong>markup</strong>",
                    "published": "2026-09-01T00:00:00",
                },
            ],
        )

    def test_brave_results_malformed(self):
        """Test that malformed Brave results are skipped."""
        for response in (
            {},
            {"web": None},
            {"web": {"results": None}},
            {"web": {"results": [None, {"title": "no url"}]}},
        ):
            results, _ = self.search(BraveSearchProvider(), response)
            self.assertEqual(results, [], f"response={response}")

    def test_brave_results_enforce_policy(self):
        """Test that the domain policy is enforced even if Brave ignores it."""
        results, _ = self.search(
            BraveSearchProvider(),
            brave_response("https://blocked.example/", "https://ok.example/"),
            policy=DomainPolicy.create(blocked=["blocked.example"]),
        )
        self.assertEqual([result.url for result in results], ["https://ok.example/"])

    # =========================================================================
    # Tavily
    # =========================================================================
    def test_tavily_request(self):
        """Test the Tavily Search API request."""
        policy = DomainPolicy.create(allowed=["docs.example.com"], blocked=["old.docs.example.com"])
        _, call = self.search(
            TavilySearchProvider(),
            tavily_response(),
            policy=policy,
            freshness="month",
            language="fr",
            country="fr",
            safe_search="off",
        )
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], TAVILY_URL)
        self.assertEqual(call["headers"]["Authorization"], "Bearer the-api-key")
        body = call["json"]
        self.assertEqual(body["query"], "django release")
        self.assertEqual(body["max_results"], 6)
        self.assertEqual(body["include_domains"], ["docs.example.com"])
        self.assertEqual(body["exclude_domains"], ["old.docs.example.com"])
        self.assertEqual(body["time_range"], "month")
        self.assertEqual(body["language"], "fr")
        self.assertFalse(body["safe_search"])
        self.assertFalse(body["include_answer"])
        self.assertFalse(body["include_raw_content"])
        self.assertNotIn("country", body)
        self.assertNotIn("api_key", body)

    def test_tavily_safe_search(self):
        """Test that moderate and strict safe search enable Tavily's safe search."""
        for safe_search in ("moderate", "strict"):
            _, call = self.search(TavilySearchProvider(), tavily_response(), safe_search=safe_search)
            self.assertTrue(call["json"]["safe_search"], safe_search)

    def test_tavily_results(self):
        """Test parsing Tavily Search API results."""
        results, _ = self.search(TavilySearchProvider(), tavily_response("https://a.com/"))
        self.assertEqual(
            [result.to_dict() for result in results],
            [{"title": "Title 0", "url": "https://a.com/", "snippet": "Content 0", "published": "2026-09-01"}],
        )

    def test_tavily_results_malformed(self):
        """Test that malformed Tavily results are skipped."""
        for response in ({}, {"results": None}, {"results": ["x", {"title": "no url"}]}):
            results, _ = self.search(TavilySearchProvider(), response)
            self.assertEqual(results, [], f"response={response}")

    # =========================================================================
    # errors
    # =========================================================================
    def test_http_errors(self):
        """Test that API errors are described without disclosing the api key."""
        for status_code, expected in (
            (401, "rejected the plugin's api key"),
            (403, "rejected the plugin's api key"),
            (429, "rate limit"),
            (500, "HTTP 500"),
        ):
            for provider in (BraveSearchProvider(), TavilySearchProvider()):
                with self.assertRaises(WebsearchError, msg=f"{provider.name} {status_code}") as context:
                    self.search(provider, {"error": "the-api-key is invalid"}, status_code=status_code)
                self.assertIn(expected, str(context.exception))
                self.assertNotIn("the-api-key", str(context.exception))

    def test_unreachable(self):
        """Test that an unreachable API raises a WebsearchError."""
        host = FakeWebHost()
        with mock_web_host(host):
            host.remove(BRAVE_URL)
            with self.assertRaises(WebsearchError):
                BraveSearchProvider().search(SearchRequest(query="q", max_results=1), "key")

    def test_invalid_json(self):
        """Test that an invalid API response raises a WebsearchError."""
        for content in (b"not json", b"[1, 2]"):
            host = FakeWebHost()
            host.add(BRAVE_URL, content)
            with mock_web_host(host):
                with self.assertRaises(WebsearchError, msg=f"content={content!r}"):
                    BraveSearchProvider().search(SearchRequest(query="q", max_results=1), "key")
