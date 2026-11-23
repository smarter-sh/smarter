"""LLMClientVectorsearches model."""

from django.db import models

from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.lib.django.models import TimestampedModel

from .llmclient import LLMClient


class LLMClientVectorsearches(TimestampedModel):
    """
    The Vectorsearches that an LLMClient offers the LLM, each as a tool that searches its documents.

    Each record links an LLMClient to a :class:`~smarter.apps.vectorsearch.models.Vectorsearch`,
    as listed in the LLMClient manifest's ``spec.vectorsearches``. On each prompt, every linked,
    enabled Vectorsearch is offered to the LLM as a tool whose one argument is a search query, and
    whose result is the chunks of the Vectorsearch's Vectorstore that are closest to it in meaning.
    See :mod:`smarter.apps.vectorsearch.toolkit`.

    **Usage Example**

    .. code-block:: python

        LLMClientVectorsearches.objects.create(llmclient=my_llmclient, vectorsearch=my_vectorsearch)
        vectorsearches = LLMClientVectorsearches.vectorsearches_for(my_llmclient)
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "LLMClient Vectorsearches"
        constraints = [
            models.UniqueConstraint(
                fields=["llmclient", "vectorsearch"], name="llmclient_llmclientvectorsearches_unique"
            ),
        ]

    llmclient = models.ForeignKey(LLMClient, on_delete=models.CASCADE)
    vectorsearch = models.ForeignKey(
        Vectorsearch,
        on_delete=models.CASCADE,
        related_name="llmclient_vectorsearches",
        help_text="The Vectorsearch.",
    )

    @classmethod
    def vectorsearches_for(cls, llmclient: LLMClient) -> list[Vectorsearch]:
        """
        Return the enabled Vectorsearches of a LLMClient, in order of name.

        :param llmclient: The LLMClient.
        :returns: The LLMClient's enabled Vectorsearches, with their Vectorstores.
        :rtype: list[Vectorsearch]
        """
        links = (
            cls.objects.filter(llmclient=llmclient, vectorsearch__is_enabled=True)
            .select_related("vectorsearch", "vectorsearch__vectorstore")
            .order_by("vectorsearch__name")
        )
        vectorsearches = [link.vectorsearch for link in links]
        return vectorsearches


__all__ = [
    "LLMClientVectorsearches",
]
