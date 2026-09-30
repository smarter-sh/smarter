"""
Web search APIs for the WebsearchPlugin.

Each web search API is wrapped by a :class:`SearchProvider`, which translates a
:class:`SearchRequest` into the API's request, and the API's response into a list of
:class:`SearchResult`. Every provider returns results in the same form, so that the LLM
sees the same fields regardless of the API, and can cite each result by its URL.

**Providers:**

- ``brave``: the Brave Search API, https://brave.com/search/api/
- ``tavily``: the Tavily Search API, which is designed for LLMs, https://tavily.com

The plugin's domain policy is passed to each API, so that the API restricts its results,
and is also applied to the results that the API returns, so that the policy is enforced
even if an API ignores it.

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

from smarter.apps.plugin.manifest.models.websearch_plugin.enum import (
    WebsearchProvider,
    WebsearchSafeSearch,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.policy import (
    DomainPolicy,
    url_host,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from . import safe_http

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])

MAX_SNIPPET_LENGTH = 1000
MAX_TITLE_LENGTH = 300
MAX_RESPONSE_BYTES = 5_000_000


class WebsearchError(SmarterValueError):
    """Raised when a web search cannot be performed.

    The message is safe to show to the LLM.
    """


# pylint: disable=too-many-instance-attributes
@dataclass(frozen=True)
class SearchRequest:
    """
    A web search.

    :ivar query: The search query.
    :ivar max_results: The maximum number of results.
    :ivar policy: The domain policy that results must satisfy.
    :ivar safe_search: Adult content filtering: off, moderate or strict.
    :ivar country: An ISO 3166-1 alpha-2 country code, to localize results.
    :ivar language: An ISO 639-1 language code, to localize results.
    :ivar freshness: Restricts results to those published within the last day, week, month or year.
    :ivar timeout: Seconds to wait for the web search API.
    """

    query: str
    max_results: int
    policy: DomainPolicy = DomainPolicy()
    safe_search: str = WebsearchSafeSearch.MODERATE.value
    country: Optional[str] = None
    language: Optional[str] = None
    freshness: Optional[str] = None
    timeout: float = safe_http.DEFAULT_TIMEOUT


@dataclass(frozen=True)
class SearchResult:
    """
    A web search result.

    :ivar title: The title of the web page.
    :ivar url: The URL of the web page, which the LLM should cite.
    :ivar snippet: An excerpt of the web page that is relevant to the query.
    :ivar published: When the web page was published or updated, as reported by the API, if known.
    """

    title: str
    url: str
    snippet: str
    published: Optional[str] = None

    @property
    def domain(self) -> Optional[str]:
        """The host of the result's URL."""
        return url_host(self.url)

    def to_dict(self) -> dict[str, Any]:
        """Return the result as a dict for the LLM, omitting empty fields."""
        retval: dict[str, Any] = {"title": self.title, "url": self.url, "snippet": self.snippet}
        if self.published:
            retval["published"] = self.published
        return retval


def clean_text(value: Any, max_length: int) -> str:
    """Return a value as single-line text, truncated to a maximum length."""
    text = " ".join(str(value or "").split())
    return text if len(text) <= max_length else text[: max_length - 1].rstrip() + "…"


def post_filter(results: list[SearchResult], request: SearchRequest) -> list[SearchResult]:
    """
    Enforce the domain policy on search results, remove duplicate and non-http(s) URLs, and.

    limit the number of results.
    """
    filtered: list[SearchResult] = []
    seen: set[str] = set()
    for result in results:
        if urlparse(result.url).scheme not in ("http", "https"):
            continue
        if not request.policy.permits_url(result.url):
            continue
        key = result.url.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        filtered.append(result)
        if len(filtered) >= request.max_results:
            break
    return filtered


def describe_http_error(provider: str, error: safe_http.SafeHttpError) -> str:
    """Describe a failed web search API request, without disclosing the api key."""
    if error.status_code in (401, 403):
        return f"the {provider} web search api rejected the plugin's api key."
    if error.status_code == 429:
        return f"the {provider} web search api rate limit was exceeded. Try again later."
    if error.status_code:
        return f"the {provider} web search api responded with HTTP {error.status_code}."
    return f"the {provider} web search api could not be reached."


