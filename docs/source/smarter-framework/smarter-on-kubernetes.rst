Smarter on Kubernetes
=====================

Smarter runs in two kinds of environment, and the same Docker image serves both:

- **Docker**, with ``docker-compose.yml``, on a developer's computer. Every service runs as one
  container on one machine, the web console is served on ``http://localhost:9357``, and nothing is
  reachable from the internet.
- **Kubernetes**, with the :doc:`Smarter Helm chart <technologies/kubernetes>`, in production. The
  platform runs as several Deployments that scale horizontally, behind a load balancer, and every
  deployed :doc:`LLMClient <../smarter-resources/smarter-llmclient>` gets its own hostname, DNS
  record, Kubernetes Ingress and TLS certificate.

The Python code is the same in both. What differs is the infrastructure around it, and that difference
matters most when an LLMClient is deployed: in Docker, deploying an LLMClient changes a row in the
database; in Kubernetes, it also creates cloud and cluster resources that someone has to support.

This section is for the people who install, operate and support Smarter in production: platform
engineers, SREs, and the administrators who answer "why isn't my LLMClient reachable?".
:doc:`ADR-002 <../adr/002-docker>` and :doc:`ADR-003 <../adr/003-kubernetes>` record why Smarter
chose Docker and Kubernetes (AWS EKS) in the first place.

.. toctree::
   :maxdepth: 1

   smarter-on-kubernetes/llmclient-deploy
   smarter-on-kubernetes/operations
   smarter-on-kubernetes/slack-bot
   smarter-on-kubernetes/tool-worker


The Services
------------

Both environments run the same processes. Only how they are started, scaled and connected
differs.

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Process
     - Docker (``docker-compose.yml``)
     - Kubernetes (Helm chart)
   * - Web application and REST API
     - ``smarter-api``: one container, uvicorn with auto-reload, on port 9357.
     - Deployment ``smarter-api``: uvicorn with 2 workers per pod (``api.workers``), on port 8000,
       behind the ClusterIP Service ``smarter-api``. Before v0.43.0 both were named ``smarter``. An
       install that upgrades from an older release sets ``api.legacyName.enabled`` for one upgrade,
       which also runs a Deployment and a Service under the old name, both Services reaching both
       Deployments' pods, so that the rename drops no request while its Ingresses still name
       ``smarter``; once they name ``smarter-api``, it upgrades again without it. Each worker accepts at most 100 concurrent
       requests (``api.limitConcurrency``) and answers 503 above that, so an overloaded pod sheds
       load instead of running out of memory. Each worker runs at most 32 streamed chat prompts
       at once, in a thread pool of their own (``api.promptThreads``,
       ``SMARTER_PROMPT_THREADS``), and queues the next ones. A HorizontalPodAutoscaler scales
       it on CPU and memory (3 to 25 pods by default, ``hpa.*``), and a PodDisruptionBudget lets
       node drains evict only one app pod at a time (``api.podDisruptionBudget``). A deploy
       replaces one app pod at a time, and may stop an old pod before its replacement is ready
       (``api.rollingUpdate``), so that it finishes even when no node has room for an extra
       pod and the cluster can't add one.
   * - Operational Celery worker
     - ``smarter-worker``, queue ``default_celery_task_queue``.
     - Deployment ``smarter-worker``, same queue, with its own HorizontalPodAutoscaler.
   * - Infrastructure Celery worker
     - ``smarter-worker-infrastructure``, queue ``infrastructure_celery_task_queue``.
     - Deployment ``smarter-worker-infrastructure``, same queue, a fixed number of replicas
       (``workerInfrastructure.replicaCount``, 1 by default).
   * - Tool Celery worker
     - ``smarter-worker-tools``, queue ``tools_celery_task_queue``, without a database. It takes
       calls when the app's ``SMARTER_APP_LLMTOOL_TOOL_RUNNER`` is ``remote``.
     - Deployment ``smarter-worker-tools``, same queue, off by default (``workerTools.enabled``),
       without a database, a Secret of the platform's, a token or an IAM role. See
       :doc:`smarter-on-kubernetes/tool-worker`.
   * - Extension Celery worker
     - ``smarter-worker-extensions``, queue ``extensions_celery_task_queue``, without a database, each
       call in a process of its own. It takes Extensions' calls when the tool runner is ``remote``.
     - Deployment ``smarter-worker-extensions``, same queue, deployed with the tool worker
       (``workerTools.extensions``). See :doc:`smarter-on-kubernetes/tool-worker`.
   * - Celery Beat
     - ``smarter-beat``.
     - Deployment ``smarter-beat``. Run exactly one replica, or scheduled tasks run more than once.
   * - Database and cache
     - ``smarter-mariadb`` and ``smarter-redis`` containers, with local volumes.
     - MySQL or MariaDB and Redis, inside the cluster or managed by the cloud
       (``database.type``, the ``SMARTER_SQL_*`` values, ``DJANGO_CELERY_BROKER_URL``, and
       ``DJANGO_CACHES``). The
       chart's own MariaDB and Redis are each a single pod on a ReadWriteOnce volume, so any
       eviction stops them for about a minute. Their pods tell the cluster autoscaler not to evict
       them (``cluster-autoscaler.kubernetes.io/safe-to-evict: "false"``), and their
       PodDisruptionBudgets (``minAvailable: 1``) make a node drain wait until an operator deletes
       the pod. Their images are pinned by digest (``mariadb.image.digest`` and
       ``redis.image.digest``), since Bitnami publishes them only as ``latest``.

