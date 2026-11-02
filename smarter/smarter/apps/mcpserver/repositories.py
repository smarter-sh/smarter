"""
The Smarter Project's GitHub repositories, and its blog, which the Smarter Project MCP server reads.

Each :class:`ProjectRepository` is one public repository of the ``smarter-sh`` GitHub
organization. The MCP server serves each repository at its own endpoint,
``/api/v1/mcp/smarter-project/<name>/``, and all of them together at
``/api/v1/mcp/smarter-project/``. The repositories are a fixed part of the platform,
declared here rather than in a manifest, because the MCP server is an internal utility of
the platform, not a resource that accounts create.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import posixpath
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from smarter.common.const import SMARTER_PROJECT_BLOG_URL, SMARTER_PROJECT_DOCS_URL

GITHUB_URL = "https://github.com"
"""GitHub's web site, the base of the links to repositories and their files."""

GITHUB_API_URL = "https://api.github.com"
"""GitHub's REST api, which the indexer asks for a branch's latest commit."""

GITHUB_CODELOAD_URL = "https://codeload.github.com"
"""GitHub's archive host, which the indexer downloads a repository's tar archive from."""

SMARTER_PROJECT_GITHUB_ORGANIZATION = "smarter-sh"
"""The GitHub organization that owns The Smarter Project's repositories."""

SMARTER_PROJECT_DOCS_LATEST_URL = f"{SMARTER_PROJECT_DOCS_URL}/en/latest/"
"""The latest version of the Sphinx documentation, built from the smarter repository's docs/source."""

DOCUMENTATION_PAGE_EXTENSIONS = (".rst", ".md")
"""The extensions of Sphinx source files, which are published as html pages."""


class ProjectRepository(BaseModel):
    """
    A public GitHub repository of The Smarter Project.

    It says where the repository is, which branch is indexed, and, for a repository with
    Sphinx documentation, where its pages are published. Its methods build the links that the
    MCP server's tools give the LLM: to a file on GitHub, to a range of its lines, and to the
    published page that a documentation source file becomes. The model is frozen: the
    repositories are declared once, in :data:`SMARTER_PROJECT_REPOSITORIES`.

    **Example usage**::

        repository = get_repository("smarter-cli")
        repository.github_url  # 'https://github.com/smarter-sh/smarter-cli'
        repository.file_url("0123abc", "README.md", 1, 20)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="The repository's name, which is also its endpoint's path, e.g. smarter-cli.")
    """The repository's name in its organization, e.g. ``smarter-cli``.

    It is also the last part of its MCP endpoint, ``/api/v1/mcp/smarter-project/<name>/``, and
    the ``repository`` of its :class:`~smarter.apps.mcpserver.models.RepositoryIndex`.
    """

    title: str = Field(
        description="What the repository contains, in a few words, e.g. 'the Smarter command-line interface'."
    )
    """What the repository contains, in a few words, e.g. ``the Smarter command-line interface``."""

    description: str = Field(description="What the repository contains, and what questions it answers.")
    """What the repository contains, and what questions it answers.

    The MCP server shows it to the LLM, so that it can choose which repository to search.
    """

    owner: str = Field(default=SMARTER_PROJECT_GITHUB_ORGANIZATION, description="The GitHub organization.")
    """The GitHub organization that owns the repository, :data:`SMARTER_PROJECT_GITHUB_ORGANIZATION` by default."""

    ref: str = Field(default="main", description="The branch that is indexed.")
    """The branch that is indexed, ``main`` by default, and that links without a commit point to."""

    docs_root: Optional[str] = Field(
        default=None, description="The folder of the Sphinx documentation's source files, e.g. docs/source."
    )
    """The folder of the Sphinx documentation's source files, e.g. ``docs/source``, or None if it has none."""

    docs_url: Optional[str] = Field(
        default=None, description="The url of the published Sphinx documentation that is built from docs_root."
    )
    """The url of the published Sphinx documentation that is built from :attr:`docs_root`, with a trailing slash.

    It is None if the repository has no published documentation.
    """

    @property
    def full_name(self) -> str:
        """The repository's GitHub name, e.g. ``smarter-sh/smarter-cli``."""
        return f"{self.owner}/{self.name}"

    @property
    def github_url(self) -> str:
        """The repository's GitHub url, e.g. ``https://github.com/smarter-sh/smarter-cli``."""
        return f"{GITHUB_URL}/{self.full_name}"

    @property
    def commit_api_url(self) -> str:
        """
        The GitHub api url of the latest commit of :attr:`ref`.

        The indexer requests it to find out whether the branch has moved since it was indexed.
        """
        return f"{GITHUB_API_URL}/repos/{self.full_name}/commits/{self.ref}"

    def archive_url(self, commit_sha: str) -> str:
        """
        Return the url of the repository's gzipped tar archive at a commit.

        :param commit_sha: The commit.
        :returns: The url, e.g. ``https://codeload.github.com/smarter-sh/smarter-cli/tar.gz/0123abc``.
        """
        return f"{GITHUB_CODELOAD_URL}/{self.full_name}/tar.gz/{commit_sha}"

    def file_url(
        self, commit_sha: Optional[str], path: str, start_line: Optional[int] = None, end_line: Optional[int] = None
    ) -> str:
        """
        Return the GitHub url of a file, optionally of a range of its lines.

        :param commit_sha: The commit, for a permanent link. Defaults to :attr:`ref`.
        :param path: The file's path in the repository.
        :param start_line: The first line to highlight.
        :param end_line: The last line to highlight. Ignored unless it is after ``start_line``.
        :returns: The url, e.g. ``https://github.com/smarter-sh/smarter-cli/blob/0123abc/README.md#L1-L20``.
        """
        if commit_sha:
            version = commit_sha
        else:
            version = self.ref
        url = f"{self.github_url}/blob/{version}/{path}"
        if start_line:
            url += f"#L{start_line}"
            if end_line and end_line > start_line:
                url += f"-L{end_line}"
        return url

    def documentation_url(self, path: str) -> Optional[str]:
        """
        Return the url of the published documentation page that a source file becomes.

        :param path: The file's path in the repository, e.g. ``docs/source/smarter-resources/smarter-mcpclient.rst``.
        :returns: The page's url, e.g. ``https://docs.smarter.sh/en/latest/smarter-resources/smarter-mcpclient.html``,
            or None if the file is not a page of the repository's published documentation.
        """
        if not self.docs_root or not self.docs_url:
            return None
        prefix = self.docs_root.rstrip("/") + "/"
        if not path.startswith(prefix):
            return None
        stem, extension = posixpath.splitext(path)
        if extension.lower() not in DOCUMENTATION_PAGE_EXTENSIONS:
            return None
        page = stem[len(prefix) :]
        url = f"{self.docs_url}{page}.html"
        return url


