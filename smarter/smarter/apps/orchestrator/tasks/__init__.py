"""Celery tasks for orchestrator app."""

from smarter.common.conf import smarter_settings
from smarter.workers.celery import app


@app.task(queue=smarter_settings.app_llmclient_tasks_celery_task_queue)
def execute_orchestration_run(run_id: int) -> None:
    """
    Execute an Orchestrator's run, one step at a time (ADR-037).

    It is never retried: each step calls an LLM, and is charged, so a retry would repeat them. A run that fails
    records why, and a run that isn't pending, e.g. one that a retry or a duplicate message delivers again, is left
    as it is.

    :param run_id: The ``OrchestrationRun``'s id.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.orchestrator.runtime import execute_run

    execute_run(run_id)


__all__ = ["execute_orchestration_run"]
