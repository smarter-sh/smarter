LLMClient Deployment
====================

An :doc:`LLMClient <../../smarter-resources/smarter-llmclient>` starts out in the **sandbox**: it
is served on the web console's own host, e.g.
``https://platform.example.com/workbench/llm-clients/<id>/``, and only signed-in users of its account
can chat with it. **Deploying** it gives it its own public hostname, for example:

.. code-block:: text

   https://stackademy.3141-5926-5359.api.platform.example.com/

where ``stackademy`` is the LLMClient's name, ``3141-5926-5359`` is its account number, and
``api.platform.example.com`` is the environment's API domain (``smarter_settings.environment_api_domain``).
A deployed LLMClient authenticates its callers with :doc:`API keys <../../smarter-platform/api-keys>`
instead of the Django session, and can be the backend of
:doc:`Smarter Chat <../smarter-chat>` on any web page.

On Kubernetes, that hostname is not just a string. Deploying creates four resources, and each must
exist before the hostname works:

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Resource
     - Name
     - Purpose
   * - DNS A record
     - ``<default host>``, in the API domain's zone
     - Resolves the hostname to the platform's load balancer. It is a copy of the API domain's own A
       record (an alias record on Route53).
   * - Ingress
     - ``<default host>``, in the environment's namespace
     - Tells Traefik to route HTTPS requests for the hostname to the ``smarter`` Service, port 8000.
   * - cert-manager Certificate
     - ``<default host>-tls``
     - Created by cert-manager from the Ingress's annotations. Requests and renews the hostname's TLS
       certificate from the ClusterIssuer.
   * - Secret
     - ``<default host>-tls``
     - The issued certificate and its private key. Traefik serves it for the hostname.

An LLMClient with a verified :doc:`Custom Domain <../../smarter-resources/smarter-custom-domain>`
gets the same A record and Ingress (and so a Certificate and Secret) for its custom host too, e.g.
``stackademy.llmclients.example.com``.

No Pod, Deployment or Service is created per LLMClient. Every LLMClient is served by the same
``smarter`` pods, which find the LLMClient from the request's ``Host`` header. Deploying an LLMClient
adds routing, not compute.


Starting a Deployment
---------------------

There are four ways to deploy an LLMClient. All of them end the same way: the LLMClient's
``deployed`` field changes from false to true, and ``LLMClient.save()`` sends the
``llmclient_deploy`` signal, whose receiver queues the Celery task ``deploy_default_api``.

.. code-block:: console

   # the smarter CLI, which calls the REST API: POST /api/v1/cli/deploy/LLMClient/
   smarter deploy llmclient stackademy

   # an administrator, in a smarter pod
   python manage.py deploy_llmclient --account_number 3141-5926-5359 --name stackademy

The fourth is the manifest itself: ``spec.config.prompt.deployed: true``, applied with
``smarter apply -f llmclient.yaml``.

.. warning::

   ``spec.config.prompt.deployed`` defaults to false. Applying a manifest that omits it, or sets it
   to false, **undeploys** an LLMClient that is deployed, which destroys its DNS record. Keep
   ``deployed: true`` in the manifests of deployed LLMClients, for example in a CI pipeline that
   applies them.

The web console's deploy action calls the same API. The API answers as soon as ``deployed`` is
saved: the response means "deployment started", not "the hostname works". The rest happens in the
infrastructure worker over the next few minutes, and you follow it in the LLMClient's status (see
`Status Fields`_).

.. important::

   The task is queued only when ``deployed`` **changes**. Deploying an LLMClient that is already
   deployed queues nothing, even if its last deployment failed. To retry a deployment, undeploy the
   LLMClient and deploy it again.

All LLMClient deployment tasks run in the infrastructure queue (``infrastructure_celery_task_queue``),
served by the ``smarter-worker-infrastructure`` Deployment. They retry on an unexpected exception with
exponential backoff, up to ``SMARTER_LLM_CLIENT_TASKS_CELERY_MAX_RETRIES`` times.


