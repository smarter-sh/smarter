"""All models for the OpenAI Function Calling API app."""

from django.db import models

from smarter.lib import json, logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .llmclient import LLMClient

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


class LLMClientRequests(TimestampedModel):
    """
    Stores the request history for a LLMClient instance within the Smarter platform.

    This model is designed to record and manage all incoming requests made to an llmclient, providing a persistent audit trail
    of interactions for analysis, debugging, and reporting. Each record in this model captures the details of a single request,
    including the associated llmclient, the request payload, session information, and aggregation status.

    **Purpose and Usage**

    The LLMClientRequests model enables comprehensive tracking of llmclient usage and user interactions. By storing each request,
    the platform can support features such as:

    - Request analytics and reporting for llmclient performance and user engagement.
    - Debugging and trouble shooting of llmclient behavior by reviewing historical requests.
    - Session management, allowing grouping and correlation of requests within a user session.
    - Aggregation of requests for batch processing or summarization.

    **Model Relationships**

    - Each LLMClientRequests entry is linked to one :class:`LLMClient` instance, establishing a direct association between the request and the llmclient that handled it.

    **Notes**

    - This model is intended for internal use to support auditing, analytics, and operational monitoring of llmclient activity.
    - The request data is stored in JSON format to accommodate flexible and extensible payload structures.
    - Aggregation support allows for efficient handling of bulk or grouped requests, which may be relevant for advanced llmclient workflows.

    **Example Usage**

    .. code-block:: python

        # Record a new request for an llmclient
        LLMClientRequests.objects.create(
            llmclient=my_llmclient,
            request={"message": "Hello, llmclient!"},
            session_key="abc123",
            is_aggregation=False,
        )

        # Retrieve all requests for a specific llmclient
        requests = LLMClientRequests.objects.filter(llmclient=my_llmclient)

    See Also:

    - :mod:`smarter.apps.llmclient.tasks`
    """

    class Meta:
        verbose_name_plural = "LLMClient Requests History"

    llmclient = models.ForeignKey(LLMClient, on_delete=models.CASCADE)
    request = models.JSONField(
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )
    session_key = models.CharField(max_length=255, blank=True, null=True)
    is_aggregation = models.BooleanField(default=False, blank=True, null=True)


__all__ = [
    "LLMClientRequests",
]
