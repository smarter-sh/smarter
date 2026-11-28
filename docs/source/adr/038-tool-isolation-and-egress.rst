ADR-038: Tool Isolation and Egress Control
==========================================

Status
------
Accepted. Phases 1 and 2 are implemented, and smarter-sh's deploy runs the tool worker. Phase 0's
inventory of the code is done; its inventory of live traffic waits for phase 4's proxy. Phases 3 and 4
are not started.

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
Three parts, each useful by itself.

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
   - The settings enforce it. In a worker without a database, the tool worker and the Extension worker,
     ``Settings.check_restricted_worker_credentials()`` refuses to start if the environment gives it any
     credential but its own Redis user's password. A credential is any ``SecretStr`` setting, so a new
     one is covered without being listed, and the one exception is marked on its field
     (:mod:`smarter.common.conf.credentials`). A deployment that passed the worker the platform's whole
     environment would fail at once, rather than run with every key in reach. docker-compose gives both
     workers only the settings that the Helm chart does, never ``.env``, so local development is isolated
     the same way. The check keys on ``SMARTER_DATABASE_UNAVAILABLE``, so a worker that lost that flag
     would skip it; each pod also names its kind in ``SERVICE_TYPE``, and a ``worker-tools`` or
     ``worker-extensions`` pod with a database refuses to start (``Settings.check_service_type()``). The
     settings' first log line names the kind and the checks made for it.
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
   contacts, from the code and from a week of the proxy in log-only mode (phase 4's proxy, allowing
   everything). The table in part 2 is corrected from this.

   The code's half is done, as of 0.48.8. It was read, not traced, so the proxy's log confirms it and
   finds what a search of the code misses: a host built at run time, or a library's own calls. What it
   found:

   .. image:: ../_static/adr-038/credentials.svg
      :alt: A matrix of the platform's credentials against its workloads. The LLM providers' and services'
            keys, the MariaDB root password and the administrator's password are used only by the init Job
            (and the root password by the bastion), but every pod but the tool worker holds them. Every
            process with a database holds DJANGO_SECRET_KEY only because a startup check requires it. The
            app uses the SMTP password, the Kubernetes Role and the IAM role. The tool worker holds none.

   **Where each credential is read.** Everything is in one Secret, ``secret-env.yaml``, which the app,
   both workers, beat and the Jobs read with ``envFrom``. The bastion reads only the database's and
   AWS's keys, one by one, and has no ServiceAccount token. The backup CronJob has its own
   ServiceAccount and IAM role. The code reads each credential in these places:

   - **The LLM providers' keys** (OpenAI, Anthropic, Gemini, Mistral, Cohere, Fireworks, Together AI,
     Llama), the Google service account, Google Maps', Tavily's, Brave Search's and Pinecone's keys:
     only ``initialize_platform``'s commands read them from the environment (``initialize_providers``,
     ``initialize_llmtool_api_keys``, ``initialize_vectorstore_providers``), and each stores them as a
     Smarter Secret. Every other process reads them from the database, decrypted with the Fernet key.
     The app and the workers need the Fernet key, then, but not these keys: only the init Job does.
   - **The Fernet key** (``apps/secret/models.py``): every process that decrypts a Smarter Secret.
     That includes ``smarter-worker-infrastructure``, which part 2 leaves out: ``deploy_vectorstore``
     writes a self-hosted vectorstore's api key into a Kubernetes Secret.
   - **The database's password**: every process but the tool worker. ``require_django_secret_key()``
     makes every process with a database refuse to start without ``DJANGO_SECRET_KEY``, outside the
     local environment, so beat and the workers hold it too, though they sign nothing. Phase 3 has to
     relax that check for them.
   - **The MariaDB root password**: ``load_from_github``, for a repository's SQL scripts
     (``repository_scripts.py``), so the init Job, and the bastion. No running pod uses it.
   - **The backup account's password**: the backup CronJob and the bastion.
   - **The platform administrator's password**: ``initialize_platform`` only.
   - **The SMTP (SES) password**: every process that sends email. That includes the app, which part 2
     leaves out: activation, password reset and account contacts' emails are sent inside the request.
     Also the worker (data exports, notifications) and the Jobs (``email_job_log``).
   - **The social sign-in keys** (Google, GitHub, LinkedIn): Django's settings, used by the app only.
   - **The GitHub token** (``GITHUB_TOKEN``): skill downloads (``skill_sources.py``), bug reports, and the indexing of
     The Smarter Project's repositories (``mcpserver.services.github``).
   - **The Slack bot's token**: ``infrastructure.slack``, for the Jobs' notifications. The Slack app
     token is read only by the separate Slack bot chart. ``DOCKERHUB_*`` is read by no Python.

   .. image:: ../_static/adr-038/cluster-writes.svg
      :alt: The LLMClient broker hands its writes to tasks on the infrastructure queue, which
            smarter-worker-infrastructure runs against the Kubernetes api, Route53, ACM and EKS. The LLMHost
            and vectorstore brokers write to the Kubernetes api, and the LLMHostCompute broker to EKS, from
            the app's own request. The app's status pages and tools read the Kubernetes api.

   **Where the Kubernetes and AWS calls are made.** Part 2 gives the cluster and the cloud to
   ``smarter-worker-infrastructure`` alone. The code calls them from the app as well:

   - **The cluster, written from the app's request**: an LLMHost's ``deploy``, ``undeploy`` and
     ``delete`` (``LLMHostService.launch()``, ``destroy()``, ``delete()``: Deployments, Services,
     Ingresses, Secrets), and a vectorstore's ``apply`` and ``delete`` (``backend.provision()`` and
     ``destroy()``: a StatefulSet, Service, Secret and volume). The LLMClients' ingresses, DNS records
     and certificates are already infrastructure tasks.
   - **EKS and Auto Scaling, written from the app's request**: an LLMHostCompute's ``deploy``
     (``ComputeProvisioner.reconcile()``) creates and scales its node group, and its ``delete`` (a
     ``pre_delete`` receiver) deletes it.
   - **The cluster, read by the app**: an LLMHost's observation and logs, a vectorstore's conditions
     and logs, the MCPServer's status tools (pods, nodes), ``smarter status``
     (``get_kubernetes_cluster_info()``), and the startup check ``check_kubernetes``, which the app and
     every Celery worker but the tool worker run.
   - **AWS, read by every process with a database**: ``sts:GetCallerIdentity`` when the settings are
     checked (``aws_credentials_work()``). Without AWS it only warns.
   - **S3**: the data exports (worker: ``put_object``, a presigned url, and ``delete_object`` when they
     expire), and the static files on the CDN (init Job, ``collectstatic``).
   - **The init Job** reads Route53 (``verify_dns_configuration``), rewrites the LLMClients' ingresses
     (``retarget_llmclient_ingresses``) and reads the cluster for the inventory
     (``sync_infrastructure_inventory``, which beat also schedules on the infrastructure queue).

   So the Kubernetes Role can't move to ``smarter-worker-infrastructure`` alone until the LLMHost,
   LLMHostCompute and vectorstore brokers hand their writes to infrastructure tasks, as the LLMClient's
   already do. Until then the app needs the write Role and the EKS permissions. Its reads need a
   read-only Role of their own either way.

   .. image:: ../_static/adr-038/egress.svg
      :alt: For each process, the services in the cluster it reaches, the fixed hosts on the internet,
            which seed phase 4's allowlist, and the hosts that a manifest author chooses. The app and the
            default worker reach MCPClients' servers and vectorstores' ApiConnections, and the app custom
            LLM endpoints, outside the tool worker. The tool worker reaches every host a tool call chooses.

   **Which hosts each process contacts.** The fixed hosts, the seed of phase 4's allowlist:

   - App: the LLM providers' apis, Pinecone's, the social sign-in providers', GitHub's
     (``api.github.com``, ``raw.githubusercontent.com``, ``codeload.github.com``; ``smarter version``
     fetches the cli's ``VERSION`` file), the account manager's subscription api
     (``api.am.<root domain>``), SES's SMTP endpoint, and AWS's STS and S3. In-cluster: MariaDB,
     Redis, Loki, the Kubernetes api, the LLMHosts and the self-hosted vectorstores.
   - ``smarter-worker``: the LLM providers (prompts, embeddings, the LLM price checker), Pinecone,
     GitHub and the blog (indexing), the extension registry (``smarter-sh.github.io``), SES and S3.
   - ``smarter-worker-infrastructure``: Route53, ACM, EKS, the Kubernetes api, and public DNS
     (``resolve_domain()``).
   - beat: Redis (RedBeat), and STS when the settings are checked. It only sends tasks.
   - Jobs: all of the above, and GitHub's clones (``load_from_github``), the extension registry
     (``install_official_extensions``) and Slack's api.

   And the hosts that a manifest author chooses, reached outside the tool worker. These decide phase
   4's custom-endpoint question for more than LLMs:

   - **An MCPClient's catalog.** Each tool call goes through the runner, but the connection that
     lists the server's tools (``mcpclient.caching.connect()``) is made in the app, when a chat builds
     its tools and when the console refreshes it, and in the worker (``mcpclient.tasks``), with the
     MCPClient's credential.
   - **A vectorstore's ApiConnection**, e.g. Qdrant Cloud: the app (search) and the worker (loading
     documents).
   - **An LLMClient's or LLMHost's custom endpoint**, as part 3 says.
   - **A provider's website, terms and docs urls** (``provider.verification``), and an LLM price's
     ``source_url`` (``llm_price_checker``): the worker.
   - ``PluginDataApi.execute_request()`` still calls ``requests.get()`` itself, outside the runner.
     Nothing calls it, or the ``test()`` and ``sanitized_return_data()`` that wrap it, so they can be
     deleted. ``smarter.apps.api.utils.apply_manifest()``, which posts a manifest to the platform's
     own url, has no caller either.

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
   dependency on the database remained for phase 2: an Extension's code, its archive, which a process
   read from the database the first time it ran a version (``load_by_key()``).

