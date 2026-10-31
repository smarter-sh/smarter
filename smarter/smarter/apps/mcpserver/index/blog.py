"""
The indexer of The Smarter Project's blog.

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
    REQUEST_TIMEOUT,
    ArchiveFile,
    markdown_image,
    store_files,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPSERVER_LOGGING])

POSTS_PER_PAGE = 100
"""The most posts that the WordPress REST api returns in one request."""
MAX_PAGES = 20
"""The maximum number of requests for posts, i.e. at most 2000 posts."""
POST_FIELDS = "id,date,modified,slug,link,title,content"
"""The fields of a post to request, so that WordPress leaves out the rest."""
LINE_WIDTH = 100
"""The column at which paragraphs, list items and quotes are wrapped."""
HEADINGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
WHITESPACE = re.compile(r"\s+")


class WordPressRendered(BaseModel):
    """A rendered field of a WordPress post, e.g. its title or content."""

    model_config = ConfigDict(extra="ignore")

    rendered: str = ""


class WordPressPost(BaseModel):
    """
    A post, as the WordPress REST api returns it.

    Only the fields that the indexer reads are modeled. WordPress and its plugins add others,
    e.g. ``protected`` and ``raw``, which are ignored.
    """

    model_config = ConfigDict(extra="ignore")

    id: int
    date: datetime
    modified: datetime
    slug: str
    link: str
    title: WordPressRendered
    content: WordPressRendered


WORDPRESS_POSTS = TypeAdapter(list[WordPressPost])


def inline_text(element: Tag) -> str:
    """
    Return an element's text on one line, with inline code in backticks.

    :param element: e.g. a paragraph, a list item or a table cell.
    :returns: The text, with its whitespace collapsed.
    """
    for code in element.find_all("code"):
        code.replace_with(f"`{code.get_text()}`")
    for separated in element.find_all(["br", "li", "p"]):
        separated.insert_before(" ")
    return WHITESPACE.sub(" ", element.get_text()).strip()


def wrap(text: str, first: str = "", rest: str = "") -> str:
    """
    Wrap a block's text at :data:`LINE_WIDTH` columns, as the reStructuredText documentation is.

    A search shows a passage of lines around the best one, so a paragraph on one long line
    would be cut short.

    :param text: The text.
    :param first: The prefix of the first line, e.g. ``- ``.
    :param rest: The prefix of the other lines, e.g. two spaces.
    :returns: The wrapped text.
    """
    return textwrap.fill(
        text,
        width=LINE_WIDTH,
        initial_indent=first,
        subsequent_indent=rest,
        break_long_words=False,
        break_on_hyphens=False,
    )


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
    src = image.get("src")
    if not isinstance(src, str) or not src.strip():
        return None
    url = urljoin(base_url + "/" if base_url else "", src.strip())
    if urlparse(url).scheme not in ("http", "https") or any(character in url for character in " ()"):
        return None
    alt = image.get("alt")
    description = WHITESPACE.sub(" ", alt if isinstance(alt, str) else "").strip()
    markdown, complete = markdown_image(description, url)
    if complete:
        return markdown
    return markdown + "\n" + wrap(f"Illustration: {description.replace('[', '(').replace(']', ')')}")


def html_blocks(element: Tag, blocks: list[str], base_url: str = "") -> None:
    """
    Append the Markdown-like blocks of an element's children to a list.

    Headings, paragraphs, lists, tables, quotes, code blocks and images become Markdown.
    Rules are dropped, and other containers, e.g. ``div`` and ``figure``, are walked.

    :param element: The element.
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
            blocks.append("#" * HEADINGS[name] + " " + inline_text(child))
        elif name == "pre":
            blocks.append("```\n" + child.get_text().strip("\n") + "\n```")
        elif name in ("ul", "ol"):
            items = child.find_all("li", recursive=False)
            blocks.append(
                "\n".join(
                    wrap(inline_text(item), f"{number}. " if name == "ol" else "- ", "   " if name == "ol" else "  ")
                    for number, item in enumerate(items, start=1)
                )
            )
        elif name == "table":
            rows = [
                "| " + " | ".join(inline_text(cell) for cell in row.find_all(["th", "td"])) + " |"
                for row in child.find_all("tr")
            ]
            blocks.append("\n".join(rows))
        elif name == "blockquote":
            blocks.append(wrap(inline_text(child), "> ", "> "))
        elif name in ("p", "figcaption"):
            images = [image_markdown(image, base_url) for image in child.find_all("img")]
            text = inline_text(child)
            if text:
                blocks.append(wrap(text))
            blocks.extend(markdown for markdown in images if markdown)
        elif name == "img":
            markdown = image_markdown(child, base_url)
            if markdown:
                blocks.append(markdown)
        elif name in ("hr", "br", "script", "style", "noscript", "svg", "iframe"):
            continue
        else:
            html_blocks(child, blocks, base_url)


