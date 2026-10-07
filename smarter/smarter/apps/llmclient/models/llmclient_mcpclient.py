"""
LLMClientMCPClients model.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.db import models

from smarter.apps.mcpclient.models import MCPClient
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .llmclient import LLMClient

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MCPCLIENT_LOGGING])


class LLMClientMCPClients(TimestampedModel):
    """
    The MCPClients whose MCP servers' tools a LLMClient offers the LLM.

    Each record links an LLMClient to an :class:`~smarter.apps.mcpclient.models.MCPClient`,
    as listed in the LLMClient manifest's ``spec.mcpClients``. On each prompt, the tools of
    the linked, active MCPClients are offered to the LLM, in order of their priority.

    **Usage Example**

    .. code-block:: python

        LLMClientMCPClients.objects.create(llmclient=my_llmclient, mcpclient=my_mcpclient)
        mcpclients = LLMClientMCPClients.mcpclients_for(my_llmclient)
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "LLMClient MCPClients"
        unique_together = ("llmclient", "mcpclient")

    llmclient = models.ForeignKey(LLMClient, on_delete=models.CASCADE)
    mcpclient = models.ForeignKey(
        MCPClient,
        on_delete=models.CASCADE,
        related_name="llmclient_mcpclients",
        help_text="The MCPClient.",
    )

    @classmethod
    def mcpclients_for(cls, llmclient: LLMClient) -> list[MCPClient]:
        """
        Return the active MCPClients of a LLMClient, in order of priority and then name.

        :param llmclient: The LLMClient.
        :returns: The LLMClient's active MCPClients.
        :rtype: list[MCPClient]
        """
        return [
            link.mcpclient
            for link in cls.objects.filter(llmclient=llmclient, mcpclient__is_active=True)
            .select_related("mcpclient", "mcpclient__credentials", "mcpclient__user_profile__user")
            .order_by("mcpclient__priority", "mcpclient__name")
        ]


__all__ = [
    "LLMClientMCPClients",
]
