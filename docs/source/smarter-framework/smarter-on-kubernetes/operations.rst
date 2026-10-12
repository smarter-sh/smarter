Operating Smarter at Scale
==========================

This page is for the people who keep a Smarter installation running: who answer tickets about
LLMClients that can't be reached, size the cluster, review its security, and clean up after
customers. It assumes you have read :doc:`llmclient-deploy`.


What Grows with Every LLMClient
-------------------------------

The ``smarter`` pods serve every LLMClient, so the compute that you need grows with traffic, not with
the number of LLMClients. The routing does grow with the number of LLMClients:

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Resource
     - Count
     - What to watch
   * - DNS A records
     - one per deployed LLMClient, plus one per custom host
     - The DNS provider's records-per-zone limit. On Route53, the default quota is 10,000 records per
       hosted zone, and can be raised.
   * - Ingresses
     - one per LLMClient ever deployed, plus one per custom host
     - Traefik keeps a router and a TLS configuration for each one in memory, and reloads them when
       any of them change. Watch Traefik's memory and reload times.
   * - cert-manager Certificates and TLS Secrets
     - one each per Ingress
     - Your ACME certificate authority's rate limits. Let's Encrypt, for example, limits the number of
       new certificates per registered domain per week, so deploying hundreds of LLMClients at once
       can be throttled. cert-manager renews every certificate before it expires, so the renewal
       load is steady, and grows with the number of Ingresses.
   * - Celery tasks
     - about 10 to 15 per deployment, mostly short checks
     - The infrastructure worker's capacity. See below.

Ingresses outlive undeployments (see :doc:`llmclient-deploy`), so their number follows the
LLMClients that were ever deployed and not yet deleted, not the ones deployed now.


Sizing the Infrastructure Worker
--------------------------------

Every deployment, undeployment and deletion runs in the ``smarter-worker-infrastructure`` Deployment.
Each pod runs 4 concurrent tasks (``--concurrency=4``), and each task shells out to ``kubectl`` and the
AWS CLI, which are CPU bound while they start. That is why the chart gives this worker a CPU limit of 2.

A deployment holds a worker only while it works: its waits (10 minutes for the certificate, up to 4
hours for DNS) are scheduled with Celery's ``countdown``, not slept. So a few infrastructure workers
can carry many deployments in flight. Add replicas (``workerInfrastructure.replicaCount``) when:

- the infrastructure queue's length grows and stays high, for example after ``helm install`` on a new
  cluster, when the init Job deploys every built-in LLMClient at once, or after restoring a database;
- deployments take noticeably longer than the timeline in :doc:`llmclient-deploy`.

The infrastructure worker has no HorizontalPodAutoscaler, on purpose: its work is bursty and bounded by
the cloud's and cert-manager's speed, not by CPU.

Delayed tasks wait in the broker (Redis) and in the workers that have reserved them. When a worker
shuts down cleanly, Celery returns its reserved tasks to the queue; when it is killed, the Redis
transport redelivers them after its visibility timeout. Restarting the infrastructure worker in the
middle of deployments delays them, but does not lose them.


Security
--------

Who Can Change the Cluster
~~~~~~~~~~~~~~~~~~~~~~~~~~

Smarter changes the cluster with ``kubectl``, using the cloud identity of the pod it runs in. Every pod
that runs the Smarter image has the same environment, so in practice that identity belongs to the
whole platform. Give it the least Kubernetes RBAC that the platform needs, in the environment's
namespace only. For LLMClient deployment, that is:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Resource
     - Verbs
   * - ``ingresses`` (``networking.k8s.io``)
     - ``get``, ``list``, ``create``, ``patch``, ``delete``
   * - ``certificates`` (``cert-manager.io``)
     - ``get``, ``list``, ``delete``
   * - ``secrets``
     - ``get``, ``delete``
   * - ``namespaces``
     - ``get``

:doc:`LLMHosts <../../smarter-resources/smarter-llmhost>` and self-hosted
:doc:`vector stores <../../smarter-resources/smarter-vectorstore>` need more (StatefulSets,
PersistentVolumeClaims, Services, pod logs), and the infrastructure inventory lists cluster-scoped
nodes and persistent volumes. Grant those only if you use those features.

