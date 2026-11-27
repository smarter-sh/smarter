The Tool Worker
===============

The tool worker, ``smarter-worker-tools``, is the Celery worker that executes LLM tool calls: API, SQL
and MCP calls, Extensions' tools, and the web search plugin's searches and page fetches. These run
requests and code that manifest authors, Extension authors and the LLM choose, so the tool worker
holds nothing else of the platform's: no database, no Smarter Secret, no Django or Fernet key, no LLM
provider's key, no IAM role and no Kubernetes token. Each call brings the credentials that it needs,
resolved by the app. :doc:`ADR-038 </adr/038-tool-isolation-and-egress>` is the design, and
:doc:`/smarter-resources/llmtool/runner` describes the runner that sends calls to it.

The tool worker also knows only its own task, ``run_tool_call``. It runs the platform's image and
Celery app, which register every app's tasks, so at startup it removes all but that one and Celery's
own from its registry (``TOOL_WORKER_TASKS`` in :mod:`smarter.lib.celery_conf`). Its banner lists
that one task, and it rejects any other message on its queue as an unregistered task.

Without the tool worker, which is the default, the app runs each tool call in its own process, where
the platform's credentials are.

What the Chart Deploys
----------------------

``workerTools.enabled`` adds:

- the Deployment ``smarter-worker-tools``, ``workerTools.replicaCount`` pods (2 by default), each
  running ``workerTools.concurrency`` calls at once (4 by default, each a process of about 0.2 to 0.4
  GiB), on the queue
  ``SMARTER_APP_TOOLS_TASKS_CELERY_TASK_QUEUE``. It runs without task events (no ``-E``), which would
  copy each call's arguments to Celery's events stream, and without the init container that waits for
  the database;
- its Secret, ``smarter-env-tools``, with only its own Redis user's credentials, settings that aren't
  secret, ``SMARTER_DATABASE_UNAVAILABLE=true`` and ``AWS_EC2_METADATA_DISABLED=true``. The template
  ``smarter.toolsEnv`` in ``_helpers.tpl`` lists them;
- its Redis user, ``tools`` (``redis.auth.acl.users``), described below;
- its ServiceAccount, ``smarter-tools``, which has no IAM role and no Kubernetes permissions, and whose
  token isn't mounted.

It also sets ``SMARTER_APP_LLMTOOL_TOOL_RUNNER=remote`` in the platform's environment, so that the app
and the other workers send their tool calls to the tool worker, unless ``env`` sets it.

The tool worker's pods are in the application-group ``smarter-tools``, not ``smarter``, so that none of
the platform's network policies apply to them. smarter-infrastructure's ``smarter-tools-egress`` lets
them reach Redis, MariaDB's port, for SQL plugins whose connection is the platform's own database, DNS,
and the internet on ports 443, 80 and 3306, but no private or link-local address: not the app's pods,
the other workers, the nodes, the EKS api or the instance metadata service. Redis's and MariaDB's own
policies admit them. Nothing may connect to the tool worker.

Its Redis User
--------------

Every other pod is Redis's ``default`` user, which may do anything. The tool worker is the user ``tools``,
whose password smarter-infrastructure generates in the Secret ``smarter-redis-users``, and whose ACL lets
it touch only:

- its own queue, ``tools_celery_task_queue``, and the keys under that name where kombu keeps its messages
  in flight (``CELERY_BROKER_TRANSPORT_OPTIONS`` in ``settings/base.py``);
- the tool calls' results, ``celery-task-meta-*``;
- Extensions' archives in the cache, read-only, and the robots.txt cache that a page fetch checks;
- the console's log streams, write-only.

It may not list keys or channels, whose names include sessions' keys, nor subscribe to a channel. So code
that a tool call runs there, an Extension's included, can't push a task to another worker's queue, such as
the infrastructure worker's, which holds the Kubernetes Role and the IAM role, nor read anyone's session
or edit Celery Beat's schedule (:doc:`ADR-030 </adr/030-task-queues>`, rule 8). For the same reason, the
tool worker doesn't declare its queue, which would write kombu's routing set (the app declares it), and
runs without remote control, mingle, gossip or heartbeats.

