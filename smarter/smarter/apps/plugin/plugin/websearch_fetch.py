"""
Reading web pages for the WebsearchPlugin.

:py:func:`fetch_page` downloads a web page by URL, and returns its main content as Markdown,
which is compact, and preserves the structure and links that an LLM needs to understand
and cite a page.

**Behavior:**

- ``http`` URLs are upgraded to ``https``. Other schemes are rejected.
- The plugin's domain policy is enforced on the URL, and on every redirect.
- ``robots.txt`` is obeyed, per RFC 9309, unless the plugin disables it: if robots.txt is
  missing (4xx) the page may be read, and if it is unreachable (5xx, or a network error)
  the page may not.
- Only text formats are read: HTML, XHTML, plain text, Markdown, JSON, XML, RSS, Atom and
  CSV. Binary formats, e.g. PDF and images, are rejected.
- HTML is converted to Markdown. Scripts, styles, forms and embedded media are removed. If
  the page has a ``<main>`` or ``<article>`` element, only it is read. Otherwise page
  navigation, headers, footers and sidebars are removed. Links are made absolute, so that
  the LLM can cite, and read, them.
- Content longer than the plugin's limit is truncated, at a word boundary.

All requests are made with :py:mod:`smarter.apps.plugin.plugin.safe_http`.

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup, Comment
from bs4.element import NavigableString, Tag

from smarter.apps.plugin.const import PluginCacheTtl
from smarter.apps.plugin.manifest.models.websearch_plugin.const import (
    MAX_URL_LENGTH,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.policy import (
    DomainPolicy,
    url_host,
)
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from . import safe_http

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])

USER_AGENT_TOKEN = "SmarterBot"
"""The user agent token that robots.txt rules are matched against."""
USER_AGENT = f"Mozilla/5.0 (compatible; {USER_AGENT_TOKEN}/1.0; +https://smarter.sh)"
ACCEPT = "text/html,application/xhtml+xml,text/plain,text/markdown,application/json,application/xml;q=0.9,*/*;q=0.1"
MAX_PAGE_BYTES = 5_000_000
MAX_ROBOTS_BYTES = 512_000
MAX_REDIRECTS = 5
TRUNCATION_MARKER = "\n\n[content truncated]"

HTML_TYPES = ("text/html", "application/xhtml+xml")
TEXT_TYPES = ("text/plain", "text/markdown", "text/x-markdown", "text/csv")
JSON_TYPES = ("application/json", "application/ld+json")
XML_TYPES = ("application/xml", "text/xml", "application/rss+xml", "application/atom+xml")
SUPPORTED_TYPES = HTML_TYPES + TEXT_TYPES + JSON_TYPES + XML_TYPES

REMOVED_TAGS = (
    "script",
    "style",
    "noscript",
    "template",
    "iframe",
    "frame",
    "svg",
    "canvas",
    "form",
    "button",
    "input",
    "select",
    "textarea",
    "object",
    "embed",
    "video",
    "audio",
    "picture",
    "source",
    "link",
    "meta",
    "head",
)
BOILERPLATE_TAGS = ("nav", "header", "footer", "aside")
BLOCK_TAGS = (
    "p",
    "div",
    "section",
    "article",
    "main",
    "body",
    "html",
    "figure",
    "figcaption",
    "address",
    "details",
    "summary",
    "dl",
    "dt",
    "dd",
    "center",
)
HEADINGS = {f"h{level}": level for level in range(1, 7)}


class WebFetchError(SmarterValueError):
    """Raised when a web page cannot be read.

    The message is safe to show to the LLM.
    """


@dataclass
class FetchedPage:
    """
    A web page.

    :ivar url: The requested URL, after upgrading http to https.
    :ivar final_url: The URL of the page that was read, after any redirects. The LLM should cite it.
    :ivar title: The page title, if any.
    :ivar content: The page's main content, as Markdown for HTML, and as text for other formats.
    :ivar content_type: The media type of the page, e.g. ``text/html``.
    :ivar truncated: True if the content was truncated.
    :ivar retrieved_at: When the page was read.
    :ivar cached: True if the page was served from the cache.
    """

    url: str
    final_url: str
    title: Optional[str]
    content: str
    content_type: str
    truncated: bool = False
    retrieved_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cached: bool = False


def normalize_url(url: str) -> str:
    """
    Normalize a URL to read: upgrade http to https, and remove the fragment.

    :raises WebFetchError: If the value is not an http(s) URL with a host, or is too long.
    """
    if not isinstance(url, str) or not url.strip():
        raise WebFetchError("url must be a non-empty string.")
    url = url.strip()
    if len(url) > MAX_URL_LENGTH:
        raise WebFetchError(f"url must be at most {MAX_URL_LENGTH} characters.")
    try:
        parsed = urlparse(url)
    except ValueError as e:
        raise WebFetchError(f"invalid url: {url}") from e
    if parsed.scheme not in ("http", "https"):
        raise WebFetchError(f"only http and https urls can be read: {url}")
    if not parsed.hostname:
        raise WebFetchError(f"url has no host: {url}")
    return urlunparse(parsed._replace(scheme="https", fragment=""))


def robots_rules(url: str, timeout: float) -> Optional[RobotFileParser]:
    """
    Return the robots.txt rules of a URL's website, or None if the website may not be read.

    Per RFC 9309, a missing robots.txt (4xx) permits everything, and an unreachable robots.txt
    (5xx, or a network error) permits nothing. robots.txt files are cached for an hour.
    """
    parsed = urlparse(url)

    @cache_results(timeout=PluginCacheTtl.WEBSEARCH_ROBOTS_TXT)
    def get_cached_robots_txt(netloc: str) -> str:
        try:
            response = safe_http.fetch(
                f"https://{netloc}/robots.txt",
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
                max_bytes=MAX_ROBOTS_BYTES,
            )
        except safe_http.SafeHttpError as e:
            if e.status_code and 400 <= e.status_code < 500:
                return ""
            # raise rather than return so that an unreachable robots.txt is never cached.
            raise
        return response.content.decode("utf-8", errors="replace")

    try:
        text = get_cached_robots_txt(parsed.netloc.lower())
    except safe_http.SafeHttpError as e:
        logger.info("robots_rules() robots.txt of %s is unreachable: %s", parsed.netloc, e)
        return None
    parser = RobotFileParser()
    parser.parse(text.splitlines())
    return parser


def robots_permit(url: str, timeout: float) -> bool:
    """Return True if a website's robots.txt permits the Smarter user agent to read a URL."""
    rules = robots_rules(url, timeout)
    return rules is not None and rules.can_fetch(USER_AGENT_TOKEN, url)