The two Celery queues are separate on purpose. The infrastructure queue carries the slow tasks that
deploy, verify and destroy DNS records, ingresses, certificates, node groups and databases, so that
they can never delay the operational tasks that record prompt history, charges and budgets. See
:doc:`ADR-030 <../adr/030-task-queues>`.

The Helm chart also runs a Job, ``smarter-job-init``, on every install and upgrade. It migrates the
database, initializes the platform, loads the example resources and deploys the built-in LLMClients.
On a new cluster, that one Job queues a deployment for every built-in LLMClient at once.

Before an upgrade's rollout, a second Job, ``smarter-job-migrate``, a ``pre-upgrade`` hook, runs only
``manage.py migrate``, so that the new release's pods never take requests before the columns and
tables that their code reads exist. ``smarter-job-init`` runs after the rollout, and its migrate then
has nothing left to do. A failed migration fails ``helm upgrade`` before any pod is replaced. Until
the rollout finishes, the previous release's pods run against the new schema, which is why a
migration that removes or renames a column needs two releases: one that stops reading it, then one
that drops it. On a fresh install, there is no ``pre-install``
migration: the chart's Secret doesn't exist yet, and ``smarter-job-init`` creates the database
before it migrates. Meanwhile the pods of the app, the Celery workers and beat wait in an init
container that retries ``manage.py migrate --check`` every 10 seconds, so that they start on a
migrated database, rather than answering errors and restarting until the Job is done. The init
container is rendered only on an install, so an upgrade's pods start without it.
``smarter-job-init`` runs once: a failed step fails it, and Kubernetes doesn't retry it
(``backoffLimit: 0``). The next deployment runs it again.
When it completes, it emails its whole log, with credentials redacted, to the chart's
``databaseInit.notifyEmail``, or by default to the platform's admin, ``SMARTER_PLATFORM_EMAIL_ADMIN``, with
``manage.py email_job_log``. The email reports whether the Job succeeded, and carries the log as an
attachment. A log larger than 5 MB would exceed the SMTP server's message size limit, so it is saved
instead to the platform's public S3 bucket, under ``job-logs/`` with an unguessable name, and the
email links to its CDN URL. The email is sent only when SMTP is configured (see
:doc:`technologies/smtp`), and a Job that is killed, for example for running out of memory, sends
none.

