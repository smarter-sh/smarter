ADR-038: Tool Isolation and Egress Control
==========================================

Status
------
Proposed

Context
-------
:doc:`../smarter-platform/system-administration/security/supply-chain` lists two weaknesses that remain
after the cheaper ones were fixed:

- **Outbound traffic is open to any address** on ports 443, 80, 587 and 3306. Most malicious packages send
  what they steal with an ordinary HTTPS request, which the network policies allow.
- **Every application pod holds every credential.** The app, both workers, beat and the Jobs share the
  ServiceAccount ``smarter``, its IAM role, its Kubernetes Role (which includes Secrets), and one Secret with
  the database password, the Fernet key that encrypts Smarter Secrets, the LLM providers' API keys and the
  SES password (``helm/charts/smarter/templates/secret-env.yaml``, read with ``envFrom`` by every
  deployment).

Port 443 can't simply be closed, because several features call hosts that a manifest author or the LLM
chooses. All of them run **inside the chat request**, in the app's process:
``OpenAICompatibleChatProvider.process_tool_call()``
(``smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider``) dispatches each
tool call in-process to:

- **API and SQL plugins**, and the web search and image search plugins (``smarter.apps.llmtool.plugin``,
  ``smarter.apps.connection``), which connect to any host, on 443, 80 or 3306;
- **MCP clients** (``smarter.apps.mcpclient``), which connect to any MCP server;
- **Extensions** (``smarter.apps.llmtool.extension``). An extension is third-party Python code: its archive
  is stored in the database, extracted and **imported into the app's own process** at run time
  (``extension/loader.py``), where it can read every credential. The registry's signature says who
  published an extension, not what its code does;
- **vector search**, which reaches the vectorstore's backend.

The LLM call itself also runs in the app's process, and an LLMClient or LLMHost can point it at a
custom endpoint.

The cloud and Kubernetes writes are already separate. They run in Celery tasks on the infrastructure
queue, in ``smarter-worker-infrastructure`` (:doc:`ADR-030 <030-task-queues>`), not in the app.

Decision
--------
Proposed, in three parts, each useful by itself.

