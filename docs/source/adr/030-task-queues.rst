ADR-030: Operational and Infrastructure Task Queues
===================================================

Status
------
Accepted

Context
-------
Smarter's Celery tasks are of two kinds:

- **Operational** tasks record what happens on the platform: a prompt's history, tool calls and
  plugin usage, charges, budgets, and the aggregation of these records. They are quick, there are
  many of them, and users depend on them: a conversation whose history is not recorded loses its
  context, and a charge that is not recorded escapes its budget.
- **Infrastructure** tasks deploy, verify and destroy cloud, Kubernetes and DNS resources: an
  LLMClient's DNS record, ingress and TLS certificate, a custom domain, an LLMHost's node group, a
  vectorstore's database. A certificate takes minutes to be issued, and a DNS record or a domain's
  name servers take up to a day to propagate.

Both kinds shared one queue and one pool of workers, and the infrastructure tasks waited by
sleeping: ``deploy_default_api`` slept 10 minutes and then polled its certificate for 30 more, and
``verify_domain`` and ``verify_custom_domain`` slept between checks for up to 4 and 24 hours. Deploying
the built-in LLMClients occupied every worker for half an hour, until Celery's task time limit killed
them, while the operational tasks waited behind them. Conversations lost their history, and failed
on their next prompt.

Decision
--------
1. **Separate queues and workers.** Operational tasks run in
   ``smarter_settings.llmclient_tasks_celery_task_queue`` (``default_celery_task_queue``), served by
   the ``smarter-worker``. Infrastructure tasks run in
   ``smarter_settings.infrastructure_tasks_celery_task_queue`` (``infrastructure_celery_task_queue``),
   served by its own ``smarter-worker-infrastructure``. A deployment can never block an operational task.
2. **Never wait in a task.** A task that waits for something outside Smarter checks once, and if it
   is not ready, schedules itself to check again later, with ``apply_async(countdown=...)``, passing the
   number of attempts made. It does not ``time.sleep()``, so it holds a worker only while it works.
3. **Each task declares its queue** in its ``@app.task(queue=...)``, and each Celery Beat entry names
   the same queue in its ``options``, because Beat sends a task by name, without importing it. A queue
   that no worker consumes is never processed.

Alternatives Considered
-----------------------
- **More workers in one queue.** It postpones the problem: enough deployments still occupy every worker.
- **Celery task priorities.** They reorder waiting tasks, but cannot free a worker that a task holds.
- **Separate queues only.** Infrastructure tasks would still hold their own workers while they sleep,
  and run into Celery's task time limit, so a slow DNS propagation would fail a deployment.

Consequences
------------
- **Positive:**

  - Operational tasks run promptly, however many deployments are in progress.
  - A deployment that waits hours for DNS holds no worker, and is not killed by the task time limit.
  - The two kinds of task can be scaled, monitored and restarted independently.

- **Negative:**

  - One more worker Deployment (``templates/deployment-worker-infrastructure.yaml``) and docker-compose service.
  - A new task must be assigned to the right queue, and a task that waits must be written as a sequence
    of checks rather than a loop.

Related ADRs
------------
- :doc:`ADR-009: Async Tasks <009-async-tasks>`
