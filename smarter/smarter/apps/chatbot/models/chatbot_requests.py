# pylint: disable=W0613,C0115,C0302
"""All models for the OpenAI Function Calling API app."""

from django.db import models

from smarter.lib import json, logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .chatbot import ChatBot

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CHATBOT_LOGGING])


class ChatBotRequests(TimestampedModel):
    """
    Stores the request history for a ChatBot instance within the Smarter platform.

    This model is designed to record and manage all incoming requests made to a chatbot, providing a persistent audit trail
    of interactions for analysis, debugging, and reporting. Each record in this model captures the details of a single request,
    including the associated chatbot, the request payload, session information, and aggregation status.

    **Purpose and Usage**

    The ChatBotRequests model enables comprehensive tracking of chatbot usage and user interactions. By storing each request,
    the platform can support features such as:

    - Request analytics and reporting for chatbot performance and user engagement.
    - Debugging and trouble shooting of chatbot behavior by reviewing historical requests.
    - Session management, allowing grouping and correlation of requests within a user session.
    - Aggregation of requests for batch processing or summarization.

    **Model Relationships**

    - Each ChatBotRequests entry is linked to one :class:`ChatBot` instance, establishing a direct association between the request and the chatbot that handled it.

    **Notes**

    - This model is intended for internal use to support auditing, analytics, and operational monitoring of chatbot activity.
    - The request data is stored in JSON format to accommodate flexible and extensible payload structures.
    - Aggregation support allows for efficient handling of bulk or grouped requests, which may be relevant for advanced chatbot workflows.

    **Example Usage**

    .. code-block:: python

        # Record a new request for a chatbot
        ChatBotRequests.objects.create(
            chatbot=my_chatbot,
            request={"message": "Hello, chatbot!"},
            session_key="abc123",
            is_aggregation=False,
        )

        # Retrieve all requests for a specific chatbot
        requests = ChatBotRequests.objects.filter(chatbot=my_chatbot)

    See Also:

    - :mod:`smarter.apps.chatbot.tasks`

    """

    class Meta:
        verbose_name_plural = "ChatBot Requests History"

    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)
    request = models.JSONField(
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )
    session_key = models.CharField(max_length=255, blank=True, null=True)
    is_aggregation = models.BooleanField(default=False, blank=True, null=True)


__all__ = [
    "ChatBotRequests",
]