1. **A tool worker with no credentials.** Tool calls that reach hosts chosen by a manifest author or the
   LLM (API, SQL, web search and image search plugins, MCP clients, and extensions) run in a new
   deployment, ``smarter-worker-tools``, behind a boundary in code, ``ToolRunner``.

   - The app resolves everything a call needs before it sends it: the plugin's or MCP client's
     configuration, and the Smarter Secrets that call uses, decrypted. The message is a typed Pydantic
     model (:doc:`ADR-031 <031-pydantic-over-json>`), one per kind of tool.
   - The tool worker has no database access, no Fernet key, no LLM keys, no IAM role and no Kubernetes
     token (``automountServiceAccountToken: false``). It reaches Redis, to take calls and return results,
     and the internet.
   - The tool worker runs the same image. A malicious dependency runs there too, but finds nothing to
     steal except the one call's credentials, which the call was going to send to that host anyway.
   - ``ToolRunner`` has two implementations: in-process (today's behavior, for local development and
     tests) and remote. A setting chooses between them, so the change can ship turned off.
   - Transport: a Celery task on its own queue, ``tools_celery_task_queue``, whose result the app
     waits for with a timeout (the tool's own timeout plus a margin). This follows ADR-030 and needs no
     new service. Waiting on a task's result is fine here, because the app's request waits, not a
     task. The cost is a Redis round trip per tool call, a few milliseconds beside a tool call's
     hundreds.

2. **Credentials by workload.** One ServiceAccount, IAM role and Secret per workload, each with only what
   it uses:

   ===================================== =========================================================
   Workload                              Credentials
   ===================================== =========================================================
   app (``smarter-api``)                 database, Redis, Fernet key, LLM keys, S3 (assets, data
                                         exports)
   ``smarter-worker``                    database, Redis, Fernet key, LLM keys, SES
   ``smarter-worker-infrastructure``     database, Redis, the IAM role for Route53, ACM and node
                                         groups, the Kubernetes Role (ingresses, certificates,
                                         Secrets)
   ``smarter-beat``                      database, Redis
   ``smarter-worker-tools``              Redis only; each call brings its own credentials
   Jobs (init, migrate)                  database (administrator), and what
                                         ``initialize_platform`` uses
   ===================================== =========================================================

   The table is a starting point. Phase 0 below checks it against the code: which settings each process
   reads, and which AWS and Kubernetes calls it makes.

3. **An egress allowlist for every pod but the tool worker.** The app, the workers, beat and the Jobs
   reach the internet only through an in-cluster egress proxy, which allows a list of hosts: the LLM
   providers, AWS's endpoints, and GitHub (``load_from_github``). Their network policy allows egress to the proxy, the database, Redis, Loki and DNS, and nothing else.
   The tool worker keeps today's rules: 443, 80, 3306 and DNS.

   - The proxy is `Smokescreen <https://github.com/stripe/smokescreen>`__, an HTTP CONNECT proxy built
     for this. It allows hosts by name, per client, and refuses private and metadata addresses, so it
     can't be used to reach the cluster's own services. ``HTTPS_PROXY`` and ``NO_PROXY`` in each pod's
     environment send requests, httpx (the OpenAI SDK), boto3 and urllib through it.
   - An LLMClient or LLMHost with a custom endpoint is a host that a manifest author chooses. Either its
     calls go through the tool worker too, or applying the manifest adds its host to the allowlist. The
     first is simpler; the second keeps one path for every LLM call.
   - Email: SMTP on 587 doesn't go through an HTTP proxy. Either sending moves to SES's HTTPS api
     (``django-ses``) and port 587 closes, or 587 stays open to SES's SMTP endpoint only.

Alternatives considered
-----------------------
- **DNS-aware network policies** (Calico Enterprise, Cilium) allow egress by host name in the CNI. They
  need a commercial Calico, or replacing the CNI on a running cluster. The proxy needs neither.
- **AWS Network Firewall** with domain lists filters at the VPC, so it can't tell the tool worker from the
  app: the pods' addresses change. It also costs about 0.40 USD an hour per Availability Zone, plus traffic.
- **A separate service** (an internal HTTP api) instead of a Celery queue for the tool worker. It avoids
  the result backend, but adds a server, its own scaling, and a second way for pods to talk to each
  other. Revisit if the Celery round trip proves too slow.
- **A separate image** for the tool worker with fewer packages. Worth doing later. It shrinks what a
  compromise can do there, but the tool worker already has nothing to steal.

Consequences
------------
What this stops, and what it doesn't:

- **A generic stealer in any dependency**, the common case, runs in every pod. In the tool worker it finds
  no credentials. In every other pod it finds credentials, but its HTTPS request to its own server is
  refused by the proxy.
- **An extension** runs only in the tool worker, with only its call's arguments.
- **A targeted attack is still possible.** Code running in the app can ask the tool worker to fetch a URL
  of its choosing, because fetching chosen URLs is what API plugins and web search do. That channel
  needs an attacker who knows Smarter's task protocol. It doesn't stop a determined, Smarter-specific
  attacker, and the proxy's log of every host contacted is what would show one. DNS lookups remain a
  second, slower way out for any pod.
- Tool calls gain a Redis round trip, and the tool worker is a deployment to scale and watch.
- Local development keeps the in-process runner, so ``make run`` and the tests don't need the proxy or
  the tool worker.

Plan
----
Phase 0, inventory
   For each process, which settings it reads, which AWS and Kubernetes calls it makes, and which hosts it
   contacts, from the code and from a week of the proxy in log-only mode (phase 3's proxy, allowing
   everything). The table in part 2 is corrected from this.

Phase 1, the boundary (smarter)
   ``ToolRunner``, its call and result models, and the in-process runner, with every tool call in
   ``process_tool_call()`` going through it. No change in behavior. Tests: each kind of tool, through
   the runner.

   In progress. The runner is :mod:`smarter.apps.llmtool.runner`: ``ToolCall`` and
   ``ToolCallResult``, the ``InProcessToolRunner``, and ``TOOL_EXECUTORS``, which maps each
   kind of call to its executor by dotted path, so that ``llmtool`` imports none of the apps it runs
   tools for. Caching stays in the app, around the runner: a call is resolved, and its credentials
   read, only when the cache misses. MCP clients go through it: the toolkit resolves an
   ``MCPToolCall``, which carries the MCPClient's ``MCPEndpoint`` (its url, transport, timeout,
   headers with the credential, and its permissions), and ``execute_mcp_call()`` connects from the
   endpoint alone, checking the permissions again. API plugins go through it too:
   ``ApiConnection.execute_query()`` resolves an ``ApiToolCall`` (the full url, and the headers with
   the connection's ``Authorization``), ``execute_api_call()`` sends it with ``safe_http``, and the
   app sends the connection's signals from the result, whose ``status_code`` tells a rejected
   credential from other failures. So do the web search apis (Brave, Tavily), the Brave image search
   and its checks of each image's url, as the generic ``http`` kind: ``fetch_with_runner()`` takes the
   place of ``safe_http.fetch()``, sends an ``HttpToolCall`` with ``fetch``'s arguments, and turns the
   result back into a ``SafeResponse``, with the body in base64. Every website's robots.txt is an
   ``http`` call too. The web search plugin's fetch of a page is the ``webfetch`` kind: its
   ``redirect_policy``, a function, travels as data (the domain policy's allowed and blocked domains,
   and whether to obey robots.txt), and ``execute_webfetch_call()`` builds the function where the call
   runs. SQL plugins are the ``sql`` kind: ``SqlConnection.execute_query()`` resolves a ``SqlToolCall``
   (the database's settings with its password, the final SQL, and the SSH tunnel's settings for
   ``tcpip_ssh``), and ``execute_sql_call()`` opens the tunnel, connects, queries and closes both. A
   failure to connect is a ``failure``, and a query the database rejects is ``is_error``, so the app can
   still tell them apart. The SSH tunnel, which was broken, now works, and pins the SSH server's host key
   to ``sshKnownHosts`` instead of writing an unknown key to the database mid-connection, which a worker
   couldn't do. Extensions are the ``extension`` kind: ``ExtensionToolCall`` carries the validated
   arguments, the settings with their secrets decrypted, the Extension's switches, read from waffle in
   the app, and who called, as plain identifiers (``ExtensionCaller``: account number, user id,
   LLMClient name), which replace the ``account``, ``user_profile`` and ``llmclient`` database objects
   that an Extension's context used to hold. ``execute_extension_call()`` runs the tool in its thread,
   with its timeout.

   Done: every tool call that reaches a host chosen by a manifest author or the LLM goes through the
   runner. Vector search, static and skill plugins stay in the app: they reach no such host. One
   dependency on the database remains for phase 2: an Extension's code, its archive, is read from the
   database the first time a process runs a version (``load_by_key()``), so a worker needs it from
   elsewhere, e.g. an object store keyed by its sha256.

Phase 2, the tool worker (smarter, Helm chart)
   The remote runner, the ``tools`` queue, ``deployment-worker-tools.yaml`` with its own ServiceAccount, no
   Secret and no token, and its network policy (smarter-infrastructure). Behind a setting, off by
   default, and turned on in prod once the suite passes with the remote runner.

Phase 3, credentials by workload (Helm chart, smarter-infrastructure)
   A ServiceAccount, IAM role and Secret per workload, from the phase 0 table. The Kubernetes Role
   moves to ``smarter-worker-infrastructure`` only.

Phase 4, the egress proxy (Helm chart, smarter-infrastructure)
   Smokescreen in the namespace, in log-only mode, then enforcing, and the network policies of every pod
   but the tool worker narrowed to the proxy. The decisions on custom LLM endpoints and email are made
   before this phase.

Decisions for the maintainers
-----------------------------
1. Custom LLM endpoints: through the tool worker, or added to the allowlist when a manifest is applied.
2. Email: SES's HTTPS api, closing 587, or 587 to SES only.
3. Whether phase 2 ships before phase 3 (recommended: the tool worker contains extensions, the larger
   risk, and doesn't depend on the credential split).
