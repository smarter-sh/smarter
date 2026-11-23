"""
The Vectorsearches of an LLMClient, as tools that the LLM can call.

An LLMClient lists Vectorsearches in its manifest's ``spec.vectorsearches``. On each prompt,
:class:`VectorsearchToolkit` offers each enabled one to the LLM as a function tool whose one argument
is a search query. When the LLM calls it, the toolkit runs the Vectorsearch with
:func:`~smarter.apps.vectorsearch.run.run_vectorsearch`, as the REST api does: it searches the
Vectorsearch's Vectorstore with the Vectorsearch's settings (its search type, ``k``, score threshold,
MMR settings and metadata filter), within the Vectorsearch's budget, and returns the passages that it
found, most similar first, for the LLM to answer from.

The LLM chooses when to search, and what for. A question that the documents can't help with costs
no search, and a question that needs two searches can make them.
"""

from typing import Optional, Union

from pydantic import JsonValue

from smarter.apps.account.models.budget import SmarterBudgetExceeded
from smarter.apps.vectorstore.service import VectorstoreService
from smarter.common.exceptions import SmarterException
from smarter.lib import json, logging
from smarter.lib.cache.tool_results import ERROR_KEY
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .models import Vectorsearch
from .run import run_vectorsearch

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSEARCH_LOGGING])

FUNCTION_NAME_PREFIX = "smarter_vectorsearch_"
"""The prefix of a Vectorsearch tool's function name, which ends with the Vectorsearch's id."""

QUERY_ARGUMENT = "query"
"""The name of a Vectorsearch tool's one argument."""

QUERY_DESCRIPTION = (
    "What to search for: a question, or a few words. The search finds the passages that are closest to it "
    "in meaning, so phrase it the way the documents would."
)


def function_name_for(vectorsearch: Vectorsearch) -> str:
    """
    Return the function name of a Vectorsearch's tool, e.g. ``smarter_vectorsearch_42``.

    :param vectorsearch: The Vectorsearch.
    :returns: The function name, unique to the Vectorsearch.
    """
    name = f"{FUNCTION_NAME_PREFIX}{vectorsearch.pk}"
    return name


def tool_description_for(vectorsearch: Vectorsearch) -> str:
    """
    Return the description of a Vectorsearch's tool, which the LLM reads to decide when to call it.

    :param vectorsearch: The Vectorsearch.
    :returns: The Vectorsearch's description, or one that names its Vectorstore if it has none.
    """
    description = (vectorsearch.description or "").strip()
    if description:
        return description
    fallback = f"Searches the documents of the {vectorsearch.vectorstore.name} vectorstore."
    return fallback


class VectorsearchToolkit:
    """
    An LLMClient's Vectorsearches, as function tools.

    :param vectorsearches: The Vectorsearches, e.g. from
        :meth:`~smarter.apps.llmclient.models.LLMClientVectorsearches.vectorsearches_for`.
    :param service_class: A callable that returns the service that searches a Vectorstore, given the
        Vectorstore. By default, :class:`~smarter.apps.vectorstore.service.VectorstoreService`. Tests pass one
        with a fake backend.
    """

    def __init__(self, vectorsearches: list[Vectorsearch], service_class=None):
        # looked up when the toolkit is made, rather than bound as the default, so that tests can patch it.
        self.service_class = service_class if service_class is not None else VectorstoreService
        self.functions: dict[str, Vectorsearch] = {}
        for vectorsearch in vectorsearches:
            self.functions[function_name_for(vectorsearch)] = vectorsearch

    @property
    def tools(self) -> list[SmarterDictType]:
        """
        Return the OpenAI function tool of each Vectorsearch.

        :returns: One ``{"type": "function", "function": {...}}`` per Vectorsearch.
        """
        tools = []
        for function_name, vectorsearch in self.functions.items():
            tool = {
                "type": "function",
                "function": {
                    "name": function_name,
                    "description": tool_description_for(vectorsearch),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            QUERY_ARGUMENT: {"type": "string", "description": QUERY_DESCRIPTION},
                        },
                        "required": [QUERY_ARGUMENT],
                        "additionalProperties": False,
                    },
                },
            }
            tools.append(tool)
        return tools

    def is_vectorsearch_function(self, function_name: str) -> bool:
        """
        Return whether a function name is one of this toolkit's tools.

        :param function_name: The function name that the LLM called.
        :returns: True if it is one of this toolkit's Vectorsearches.
        """
        return function_name in self.functions

    def vectorsearch_for(self, function_name: str) -> Optional[Vectorsearch]:
        """
        Return the Vectorsearch of a function name.

        :param function_name: The function name that the LLM called.
        :returns: The Vectorsearch, or None if the name isn't one of this toolkit's tools.
        """
        return self.functions.get(function_name)

    def call(self, function_name: str, arguments: Union[SmarterDictType, str, None] = None) -> JsonValue:
        """
        Run a Vectorsearch with the LLM's query, and return the passages that it found, for the LLM.

        An error, such as a missing query, a budget that forbids the search, or a Vectorstore that
        isn't ready, is returned as ``{"error": "..."}``, so that the LLM can recover.

        :param function_name: The function name that the LLM called.
        :param arguments: The function's arguments, as a dict or a JSON string, with a ``query``.
        :returns: The Vectorsearch's and its Vectorstore's names, and the results, as
            :class:`~smarter.apps.vectorsearch.contract.models.VectorsearchApiResults`, or an error.
        """
        vectorsearch = self.functions.get(function_name)
        if vectorsearch is None:
            return {ERROR_KEY: f"{function_name} is not a vectorsearch tool."}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments.strip() else {}
            except ValueError:
                return {ERROR_KEY: "The arguments are not a JSON object."}
        if not isinstance(arguments, dict):
            arguments = {}
        query = str(arguments.get(QUERY_ARGUMENT) or "").strip()
        if not query:
            return {ERROR_KEY: f"A search needs a {QUERY_ARGUMENT}."}
        try:
            response = run_vectorsearch(
                vectorsearch,
                query,
                service=self.service_class(vectorsearch.vectorstore),
                sender=self.__class__,
            )
        except SmarterBudgetExceeded as e:
            return {ERROR_KEY: e.message}
        except (SmarterException, ValueError, TypeError) as e:
            logger.warning("vectorsearch %s failed: %s", vectorsearch.name, e)
            return {ERROR_KEY: f"The search of {vectorsearch.name} failed: {e}"}
        logger.debug("vectorsearch %s found %s results", vectorsearch.name, len(response.results))
        return response.model_dump(mode="json")


__all__ = [
    "FUNCTION_NAME_PREFIX",
    "VectorsearchToolkit",
    "function_name_for",
]
