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
      retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
      max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
      queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
  )
  def long_running_task(*args, **kwargs):
        # Your long-running task logic here
        pass

  def foo():
      # Call the long-running task asynchronously
      long_running_task.delay(arg1, arg2, kwarg1=value1)
