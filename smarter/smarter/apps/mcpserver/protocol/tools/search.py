"""
The public tools that search the index: ``search_documentation``, ``search_code`` and ``search_blog``.

Each tool validates its arguments, calls :mod:`smarter.apps.mcpserver.services.search`, and formats
the hits as Markdown, with links that the LLM can cite. They are served at the MCPServer's public
endpoint (:mod:`smarter.apps.mcpserver.protocol.public`). ``search_blog`` has no ``repository``
argument, and only the endpoint of every repository serves it. Every tool is read-only, so
:meth:`~smarter.apps.mcpserver.protocol.tools.public.PublicTool.call` caches its results until an
index changes.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from abc import abstractmethod
from typing import Optional, Sequence, cast

from pydantic import Field

from smarter.apps.mcpserver.models import RepositoryFileKind
from smarter.apps.mcpserver.protocol.tools.markdown import (
    code_fence_language,
    numbered_excerpt,
)
from smarter.apps.mcpserver.protocol.tools.public import (
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    PublicTool,
    PublicToolArguments,
)
from smarter.apps.mcpserver.services.repositories import (
    ProjectRepository,
    project_blog,
)
from smarter.apps.mcpserver.services.search import (
    SearchHit,
    SearchResults,
    search_blog,
    search_code,
    search_documentation,
)


class SearchArguments(PublicToolArguments):
    """The arguments of search_documentation and search_blog, and the base of those of search_code."""

    query: str = Field(
        min_length=1,
        max_length=500,
        description='Keywords, identifiers or "quoted phrases", e.g. custom domain verification.',
    )
    limit: int = Field(
        default=DEFAULT_SEARCH_LIMIT, ge=1, le=MAX_SEARCH_LIMIT, description="The maximum number of results."
    )


class SearchCodeArguments(SearchArguments):
    """The arguments of search_code: those of search_documentation, and a folder to search under."""

    path: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Only search files under this folder, e.g. smarter/smarter/apps/llmclient.",
    )


class SearchTool(PublicTool):
    """
    The base class of the search tools of the repositories, ``search_documentation`` and ``search_code``.

    A subclass sets the noun that its results call the files, and implements :meth:`search`.
    """

    noun = ""
    """What the tool's results call the files, e.g. ``documentation`` or ``code``."""

    @abstractmethod
    def search(self, arguments: SearchArguments, repositories: Sequence[ProjectRepository]) -> SearchResults:
        """
        Search the repositories.

        :param arguments: The validated arguments.
        :param repositories: The repositories to search.
        :returns: The hits, and the repositories that were not searched.
        """

    def run(self, arguments: PublicToolArguments) -> str:
        """
        Search the named repository, or every repository of the scope, and return the hits as Markdown.

        A repository that is not indexed yet is queued for indexing, and named in a note after the results.

        **Side effects:** see :func:`~smarter.apps.mcpserver.services.search.search_repositories`.

        :param arguments: The validated arguments.
        :returns: The hits, best first, as Markdown, or a message that nothing matches.
        :raises SmarterMCPServerToolError: If the repository is not one of the scope's.
        :raises SmarterMCPServerServiceError: If no repository to search is indexed yet.
        """
        search_arguments = cast(SearchArguments, arguments)
        repository = self.scope.resolve(search_arguments.repository, required=False)
        if repository:
            repositories = [repository]
            where = repository.name
        else:
            repositories = list(self.scope.repositories)
            where = "The Smarter Project's repositories"
        results = self.search(search_arguments, repositories)
        note = ""
        if results.not_indexed:
            names = ", ".join(results.not_indexed)
            note = f"\n\nNot searched, because they are still being indexed: {names}. Try again in a few minutes."
        query = search_arguments.query
        if not results.hits:
            message = (
                f'No {self.noun} of {where} matches "{query}". Try other keywords, an identifier, '
                "or the other search tool." + note
            )
            return message
        formatted_hits = [self.format_hit(number, hit) for number, hit in enumerate(results.hits, start=1)]
        formatted = "\n\n".join(formatted_hits)
        answer = (
            f'{len(results.hits)} results in the {self.noun} of {where}, for "{query}", best first. '
            f"Read a file with read_file to see more of it.\n\n{formatted}" + note
        )
        return answer

    def format_hit(self, number: int, hit: SearchHit) -> str:
        """
        Return one hit, as Markdown: a numbered heading, its links, and its lines in a code block.

        :param number: The hit's rank, from 1.
        :param hit: The hit.
        :returns: The Markdown. The heading names the repository on the endpoint of every repository.
        """
        if hit.title:
            heading = f"{number}. **{hit.title}** `{hit.path}`"
        else:
            heading = f"{number}. `{hit.path}`"
        if not self.scope.is_single:
            heading += f" in {hit.repository}"
        links = []
        if hit.documentation_url:
            links.append(f"   Documentation: {hit.documentation_url}")
        links.append(f"   Source: {hit.url}")
        excerpt = numbered_excerpt(hit.lines)
        fence = "text"
        if hit.kind == RepositoryFileKind.CODE:
            fence = code_fence_language(hit.path)
        markdown = f"{heading}\n" + "\n".join(links) + f"\n\n```{fence}\n{excerpt}\n```"
        return markdown


