"""
Tests for smarter.apps.mcpserver.index.blog.

The blog is never contacted: ``requests.get`` is replaced, and serves the posts of
./data/blog-posts.yaml as a fake WordPress REST api.
"""

from unittest import mock

import requests

from smarter.apps.mcpserver.index import blog as blog_module
from smarter.apps.mcpserver.index import indexer
from smarter.apps.mcpserver.index.blog import (
    fetch_posts,
    html_to_text,
    index_blog,
    post_file,
    post_path,
    posts_fingerprint,
)
from smarter.apps.mcpserver.models import (
    RepositoryFile,
    RepositoryFileKind,
    RepositoryIndex,
    RepositoryIndexStatus,
)
from smarter.apps.mcpserver.repositories import ProjectBlog, project_blog
from smarter.apps.mcpserver.signals import (
    mcpserver_repository_index_failed,
    mcpserver_repository_indexed,
)
from smarter.lib import json

from .base_classes import BLOG_URL, MCPServerTestBase, blog_posts

REQUESTS_PATCH = "smarter.apps.mcpserver.index.blog.requests.get"
SECRETS_POST = "2026/10/20/keeping-secrets-out-of-the-logs"


class FakeResponse:
    """A requests response, for a fake WordPress."""

    def __init__(self, status_code: int = 200, content: bytes = b"[]", total_pages: str = "1"):
        self.status_code = status_code
        self.content = content
        self.headers = {"X-WP-TotalPages": total_pages}


