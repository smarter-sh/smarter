# pylint: disable=W0613
"""
API view for the Dashboard "Recent Activity" React component.

Returns the user's most recent manifest commands that change something, i.e.
``apply``, ``delete``, ``deploy`` and ``undeploy``, from the
:class:`~smarter.lib.journal.models.SAMJournal`. The journal is only written
while the ``enable_journal`` waffle switch is active, so the response says
whether it is.
"""

from http import HTTPStatus
from typing import Any, Optional

from django.http import HttpRequest, JsonResponse

from smarter.apps.account.models import get_resolved_user
from smarter.lib.django.views import SmarterAuthenticatedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseErrorKeys,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)
from smarter.lib.journal.models import SAMJournal

MAX_ITEMS = 10
MAX_MESSAGE_LENGTH = 200
ACTIVITY_COMMANDS = (
    SmarterJournalCliCommands.APPLY.value,
    SmarterJournalCliCommands.DELETE.value,
    SmarterJournalCliCommands.DEPLOY.value,
    SmarterJournalCliCommands.UNDEPLOY.value,
)


def journal_message(response: Any) -> Optional[str]:
    """The message of a journaled response, or the description of its error."""
    if not isinstance(response, dict):
        return None
    message = response.get(SmarterJournalApiResponseKeys.MESSAGE)
    error = response.get(SmarterJournalApiResponseKeys.ERROR)
    if not message and isinstance(error, dict):
        message = error.get(SmarterJournalApiResponseErrorKeys.DESCRIPTION)
    if not isinstance(message, str):
        return None
    return message[:MAX_MESSAGE_LENGTH]


class ActivityView(SmarterAuthenticatedWebView):
    """
    The user's most recent manifest commands that change something.

    Response shape:

    .. code-block:: json

        {
            "journal_enabled": true,
            "items": [
                {
                    "created_at": "2026-10-04T17:20:16Z",
                    "thing": "Plugin",
                    "command": "apply",
                    "status_code": 200,
                    "message": "Plugin everlasting_gobstopper applied successfully"
                }
            ]
        }
    """

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        user = get_resolved_user(request.user)
        entries = SAMJournal.objects.filter(user=user, command__in=ACTIVITY_COMMANDS).order_by("-created_at")[
            :MAX_ITEMS
        ]
        retval = {
            "journal_enabled": switch_is_active(SmarterWaffleSwitches.ENABLE_JOURNAL),
            "items": [
                {
                    "created_at": entry.created_at,
                    "thing": entry.thing,
                    "command": entry.command,
                    "status_code": entry.status_code,
                    "message": journal_message(entry.response),
                }
                for entry in entries
            ],
        }
        return JsonResponse(retval, status=HTTPStatus.OK)