SMARTER_PROJECT_REPOSITORIES: tuple[ProjectRepository, ...] = (
    ProjectRepository(
        name="smarter",
        title="the Smarter platform, and its documentation",
        description=(
            "The Smarter platform: its Django backend, SAM manifests and resources (LLMClients, "
            "Plugins, MCPClients, Guardrails, Secrets, ...), its api, its React web console and its "
            "npm packages (SmarterChat, the React chat component of LLMClients, as @smarter.sh/ui-chat, and "
            "@smarter.sh/ui-widgets), its Helm chart, and the source of its documentation, "
            f"{SMARTER_PROJECT_DOCS_URL}, in docs/source."
        ),
        docs_root="docs/source",
        docs_url=SMARTER_PROJECT_DOCS_LATEST_URL,
    ),
    ProjectRepository(
        name="smarter-cli",
        title="the Smarter command-line interface",
        description="The smarter command-line interface, written in Go, which applies, gets, describes and deletes manifests.",
    ),
    ProjectRepository(
        name="smarter-python",
        title="the Smarter Python SDK",
        description="The official Python library for the Smarter platform's api, published to PyPI as smarter-api.",
    ),
    ProjectRepository(
        name="smarter-nodejs",
        title="the Smarter Node.js SDK",
        description="The official Node.js library for the Smarter platform's api, written in TypeScript, published to npm as @smarter.sh/api.",
    ),
    ProjectRepository(
        name="smarter-golang",
        title="the Smarter Go SDK",
        description="The official Go library for the Smarter platform's api, the module github.com/smarter-sh/smarter-golang.",
    ),
    ProjectRepository(
        name="smarter-vscode-yaml",
        title="the VS Code extension for Smarter manifests",
        description="The VS Code extension that validates and completes Smarter yaml manifests.",
    ),
    ProjectRepository(
        name="smarter-infrastructure",
        title="the Smarter cloud infrastructure",
        description="The Terraform and Kubernetes code of the cloud infrastructure that the Smarter platform runs on.",
    ),
    ProjectRepository(
        name="smarter-deploy",
        title="the Smarter platform quick start, with Docker",
        description="The quick start that runs the Smarter platform on a computer with Docker Compose.",
    ),
    ProjectRepository(
        name="example-manifests",
        title="the example manifests that every platform applies",
        description=(
            "Working example manifests of every Smarter resource kind, ready to apply, read and copy: "
            "LLMClients, Plugins, MCPClients, Guardrails, Proxies, LLMHosts, Vectorstores, Budgets and more. "
            "Every Smarter platform applies them when it is initialized."
        ),
    ),
    ProjectRepository(
        name="stackademy",
        title="Stackademy, the example project",
        description=(
            "Stackademy, an AI course advisor for a fictional online code academy, built with Smarter's no-code "
            "tool calling over a private database, and managed with git and GitHub: the example project of the "
            "documentation."
        ),
    ),
    ProjectRepository(
        name="smarter-wordpress",
        title="Smarter Chat for WordPress",
        description="The WordPress plugin that adds a Smarter chatbot to a site: a chat launcher, a block and a shortcode.",
    ),
    ProjectRepository(
        name="smarter-drupal",
        title="Smarter Chat for Drupal",
        description="The Drupal module that adds a Smarter chatbot to a site: a chat launcher, and a block for any region.",
    ),
    ProjectRepository(
        name="smarter-shopify",
        title="Smarter Chat for Shopify",
        description="The Shopify theme app extension that adds a Smarter chatbot to a store: a chat launcher, and an app block.",
    ),
    ProjectRepository(
        name="smarter-gtm-template",
        title="Smarter Chat for Google Tag Manager",
        description="The Google Tag Manager tag template that adds a Smarter chatbot to any site with a GTM web container.",
    ),
    ProjectRepository(
        name="smarter-docs-site-generators",
        title="Smarter Chat for documentation sites",
        description="The packages that add a Smarter chatbot to every page of a Docusaurus, MkDocs, Sphinx or VitePress site.",
    ),
    ProjectRepository(
        name="extensions-registry",
        title="the Smarter Extension registry",
        description=(
            "The registry of Smarter Extensions, the installable Python packages that add tools to a platform's "
            "LLMs: their publishers, releases and signed index, and how to publish a release."
        ),
    ),
    ProjectRepository(
        name="smarter-extension-calculator",
        title="the Calculator extension",
        description="The official Smarter Extension whose calculator tool evaluates math expressions exactly.",
    ),
    ProjectRepository(
        name="smarter-extension-date-calculator",
        title="the Date Calculator extension",
        description="The official Smarter Extension whose date_calculator tool does date arithmetic exactly.",
    ),
    ProjectRepository(
        name="smarter-extension-weather",
        title="the Weather extension",
        description="The official Smarter Extension whose get_weather tool gives the current weather and a forecast.",
    ),
    ProjectRepository(
        name="cache-results",
        title="cache-results, the Django caching decorator",
        description=(
            "cache-results, on PyPI: the @cache_results() Django decorator that caches a function's results by "
            "its arguments, and lazy_cache. Smarter caches with it."
        ),
        docs_root="docs/source",
        docs_url="https://docs.cache-results.smarter.sh/",
    ),
    ProjectRepository(
        name="smarter-types",
        title="the shared Smarter type definitions",
        description="smarter-types, on PyPI: the plain-Python type definitions that the platform and the Python SDK share.",
    ),
)
"""Every repository that the MCP server reads."""