When it starts, the tool worker checks this itself (``check_tool_worker_redis`` in
:mod:`smarter.apps.infrastructure.startup`): it reads its own queue, then tries each read that its user
must be refused, and logs one line per read, INFO when it is refused and ERROR when it isn't. The ACL's
rules are in the Helm chart's ``values.yaml``; docker-compose's Redis has the same, which a test keeps
in step.

Turning It On
-------------

1. Apply smarter-infrastructure's network policies for ``smarter-tools`` in the environment, and its
   Secrets ``smarter-redis-password`` and ``smarter-redis-users``. Without the policies, the namespace's
   default-deny policy keeps the tool worker from reaching Redis: it starts, but takes no task, and every
   tool call fails after its timeout. Without ``smarter-redis-users``, the tool worker has no Redis
   password, and refuses to start.
2. Set ``workerTools.enabled: true`` in the environment's values, and deploy. smarter-sh's own deploy
   action, ``.github/actions/deploy``, sets it from its input ``tool-worker-enabled``, ``true`` by default.
3. Watch a tool call: its ``run_tool_call`` task appears in ``smarter-worker-tools``' log, and the
   tool's answer in the chat. ``smarter-worker-tools`` is a component of the MCPServer's log tools.

To turn it off, set ``workerTools.enabled: false`` and deploy: the app runs tool calls itself again.

What Changes for Tool Calls
---------------------------

- **Latency.** Each call makes a round trip through Redis, a few milliseconds.
- **Timeouts.** The app waits four times the call's own timeout, plus 15 seconds, at most 10 minutes.
  A tool worker that doesn't answer in that time, e.g. because none is running, is an error that the
  LLM sees and can recover from, not a failed prompt.
- **Waffle switches** read as off in the tool worker, which has no database. Extensions receive their
  switches with each call, read in the app.
- **Extensions' code** reaches the tool worker through the cache: the app publishes an installed
  version's archive there, keyed by its sha256, when it sends a call, and the tool worker checks the
  sha256 before it loads the code. An archive that isn't in the cache, e.g. right after
  ``manage.py reset_cache``, is published again by the next call.
- **The log.** The tool worker logs one line per call: its kind, its task id, its outcome
  (``succeeded``, ``tool error`` or ``failed``, with the HTTP status when there was a response), how
  long it took, and its label: the tool's name, the LLMClient, the chat session's key, masked, and the
  request's id. For example, ``http call 8b96acda-... succeeded (HTTP 200) in 0.586s: tool=image_search
  llmclient=stackademy (12) session=****a1b2c3 request=-``. A call that failed or that the tool answered
  with an error is a warning. The line never holds the call's arguments, its result or a failure's text,
  which can hold a credential or what a database answered. Celery's own lines hide each task's
  arguments and result. A call made outside a chat, e.g. by an orchestration, is ``unlabeled``. When
  the tool worker doesn't answer, the app logs a warning with the same label.
- **Credentials in Redis.** A call's arguments, with its credentials, wait in Redis until the tool
  worker takes the task, and its result waits until the app reads it, then is deleted. Only the
  namespace's pods can reach Redis. The tool worker's own user may read its queue, so code in one of its
  processes can read the other calls waiting there; issue #1077 isolates Extensions' calls from them.

Local Development
-----------------

``make run`` starts ``smarter-worker-tools`` too, with ``SMARTER_DATABASE_UNAVAILABLE=true``, as Redis's
``tools`` user, which docker-compose's Redis defines with the chart's rules. It shares ``.env`` with the
other services, for convenience, so it is not isolated from their credentials locally. It takes calls only
when ``.env`` sets ``SMARTER_APP_LLMTOOL_TOOL_RUNNER=remote``; the tests use the in-process runner.