The Deployment, Step by Step
----------------------------

1. Is the Cloud Ready?
~~~~~~~~~~~~~~~~~~~~~~

Every task first checks that the cloud provider, its DNS service and its certificate service are
ready, that is, configured with working credentials. If not, the task returns without doing anything,
and logs ``Request is not taskable``. The LLMClient stays ``deployed``, with no resources. This is
what happens in a Docker environment without cloud credentials.

2. The DNS Record
~~~~~~~~~~~~~~~~~

``deploy_default_api`` locks the LLMClient's database row (``SELECT ... FOR UPDATE``) and, unless
``SMARTER_LLM_CLIENT_TASKS_CREATE_DNS_RECORD`` is false, copies the A record of the API domain to the
LLMClient's default host, in the API domain's zone, with a TTL of
``SMARTER_LLM_CLIENT_TASKS_DEFAULT_TTL`` seconds (600 by default; alias records have no TTL of their
own). If the record already exists with the same target, it is left alone; if it exists with a
different target, it is updated.

The row lock matters because a deploy and an undeploy of the same LLMClient can run at the same time
on different workers. Each holds the lock until its A record and status are consistent, so neither
destroys a record the other has just created.

If the LLMClient is already deployed **and** its DNS is verified, the task stops here.

3. The Ingress
~~~~~~~~~~~~~~

Unless ``SMARTER_LLM_CLIENT_TASKS_CREATE_INGRESS_MANIFEST`` is false, the task renders
``smarter/apps/llmclient/k8s/ingress.yaml.tpl`` and applies it with ``kubectl apply``:

.. code-block:: yaml

   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: stackademy.3141-5926-5359.api.platform.example.com
     namespace: smarter-platform-prod
     annotations:
       kubernetes.io/tls-acme: "true"
       cert-manager.io/cluster-issuer: api.platform.example.com
       traefik.ingress.kubernetes.io/router.entrypoints: websecure
       traefik.ingress.kubernetes.io/router.middlewares: smarter-platform-prod-https-redirect@kubernetescrd
     labels:
       app.kubernetes.io/application-group: smarter
       app.kubernetes.io/name: smarter
   spec:
     ingressClassName: traefik
     rules:
     - host: stackademy.3141-5926-5359.api.platform.example.com
       http:
         paths:
         - backend:
             service:
               name: smarter
               port:
                 number: 8000
           path: /
           pathType: Prefix
     tls:
     - hosts:
       - stackademy.3141-5926-5359.api.platform.example.com
       secretName: stackademy.3141-5926-5359.api.platform.example.com-tls

``kubectl apply`` is idempotent: applying it again to an existing Ingress changes nothing. A failure
(the cluster rejects the manifest, or kubectl is not configured) sets the LLMClient's
``tls_certificate_issuance_status`` to ``Failed`` and ends the deployment.

The Ingress deliberately has no Traefik CORS middleware. Traefik would answer CORS preflight requests
itself, so Django, which applies the platform's CORS settings and each LLMClient's
``allowedOrigins``, would never see them.

Then the task sets ``tls_certificate_issuance_status`` to ``Requested`` and ends. It does not wait.

4. The Certificate
~~~~~~~~~~~~~~~~~~

cert-manager sees the Ingress's annotations, creates a Certificate named ``<host>-tls``, and solves an
ACME challenge for the hostname. That takes minutes, and depends on the new A record having
propagated. Rather than hold a worker while it waits (see :doc:`ADR-030 <../../adr/030-task-queues>`),
``deploy_default_api`` schedules a second task, ``continue_default_api_deployment``, to check later:

- first after **10 minutes**, then **every minute**, **30 times** at most, so about 40 minutes in all;
- each check is one ``kubectl get`` of the Ingress, the Certificate and the Secret together, and passes
  when all three exist and the Certificate's ``Ready`` condition is ``True``.