class ProjectBlog(BaseModel):
    """
    The Smarter Project's blog, a WordPress site, whose posts the MCP server reads.

    It has the same ``name``, ``title``, ``description``, ``file_url()`` and
    ``documentation_url()`` as a :class:`ProjectRepository`, so that the search tools can
    treat the blog as one more source (see :data:`ProjectSource`). The model is frozen: the
    blog is declared once, in :data:`SMARTER_PROJECT_BLOG`.

    Its posts are indexed like a repository's documentation, by
    :func:`smarter.apps.mcpserver.index.blog.index_blog`, under the blog's :attr:`name`. A post's
    path is its permalink's path, e.g. ``2026/10/26/release-smarter-api-v0-6``.

    **Example usage**::

        blog = project_blog()
        blog.post_url("2026/10/26/release-smarter-api-v0-6")
        # 'https://blog.smarter.sh/2026/10/26/release-smarter-api-v0-6/'
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="The name of the blog's index, e.g. blog.smarter.sh. It is not a repository's name.")
    """The name of the blog's index, e.g. ``blog.smarter.sh``.

    It is the ``repository`` of the blog's :class:`~smarter.apps.mcpserver.models.RepositoryIndex`,
    and is never the name of a repository.
    """

    title: str = Field(description="What the blog contains, in a few words.")
    """What the blog contains, in a few words, e.g. ``the Smarter blog``."""

    description: str = Field(description="What the blog contains, and what questions it answers.")
    """What the blog contains, and what questions it answers, which the MCP server shows the LLM."""

    url: str = Field(description="The blog's url, without a trailing slash, e.g. https://blog.smarter.sh.")
    """The blog's url, without a trailing slash, e.g. ``https://blog.smarter.sh``."""

    @property
    def posts_api_url(self) -> str:
        """
        The url of the WordPress REST api's posts, e.g. ``https://blog.smarter.sh/wp-json/wp/v2/posts``.

        The blog's indexer pages through it to read every published post.
        """
        return f"{self.url}/wp-json/wp/v2/posts"

    def post_url(self, path: str) -> str:
        """
        Return the url of a post.

        :param path: The post's path, e.g. ``2026/10/26/release-smarter-api-v0-6``.
        :returns: The post's url.
        """
        return f"{self.url}/{path.strip('/')}/"

    def post_path(self, url_or_path: str) -> str:
        """
        Return the path of a post, from its url or its path.

        The blog's url, over https or http, is removed, and so are a fragment (``#...``), a query
        (``?...``) and the slashes at either end. An LLM may give either form, so the tools
        accept both.

        :param url_or_path: e.g. ``https://blog.smarter.sh/2026/10/26/release-smarter-api-v0-6/``.
        :returns: The path, e.g. ``2026/10/26/release-smarter-api-v0-6``.
        """
        value = url_or_path.strip()
        http_url = self.url.replace("https://", "http://", 1)
        for prefix in (self.url, http_url):
            if value.startswith(prefix):
                value = value[len(prefix) :]
                break
        without_fragment = value.split("#", 1)[0]
        without_query = without_fragment.split("?", 1)[0]
        path = without_query.strip("/")
        return path

    def file_url(
        self, commit_sha: Optional[str], path: str, start_line: Optional[int] = None, end_line: Optional[int] = None
    ) -> str:
        """
        Return the url of a post, for :func:`smarter.apps.mcpserver.index.search.search_files`.

        The signature is that of :meth:`ProjectRepository.file_url`. A post has no commit,
        and its page has no line anchors, so only ``path`` is used.

        :param commit_sha: Ignored.
        :param path: The post's path, e.g. ``2026/10/26/release-smarter-api-v0-6``.
        :param start_line: Ignored.
        :param end_line: Ignored.
        :returns: The post's url.
        """
        return self.post_url(path)

    def documentation_url(self, path: str) -> Optional[str]:
        """
        Return the url of a post, which is its published page.

        The signature is that of :meth:`ProjectRepository.documentation_url`. Every post is a
        published page, so the url is never None.

        :param path: The post's path, e.g. ``2026/10/26/release-smarter-api-v0-6``.
        :returns: The post's url.
        """
        return self.post_url(path)