class SearchProvider(ABC):
    """A web search API."""

    name: str = ""

    def search(self, request: SearchRequest, api_key: str) -> list[SearchResult]:
        """
        Search the web.

        :param request: The search.
        :param api_key: The web search API's api key.
        :return: The results, which satisfy the request's domain policy.
        :raises WebsearchError: If the search fails.
        """
        try:
            response = self.request(request, api_key)
        except safe_http.SafeHttpError as e:
            raise WebsearchError(describe_http_error(self.name, e)) from e
        try:
            data = json.loads(response.content)
        except (ValueError, UnicodeDecodeError) as e:
            raise WebsearchError(f"the {self.name} web search api returned an invalid response.") from e
        if not isinstance(data, dict):
            raise WebsearchError(f"the {self.name} web search api returned an invalid response.")
        return post_filter(self.parse(data), request)

    @staticmethod
    def site_operators(policy: DomainPolicy) -> str:
        """Return search operators that apply a domain policy, for APIs that support them in queries."""
        operators = []
        if policy.allowed:
            sites = " OR ".join(f"site:{domain}" for domain in policy.allowed)
            operators.append(f"({sites})" if len(policy.allowed) > 1 else sites)
        operators.extend(f"-site:{domain}" for domain in policy.blocked)
        return " ".join(operators)

    @abstractmethod
    def request(self, request: SearchRequest, api_key: str) -> safe_http.SafeResponse:
        """Make the web search API request."""

    @abstractmethod
    def parse(self, data: dict[str, Any]) -> list[SearchResult]:
        """Parse the web search API response."""


class BraveSearchProvider(SearchProvider):
    """
    The Brave Search API.

    https://api-dashboard.search.brave.com/app/documentation/web-search/get-started
    """

    name = WebsearchProvider.BRAVE.value
    url = "https://api.search.brave.com/res/v1/web/search"
    freshness = {"day": "pd", "week": "pw", "month": "pm", "year": "py"}

    def request(self, request: SearchRequest, api_key: str) -> safe_http.SafeResponse:
        query = request.query
        operators = self.site_operators(request.policy)
        if operators:
            query = f"{query} {operators}"
        params: dict[str, Any] = {
            "q": query,
            # request extra results, since some may be removed by the domain policy
            "count": min(20, request.max_results * 2),
            "safesearch": request.safe_search,
        }
        if request.country:
            params["country"] = request.country.upper()
        if request.language:
            params["search_lang"] = request.language
        if request.freshness:
            params["freshness"] = self.freshness[request.freshness]
        return safe_http.fetch(
            self.url,
            headers={"Accept": "application/json", "X-Subscription-Token": api_key},
            params=params,
            timeout=request.timeout,
            max_bytes=MAX_RESPONSE_BYTES,
        )

    def parse(self, data: dict[str, Any]) -> list[SearchResult]:
        web = data.get("web") or {}
        results = web.get("results") if isinstance(web, dict) else None
        return [
            SearchResult(
                title=clean_text(item.get("title"), MAX_TITLE_LENGTH),
                url=str(item.get("url") or ""),
                snippet=clean_text(item.get("description"), MAX_SNIPPET_LENGTH),
                published=item.get("page_age") or item.get("age") or None,
            )
            for item in (results or [])
            if isinstance(item, dict) and item.get("url")
        ]


class TavilySearchProvider(SearchProvider):
    """
    The Tavily Search API, which is designed for LLMs.

    https://docs.tavily.com/documentation/api-reference/endpoint/search

    .. note::

        Tavily localizes results by country name rather than by country code, so the plugin's
        ``country`` is not passed to Tavily.
    """

    name = WebsearchProvider.TAVILY.value
    url = "https://api.tavily.com/search"

    def request(self, request: SearchRequest, api_key: str) -> safe_http.SafeResponse:
        body: dict[str, Any] = {
            "query": request.query,
            "max_results": min(20, request.max_results * 2),
            "topic": "general",
            "search_depth": "basic",
            "include_answer": False,
            "include_raw_content": False,
            "include_published_date": True,
            "safe_search": request.safe_search != WebsearchSafeSearch.OFF.value,
        }
        if request.policy.allowed:
            body["include_domains"] = list(request.policy.allowed)
        if request.policy.blocked:
            body["exclude_domains"] = list(request.policy.blocked)
        if request.freshness:
            body["time_range"] = request.freshness
        if request.language:
            body["language"] = request.language
        return safe_http.fetch(
            self.url,
            method="POST",
            headers={"Accept": "application/json", "Authorization": f"Bearer {api_key}"},
            json_body=body,
            timeout=request.timeout,
            max_bytes=MAX_RESPONSE_BYTES,
        )

    def parse(self, data: dict[str, Any]) -> list[SearchResult]:
        return [
            SearchResult(
                title=clean_text(item.get("title"), MAX_TITLE_LENGTH),
                url=str(item.get("url") or ""),
                snippet=clean_text(item.get("content"), MAX_SNIPPET_LENGTH),
                published=item.get("published_date") or None,
            )
            for item in (data.get("results") or [])
            if isinstance(item, dict) and item.get("url")
        ]


PROVIDERS: dict[str, SearchProvider] = {
    WebsearchProvider.BRAVE.value: BraveSearchProvider(),
    WebsearchProvider.TAVILY.value: TavilySearchProvider(),
}


def get_provider(name: str) -> SearchProvider:
    """
    Return the web search API with the given name.

    :raises WebsearchError: If the name is not a supported web search API.
    """
    try:
        return PROVIDERS[name]
    except KeyError as e:
        raise WebsearchError(f"unsupported web search api: {name}") from e