def collapse_whitespace(text: str) -> str:
    """Collapse runs of whitespace to single spaces."""
    return re.sub(r"\s+", " ", text)


# pylint: disable=too-many-return-statements,too-many-branches,too-many-locals
def render(node, base_url: str, list_depth: int = 0) -> str:
    """Render an HTML node as Markdown."""
    if isinstance(node, Comment):
        return ""
    if isinstance(node, NavigableString):
        return collapse_whitespace(str(node))
    if not isinstance(node, Tag):
        return ""
    name = node.name.lower() if node.name else ""

    def children(depth: int = list_depth) -> str:
        return "".join(render(child, base_url, depth) for child in node.children)

    if name in HEADINGS:
        text = collapse_whitespace(node.get_text(" ")).strip()
        return f"\n\n{'#' * HEADINGS[name]} {text}\n\n" if text else ""
    if name == "br":
        return "\n"
    if name == "hr":
        return "\n\n---\n\n"
    if name == "pre":
        text = node.get_text().strip("\n")
        return f"\n\n```\n{text}\n```\n\n" if text.strip() else ""
    if name == "code":
        text = node.get_text()
        return f"`{text}`" if text.strip() else ""
    if name in ("strong", "b"):
        text = children().strip()
        return f"**{text}**" if text else ""
    if name in ("em", "i"):
        text = children().strip()
        return f"*{text}*" if text else ""
    if name == "a":
        text = children().strip()
        href = node.get("href")
        if isinstance(href, str) and href.strip() and not href.strip().startswith("#"):
            absolute = urljoin(base_url, href.strip())
            if urlparse(absolute).scheme in ("http", "https"):
                return f"[{text or absolute}]({absolute})"
        return text
    if name == "img":
        alt = node.get("alt")
        return f"[image: {collapse_whitespace(alt).strip()}]" if isinstance(alt, str) and alt.strip() else ""
    if name in ("ul", "ol"):
        items = [child for child in node.children if isinstance(child, Tag) and child.name == "li"]
        lines = []
        for index, item in enumerate(items, start=1):
            marker = f"{index}." if name == "ol" else "-"
            text = "".join(render(child, base_url, list_depth + 1) for child in item.children).strip()
            text = re.sub(r"\n{2,}", "\n", text).replace("\n", "\n" + "  " * (list_depth + 1))
            lines.append(f"{'  ' * list_depth}{marker} {text}")
        return "\n\n" + "\n".join(lines) + "\n\n" if lines else ""
    if name == "blockquote":
        text = children().strip()
        return "\n\n" + "\n".join(f"> {line}" for line in text.splitlines()) + "\n\n" if text else ""
    if name == "table":
        rows = []
        for row in node.find_all("tr"):
            cells = [collapse_whitespace(cell.get_text(" ")).strip() for cell in row.find_all(["th", "td"])]
            if any(cells):
                rows.append("| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")
        if not rows:
            return ""
        columns = rows[0].count(" | ") + 1
        rows.insert(1, "|" + " --- |" * columns)
        return "\n\n" + "\n".join(rows) + "\n\n"
    if name in BLOCK_TAGS:
        text = children().strip()
        return f"\n\n{text}\n\n" if text else ""
    return children()


