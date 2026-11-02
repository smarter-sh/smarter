"""
The indexer of The Smarter Project's blog, which copies its posts from WordPress into the database.

:func:`index_blog` brings the blog's :class:`~smarter.apps.mcpserver.models.RepositoryIndex`
up to date with its published posts, so that the MCP server's ``search_blog`` and
``read_blog_post`` tools can read them as they read a repository's documentation:

1. It reads every published post from the blog's public WordPress REST api,
   ``/wp-json/wp/v2/posts``, 100 posts a request.
2. It fingerprints the posts by their ids and modification times. If the fingerprint is
   already indexed, there is nothing to do.
3. Otherwise it converts each post's html to Markdown-like text, with its illustrations as
   Markdown images, ``![alt](url)``, which Smarter Chat displays, and replaces the blog's
   files in one transaction, with :func:`~smarter.apps.mcpserver.index.indexer.store_files`. A
   post's path is its permalink's path, e.g. ``2026/10/26/release-smarter-api-v0-6``, and
   the fingerprint is stored as the index's ``commit_sha``.

The blog is stored like a repository, under the blog's name, so that
:func:`~smarter.apps.mcpserver.index.search.search_files` searches it like any other. The Celery task
:func:`smarter.apps.mcpserver.tasks.index_blog` calls :func:`index_blog`.

The url is the fixed url of the project's public blog, not a user-supplied one, so the
requests do not go through :mod:`smarter.apps.llmtool.plugin.safe_http`.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import hashlib
import html
import re
import textwrap
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from smarter.apps.mcpserver.const import USER_AGENT
from smarter.apps.mcpserver.exceptions import SmarterMCPServerIndexError
from smarter.apps.mcpserver.models import (
    RepositoryFileKind,
    RepositoryIndex,
    RepositoryIndexStatus,
)
from smarter.apps.mcpserver.repositories import ProjectBlog, project_blog
from smarter.apps.mcpserver.signals import (
    mcpserver_repository_index_failed,
    mcpserver_repository_indexed,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .indexer import (
    MAX_FILE_BYTES,
    MAX_TITLE_LENGTH,
    REQUEST_TIMEOUT,
    ArchiveFile,
    count_lines,
    markdown_image,
    store_files,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

POSTS_PER_PAGE = 100
"""The most posts that the WordPress REST api returns in one request."""

MAX_PAGES = 20
"""The maximum number of requests for posts, i.e. at most 2000 posts."""

POST_FIELDS = "id,date,modified,slug,link,title,content"
"""The fields of a post to request, so that WordPress leaves out the rest."""

LINE_WIDTH = 100
"""The column at which paragraphs, list items and quotes are wrapped."""

HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
"""The html heading elements, and their levels, which become as many ``#`` in Markdown."""

SKIPPED_ELEMENTS = ("hr", "br", "script", "style", "noscript", "svg", "iframe")
"""The html elements that are dropped, with their contents: rules, line breaks, scripts and embeds."""

WHITESPACE = re.compile(r"\s+")
"""A run of whitespace, which html collapses to one space."""


class WordPressRendered(BaseModel):
    """A rendered field of a WordPress post, e.g. its title or content, which WordPress returns as ``{"rendered": "<html>"}``."""

    model_config = ConfigDict(extra="ignore")

    rendered: str = ""
    """The field's html, as WordPress renders it for the published page."""


class WordPressPost(BaseModel):
    """
    A post, as the WordPress REST api returns it.

    Only the fields that the indexer reads are modeled. WordPress and its plugins add others,
    e.g. ``protected`` and ``raw``, which are ignored.
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    """The post's WordPress id, which the fingerprint uses."""

    date: datetime
    """When the post was published."""

    modified: datetime
    """When the post was last changed.

    A change makes the fingerprint change, and the blog is indexed again.
    """

    slug: str
    """The post's slug, e.g. ``release-smarter-api-v0-6``, its path if its permalink has none."""

    link: str
    """The post's permalink, e.g. ``https://blog.smarter.sh/2026/10/26/release-smarter-api-v0-6/``."""

    title: WordPressRendered
    """The post's title, as html."""

    content: WordPressRendered
    """The post's body, as html."""


WORDPRESS_POSTS = TypeAdapter(list[WordPressPost])
"""Validates a page of the WordPress REST api's posts, a JSON list, into :class:`WordPressPost` objects."""


