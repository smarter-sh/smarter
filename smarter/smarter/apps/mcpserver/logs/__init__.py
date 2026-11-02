"""
The platform's pod logs, and the operations tools that search and summarize them.

- :mod:`~smarter.apps.mcpserver.logs.summary`: formats log lines for the LLM, and groups errors by
  their signature.
- :mod:`~smarter.apps.mcpserver.logs.tools`: ``list_log_sources``, ``search_logs`` and
  ``summarize_log_errors``.

The logs come from :data:`smarter.apps.infrastructure.services.infrastructure` ``.logs``, the last
72 hours of the app, the Celery workers, beat and MariaDB, kept in Loki.
"""
