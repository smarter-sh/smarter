The Egress Proxy
================

The egress proxy, ``smarter-egress-proxy``, is `Smokescreen <https://github.com/stripe/smokescreen>`__,
Stripe's HTTP CONNECT proxy, in the platform's namespace. The app, ``smarter-worker``,
``smarter-worker-infrastructure``, Celery Beat and the Jobs send their HTTP and HTTPS requests through
it, and it logs every host they contact. Most malicious packages send what they steal with an ordinary
HTTPS request; once the proxy enforces its allowlist and the pods' network policies send their traffic
nowhere else, that request is refused. :doc:`ADR-038 </adr/038-tool-isolation-and-egress>`, phase 4, is
the design.

It is rolled out in two stages (issue #1085):

1. **Report.** The proxy allows every host, and logs the ones that its allowlist doesn't list. A week
   of this is the live half of ADR-038's inventory of the hosts each process contacts: it confirms the
   fixed hosts that a reading of the code found, and finds what the reading missed, e.g. a host built at
   run time or a library's own calls. The pods' network policies are unchanged.
2. **Enforce.** The proxy refuses the hosts that its allowlist doesn't list, and the pods' network
   policies allow the proxy, MariaDB, Redis, Loki and DNS, and nothing else.

The tool worker, the Extension worker and the bastion don't use it. The tool worker reaches the hosts
that tool calls choose, under network policies of its own (:doc:`tool-worker`), and the bastion is an
administrator's shell.

What the Chart Deploys
----------------------

``egressProxy.enabled`` adds:

- the Deployment ``smarter-egress-proxy``, ``egressProxy.replicaCount`` pods (2 by default), running
  Stripe's own image, ``ghcr.io/stripe/smokescreen``, pinned by digest in ``egressProxy.image``. Its pods
  have no ServiceAccount token, no Secret and no environment, and run as the platform's non-root user
  from a read-only root filesystem;
- its Service, ``smarter-egress-proxy``, on port 4750 (``egressProxy.port``);
- its configuration, the ConfigMap ``smarter-egress-proxy``: Smokescreen's ``config.yaml`` and its ACL,
  ``acl.yaml``.

It also gives the proxied pods' containers ``HTTPS_PROXY``, ``HTTP_PROXY`` and ``NO_PROXY``, in both
upper and lower case (curl and apt, which the backup's container runs, read only the lower case
names). requests, httpx (the LLM providers' SDKs), botocore and urllib read them, and so do kubectl and
the AWS CLI.

The proxy's pods are in the application-group ``smarter-egress``, not ``smarter``, so that their network
policies are their own: smarter-infrastructure's let the platform's pods reach them on port 4750, and
let them reach DNS and the internet's public addresses on ports 443 and 80.

The ACL
-------

The platform's pods present no TLS client certificate, which is how Smokescreen tells its clients
apart, so every request gets the ACL's default rule (``allow_missing_role`` in ``config.yaml``; without
it, Smokescreen refuses every request). Its action is ``egressProxy.action``: ``report`` (stage 1) or
``enforce`` (stage 2). Its allowlist is ``egressProxy.allowedDomains``, the fixed hosts of ADR-038's
inventory, plus the AWS endpoints of ``env.AWS_REGION`` and the account manager's api,
``api.am.<root domain>``. A leading ``*.`` matches every subdomain, not the domain itself.

Smokescreen refuses private, link-local and metadata addresses whatever the action, so a request
through it can't reach the cluster, the VPC or the instance metadata service.

What Goes Around It
-------------------

Because the proxy refuses private addresses, the pods send everything in the cluster and the VPC around
it. ``NO_PROXY`` (``smarter.egressProxyNoProxy`` in ``_helpers.tpl``) lists:

- ``localhost``, and the in-cluster names ``.svc`` and ``.cluster.local``, which the LLMHosts' and the
  self-hosted vectorstores' endpoints use;
- the short names that the settings use: Loki's (from ``SMARTER_SUBSYSTEM_LOGGING_LOKI_URL``), the
  database's (``SMARTER_SUBSYSTEM_SQL_HOST``) and the app's Services;
- ``.eks.amazonaws.com``, the cluster's api, which kubectl reaches at its private endpoint from inside the
  VPC;
- the instance metadata service and the EKS pod identity agent;
- the private ranges, for the clients that read a CIDR in ``NO_PROXY``: requests and Go's (kubectl).
  httpx, urllib and botocore don't, so a private address they reach must be reached by a name in the
  list.

``egressProxy.noProxy`` adds to it. Redis and MariaDB aren't HTTP, and don't use the proxy at all.

Reading Its Log
---------------

The proxy logs JSON, one ``CANONICAL-PROXY-DECISION`` line per connection and one
``CANONICAL-PROXY-CN-CLOSE`` line when it closes. The fields that matter:

- ``requested_host``: the host and port that the client asked for;
- ``inbound_remote_addr``: the client pod's address, which names the pod, and so its kind;
- ``enforce_would_deny``: ``true`` when the allowlist doesn't list the host. In stage 1 these are the
  hosts to review: each one is either added to ``egressProxy.allowedDomains`` or found to be a request
  that shouldn't happen;
- ``allow`` and ``decision_reason``: what the proxy did, and why, e.g. ``default rule policy used`` or
  ``denied by rule 'Deny: Private Range'``.

It never logs a path, a query string or a header: only hosts. Alloy ships its log to Loki with the
other pods'.

Turning It On
-------------

1. Apply smarter-infrastructure's network policies for ``smarter-egress`` in the environment
   (smarter-sh/smarter-infrastructure#19). Without them, the namespace's default-deny policy keeps the
   platform's pods from reaching the proxy, and every outbound HTTP request fails.
2. Set ``egressProxy.enabled: true`` in the environment's values, and deploy. smarter-sh's own deploy
   action, ``.github/actions/deploy``, sets it from its input ``egress-proxy-enabled``, ``false`` by
   default, which the deploy workflow reads from the repository variable ``EGRESS_PROXY_ENABLED``.
3. Watch its log: a chat's prompt appears as a ``CANONICAL-PROXY-DECISION`` for its LLM provider's host.

To turn it off, set ``egressProxy.enabled: false`` and deploy: the pods reach the internet directly
again.

Local Development
-----------------

``make run`` and the tests don't use the proxy: docker-compose sets no proxy variable.