When the check passes, ``tls_certificate_issuance_status`` becomes ``Issued``. When it never passes, it
becomes ``Failed`` and the deployment ends. A redeployment of an LLMClient whose certificate was
already issued checks at once instead of waiting 10 minutes.

5. Domain Verification
~~~~~~~~~~~~~~~~~~~~~~

Next, ``continue_default_api_deployment`` checks that the hostname resolves. It sets
``dns_verification_status`` to ``Verifying`` and resolves the hostname **every 5 minutes, up to 48 times**
(4 hours), again by rescheduling itself rather than sleeping. If it resolves, the status becomes
``Verified``; if it never does, ``Failed``.

6. Done
~~~~~~~

The LLMClient is deployed and verified. The account's primary contact receives an email saying that
the LLMClient is live at its URL. If the LLMClient has a verified Custom Domain, the
``llmclient_deployed`` signal also queues ``deploy_custom_api``.

7. The Custom Host
~~~~~~~~~~~~~~~~~~

``deploy_custom_api`` does steps 2 and 3 again for the custom host: it copies the API domain's A
record into the **custom domain's own DNS zone**, and applies an Ingress for the custom host, for which
cert-manager issues its own certificate. It does not wait for that certificate. It does nothing if
the LLMClient is not deployed or its custom domain is not verified, and it is idempotent.

Verifying the custom domain itself (its NS delegation and ACM certificate) is a separate process,
described in :doc:`Custom Domain <../../smarter-resources/smarter-custom-domain>`. Once that
verification succeeds, it deploys the LLMClients that use the domain.


Timeline
~~~~~~~~

A typical first deployment, when everything works:

.. list-table::
   :header-rows: 1
   :widths: 15 85

   * - Time
     - What happens
   * - 0 s
     - The API returns. ``deployed`` is true. ``deploy_default_api`` is queued.
   * - Seconds
     - The A record and the Ingress are created. ``tls_certificate_issuance_status`` is ``Requested``.
   * - 1-5 minutes
     - cert-manager obtains the certificate (outside Smarter).
   * - 10 minutes
     - The first certificate check passes. ``tls_certificate_issuance_status`` is ``Issued``.
       ``dns_verification_status`` is ``Verifying``.
   * - 10-15 minutes
     - The hostname resolves. ``dns_verification_status`` is ``Verified``. The owner gets an email.

The hostname usually works some minutes before the status says so, because the first certificate
check waits 10 minutes.


Status Fields
-------------

Two fields of the LLMClient model record the deployment's progress. Both are listed in the Django
admin's LLMClient page. ``dns_verification_status`` is also in the manifest's read-only ``status``,
as ``dnsVerificationStatus``, so ``smarter describe llmclient <name>`` shows it, next to ``deployed``.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``tls_certificate_issuance_status``
     - Meaning
   * - ``No Certificate``
     - Never deployed on Kubernetes.
   * - ``Requested``
     - The Ingress was applied; waiting for cert-manager.
   * - ``Issued``
     - The Ingress, Certificate and Secret exist, and the Certificate is ready.
   * - ``Failed``
     - The Ingress could not be applied, or the certificate was not ready within about 40 minutes.

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - ``dns_verification_status``
     - Meaning
   * - ``Not Verified``
     - Never deployed, or undeployed.
   * - ``Verifying``
     - Waiting for the hostname to resolve.
   * - ``Verified``
     - The hostname resolves. The deployment is complete.
   * - ``Failed``
     - The hostname did not resolve within 4 hours.

``deployed`` true with ``dns_verification_status`` ``Verified`` is a working deployment. ``deployed``
true with anything else is a deployment in progress, or one that failed and must be retried.


Undeploying
-----------

.. code-block:: console

   smarter undeploy llmclient stackademy

   # or, in a smarter pod
   python manage.py undeploy_llmclient --account_number 3141-5926-5359 --name stackademy

Undeploying sets ``deployed`` to false, and ``LLMClient.save()`` queues ``undeploy_default_api``. That
task locks the row, **destroys the default host's A record**, and resets ``dns_verification_status`` to
``Not Verified``. If the LLMClient was deployed again in the meantime, it does nothing.