def html_to_markdown(html: bytes, base_url: str, encoding: Optional[str] = None) -> tuple[Optional[str], str]:
    """
    Convert an HTML page to Markdown.

    :param html: The HTML document.
    :param base_url: The URL of the page, to make links absolute.
    :param encoding: The character encoding declared by the server, if any.
    :return: A tuple of the page title and its main content as Markdown.
    """
    soup = BeautifulSoup(html, "lxml", from_encoding=encoding)
    title = collapse_whitespace(soup.title.get_text()).strip() if soup.title else None
    base = soup.find("base", href=True)
    if isinstance(base, Tag) and isinstance(base.get("href"), str):
        base_url = urljoin(base_url, str(base["href"]))
    for tag in soup.find_all(REMOVED_TAGS):
        tag.decompose()
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    root = soup.find("main") or soup.find("article")
    if not isinstance(root, Tag):
        root = soup.body if isinstance(soup.body, Tag) else soup
        for tag in root.find_all(BOILERPLATE_TAGS):
            tag.decompose()
    markdown = render(root, base_url)
    markdown = "\n".join(line.rstrip() for line in markdown.splitlines())
    markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()
    return title or None, markdown


def decode(content: bytes, charset: Optional[str]) -> str:
    """Decode a response body, falling back to UTF-8."""
    try:
        return content.decode(charset or "utf-8", errors="replace")
    except LookupError:
        return content.decode("utf-8", errors="replace")


def truncate(content: str, max_characters: int) -> tuple[str, bool]:
    """Truncate content to a maximum number of characters, at a word boundary if possible."""
    if len(content) <= max_characters:
        return content, False
    cut = content[:max_characters]
    boundary = max(cut.rfind(" "), cut.rfind("\n"))
    if boundary > max_characters * 0.8:
        cut = cut[:boundary]
    return cut.rstrip() + TRUNCATION_MARKER, True


def make_redirect_policy(policy: DomainPolicy, respect_robots_txt: bool, timeout: float) -> Callable[[str], None]:
    """Return a safe_http redirect policy that enforces the domain policy and robots.txt on each redirect."""

    def redirect_policy(url: str) -> None:
        if not policy.permits_url(url):
            raise safe_http.SafeHttpError(f"the page redirected to {url_host(url)}, which is not permitted.")
        if respect_robots_txt and not robots_permit(url, timeout):
            raise safe_http.SafeHttpError(f"the page redirected to {url}, which robots.txt does not permit reading.")

    return redirect_policy