Note that checking a deployment reads the TLS Secret with ``kubectl get``, which returns its private
key to the worker. Smarter only checks that the Secret exists, but the permission is to read it.

Who Can Change DNS
~~~~~~~~~~~~~~~~~~

The same identity changes DNS. It needs to read and change records in the API domain's hosted zone
and, for :doc:`Custom Domains <../../smarter-resources/smarter-custom-domain>`, to create hosted zones
and records in them, and to request and read ACM certificates. Scope the IAM policy to those zones
where you can.

The API domain must have its **own** A record, pointing at the platform's load balancer: every
LLMClient's record is a copy of it. Never point the API domain at the root domain's A record, which
may point at a marketing site or a CDN rather than the platform.

Configuration Secrets
~~~~~~~~~~~~~~~~~~~~~

The Helm chart renders the ``env`` map of ``values.yaml`` into the environment of every pod, as
plain values in the Deployment and Job specs. That map holds the database passwords, the Django secret
key, the Fernet encryption key, the cloud credentials and the LLM providers' API keys. Anyone who can
``get`` the Deployments, Pods or Jobs of the namespace can read all of them. So:

- restrict ``get`` on those resources in the platform's namespace to the people who operate it;
- keep the values file out of version control, or encrypt it;
- prefer short-lived cloud credentials for the pods (for example IAM roles for service accounts on
  EKS) over static access keys, where your installation supports it.

Tenants and Isolation
~~~~~~~~~~~~~~~~~~~~~

Every account's LLMClients run in the same pods, with the same database, and share the same Ingress
controller and load balancer. Isolation between tenants is enforced by the application: each
resource belongs to an account, and a request for a deployed LLMClient is authenticated with that
LLMClient's :doc:`API keys <../../smarter-platform/api-keys>`. An LLMClient that has no active API key
is **public**: anyone who knows its URL can prompt it, and its prompts are billed to its account.
Make sure your customers know this before they deploy.

The chart labels every pod ``app.kubernetes.io/application-group``, which the network policies of
the Smarter infrastructure use to allow traffic between the platform's pods. A pod without that
label cannot reach the platform's backing services.

Every LLMClient Ingress uses the ``websecure`` entry point and the ``https-redirect`` middleware, so a
deployed LLMClient is only served over HTTPS. CORS is enforced by Django, not Traefik, from each
LLMClient's ``allowedOrigins``.

Deletion Safety
~~~~~~~~~~~~~~~

The task that deletes an LLMClient's DNS record and Ingress checks that the hostname is
``<name>.<account number>.<API domain>`` for the LLMClient's own account before it deletes anything,
so a malformed or tampered task cannot delete another tenant's, or the platform's, resources.


Monitoring and Logs
-------------------

Deployment tasks log through Smarter's logger, behind `waffle <https://waffle.readthedocs.io/>`__
switches that you turn on in the :doc:`Django admin <../../smarter-platform/django-admin>`:

- ``log_tasks``: every Celery task;
- ``log_llmclient``: LLMClient deployment, undeployment and deletion;
- ``log_infrastructure``: every DNS, certificate and Kubernetes call, including the full manifest
  that is applied.

Every log line of a deployment carries the ``task_id`` of its ``deploy_default_api`` task, so you can
follow one deployment across its rescheduled checks:

.. code-block:: console

   kubectl logs -n smarter-platform-prod deploy/smarter-worker-infrastructure | grep <task_id>

The **infrastructure resource ledger** (``InfrastructureResource``, in the Django admin) records the
DNS records and Kubernetes resources that Smarter creates and destroys. The Celery Beat task
``sync_infrastructure_inventory`` reconciles it every 15 minutes with what actually exists in the
environment's namespace: Ingresses, Certificates, load balancers, volumes, and the cluster's nodes.
Run it on demand with:

.. code-block:: console

   python manage.py sync_infrastructure_inventory


Troubleshooting a Deployment
----------------------------

Start from the LLMClient's two status fields, then look at the matching resource. Run these commands
with a kubeconfig for the cluster, against the environment's namespace.

