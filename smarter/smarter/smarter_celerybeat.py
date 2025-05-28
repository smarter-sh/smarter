"""Celery Beat schedule for the smarter project."""

import os

from celery.schedules import timedelta


# Set the default Django settings module for the 'celery' program
# and then instantiate the Celery singleton.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smarter.settings.local")

# pylint: disable=wrong-import-position,unused-import
from smarter.lib.celery_conf import APP as app


app.conf.beat_schedule = {
    "aggregate-chatbot-history": {
        "task": "smarter.apps.chatbot.tasks.aggregate_chatbot_history",
        "schedule": timedelta(hours=12),
        "options": {"queue": "beat_tasks"},
    },
    "aggregate-chat-history": {
        "task": "smarter.apps.prompt.tasks.aggregate_chat_history",
        "schedule": timedelta(hours=12),
        "options": {"queue": "beat_tasks"},
    },
    "aggregate-charges": {
        "task": "smarter.apps.account.tasks.aggregate_charges",
        "schedule": timedelta(hours=1),
        "options": {"queue": "beat_tasks"},
    },
}