def html_to_text(content: str, base_url: str = "") -> str:
    """
    Return a post's html as Markdown-like text, for search and for an LLM to read.

    :param content: The post's rendered html.
    :param base_url: The url that relative image urls are relative to, e.g. the blog's.
    :returns: The text, one block per paragraph, heading, list, table, code block or image.
    """
    soup = BeautifulSoup(content, "lxml")
    blocks: list[str] = []
    html_blocks(soup.body or soup, blocks, base_url)
    return "\n\n".join(blocks)


def post_path(post: WordPressPost) -> str:
    """
    Return a post's path: its permalink's path, or its slug if it has none.

    :param post: The post.
    :returns: e.g. ``2026/10/26/release-smarter-api-v0-6``.
    """
    return urlparse(post.link).path.strip("/") or post.slug


def post_title(post: WordPressPost) -> str:
    """Return a post's title, as plain text."""
    return WHITESPACE.sub(" ", html.unescape(BeautifulSoup(post.title.rendered, "lxml").get_text())).strip()


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
    content = f"# {title}\n\n{dates}: {blog.post_url(path)}\n\n{html_to_text(post.content.rendered, blog.url)}\n"
    encoded = content.encode()
    if len(encoded) > MAX_FILE_BYTES:
        content = encoded[:MAX_FILE_BYTES].decode(errors="ignore") + "\n\n[The post is truncated.]\n"
        encoded = content.encode()
    return ArchiveFile(
        path=path,
        kind=RepositoryFileKind.DOCUMENTATION,
        title=title[:255],
        content=content,
        size=len(encoded),
        line_count=content.count("\n") + (0 if content.endswith("\n") else 1),
    )


def fetch_posts(blog: ProjectBlog) -> list[WordPressPost]:
    """
    Return the blog's published posts, newest first, from its WordPress REST api.

    :param blog: The blog.
    :returns: The posts.
    :raises SmarterMCPServerIndexError: If the blog does not answer with posts.
    """
    posts: list[WordPressPost] = []
    page = 1
    while True:
        try:
            response = requests.get(
                blog.posts_api_url,
                params={
                    "per_page": POSTS_PER_PAGE,
                    "page": page,
                    "_fields": POST_FIELDS,
                    "orderby": "date",
                    "order": "desc",
                },
                headers={"Accept": "application/json", "User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            )
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
        try:
            total_pages = int(response.headers.get("X-WP-TotalPages") or 1)
        except ValueError:
            total_pages = 1
        if not batch or page >= total_pages or page >= MAX_PAGES:
            return posts
        page += 1


def posts_fingerprint(posts: list[WordPressPost]) -> str:
    """
    Return a fingerprint of the posts, which changes when a post is published, changed or removed.

    :param posts: The posts.
    :returns: 40 hexadecimal characters, the size of a commit's sha.
    """
    text = "\n".join(f"{post.id}:{post.modified.isoformat()}" for post in sorted(posts, key=lambda post: post.id))
    return hashlib.sha1(text.encode(), usedforsecurity=False).hexdigest()


def index_blog(force: bool = False, blog: Optional[ProjectBlog] = None) -> RepositoryIndex:
    """
    Bring the blog's index up to date with its published posts.

    :param force: Index the posts even if they are already indexed.
    :param blog: The blog. Defaults to :func:`~smarter.apps.mcpserver.repositories.project_blog`.
    :returns: The blog's index. If indexing fails, its ``error`` says why, and an existing
        index is kept.

    **Example usage**::

        index = index_blog()
        index.file_count  # the number of posts
    """
    prefix = f"{logging.SmarterFormattedText.text(__name__)}.index_blog()"
    blog = blog or project_blog()
    index, _ = RepositoryIndex.objects.get_or_create(repository=blog.name)
    try:
        posts = fetch_posts(blog)
        fingerprint = posts_fingerprint(posts)
        if index.is_ready and index.commit_sha == fingerprint and not force:
            logger.info("%s %s is up to date: %s posts.", prefix, blog.name, len(posts))
            if index.error:
                RepositoryIndex.objects.filter(pk=index.pk).update(error=None)
                index.error = None
            return index
        files = {}
        for post in posts:
            file = post_file(blog, post)
            files.setdefault(file.path, file)
        index = store_files(index, fingerprint, list(files.values()))
    except SmarterMCPServerIndexError as e:
        status = RepositoryIndexStatus.READY if index.is_ready else RepositoryIndexStatus.FAILED
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
