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


The Services
------------

Both environments run the same five processes. Only how they are started, scaled and connected
differs.

.. list-table::
   :header-rows: 1
   :widths: 22 39 39

   * - Process
     - Docker (``docker-compose.yml``)
     - Kubernetes (Helm chart)
   * - Web application and REST API
     - ``smarter-app``: one container, uvicorn with auto-reload, on port 9357.
     - Deployment ``smarter``: uvicorn with 2 workers per pod, on port 8000, behind the ClusterIP
       Service ``smarter``. A HorizontalPodAutoscaler scales it on CPU (3 to 25 pods by default).
   * - Operational Celery worker
     - ``smarter-worker``, queue ``default_celery_task_queue``.
     - Deployment ``smarter-worker``, same queue, with its own HorizontalPodAutoscaler.
   * - Infrastructure Celery worker
     - ``smarter-worker-infrastructure``, queue ``infrastructure_celery_task_queue``.
     - Deployment ``smarter-worker-infrastructure``, same queue, a fixed number of replicas
       (``workerInfrastructure.replicaCount``, 1 by default).
   * - Celery Beat
     - ``smarter-beat``.
     - Deployment ``smarter-beat``. Run exactly one replica, or scheduled tasks run more than once.
   * - Database and cache
     - ``smarter-mariadb`` and ``smarter-redis`` containers, with local volumes.
     - MySQL or MariaDB and Redis, inside the cluster or managed by the cloud
       (``database.type`` and the ``SMARTER_MYSQL_*`` and ``CACHES_LOCATION`` values).

The two Celery queues are separate on purpose. The infrastructure queue carries the slow tasks that
deploy, verify and destroy DNS records, ingresses, certificates, node groups and databases, so that
they can never delay the operational tasks that record prompt history, charges and budgets. See
:doc:`ADR-030 <../adr/030-task-queues>`.

The Helm chart also runs a Job, ``smarter-job-init``, on every install and upgrade. It migrates the
database, initializes the platform, loads the example resources and deploys the built-in LLMClients.
On a new cluster, that one Job queues a deployment for every built-in LLMClient at once.
When it completes, it emails the end of its log, with credentials redacted, to the chart's
``databaseInit.notifyEmail``, or by default to the platform's admin, ``SMARTER_EMAIL_ADMIN``, with
``manage.py email_job_log``. The email reports whether the Job succeeded. It is sent only when SMTP
is configured (see :doc:`technologies/smtp`), and a Job that is killed, for example for running out
of memory, sends none.


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
       Custom Domains also get an ACM certificate.
   * - Routing a request to an LLMClient
     - Django resolves the LLMClient from the URL path (sandbox URLs).
     - Traefik routes the hostname to the ``smarter`` Service through the LLMClient's own Ingress.
       Django then resolves the LLMClient from the ``Host`` header.
   * - Deploying an LLMClient
     - Sets ``deployed`` in the database. The deployment tasks only create cloud resources if the
       containers have cloud credentials and a kubeconfig (see the warning below).
     - Creates a DNS A record, an Ingress, a cert-manager Certificate and a TLS Secret, then
       verifies them. See :doc:`smarter-on-kubernetes/llmclient-deploy`.
   * - Scaling
     - One container per service.
     - HorizontalPodAutoscalers for the app and the operational worker. Pods are stateless; all
       state is in the database, Redis, and the cloud.
   * - Health checks
     - None.
     - Liveness, readiness and startup probes on ``/healthz/`` and ``/readiness/``, with
       ``Host: localhost``, which the security middleware lets through.
   * - Upgrades
     - Rebuild the image and restart the containers.
     - ``helm upgrade``: a rolling update with ``maxUnavailable: 0``, then the init Job.
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
   credentials out, or set ``SMARTER_LLM_CLIENT_TASKS_CREATE_DNS_RECORD=false`` and
   ``SMARTER_LLM_CLIENT_TASKS_CREATE_INGRESS_MANIFEST=false``.


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
(``SMARTER_CLOUD_PROVIDER``), and tests replace it with an in-memory provider.


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
