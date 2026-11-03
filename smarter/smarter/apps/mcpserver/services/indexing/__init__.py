"""
The index of The Smarter Project's repositories and blog: the platform's own copy of their text.

The search and reading services answer from this copy, stored in the database as
:class:`~smarter.apps.mcpserver.models.RepositoryIndex` and
:class:`~smarter.apps.mcpserver.models.RepositoryFile` rows, rather than from GitHub. Celery tasks
(:mod:`smarter.apps.mcpserver.tasks`) refresh it every hour.

- :mod:`~smarter.apps.mcpserver.services.indexing.github`: indexes a repository from its GitHub archive.
- :mod:`~smarter.apps.mcpserver.services.indexing.blog`: indexes the blog from its WordPress REST api.
- :mod:`~smarter.apps.mcpserver.services.indexing.indexes`: which indexes are ready to read, and
  queues the others for indexing.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""
