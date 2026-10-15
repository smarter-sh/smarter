"""LLMClientExtensions model."""

from django.db import models

from smarter.apps.llmtool.models import Extension
from smarter.lib import logging
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .llmclient import LLMClient

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


class LLMClientExtensions(TimestampedModel):
    """
    The Extensions whose tools a LLMClient offers the LLM.

    Each record links an LLMClient to an :class:`~smarter.apps.llmtool.models.Extension`,
    as listed, by slug, in the LLMClient manifest's ``spec.extensions``. On each prompt, the
    tools of the linked extensions that are enabled, and available to the LLMClient's
    account, are offered to the LLM.

    **Usage Example**

    .. code-block:: python

        LLMClientExtensions.objects.create(llmclient=my_llmclient, extension=weather)
        extensions = LLMClientExtensions.extensions_for(my_llmclient)
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "LLMClient Extensions"
        unique_together = ("llmclient", "extension")

    llmclient = models.ForeignKey(LLMClient, on_delete=models.CASCADE)
    extension = models.ForeignKey(
        Extension,
        on_delete=models.CASCADE,
        related_name="llmclient_extensions",
        help_text="The Extension.",
    )

    @classmethod
    def extensions_for(cls, llmclient: LLMClient) -> list[Extension]:
        """
        Return the extensions of a LLMClient, in order of slug, with their installed versions.

        The versions' archives are not fetched: :func:`~smarter.apps.llmtool.extension.loader.load_version`
        reads one only the first time a process loads it.

        :param llmclient: The LLMClient.
        :returns: The LLMClient's extensions, enabled or not.
        :rtype: list[Extension]
        """
        return [
            link.extension
            for link in cls.objects.filter(llmclient=llmclient)
            .select_related("extension", "extension__installed_version", "extension__installed_version__extension")
            .defer("extension__installed_version__archive")
            .order_by("extension__slug")
        ]


__all__ = [
    "LLMClientExtensions",
]