class SearchDocumentationTool(SearchTool):
    """The ``search_documentation`` tool: ranked passages of the repositories' documentation."""

    name = "search_documentation"
    title = "Search documentation"
    description = (
        "Search the documentation of The Smarter Project: the Sphinx documentation published at "
        "docs.smarter.sh, READMEs, and other reStructuredText and Markdown files. Returns the best "
        "passages, with links to the published page and to the source. Use it for concepts, features, "
        "configuration, installation and how-to questions."
    )
    arguments_model = SearchArguments
    noun = "documentation"

    def search(self, arguments: SearchArguments, repositories: Sequence[ProjectRepository]) -> SearchResults:
        """
        Search the documentation, with :func:`~smarter.apps.mcpserver.services.search.search_documentation`.

        :param arguments: The validated arguments.
        :param repositories: The repositories to search.
        :returns: The hits, and the repositories that were not searched.
        """
        results = search_documentation(repositories, arguments.query, limit=arguments.limit)
        return results


class SearchCodeTool(SearchTool):
    """The ``search_code`` tool: ranked files of the repositories' source code, with their matching lines."""

    name = "search_code"
    title = "Search code"
    description = (
        "Search the source code and configuration of The Smarter Project: Python, TypeScript, Go, YAML "
        "manifests, Helm charts, Terraform and more. Returns the best files, with their matching lines "
        "and GitHub links. Use it for how something is implemented, and to find a class, function, "
        "setting or manifest field by name."
    )
    arguments_model = SearchCodeArguments
    noun = "code"

    def search(self, arguments: SearchArguments, repositories: Sequence[ProjectRepository]) -> SearchResults:
        """
        Search the code, under the folder that the arguments name, if any, with :func:`~smarter.apps.mcpserver.services.search.search_code`.

        :param arguments: The validated arguments, a :class:`SearchCodeArguments`.
        :param repositories: The repositories to search.
        :returns: The hits, and the repositories that were not searched.
        """
        code_arguments = cast(SearchCodeArguments, arguments)
        results = search_code(repositories, code_arguments.query, limit=code_arguments.limit, path=code_arguments.path)
        return results


class SearchBlogTool(PublicTool):
    """The ``search_blog`` tool: ranked passages of the blog's posts, with links to them."""

    name = "search_blog"
    title = "Search blog"
    description = (
        "Search the posts of The Smarter Project's blog, blog.smarter.sh: release announcements, with what "
        "changed in each version and how to upgrade, and articles about how and why Smarter was built, e.g. "
        "its security, logging, testing, caching and use of AI coding agents. Returns the best passages, with "
        "links to the posts. Use it, together with search_documentation, for why and how questions, design "
        "decisions, what changed in a release, and the project's history."
    )
    arguments_model = SearchArguments
    uses_repository = False
    project_wide = True

    def run(self, arguments: PublicToolArguments) -> str:
        """
        Search the blog's posts, with :func:`~smarter.apps.mcpserver.services.search.search_blog`.

        **Side effects:** database queries, and, if the blog is not indexed yet, a Celery task queued to
        index it.

        :param arguments: The validated arguments, a :class:`SearchArguments`.
        :returns: The hits, best first, as Markdown, or a message that nothing matches.
        :raises SmarterMCPServerServiceError: If the blog is not indexed yet.
        """
        search_arguments = cast(SearchArguments, arguments)
        hits = search_blog(search_arguments.query, limit=search_arguments.limit)
        blog_url = project_blog().url
        query = search_arguments.query
        if not hits:
            message = (
                f'No post of the blog, {blog_url}, matches "{query}". Try other keywords, or search_documentation.'
            )
            return message
        formatted_hits = [self.format_hit(number, hit) for number, hit in enumerate(hits, start=1)]
        formatted = "\n\n".join(formatted_hits)
        answer = (
            f'{len(hits)} posts of the blog, {blog_url}, for "{query}", best first. '
            f"Read a post with read_blog_post to see more of it.\n\n{formatted}"
        )
        return answer

    @staticmethod
    def format_hit(number: int, hit: SearchHit) -> str:
        """
        Return one hit, as Markdown: a numbered heading, the post's url, and its passage in a code block.

        :param number: The hit's rank, from 1.
        :param hit: The hit.
        :returns: The Markdown.
        """
        excerpt = numbered_excerpt(hit.lines)
        heading = hit.title
        if not heading:
            heading = hit.path
        markdown = f"{number}. **{heading}** `{hit.path}`\n   Post: {hit.url}\n\n```text\n{excerpt}\n```"
        return markdown


__all__ = [
    "SearchArguments",
    "SearchBlogTool",
    "SearchCodeArguments",
    "SearchCodeTool",
    "SearchDocumentationTool",
    "SearchTool",
]