def inline_text(element: Tag) -> str:
    """
    Return an element's text on one line, with inline code in backticks.

    The element is changed in place: each ``code`` element is replaced by its text in backticks,
    and a space is inserted before each ``br``, ``li`` and ``p``, so that their words do not run
    together.

    :param element: e.g. a paragraph, a list item or a table cell.
    :returns: The text, with its whitespace collapsed.
    """
    for code in element.find_all("code"):
        code.replace_with(f"`{code.get_text()}`")
    for separated in element.find_all(["br", "li", "p"]):
        separated.insert_before(" ")
    text = element.get_text()
    collapsed = WHITESPACE.sub(" ", text).strip()
    return collapsed


def wrap(text: str, first: str = "", rest: str = "") -> str:
    """
    Wrap a block's text at :data:`LINE_WIDTH` columns, as the reStructuredText documentation is.

    A search shows a passage of lines around the best one, so a paragraph on one long line
    would be cut short. Long words, e.g. urls, and hyphenated words are never broken.

    :param text: The text.
    :param first: The prefix of the first line, e.g. ``- ``.
    :param rest: The prefix of the other lines, e.g. two spaces.
    :returns: The wrapped text.
    """
    wrapped = textwrap.fill(
        text,
        width=LINE_WIDTH,
        initial_indent=first,
        subsequent_indent=rest,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return wrapped


def image_url(image: Tag, base_url: str = "") -> Optional[str]:
    """
    Return the absolute url of an image, if it can be a Markdown image's.

    :param image: An ``img`` element.
    :param base_url: The url that a relative ``src`` is relative to, e.g. the blog's.
    :returns: The url, or None if the image has no ``src``, its url is not http(s), e.g. a data url,
        or it has a space or a parenthesis, which would break the Markdown.
    """
    src = image.get("src")
    if not isinstance(src, str):
        return None
    src = src.strip()
    if not src:
        return None
    base = ""
    if base_url:
        base = base_url + "/"
    url = urljoin(base, src)
    if urlparse(url).scheme not in ("http", "https"):
        return None
    for character in " ()":
        if character in url:
            return None
    return url


def image_markdown(image: Tag, base_url: str = "") -> Optional[str]:
    """
    Return an image as a Markdown image, ``![alt](url)``, which Smarter Chat displays.

    The LLM cannot see the image, so its alt text is what tells the LLM what it shows. An alt
    text too long to fit on the image's line, see :func:`~smarter.apps.mcpserver.index.indexer.markdown_image`,
    is given in full on the lines after it.

    :param image: An ``img`` element.
    :param base_url: The url that a relative ``src`` is relative to, e.g. the blog's.
    :returns: The Markdown, or None if the image has no http(s) url, e.g. a data url.
    """
    url = image_url(image, base_url)
    if url is None:
        return None
    alt = image.get("alt")
    if not isinstance(alt, str):
        alt = ""
    description = WHITESPACE.sub(" ", alt).strip()
    markdown, complete = markdown_image(description, url)
    if complete:
        return markdown
    escaped = description.replace("[", "(").replace("]", ")")
    full_description = wrap(f"Illustration: {escaped}")
    return markdown + "\n" + full_description


def list_block(element: Tag) -> str:
    """
    Return an html list as a Markdown list, one wrapped item per entry.

    :param element: A ``ul`` or ``ol`` element. Only its own items are read: a nested list's items
        are part of their parent item's text.
    :returns: The list, with ``- `` before each item of a ``ul``, and ``1. ``, ``2. ``, and so on,
        of an ``ol``.
    """
    is_ordered = element.name == "ol"
    items = element.find_all("li", recursive=False)
    wrapped_items = []
    for number, item in enumerate(items, start=1):
        if is_ordered:
            first = f"{number}. "
            rest = "   "
        else:
            first = "- "
            rest = "  "
        wrapped_items.append(wrap(inline_text(item), first, rest))
    return "\n".join(wrapped_items)


def table_block(element: Tag) -> str:
    """
    Return an html table as a Markdown table, one row per line.

    No separator row is added after the header: the table is for search, and for an LLM to read.

    :param element: A ``table`` element.
    :returns: The rows, e.g. ``| Version | Date |``.
    """
    rows = []
    for row in element.find_all("tr"):
        cells = [inline_text(cell) for cell in row.find_all(["th", "td"])]
        rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(rows)


def html_blocks(element: Tag, blocks: list[str], base_url: str = "") -> None:
    """
    Append the Markdown-like blocks of an element's children to a list.

    Headings, paragraphs, lists, tables, quotes, code blocks and images become Markdown.
    Rules, scripts and embeds are dropped (see :data:`SKIPPED_ELEMENTS`), and other containers,
    e.g. ``div`` and ``figure``, are walked, recursively.

    :param element: The element. Its children's text is changed in place (see :func:`inline_text`).
    :param blocks: The blocks, appended to.
    :param base_url: The url that relative image urls are relative to.
    """
    for child in element.children:
        if isinstance(child, NavigableString):
            text = WHITESPACE.sub(" ", str(child)).strip()
            if text:
                blocks.append(text)
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name
        if name in HEADINGS:
            hashes = "#" * HEADINGS[name]
            blocks.append(hashes + " " + inline_text(child))
        elif name == "pre":
            code = child.get_text().strip("\n")
            blocks.append("```\n" + code + "\n```")
        elif name in ("ul", "ol"):
            blocks.append(list_block(child))
        elif name == "table":
            blocks.append(table_block(child))
        elif name == "blockquote":
            blocks.append(wrap(inline_text(child), "> ", "> "))
        elif name in ("p", "figcaption"):
            # The images are read first, since inline_text() changes the element.
            images = [image_markdown(image, base_url) for image in child.find_all("img")]
            text = inline_text(child)
            if text:
                blocks.append(wrap(text))
            for markdown in images:
                if markdown:
                    blocks.append(markdown)
        elif name == "img":
            markdown = image_markdown(child, base_url)
            if markdown:
                blocks.append(markdown)
        elif name in SKIPPED_ELEMENTS:
            continue
        else:
            html_blocks(child, blocks, base_url)


def html_to_text(content: str, base_url: str = "") -> str:
    """
    Return a post's html as Markdown-like text, for search and for an LLM to read.

    :param content: The post's rendered html.
    :param base_url: The url that relative image urls are relative to, e.g. the blog's.
    :returns: The text, one block per paragraph, heading, list, table, code block or image,
        separated by blank lines.
    """
    soup = BeautifulSoup(content, "lxml")
    root = soup.body
    if root is None:
        root = soup
    blocks: list[str] = []
    html_blocks(root, blocks, base_url)
    return "\n\n".join(blocks)


def post_path(post: WordPressPost) -> str:
    """
    Return a post's path: its permalink's path, or its slug if it has none.

    :param post: The post.
    :returns: e.g. ``2026/10/26/release-smarter-api-v0-6``.
    """
    path = urlparse(post.link).path.strip("/")
    if path:
        return path
    return post.slug


def post_title(post: WordPressPost) -> str:
    """
    Return a post's title, as plain text.

    WordPress renders a title as html, with entities such as ``&#8217;``, which are unescaped.

    :param post: The post.
    :returns: The title, with its whitespace collapsed.
    """
    soup = BeautifulSoup(post.title.rendered, "lxml")
    text = html.unescape(soup.get_text())
    title = WHITESPACE.sub(" ", text).strip()
    return title


def post_file(blog: ProjectBlog, post: WordPressPost) -> ArchiveFile:
    """
    Return a post as a file of the blog's index.

    The text starts with the post's title, dates and url, so that a reader of any part of it
    can cite it. A post longer than :data:`~smarter.apps.mcpserver.index.indexer.MAX_FILE_BYTES` is
    truncated.

    :param blog: The blog.
    :param post: The post.
    :returns: The file.
    """
    path = post_path(post)
    title = post_title(post)
    dates = f"Published {post.date:%Y-%m-%d}"
    if post.modified.date() != post.date.date():
        dates += f", updated {post.modified:%Y-%m-%d}"
    url = blog.post_url(path)
    body = html_to_text(post.content.rendered, blog.url)
    content = f"# {title}\n\n{dates}: {url}\n\n{body}\n"
    encoded = content.encode()
    if len(encoded) > MAX_FILE_BYTES:
        # Cutting the bytes may split a character, whose remains are dropped.
        truncated = encoded[:MAX_FILE_BYTES].decode(errors="ignore")
        content = truncated + "\n\n[The post is truncated.]\n"
        encoded = content.encode()
    return ArchiveFile(
        path=path,
        kind=RepositoryFileKind.DOCUMENTATION,
        title=title[:MAX_TITLE_LENGTH],
        content=content,
        size=len(encoded),
        line_count=count_lines(content),
    )


def total_pages(response: requests.Response) -> int:
    """
    Read how many pages of posts there are, from a WordPress REST api response.

    :param response: A response of the posts api.
    :returns: The ``X-WP-TotalPages`` header's value, or 1 if it is missing or not a number.
    """
    header = response.headers.get("X-WP-TotalPages")
    if not header:
        return 1
    try:
        pages = int(header)
    except ValueError:
        return 1
    return pages


def fetch_posts(blog: ProjectBlog) -> list[WordPressPost]:
    """
    Return the blog's published posts, newest first, from its WordPress REST api.

    The posts are read a page of :data:`POSTS_PER_PAGE` at a time, until the last page, which
    WordPress names in its ``X-WP-TotalPages`` header, an empty page, or :data:`MAX_PAGES` pages.

    Side effects: one unauthenticated HTTP request to the blog for each page.

    :param blog: The blog.
    :returns: The posts.
    :raises SmarterMCPServerIndexError: If the blog does not answer with posts.
    """
    posts: list[WordPressPost] = []
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    page = 1
    while True:
        params = {
            "per_page": POSTS_PER_PAGE,
            "page": page,
            "_fields": POST_FIELDS,
            "orderby": "date",
            "order": "desc",
        }
        try:
            response = requests.get(blog.posts_api_url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.RequestException as e:
            raise SmarterMCPServerIndexError(f"{blog.url} could not be reached: {type(e).__name__}") from e
        if response.status_code != 200:
            raise SmarterMCPServerIndexError(
                f"{blog.url} responded with HTTP {response.status_code} for page {page} of its posts"
            )
        try:
            batch = WORDPRESS_POSTS.validate_json(response.content)
        except ValidationError as e:
            raise SmarterMCPServerIndexError(
                f"{blog.url} did not respond with a list of posts: {e.error_count()} errors"
            ) from e
        posts.extend(batch)
        if not batch:
            return posts
        if page >= total_pages(response):
            return posts
        if page >= MAX_PAGES:
            return posts
        page += 1


def posts_fingerprint(posts: list[WordPressPost]) -> str:
    """
    Return a fingerprint of the posts, which changes when a post is published, changed or removed.

    It is a SHA-1 of each post's id and modification time, in the order of their ids, and is not
    used for security. It is stored as the index's ``commit_sha``, which has room for a sha.

    :param posts: The posts.
    :returns: 40 hexadecimal characters, the size of a commit's sha.
    """
    posts_by_id = sorted(posts, key=lambda post: post.id)
    versions = []
    for post in posts_by_id:
        versions.append(f"{post.id}:{post.modified.isoformat()}")
    text = "\n".join(versions)
    fingerprint = hashlib.sha1(text.encode(), usedforsecurity=False).hexdigest()
    return fingerprint


def index_blog(force: bool = False, blog: Optional[ProjectBlog] = None) -> RepositoryIndex:
    """
    Bring the blog's index up to date with its published posts.

    If the posts' fingerprint is already indexed, only a previous error is cleared. Two posts with
    the same path are indexed once, the newer one.

    A failure never raises: the index keeps its posts, and stays ready if it was, so that the tools
    can go on answering from them, and the failure is recorded in its ``error``.

    Side effects: HTTP requests to the blog (see :func:`fetch_posts`), database writes (the index's
    row is created if it does not exist, and see :func:`~smarter.apps.mcpserver.index.indexer.store_files`),
    and a signal: ``mcpserver_repository_indexed`` when the posts are replaced, whose receiver makes
    the cached tool results stale, or ``mcpserver_repository_index_failed``.

    :param force: Index the posts even if they are already indexed.
    :param blog: The blog. Defaults to :func:`~smarter.apps.mcpserver.repositories.project_blog`.
    :returns: The blog's index. If indexing fails, its ``error`` says why, and an existing
        index is kept.

    **Example usage**::

        index = index_blog()
        index.file_count  # the number of posts
    """
    if blog is None:
        blog = project_blog()
    index, _ = RepositoryIndex.objects.get_or_create(repository=blog.name)
    try:
        posts = fetch_posts(blog)
        fingerprint = posts_fingerprint(posts)
        is_up_to_date = index.is_ready and index.commit_sha == fingerprint
        if is_up_to_date and not force:
            logger.info("%s.index_blog() %s is up to date: %s posts.", logger_prefix, blog.name, len(posts))
            if index.error:
                RepositoryIndex.objects.filter(pk=index.pk).update(error=None)
                index.error = None
            return index
        # The posts are newest first, so the first post of a path is kept.
        files_by_path: dict[str, ArchiveFile] = {}
        for post in posts:
            file = post_file(blog, post)
            if file.path not in files_by_path:
                files_by_path[file.path] = file
        files = list(files_by_path.values())
        index = store_files(index, fingerprint, files)
    except SmarterMCPServerIndexError as e:
        # Keep a ready index ready, so that its posts are still searched.
        if index.is_ready:
            status = RepositoryIndexStatus.READY
        else:
            status = RepositoryIndexStatus.FAILED
        RepositoryIndex.objects.filter(pk=index.pk).update(status=status, error=e.message)
        index.refresh_from_db()
        mcpserver_repository_index_failed.send(sender=index_blog, repository=blog.name, error=e.message)
        return index
    mcpserver_repository_indexed.send(sender=index_blog, index=index)
    return index


__all__ = [
    "WORDPRESS_POSTS",
    "WordPressPost",
    "fetch_posts",
    "html_to_text",
    "index_blog",
    "post_file",
    "posts_fingerprint",
]