class TestBlog(MCPServerTestBase):
    """Test the blog's indexer."""

    def setUp(self):
        super().setUp()
        self.test_blog = ProjectBlog(
            name=f"{self.blog.name}-indexer", title="a blog", description="A blog.", url=BLOG_URL
        )
        self.addCleanup(RepositoryIndex.objects.filter(repository=self.test_blog.name).delete)
        self.posts = blog_posts()
        self.posts_json = [post.model_dump(mode="json") for post in self.posts]

    def wordpress(self, pages: list[list], status_code: int = 200):
        """Return a fake requests.get that serves pages of posts."""

        def get(url, params=None, headers=None, timeout=None):
            self.assertEqual(url, f"{BLOG_URL}/wp-json/wp/v2/posts")
            self.assertEqual(params["per_page"], 100)
            page = pages[params["page"] - 1]
            return FakeResponse(status_code, json.dumps(page).encode(), str(len(pages)))

        return get

    # -------------------------------------------------------------------------
    # html
    # -------------------------------------------------------------------------
    def test_html_to_text(self):
        """Headings, paragraphs, code, lists, tables, quotes and images become Markdown."""
        text = html_to_text(self.posts[0].content.rendered)
        self.assertIn("Every log message is reviewed for leaked credentials before a release.", text)
        self.assertIn("## How the review works", text)
        self.assertIn("```\nscan-log init-job.log\n```", text)
        self.assertIn("- Secrets are `SecretStr` values.\n- Connection strings are masked.", text)
        self.assertIn("| Leak | Fix |\n| token prefix | removed |", text)
        self.assertIn("> A log is public until proven otherwise.", text)
        self.assertIn("The scanner's report.", text)
        self.assertIn("1. Scan.\n2. Fix.", text)
        self.assertIn("![Illustration](https://blog.example.com/x.png)\n\nThe scanner's report.", text)
        self.assertNotIn("<", text)

    def test_html_to_text_wraps_long_paragraphs(self):
        """Paragraphs and list items are wrapped at LINE_WIDTH, and links keep their punctuation."""
        sentence = "Every word of this sentence is short. " * 10
        text = html_to_text(f'<p><a href="https://x">Smarter</a>, {sentence}</p><ul><li>{sentence}</li></ul>')
        self.assertTrue(text.startswith("Smarter, Every word"))
        lines = text.splitlines()
        self.assertGreater(len(lines), 4)
        self.assertTrue(all(len(line) <= blog_module.LINE_WIDTH for line in lines))
        self.assertTrue(any(line.startswith("- Every") for line in lines))
        self.assertTrue(any(line.startswith("  Every") or line.startswith("  short") for line in lines))

    def test_images(self):
        """Images are Markdown images, whose alt text tells the LLM what they show."""
        long_alt = "Diagram of the [namespace] under default-deny-all, where " + "every pod is isolated " * 20
        text = html_to_text(
            '<figure><img src="/wp-content/a.png" alt="A  short [diagram]"/></figure>'
            f'<figure><a href="https://cdn.example.com/b.png"><img src="https://cdn.example.com/b.png" alt="{long_alt}"/></a></figure>'
            '<p>See <img src="https://cdn.example.com/c.png"/> inline.</p>'
            '<img src="data:image/png;base64,AAAA" alt="inline data"/><img alt="no source"/>'
            '<img src="javascript:alert(1)" alt="script"/><img src="https://cdn.example.com/a b.png" alt="blank in its url"/>',
            BLOG_URL,
        )
        lines = text.splitlines()
        self.assertIn("![A short (diagram)](https://blog.example.com/wp-content/a.png)", lines)
        shortened = next(line for line in lines if "cdn.example.com/b.png" in line)
        self.assertTrue(shortened.startswith("![Diagram of the (namespace) under default-deny-all"))
        self.assertTrue(shortened.endswith("…](https://cdn.example.com/b.png)"))
        self.assertLessEqual(len(shortened), indexer.MAX_IMAGE_LINE_LENGTH)
        self.assertIn("Illustration: Diagram of the (namespace)", text)
        self.assertIn("See inline.\n\n![Illustration](https://cdn.example.com/c.png)", text)
        for absent in ("data:", "no source", "javascript", "blank in its url", "a b.png"):
            self.assertNotIn(absent, text)

    def test_image_with_a_long_url(self):
        """An image whose url leaves no room for its alt text is an Illustration, described below it."""
        url = "https://cdn.example.com/" + "x" * 230 + ".png"
        text = html_to_text(f'<img src="{url}" alt="A diagram of every pod in the namespace"/>')
        self.assertTrue(text.startswith(f"![Illustration]({url})\nIllustration: A diagram"))

    def test_html_to_text_keeps_stray_text(self):
        """Text outside of any block, and inside unknown containers, is kept."""
        self.assertEqual(html_to_text("loose text<section><p>inside</p></section><p> </p>"), "loose text\n\ninside")

    # -------------------------------------------------------------------------
    # posts
    # -------------------------------------------------------------------------
    def test_post_file(self):
        """A post is a documentation file whose path is its permalink's, and whose text cites it."""
        file = post_file(self.test_blog, self.posts[0])
        self.assertEqual(file.path, SECRETS_POST)
        self.assertEqual(file.kind, RepositoryFileKind.DOCUMENTATION)
        self.assertEqual(file.title, "Keeping Secrets Out of the Logs – a Review")
        self.assertTrue(file.content.startswith("# Keeping Secrets Out of the Logs – a Review\n\n"))
        self.assertIn(f"Published 2026-10-20, updated 2026-10-22: {BLOG_URL}/{SECRETS_POST}/", file.content)
        self.assertEqual(file.size, len(file.content.encode()))
        unchanged = post_file(self.test_blog, self.posts[1])
        self.assertIn("Published 2026-10-01: ", unchanged.content)

    def test_post_file_truncates_a_long_post(self):
        """A post longer than MAX_FILE_BYTES is truncated."""
        with mock.patch.object(blog_module, "MAX_FILE_BYTES", 100):
            file = post_file(self.test_blog, self.posts[0])
        self.assertTrue(file.content.endswith("[The post is truncated.]\n"))

    def test_post_path(self):
        """A post without a permalink path falls back to its slug."""
        post = self.posts[1].model_copy(update={"link": "https://blog.example.com/"})
        self.assertEqual(post_path(post), "release-v1-0")

    def test_posts_fingerprint(self):
        """The fingerprint changes when a post is changed or removed, and not when posts are reordered."""
        fingerprint = posts_fingerprint(self.posts)
        self.assertRegex(fingerprint, r"^[0-9a-f]{40}$")
        self.assertEqual(posts_fingerprint(list(reversed(self.posts))), fingerprint)
        self.assertNotEqual(posts_fingerprint(self.posts[:1]), fingerprint)
        changed = [self.posts[0].model_copy(update={"modified": self.posts[1].modified}), self.posts[1]]
        self.assertNotEqual(posts_fingerprint(changed), fingerprint)

    def test_project_blog(self):
        """The tests replace the blog."""
        self.assertEqual(project_blog(), self.blog)
        self.assertEqual(self.blog.posts_api_url, f"{BLOG_URL}/wp-json/wp/v2/posts")
        self.assertEqual(self.blog.post_path(f"http://blog.example.com/{SECRETS_POST}/?x=1"), SECRETS_POST)
        self.assertEqual(self.blog.file_url("ignored", SECRETS_POST, 1, 2), f"{BLOG_URL}/{SECRETS_POST}/")
        self.assertEqual(self.blog.documentation_url(SECRETS_POST), f"{BLOG_URL}/{SECRETS_POST}/")

    # -------------------------------------------------------------------------
    # fetch_posts
    # -------------------------------------------------------------------------
    def test_fetch_posts_pages(self):
        """Every page of posts is read."""
        with mock.patch(REQUESTS_PATCH, side_effect=self.wordpress([self.posts_json[:1], self.posts_json[1:]])) as get:
            posts = fetch_posts(self.test_blog)
        self.assertEqual([post.id for post in posts], [102, 101])
        self.assertEqual(get.call_count, 2)

    def test_fetch_posts_stops_at_max_pages(self):
        """At most MAX_PAGES pages are read, and a bad page count is one page."""
        with (
            mock.patch.object(blog_module, "MAX_PAGES", 1),
            mock.patch(REQUESTS_PATCH, side_effect=self.wordpress([self.posts_json[:1], self.posts_json[1:]])),
        ):
            self.assertEqual(len(fetch_posts(self.test_blog)), 1)
        response = FakeResponse(content=json.dumps(self.posts_json).encode(), total_pages="many")
        with mock.patch(REQUESTS_PATCH, return_value=response) as get:
            self.assertEqual(len(fetch_posts(self.test_blog)), 2)
        get.assert_called_once()

    def test_fetch_posts_errors(self):
        """An unreachable blog, an HTTP error and a response that is not posts are index errors."""
        cases = {
            "could not be reached": mock.patch(REQUESTS_PATCH, side_effect=requests.exceptions.ConnectionError()),
            "HTTP 503": mock.patch(REQUESTS_PATCH, return_value=FakeResponse(503)),
            "not respond with a list of posts": mock.patch(
                REQUESTS_PATCH, return_value=FakeResponse(content=b'{"code": "rest_no_route"}')
            ),
        }
        for message, patcher in cases.items():
            with self.subTest(message=message), patcher:
                with self.assertRaisesRegex(Exception, message):
                    fetch_posts(self.test_blog)

    # -------------------------------------------------------------------------
    # index_blog
    # -------------------------------------------------------------------------
    def test_index_blog(self):
        """The posts are indexed, an unchanged blog is skipped, and --force indexes it again."""
        indexed = []

        def receiver(sender, index, **kwargs):
            indexed.append(index.repository)

        mcpserver_repository_indexed.connect(receiver)
        self.addCleanup(mcpserver_repository_indexed.disconnect, receiver)
        with mock.patch(REQUESTS_PATCH, side_effect=self.wordpress([self.posts_json])):
            index = index_blog(blog=self.test_blog)
        self.assertEqual(index.status, RepositoryIndexStatus.READY)
        self.assertEqual(index.commit_sha, posts_fingerprint(self.posts))
        self.assertEqual(index.file_count, 2)
        self.assertTrue(RepositoryFile.objects.filter(index=index, path=SECRETS_POST).exists())
        self.assertEqual(indexed, [self.test_blog.name])

        RepositoryIndex.objects.filter(pk=index.pk).update(error="old")
        with mock.patch(REQUESTS_PATCH, side_effect=self.wordpress([self.posts_json])):
            unchanged = index_blog(blog=self.test_blog)
        self.assertIsNone(unchanged.error)
        self.assertEqual(indexed, [self.test_blog.name])

        with mock.patch(REQUESTS_PATCH, side_effect=self.wordpress([self.posts_json[:1]])):
            index = index_blog(force=True, blog=self.test_blog)
        self.assertEqual(index.file_count, 1)
        self.assertEqual(len(indexed), 2)

    def test_index_blog_failure(self):
        """A failure keeps an existing index, records the error, and sends a signal."""
        failures = []

        def receiver(sender, repository, error, **kwargs):
            failures.append(repository)

        mcpserver_repository_index_failed.connect(receiver)
        self.addCleanup(mcpserver_repository_index_failed.disconnect, receiver)
        with mock.patch(REQUESTS_PATCH, return_value=FakeResponse(500)):
            index = index_blog(blog=self.test_blog)
        self.assertEqual(index.status, RepositoryIndexStatus.FAILED)
        self.assertIn("HTTP 500", index.error)

        with mock.patch(REQUESTS_PATCH, side_effect=self.wordpress([self.posts_json])):
            index_blog(blog=self.test_blog)
        with mock.patch(REQUESTS_PATCH, return_value=FakeResponse(500)):
            index = index_blog(blog=self.test_blog)
        self.assertEqual(index.status, RepositoryIndexStatus.READY)
        self.assertEqual(index.file_count, 2)
        self.assertIn("HTTP 500", index.error)
        self.assertEqual(failures, [self.test_blog.name, self.test_blog.name])

    def test_index_blog_defaults_to_the_project_blog(self):
        """Without a blog, the project's blog is indexed."""
        with mock.patch(REQUESTS_PATCH, side_effect=self.wordpress([self.posts_json])):
            index = index_blog()
        self.assertEqual(index.repository, self.blog.name)