The Job can also post its outcome to a Slack channel, ``databaseInit.notifySlackChannel`` (empty by
default, which posts nothing), with ``email_job_log --slack-channel``. The message says whether the
Job succeeded, with ✅ or ❌, and the whole log, redacted, is uploaded into the message's thread, as
the same file that the email attaches. It is posted as the bot of ``SMARTER_SUBSYSTEM_SLACK_BOT_TOKEN``, which
needs the scopes ``chat:write`` and ``files:write``, and must be a member of the channel. A bot
without ``files:write`` posts the log's last lines in the thread instead, and the link to the log
when it was saved to S3. Text from the log is escaped, so that a log line can't mention anyone.
Slack, like email, never changes the Job's outcome. The deploy workflow passes the bot token to
every environment, and sets both jobs' channel to ``smarter``.

A CronJob, ``smarter-mysql-backup``, backs up the database to S3 every night. See
:doc:`Backup and Restore </smarter-platform/system-administration/operations/backup-and-restore>`.

An optional Deployment, ``smarter-slack-bot`` (``slackBot.enabled``, ``false`` by default), answers
questions in a Slack workspace with a deployed LLMClient. See :doc:`smarter-on-kubernetes/slack-bot`.


Docker and Kubernetes Compared
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Concern
     - Docker
     - Kubernetes
   * - Configuration
     - A ``.env`` file read by docker-compose. ``ENVIRONMENT`` is ``local``.
     - The ``env`` map of the chart's ``values.yaml``, rendered into every pod's environment.
       ``ENVIRONMENT`` is ``alpha``, ``beta``, ``next`` or ``prod``.
   * - Kubernetes namespace
     - None is used. ``smarter_settings.environment_namespace`` is ``smarter-local``.
     - ``<platform name>-<platform subdomain>-<environment>``, e.g. ``smarter-platform-prod``.
       Each environment of an installation has its own namespace.
   * - Hostnames
     - ``localhost:9357`` for the web console, the API and sandbox LLMClients.
     - ``platform.example.com`` (or ``<environment>.platform.example.com``) for the web console,
       ``api.platform.example.com`` for the API, and one hostname per deployed LLMClient. See
       :doc:`URL Patterns <../smarter-platform/url-patterns>`.
   * - TLS
     - None: plain HTTP on localhost.
     - cert-manager issues a certificate for every hostname, including one per deployed LLMClient.
       Custom Domains also get an ACM certificate, for the domain alone, which proves the domain's
       delegation and is never served.
   * - Routing a request to an LLMClient
     - Django resolves the LLMClient from the URL path (sandbox URLs).
     - Traefik routes the hostname to the ``smarter-api`` Service through the LLMClient's own Ingress.
       Django then resolves the LLMClient from the ``Host`` header.
   * - Deploying an LLMClient
     - Sets ``deployed`` in the database. The deployment tasks only create cloud resources if the
       containers have cloud credentials and a kubeconfig (see the warning below).
     - Creates a DNS A record, an Ingress, a cert-manager Certificate and a TLS Secret, then
       verifies them. See :doc:`smarter-on-kubernetes/llmclient-deploy`.
   * - Scaling
     - One container per service.
     - HorizontalPodAutoscalers for the app and the operational worker; the app's also scales
       on memory, measured against ``api.resources.requests.memory``, and follows
       ``hpa.behavior``. Pods are stateless; all state is in the database, Redis, and the cloud.
   * - Health checks
     - None.
     - Startup and liveness probes on ``/healthz/``, which the ASGI application answers before
       Django (:mod:`smarter.lib.django.healthz`), so they say whether the process is alive, and a
       readiness probe on ``/readiness/``, which goes through Django and its middleware, so a pod
       whose Redis or database stalls is taken out of the Service rather than restarted. The
       startup probe checks every 2 seconds, so a pod takes traffic as soon as it has loaded,
       typically within 15 seconds. The probes send ``Host: localhost``, which the security
       middleware lets through. A terminating pod waits 5 seconds (``preStop``) for the Service to
       stop sending it requests, then finishes its requests in progress.
   * - Timeouts
     - The same, except the database's.
     - Connecting to the database times out after 5 seconds, and to Redis after 2. A Redis
       command times out after 5 seconds. The web server's database queries time out after
       ``api.databaseReadTimeout`` seconds (``SMARTER_DATABASE_READ_TIMEOUT``, 60 by default),
       and the workers', the scheduler's and the init Job's never do, since migrations can run
       long. A SqlConnection's ``timeout`` is its driver's connect and query timeout.
   * - Upgrades
     - Rebuild the image and restart the containers.
     - ``helm upgrade``: the migration Job, a rolling update with ``maxUnavailable: 0``, then the
       init Job.
   * - Logs
     - ``docker logs <container>``.
     - ``kubectl logs`` per pod. Smarter reads the logs of the pods it creates itself, such as
       an LLMHost's or a self-hosted vector store's, with the Kubernetes service.
   * - Cloud resources
     - None, normally.
     - Route53 records, ACM certificates, EKS node groups (:doc:`LLMHost <../smarter-resources/smarter-llmhost>`)
       and StatefulSets with volumes (self-hosted :doc:`vector stores <../smarter-resources/smarter-vectorstore>`),
       recorded in the infrastructure resource ledger.

