"""
Run a Vectorsearch: search its Vectorstore with a query, and the Vectorsearch's own configuration.

The one implementation of a run, which the REST api
(:class:`~smarter.apps.vectorsearch.api.v1.views.default.DefaultVectorsearchApiView`) and an LLMClient's
Vectorsearch tools (:class:`~smarter.apps.vectorsearch.toolkit.VectorsearchToolkit`) both call, so that
both refuse a disabled Vectorsearch, both respect the same budgets, and both return the same results.
"""

from typing import Optional

from smarter.apps.account.models.budget import charge_authorization
from smarter.apps.vectorsearch.contract.models import VectorsearchApiResults
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorsearch.signals import vectorsearch_called
from smarter.apps.vectorstore.contract.models import VectorstoreApiSearchResult
from smarter.apps.vectorstore.service import VectorstoreService
from smarter.common.exceptions import SmarterValueError
from smarter.lib.typing import SmarterDictType


def combined_metadata_filter(vectorsearch: Vectorsearch, run_filter: Optional[SmarterDictType]) -> SmarterDictType:
    """
    Return the metadata that every result must match: the run's, then the Vectorsearch's own.

    The Vectorsearch's filter wins where both name the same key, so that a caller can narrow a
    Vectorsearch, but never widen it.

    :param vectorsearch: The Vectorsearch.
    :param run_filter: The run's own filter, if any.
    :returns: The combined filter, which may be empty.
    """
    combined: SmarterDictType = {}
    if run_filter:
        combined.update(run_filter)
    if isinstance(vectorsearch.metadata_filter, dict):
        combined.update(vectorsearch.metadata_filter)
    return combined


def run_vectorsearch(  # pylint: disable=too-many-arguments
    vectorsearch: Vectorsearch,
    query: str,
    *,
    service: Optional[VectorstoreService] = None,
    run_filter: Optional[SmarterDictType] = None,
    budget_locators: Optional[list[str]] = None,
    sender: object = None,
) -> VectorsearchApiResults:
    """
    Search a Vectorsearch's Vectorstore with a query, and return what it found, most similar first.

    :param vectorsearch: The Vectorsearch, whose search type, ``k``, score threshold, mmr settings and
        metadata filter configure the search.
    :param query: What to search for.
    :param service: The service that searches the Vectorstore. By default, a
        :class:`~smarter.apps.vectorstore.service.VectorstoreService` of the Vectorsearch's Vectorstore.
    :param run_filter: Metadata that the results must match, which the Vectorsearch's own filter narrows.
    :param budget_locators: The record locators whose budgets must allow the run, besides the
        Vectorsearch's own, e.g. the user's profile and account.
    :param sender: The ``vectorsearch_called`` signal's sender.
    :returns: The Vectorsearch's name, its Vectorstore's name and the results.
    :raises SmarterValueError: If the Vectorsearch is disabled, or the query is empty.
    :raises smarter.apps.account.models.budget.SmarterBudgetExceeded: If a budget forbids the run.
    :raises smarter.common.exceptions.SmarterException: If the search fails, e.g. the Vectorstore isn't ready.
    """
    if not vectorsearch.is_enabled:
        raise SmarterValueError(f"Vectorsearch {vectorsearch.name} is disabled.")
    if not query or not query.strip():
        raise SmarterValueError("A search requires a query.")
    locators = [vectorsearch.record_locator]
    locators.extend(budget_locators or [])
    charge_authorization(locators, run_vectorsearch.__name__)
    vectorsearch_called.send(sender=sender or run_vectorsearch, vectorsearch=vectorsearch)
    vectorstore = vectorsearch.vectorstore
    if service is None:
        service = VectorstoreService(vectorstore)
    metadata_filter = combined_metadata_filter(vectorsearch, run_filter)
    results = service.search(
        query=query,
        k=vectorsearch.k,
        search_type=vectorsearch.search_type,
        score_threshold=vectorsearch.score_threshold,
        fetch_k=vectorsearch.fetch_k,
        lambda_mult=vectorsearch.lambda_mult,
        metadata_filter=metadata_filter or None,
    )
    found = []
    for result in results:
        found.append(VectorstoreApiSearchResult.from_result(result))
    response = VectorsearchApiResults(vectorsearch=vectorsearch.name, vectorstore=vectorstore.name, results=found)
    return response


__all__ = ["combined_metadata_filter", "run_vectorsearch"]