# pylint: disable=too-many-arguments
def fetch_page(
    url: str,
    *,
    policy: DomainPolicy = DomainPolicy(),
    max_characters: int = 20_000,
    timeout: float = safe_http.DEFAULT_TIMEOUT,
    respect_robots_txt: bool = True,
    cache_ttl: int = smarter_settings.cache_expiration,
) -> FetchedPage:
    """
    Read a web page, and return its main content.

    The HTTP response is cached for ``cache_ttl`` seconds, keyed on the URL and on everything
    that decides whether its redirects may be followed: the domain policy and
    ``respect_robots_txt``. Failed requests are never cached.

    :param url: The URL of the page.
    :param policy: The domain policy that the URL, and any redirects, must satisfy.
    :param max_characters: The maximum number of characters of content to return.
    :param timeout: Seconds to wait for each request.
    :param respect_robots_txt: Whether to obey the website's robots.txt.
    :param cache_ttl: Seconds to cache the HTTP response. 0 disables caching.
    :return: The page.
    :raises WebFetchError: If the page cannot be read. The message is safe to show to the LLM.

    **Example:**

    .. code-block:: python

        page = fetch_page("https://docs.python.org/3/library/json.html", max_characters=5000)
        page.title  # 'json — JSON encoder and decoder — Python 3 documentation'
    """
    url = normalize_url(url)
    if not policy.permits_url(url):
        raise WebFetchError(
            f"{url_host(url)} is not permitted by this plugin's domain policy. {policy.describe()}".strip()
        )
    if respect_robots_txt and not robots_permit(url, timeout):
        raise WebFetchError(f"the website's robots.txt does not permit reading {url}.")
    cached = True

    @cache_results(timeout=cache_ttl)
    def get_response(
        url: str, allowed: tuple[str, ...], blocked: tuple[str, ...], respect_robots_txt: bool
    ) -> tuple[safe_http.SafeResponse, datetime]:
        nonlocal cached
        cached = False
        # failures raise SafeHttpError, so that they are never cached.
        response = safe_http.fetch(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": ACCEPT},
            timeout=timeout,
            max_bytes=MAX_PAGE_BYTES,
            max_redirects=MAX_REDIRECTS,
            redirect_policy=make_redirect_policy(
                DomainPolicy(allowed=allowed, blocked=blocked), respect_robots_txt, timeout
            ),
        )
        return response, datetime.now(timezone.utc)

    try:
        response, retrieved_at = get_response(url, policy.allowed, policy.blocked, respect_robots_txt)
    except safe_http.SafeHttpError as e:
        if e.status_code:
            raise WebFetchError(f"{url} could not be read: HTTP {e.status_code}.") from e
        raise WebFetchError(f"{url} could not be read: {e}") from e

    content_type = response.content_type or "text/html"
    if content_type not in SUPPORTED_TYPES:
        raise WebFetchError(
            f"{response.url} is {content_type}, which cannot be read. Only web pages and text formats can be read."
        )
    title: Optional[str] = None
    if content_type in HTML_TYPES:
        title, content = html_to_markdown(response.content, response.url, response.charset)
    else:
        content = decode(response.content, response.charset).strip()
        if content_type in JSON_TYPES:
            try:
                content = json.dumps(json.loads(content), indent=2, ensure_ascii=False)
            except ValueError:
                pass
    content, truncated = truncate(content, max_characters)
    return FetchedPage(
        url=url,
        final_url=response.url,
        title=title,
        content=content,
        content_type=content_type,
        truncated=truncated,
        retrieved_at=retrieved_at,
        cached=cached,
    )


# restricts the public api, and its Sphinx documentation, to this module's own
# names, excluding those it imports, like bs4's Tag.
__all__ = [
    "ACCEPT",
    "BLOCK_TAGS",
    "BOILERPLATE_TAGS",
    "HEADINGS",
    "HTML_TYPES",
    "JSON_TYPES",
    "MAX_PAGE_BYTES",
    "MAX_REDIRECTS",
    "MAX_ROBOTS_BYTES",
    "REMOVED_TAGS",
    "SUPPORTED_TYPES",
    "TEXT_TYPES",
    "TRUNCATION_MARKER",
    "USER_AGENT",
    "USER_AGENT_TOKEN",
    "XML_TYPES",
    "FetchedPage",
    "WebFetchError",
    "collapse_whitespace",
    "decode",
    "fetch_page",
    "html_to_markdown",
    "make_redirect_policy",
    "normalize_url",
    "render",
    "robots_permit",
    "robots_rules",
    "truncate",
]
