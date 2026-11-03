"""
The GitHub issues and pull requests of The Smarter Project, read and written as the caller.

These services let a caller find what is already known about a problem, and report or fix it,
under their own GitHub account. The client sends every request, keeps the caller's token secret,
and refuses to write a credential to GitHub.

- :mod:`~smarter.apps.mcpserver.services.github.client`: the GitHub REST api, the caller's token, the
  check that refuses to write a credential to GitHub, and the explanations of GitHub's errors.
- :mod:`~smarter.apps.mcpserver.services.github.issues`: searches and reads issues, and opens,
  comments on and closes them as the caller.
- :mod:`~smarter.apps.mcpserver.services.github.pulls`: opens a pull request as the caller, as one
  commit on a new branch.

The MCPServer's public tools of :mod:`smarter.apps.mcpserver.protocol.tools.github` are their adapters.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""
