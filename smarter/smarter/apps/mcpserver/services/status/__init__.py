"""
The platform's health, now.

- :mod:`~smarter.apps.mcpserver.services.status.report`: the whole report, and what looks wrong in it.
- :mod:`~smarter.apps.mcpserver.services.status.cluster`: the environment's pods, the cluster's nodes,
  their CPU and memory use, and the namespace's warning events, from Kubernetes and metrics-server.
- :mod:`~smarter.apps.mcpserver.services.status.platform`: the Celery task queues and the database.
- :mod:`~smarter.apps.mcpserver.services.status.feeds`: the public status pages of the AI providers,
  and of the cloud's services in the platform's region.

Everything is read when it is asked for. Nothing here adds cloud monitoring, e.g. CloudWatch,
which would add cost.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""
