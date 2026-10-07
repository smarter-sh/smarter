"""Celery Beat schedule for the smarter project."""

import os

from celery.schedules import timedelta

# Set the default Django settings module for the 'celery' program
# and then instantiate the Celery singleton.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smarter.settings.local")

# pylint: disable=wrong-import-position,unused-import
from smarter.common.conf import smarter_settings
from smarter.lib.celery_conf import APP as app

# Each entry names the queue of its task, the same queue that the task's @app.task declares,
# because beat sends a task by name, without importing it. A queue that no worker consumes is
# not created, and Redis drops its messages: operational tasks go to OPERATIONAL, which the
# smarter-worker consumes, and infrastructure tasks to INFRASTRUCTURE, which the
# smarter-worker-infrastructure consumes.
OPERATIONAL = {"queue": smarter_settings.llmclient_tasks_celery_task_queue}
INFRASTRUCTURE = {"queue": smarter_settings.infrastructure_tasks_celery_task_queue}

app.conf.beat_schedule = {
    "aggregate-prompt-history": {
        "task": "smarter.apps.prompt.tasks.aggregate_prompt_history",
        "schedule": timedelta(hours=12),
        "options": OPERATIONAL,
    },
    "aggregate-charges": {
        "task": "smarter.apps.account.tasks.aggregate_records",
        "schedule": timedelta(hours=1),
        "options": OPERATIONAL,
    },
    "evaluate-budget-constraints": {
        "task": "smarter.apps.account.tasks.evaluate_budget_constraints",
        "schedule": timedelta(hours=1),
        "options": OPERATIONAL,
    },
    "charge-llmhost-computes": {
        "task": "smarter.apps.llmhost.tasks.charge_llmhost_computes",
        "schedule": timedelta(hours=1),
        "options": OPERATIONAL,
    },
    "purge-guardrail-events": {
        "task": "smarter.apps.guardrail.tasks.purge_guardrail_events",
        "schedule": timedelta(days=1),
        "options": OPERATIONAL,
    },
    "refresh-llmhost-status": {
        "task": "smarter.apps.llmhost.tasks.refresh_llmhost_status",
        "schedule": timedelta(minutes=5),
        "options": INFRASTRUCTURE,
    },
    "reconcile-llmhost-computes": {
        "task": "smarter.apps.llmhost.tasks.reconcile_llmhost_computes",
        "schedule": timedelta(minutes=5),
        "options": INFRASTRUCTURE,
    },
    "reconcile-vectorstores": {
        "task": "smarter.apps.vectorstore.tasks.reconcile_vectorstores",
        "schedule": timedelta(minutes=5),
        "options": INFRASTRUCTURE,
    },
    "maintain-vectorstores": {
        "task": "smarter.apps.vectorstore.tasks.maintain_vectorstores",
        "schedule": timedelta(hours=1),
        "options": INFRASTRUCTURE,
    },
    "refresh-mcpclients": {
        "task": "smarter.apps.mcpclient.tasks.refresh_mcpclients",
        "schedule": timedelta(hours=1),
        "options": OPERATIONAL,
    },
}
app.conf.beat_schedule_filename = "/home/smarter_user/data/celery/celerybeat-schedule"

__all__ = ["app"]
