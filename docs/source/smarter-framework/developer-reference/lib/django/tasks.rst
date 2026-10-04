Asynchronous Tasks
==================

The Smarter Framework uses Celery to handle asynchronous tasks and background processing.
Namely, Smarter relies on Celery to for IO intensive operations and/or tasks that are
either/both long-running or indeterminate in length. Examples of such tasks include sending emails,
creating database records, processing large datasets, or performing scheduled maintenance operations.

In particular, Smarter relies on asynchronous Celery tasks for all IO related to processing
LLM prompts and responses, other than for the LLM prompt itself.

Basic Usage
-------------

.. code-block:: python

  from django.conf import settings
  from smarter.workers.celery import app

  @app.task(
      autoretry_for=(Exception,),
      retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
      max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
      queue=smarter_settings.llmclient_tasks_celery_task_queue,
  )
  def long_running_task(*args, **kwargs):
        # Your long-running task logic here
        pass

  def foo():
      # Call the long-running task asynchronously
      long_running_task.delay(arg1, arg2, kwarg1=value1)


Queues
------

Every task runs in one of two queues, each served by its own Celery worker. Choose the queue in the
task's ``@app.task(queue=...)``:

- ``smarter_settings.llmclient_tasks_celery_task_queue``: **operational** tasks, which record what
  happens on the platform, such as prompt history, charges and budgets. They must be quick.
- ``smarter_settings.infrastructure_tasks_celery_task_queue``: **infrastructure** tasks, which
  deploy, verify or destroy cloud, Kubernetes or DNS resources, and can take minutes.

A task that waits for something outside Smarter, such as a certificate or a DNS record, must never
``time.sleep()``. It checks once, and if it is not ready, schedules itself to check again later:

.. code-block:: python

  @app.task(queue=smarter_settings.infrastructure_tasks_celery_task_queue)
  def wait_for_certificate(hostname: str, attempt: int = 0):
      if not certificate_is_issued(hostname):
          if attempt + 1 < MAX_ATTEMPTS:
              wait_for_certificate.apply_async(
                  kwargs={"hostname": hostname, "attempt": attempt + 1}, countdown=60
              )
          return
      ...

A Celery Beat entry, in ``smarter/workers/celerybeat.py``, must name the same queue as its task, in
its ``options``. See :doc:`ADR-030 <../../../../adr/030-task-queues>`.
