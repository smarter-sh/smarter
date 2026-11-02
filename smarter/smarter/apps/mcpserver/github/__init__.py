"""
The GitHub issues and pull requests of The Smarter Project, and the MCP tools that work on them.

The Smarter Project MCP server's GitHub tools let an LLM find what is already known about a
problem, and report or fix it, under the user's own GitHub account. The package is in layers:
the tools turn arguments into calls and results into Markdown; the issues and pulls modules
do the GitHub work; and the client sends every request, and keeps the caller's token secret.

- :mod:`~smarter.apps.mcpserver.github.client`: the GitHub REST api, the caller's token, the
  check that refuses to write a credential to GitHub, and the explanations of GitHub's errors.
- :mod:`~smarter.apps.mcpserver.github.issues`: searches and reads issues, and opens, comments
  on and closes them as the caller.
- :mod:`~smarter.apps.mcpserver.github.pulls`: opens a pull request as the caller, as one commit
  on a new branch.
- :mod:`~smarter.apps.mcpserver.github.tools`: the tools ``search_issues``, ``read_issue``,
  ``create_issue``, ``comment_on_issue``, ``close_issue`` and ``create_pull_request``.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""
