"""
The platform's health, now, and the operations tools that report it.

- :mod:`~smarter.apps.mcpserver.status.cluster`: the environment's pods, the cluster's nodes, their
  CPU and memory use, and the namespace's warning events, from Kubernetes and metrics-server.
- :mod:`~smarter.apps.mcpserver.status.platform`: the Celery task queues and the database.
- :mod:`~smarter.apps.mcpserver.status.feeds`: the public status pages of the AI providers, and of
  the cloud's services in the platform's region.
- :mod:`~smarter.apps.mcpserver.status.tools`: ``platform_status`` and ``eks_status``.

Everything is read when a tool is called. Nothing here adds cloud monitoring, e.g. CloudWatch,
which would add cost.
"""