SMARTER_PROJECT_BLOG = ProjectBlog(
    name="blog.smarter.sh",
    title="the Smarter blog",
    description=(
        f"The Smarter blog, {SMARTER_PROJECT_BLOG_URL}: release announcements of the platform, the cli, "
        "the SDKs and the other packages, with what changed and how to upgrade, and articles about how "
        "and why Smarter was built."
    ),
    url=SMARTER_PROJECT_BLOG_URL,
)
"""The blog that the MCP server reads."""

ProjectSource = Union[ProjectRepository, ProjectBlog]
"""A source of the MCP server's index: a repository, or the blog."""


def project_blog() -> ProjectBlog:
    """
    Return :data:`SMARTER_PROJECT_BLOG`.

    Every module reads the blog through this function, so that tests can replace it with a
    throwaway blog, whose index does not collide with the real one.

    :returns: The blog.
    """
    return SMARTER_PROJECT_BLOG


def project_repositories() -> tuple[ProjectRepository, ...]:
    """
    Return :data:`SMARTER_PROJECT_REPOSITORIES`.

    Every module reads the repositories through this function, so that tests can replace
    them with throwaway repositories, whose indexes do not collide with the real ones.

    :returns: The repositories, in the order that the MCP server lists them.
    """
    return SMARTER_PROJECT_REPOSITORIES


def get_repository(name: str) -> Optional[ProjectRepository]:
    """
    Return one of :data:`SMARTER_PROJECT_REPOSITORIES`, by name.

    :param name: The repository's name, e.g. ``smarter-cli``.
    :returns: The repository, or None if there is no such repository.
    """
    for repository in project_repositories():
        if repository.name == name:
            return repository
    return None


def repository_names() -> list[str]:
    """
    Return the names of :data:`SMARTER_PROJECT_REPOSITORIES`.

    The indexing task and the ``index_smarter_project`` command use them to index every
    repository.

    :returns: The names, e.g. ``["smarter", "smarter-cli", ...]``, in the order that they are declared.
    """
    return [repository.name for repository in project_repositories()]


__all__ = [
    "SMARTER_PROJECT_BLOG",
    "SMARTER_PROJECT_REPOSITORIES",
    "ProjectBlog",
    "ProjectRepository",
    "ProjectSource",
    "get_repository",
    "project_blog",
    "project_repositories",
    "repository_names",
]