Phase 2, the tool worker (smarter, Helm chart)
   The remote runner, the ``tools`` queue, ``deployment-worker-tools.yaml`` with its own ServiceAccount, no
   Secret and no token, and its network policy (smarter-infrastructure). Behind a setting, off by
   default, and turned on in prod once the suite passes with the remote runner.

   Built, and off by default in the chart. smarter-sh's deploy action, ``.github/actions/deploy``, turns
   it on with its input ``tool-worker-enabled``, ``true`` by default. ``RemoteToolRunner`` sends each call, as JSON, in the Celery task
   ``run_tool_call`` on the queue ``tools_celery_task_queue``, and waits for its result in the result
   backend, the broker's Redis. ``CELERY_TASK_IGNORE_RESULT`` keeps every other task's result out of it,
   and a result is forgotten once read. ``TOOL_CALL_MODELS`` maps each kind to its call's model, which
   rebuilds the call in the worker. ``SMARTER_APP_LLMTOOL_TOOL_RUNNER`` (``in_process`` or ``remote``)
   chooses the runner. Inside the worker, every call runs in process, so that an executor's own calls,
   such as a page fetch's robots.txt, don't go back to the queue. A worker that doesn't answer within
   four times the call's timeout, plus 15 seconds, is a ``failure`` for the LLM, as is a task that fails.

   The worker, ``smarter-worker-tools``, sets ``SMARTER_DATABASE_UNAVAILABLE``: it opens no database
   connection, reads every waffle switch as off (Extensions get theirs in the call), and runs without
   the Django secret key, which would let code there forge the platform's sessions. Its Celery app
   registers ``run_tool_call`` and Celery's own tasks only, so a message for any other task that lands
   on its queue is rejected, not run. Each call it runs is logged on one line, labeled with the tool,
   the LLMClient, the chat session (masked) and the request, never its arguments or result. An Extension's
   archive reaches it through the cache: the app publishes the archive, keyed by its sha256, when it
   resolves a call for the remote runner, and renews it on each call; the worker checks the sha256
   before it loads the code. The chart's ``workerTools`` deploys it with a Secret of its own, holding
   the broker's and the cache's url and settings that aren't secret, a ServiceAccount without a token or
   an IAM role, ``AWS_EC2_METADATA_DISABLED``, and pods in the application-group ``smarter-tools``, to
   which none of the platform's network policies apply. Its own policy lets it reach Redis, MariaDB's
   port, DNS, and the internet on 443, 80 and 3306, but no private or link-local address: not the app,
   the other pods, the EKS api or the instance metadata service.

   What remains: the call's arguments, with its credentials, sit in Redis until the worker takes the
   task, as they did in the app's memory. Redis is reachable only from the namespace's pods. Encrypting
   the arguments to a key that only the tool worker holds would close that, at the cost of a key to
   manage. MariaDB's port stays open to the worker for SQL plugins whose connection is the platform's
   own MariaDB, such as Stackademy's; the worker has no credential for it but the call's. Code running
   in the tool worker, an Extension's included, held the broker's and the cache's Redis url, so it could
   reach the cache, the sessions and the other workers' queues. The tool worker is now Redis's ``tools``
   user, which reaches only its own queue, its results and a few cache keys (ADR-030, rule 8). It can
   still read the other calls waiting on its own queue. Extensions' calls, the third-party code, run apart,
   in the Extension worker, ``smarter-worker-extensions`` (#1077): on their own queue, each call in a
   process of its own (``--max-tasks-per-child=1``), and as the Redis user ``extensions``, which can't read
   the tools queue. An Extension can still read the other Extensions' calls waiting on its own queue, and
   any tool call's result.

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
3. Whether phase 2 ships before phase 3. Decided: it did, because the tool worker contains extensions,
   the larger risk, and doesn't depend on the credential split.