.. warning::

   The deployment tasks act on whatever cloud credentials and kubeconfig their container has. If you
   give a Docker environment real AWS credentials and a kubeconfig for a real cluster, deploying an
   LLMClient locally creates real Route53 records and applies a real Ingress to the namespace
   ``smarter-local`` of that cluster. To keep a Docker environment self-contained, leave the cloud
   credentials out, or set ``SMARTER_APP_LLMCLIENT_TASKS_CREATE_DNS_RECORD=false`` and
   ``SMARTER_APP_LLMCLIENT_TASKS_CREATE_INGRESS_MANIFEST=false``.


How Smarter Talks to the Cluster
--------------------------------

Smarter never calls the Kubernetes API from a client library. The
:doc:`infrastructure services <technologies/infrastructure>` run
`kubectl <https://kubernetes.io/docs/reference/kubectl/>`__ as a subprocess, with a kubeconfig that
the cloud provider writes (``aws eks update-kubeconfig`` for EKS), and with the cloud identity of the
pod. Every pod that runs the image has ``kubectl`` and the AWS CLI installed, and ``KUBECONFIG``
points at ``/home/smarter_user/data/.kube/config``.

In practice, the infrastructure worker is the pod that changes the cluster: it applies and deletes
Ingresses, and reads Certificates and Secrets. The permissions that this requires, and how to keep them small, are described in
:doc:`smarter-on-kubernetes/operations`.

Kubernetes, DNS and certificate calls all go through one facade,
``smarter.apps.infrastructure.services.infrastructure``, so the cloud is a configuration choice
(``SMARTER_PLATFORM_CLOUD_PROVIDER``), and tests replace it with an in-memory provider.


Cluster Prerequisites
---------------------

The Helm chart installs Smarter itself. It does not install the cluster add-ons that LLMClient
deployment depends on. Before the first LLMClient is deployed, the cluster needs:

- **Traefik** as an ingress controller, with the ``traefik`` IngressClass and the ``websecure``
  entry point, exposed by a cloud load balancer.
- A **Traefik Middleware** named ``https-redirect`` in the environment's namespace. Every LLMClient
  Ingress refers to it as ``<namespace>-https-redirect@kubernetescrd``.
- **cert-manager**, with a **ClusterIssuer named after the environment's API domain**, e.g.
  ``api.platform.example.com`` in production or ``alpha.api.platform.example.com`` in alpha. Every
  LLMClient Ingress names it in its ``cert-manager.io/cluster-issuer`` annotation.
- A **DNS zone** for the API domain, whose **A record points at the load balancer**. Every LLMClient's
  A record is a copy of it.
- An **identity** for the pods that can manage that DNS zone and the namespace's Ingresses. See
  :doc:`smarter-on-kubernetes/operations`.

The `Smarter Terraform modules <https://github.com/smarter-sh/smarter-infrastructure>`__ build this
infrastructure on AWS. See :doc:`Production Deployment <../smarter-platform/installation/production-deployment>`.
