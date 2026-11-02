"""
The index of The Smarter Project's repositories and blog, and the tools that answer from it.

The Smarter Project MCP server answers questions about the project from its own copy of the
repositories' text files and the blog's posts, stored in the database as
:class:`~smarter.apps.mcpserver.models.RepositoryIndex` and
:class:`~smarter.apps.mcpserver.models.RepositoryFile` rows, and searched there, without embeddings.
Celery tasks refresh the copy, and a tool that finds a source not indexed yet queues one.

- :mod:`~smarter.apps.mcpserver.index.indexer`: indexes the repositories from GitHub.
- :mod:`~smarter.apps.mcpserver.index.blog`: indexes the blog from its WordPress REST api.
- :mod:`~smarter.apps.mcpserver.index.search`: ranks the indexed files for a query.
- :mod:`~smarter.apps.mcpserver.index.tools`: the tools that read and search the index.
"""
