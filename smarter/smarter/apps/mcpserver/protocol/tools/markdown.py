"""
Markdown helpers of the public tools that show files: code fences, and numbered lines.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import posixpath

from smarter.apps.mcpserver.services.search import SearchLine

CODE_FENCE_LANGUAGES = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "jsx",
    ".go": "go",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sh": "bash",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".tf": "hcl",
    ".hcl": "hcl",
    ".sql": "sql",
    ".rst": "rst",
    ".md": "markdown",
}
"""The language of a Markdown code fence, by file extension, so that a client highlights the code.

Others are ``text``.
"""


def code_fence_language(path: str) -> str:
    """
    Return the Markdown code fence language of a file.

    :param path: The file's path.
    :returns: The language, from :data:`CODE_FENCE_LANGUAGES`, or ``text``.
    """
    extension = posixpath.splitext(path)[1].lower()
    language = CODE_FENCE_LANGUAGES.get(extension, "text")
    return language


def numbered_excerpt(lines: list[SearchLine]) -> str:
    """
    Return a hit's lines, each after its line number, right-aligned, for a code block.

    :param lines: The hit's lines.
    :returns: The lines, e.g. `` 9  text`` and ``10  text``.
    """
    width = 1
    if lines:
        width = len(str(lines[-1].number))
    numbered = [f"{line.number:>{width}}  {line.text}" for line in lines]
    excerpt = "\n".join(numbered)
    return excerpt


__all__ = ["CODE_FENCE_LANGUAGES", "code_fence_language", "numbered_excerpt"]