.. code-block:: console

   HOST=stackademy.3141-5926-5359.api.platform.example.com
   NS=smarter-platform-prod

   kubectl get ingress $HOST -n $NS
   kubectl get certificate $HOST-tls -n $NS
   kubectl describe certificate $HOST-tls -n $NS      # cert-manager's events and ACME challenge state
   kubectl get secret $HOST-tls -n $NS
   dig +short $HOST

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Symptom
     - Likely cause and fix
   * - ``deployed`` is true, both statuses are unchanged, nothing in the worker logs
     - The infrastructure worker isn't consuming ``infrastructure_celery_task_queue``, or the cloud
       isn't ready (``Request is not taskable`` with ``log_tasks`` on). Check the worker's pods and
       its cloud credentials.
   * - TLS status ``Failed`` right away
     - ``kubectl apply`` was rejected. The worker log has kubectl's error: usually RBAC, a missing
       IngressClass, or a kubeconfig that couldn't be written.
   * - TLS status ``Failed`` after about 40 minutes
     - cert-manager didn't issue the certificate. ``kubectl describe certificate`` and the
       cert-manager logs say why: the ClusterIssuer named after the API domain is missing, the ACME
       challenge can't reach the hostname, or the CA rate limited the request.
   * - DNS status ``Failed`` after 4 hours
     - The hostname never resolved. Check that the A record exists in the API domain's zone, and that
       the zone is delegated. A negative answer cached before the record existed can delay resolution
       by the zone's negative-caching TTL.
   * - Works, but the browser rejects the certificate
     - The Secret holds a certificate for another host, or a staging CA's certificate. Delete the
       Certificate and Secret; cert-manager issues a new one from the Ingress.
   * - Requests reach the hostname but return 400
     - Django rejected the ``Host`` header: the host is neither one of the platform's domains nor
       the host of a deployed LLMClient, for example a custom host whose LLMClient was undeployed.

To retry a failed deployment, undeploy the LLMClient and deploy it again. Deploying an LLMClient that
is already deployed does nothing.


Housekeeping
------------

Some resources outlive the LLMClients that needed them, and have to be cleaned up by an operator:

- **Manifests that undeploy.** ``spec.config.prompt.deployed`` defaults to false, so applying an
  LLMClient's manifest without it undeploys the LLMClient. If customers apply manifests from CI, a
  sudden wave of undeployments usually means a manifest lost that line.
- **Undeployed LLMClients keep their Ingress, Certificate and Secret** until they are deleted. That is
  deliberate, so a redeployment is fast, but each one keeps being renewed. Delete them by hand for
  LLMClients that you know won't be redeployed.
- **Custom hosts are never cleaned up.** Neither undeploying nor deleting an LLMClient removes its
  custom host's A record (in the custom domain's zone) or its Ingress, Certificate and Secret. List
  the Ingresses whose host is not under the API domain to find them:

  .. code-block:: console

     kubectl get ingress -n smarter-platform-prod -l app.kubernetes.io/name=smarter \
       -o custom-columns=NAME:.metadata.name --no-headers | grep -v '\.api\.platform\.example\.com$'

- **Stale A records.** Each LLMClient's A record is a copy of the API domain's A record, made when it
  was deployed. If the load balancer is replaced and the API domain's record changes, the copies do
  not follow. Redeploying an LLMClient updates its record; so, at scale, the simplest fix is to keep
  the API domain's record stable (an alias to a load balancer that is not recreated), or to undeploy
  and redeploy the affected LLMClients after the change.
- **Deleted accounts.** Deleting an account deletes its LLMClients, and each deletion queues its own
  cleanup task, with the account number captured beforehand, so the cleanup works after the account
  is gone.

Upgrades and Restores
---------------------

- ``helm upgrade`` performs a rolling update of the ``smarter`` Deployment with
  ``maxUnavailable: 0``, so deployed LLMClients stay reachable. It then runs the init Job, which
  migrates the database and deploys the built-in LLMClients again; those that are already deployed and
  verified need no new resources.
- Restoring the database (see :doc:`Backup and Restore <../../smarter-platform/backup-and-restore>`)
  restores the ``deployed`` and status fields, but not the cluster or DNS. A restored LLMClient that
  is marked deployed is not redeployed automatically. After restoring into a new cluster, undeploy and
  redeploy the LLMClients that must be reachable, in batches, so cert-manager and the CA aren't
  flooded.