Undeploying does **not** delete the Ingress, the Certificate or the Secret, and does not touch the
custom host. They stay in the cluster, so a later redeployment reuses the issued certificate and
completes quickly. Meanwhile the hostname no longer resolves, so clients can't reach it, even though
Traefik still has a route for it.


Deleting
--------

Deleting an LLMClient (``smarter delete llmclient <name>``, or deleting its account) queues
``delete_default_api`` once the deletion is committed, so a deletion that is rolled back deletes
nothing. The task destroys the default host's A record and deletes its Ingress, Certificate and
Secret.

As a safety check, it refuses to delete anything for a hostname that is not of the form
``<name>.<account number>.<API domain>`` of the LLMClient's own account, and logs an error instead.

If ``delete_default_api`` fails, or never runs, the A record outlives its LLMClient. Celery Beat runs
the task ``delete_orphan_dns_records`` daily, in the AWS environments only. It deletes the A records,
in the API domain's zone, whose name is exactly ``<label>.<account number>.<API domain>`` and which
no LLMClient or LLMHost uses, deployed or not, at most 50 per run. Another environment's hosts in the
same zone, e.g. ``stackademy.3141-5926-5359.alpha.api.platform.example.com``, have more labels, and
are never touched. To see what it would delete, run:

.. code-block:: console

   python manage.py delete_orphan_dns_records --dry-run

Neither undeploying nor deleting removes the **custom host's** A record and Ingress. See
:doc:`operations` for how to find and remove them.


Configuration
-------------

.. list-table::
   :header-rows: 1
   :widths: 50 15 35

   * - Environment variable
     - Default
     - Effect
   * - ``SMARTER_LLM_CLIENT_TASKS_CREATE_DNS_RECORD``
     - ``true``
     - Create an A record per LLMClient. Set it to false only if DNS answers for every LLMClient host
       some other way, such as a wildcard record.
   * - ``SMARTER_LLM_CLIENT_TASKS_CREATE_INGRESS_MANIFEST``
     - ``true``
     - Apply an Ingress per LLMClient. Without it, cert-manager issues no certificate, and the
       deployment skips the certificate check.
   * - ``SMARTER_LLM_CLIENT_TASKS_DEFAULT_TTL``
     - ``600``
     - TTL, in seconds, of the A records that are not aliases.
   * - ``SMARTER_LLM_CLIENT_TASKS_CELERY_MAX_RETRIES``
     - ``3``
     - Retries of a deployment task after an unexpected exception.
   * - ``SMARTER_LLM_CLIENT_TASKS_CELERY_RETRY_BACKOFF``
     - ``true``
     - Exponential backoff between those retries.
   * - ``SMARTER_INFRASTRUCTURE_TASKS_CELERY_TASK_QUEUE``
     - ``infrastructure_celery_task_queue``
     - The queue of every deployment task. The infrastructure worker must consume it.
   * - ``SMARTER_CLOUD_PROVIDER``
     - ``aws``
     - The provider of DNS, certificates and the kubeconfig.

A wildcard DNS record can stand in for the per-LLMClient A records, but a wildcard TLS certificate
cannot stand in for the per-LLMClient certificates: a wildcard certificate covers one DNS label, and
LLMClient hosts are two labels below the API domain (name and account number).


Technical Reference
-------------------

- ``smarter.apps.llmclient.tasks``: ``deploy_default_api``, ``continue_default_api_deployment``,
  ``deploy_custom_api``, ``undeploy_default_api``, ``delete_default_api``.
- ``smarter.apps.llmclient.k8s.ingress.yaml.tpl``: the Ingress template.
- ``smarter.apps.llmclient.receivers``: the signal receivers that queue the tasks.
- :doc:`Kubernetes <../technologies/kubernetes>` and
  :doc:`Infrastructure services <../technologies/infrastructure>`.
