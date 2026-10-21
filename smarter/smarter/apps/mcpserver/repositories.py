"""
The Smarter Project's GitHub repositories, which the Smarter Project MCP server reads.

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
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from smarter.common.const import SMARTER_PROJECT_DOCS_URL

GITHUB_URL = "https://github.com"
GITHUB_API_URL = "https://api.github.com"
GITHUB_CODELOAD_URL = "https://codeload.github.com"
SMARTER_PROJECT_GITHUB_ORGANIZATION = "smarter-sh"
SMARTER_PROJECT_DOCS_LATEST_URL = f"{SMARTER_PROJECT_DOCS_URL}/en/latest/"
"""The latest version of the Sphinx documentation, built from the smarter repository's docs/source."""

DOCUMENTATION_PAGE_EXTENSIONS = (".rst", ".md")
"""The extensions of Sphinx source files, which are published as html pages."""


class ProjectRepository(BaseModel):
    """
    A public GitHub repository of The Smarter Project.

    **Example usage**::

        repository = get_repository("smarter-cli")
        repository.github_url  # 'https://github.com/smarter-sh/smarter-cli'
        repository.file_url("0123abc", "README.md", 1, 20)
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="The repository's name, which is also its endpoint's path, e.g. smarter-cli.")
    title: str = Field(
        description="What the repository contains, in a few words, e.g. 'the Smarter command-line interface'."
    )
    description: str = Field(description="What the repository contains, and what questions it answers.")
    owner: str = Field(default=SMARTER_PROJECT_GITHUB_ORGANIZATION, description="The GitHub organization.")
    ref: str = Field(default="main", description="The branch that is indexed.")
    docs_root: Optional[str] = Field(
        default=None, description="The folder of the Sphinx documentation's source files, e.g. docs/source."
    )
    docs_url: Optional[str] = Field(
        default=None, description="The url of the published Sphinx documentation that is built from docs_root."
    )

    @property
    def full_name(self) -> str:
        """The repository's GitHub name, e.g. ``smarter-sh/smarter-cli``."""
        return f"{self.owner}/{self.name}"

    @property
    def github_url(self) -> str:
        """The repository's GitHub url."""
        return f"{GITHUB_URL}/{self.full_name}"

    @property
    def commit_api_url(self) -> str:
        """The GitHub api url of the latest commit of :attr:`ref`."""
        return f"{GITHUB_API_URL}/repos/{self.full_name}/commits/{self.ref}"

    def archive_url(self, commit_sha: str) -> str:
        """
        Return the url of the repository's gzipped tar archive at a commit.

        :param commit_sha: The commit.
        :returns: The url.
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
        :param end_line: The last line to highlight.
        :returns: The url.
        """
        url = f"{self.github_url}/blob/{commit_sha or self.ref}/{path}"
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
        stem, extension = posixpath.splitext(path)
        if not path.startswith(prefix) or extension.lower() not in DOCUMENTATION_PAGE_EXTENSIONS:
            return None
        return f"{self.docs_url}{stem[len(prefix):]}.html"


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
)
"""Every repository that the MCP server reads."""


def project_repositories() -> tuple[ProjectRepository, ...]:
    """
    Return :data:`SMARTER_PROJECT_REPOSITORIES`.

    Every module reads the repositories through this function, so that tests can replace
    them with throwaway repositories, whose indexes do not collide with the real ones.
    """
    return SMARTER_PROJECT_REPOSITORIES


def get_repository(name: str) -> Optional[ProjectRepository]:
    """
    Return one of :data:`SMARTER_PROJECT_REPOSITORIES`, by name.

    :param name: The repository's name, e.g. ``smarter-cli``.
    :returns: The repository, or None if there is no such repository.
    """
    return next((repository for repository in project_repositories() if repository.name == name), None)


def repository_names() -> list[str]:
    """Return the names of :data:`SMARTER_PROJECT_REPOSITORIES`."""
    return [repository.name for repository in project_repositories()]


__all__ = [
    "SMARTER_PROJECT_REPOSITORIES",
    "ProjectRepository",
    "get_repository",
    "project_repositories",
    "repository_names",
]
