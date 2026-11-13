"""
Run a Vectorsearch: ``POST /api/v1/vectorsearches/<hashed_id>/vectorsearch/``, ``{"query": ..., "filter": {...}}``.

A Vectorsearch is a saved search of one vectorstore: its search type, ``k``, score threshold, mmr settings
and metadata filter. A run searches the vectorstore with the request's query, and that configuration, and
returns the chunks it found, most similar first, as a
:class:`~smarter.apps.vectorsearch.contract.models.VectorsearchApiResults`.

The user needs read permission on the Vectorsearch. A run is refused when the Vectorsearch is disabled,
and when a budget locks the Vectorsearch, the user's profile or their account. Errors are Django REST
framework's ``{"detail": ...}``.
"""

from http import HTTPStatus

from django.http import Http404
from pydantic import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models.budget import (
    SmarterBudgetExceeded,
    charge_authorization,
)
from smarter.apps.vectorsearch.contract.models import (
    VectorsearchApiResults,
    VectorsearchApiRun,
)
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorsearch.signals import vectorsearch_called
from smarter.apps.vectorstore.contract.models import VectorstoreApiSearchResult
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.apps.vectorstore.service import VectorstoreService
from smarter.common.exceptions import SmarterException
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
)
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.VECTORSEARCH_LOGGING])


def error(message: str, status: int = HTTPStatus.BAD_REQUEST) -> Response:
    """
    An error response: Django REST framework's ``{"detail": ...}``, as every error of the REST api.

    :param message: The error's message.
    :param status: The HTTP status. By default 400 Bad Request.
    :returns: The response.
    """
    return Response({"detail": message}, status=status)


class DefaultVectorsearchApiView(SmarterAuthenticatedAPIView):
    """Run a Vectorsearch that the user may read: search its vectorstore with its configuration."""

    service_class = VectorstoreService

    def get_vectorsearch(self, request: Request, **kwargs) -> Vectorsearch:
        """
        Return the Vectorsearch of the url, if the user may read it.

        :param request: The request, whose user's permissions are checked.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorsearch_id``.
        :returns: The Vectorsearch.
        :raises Http404: If it does not exist, or the user may not read it.
        """
        hashed_id = kwargs.get("hashed_id")
        if hashed_id:
            vectorsearch_id = Vectorsearch.id_from_hashed_id(hashed_id)
        else:
            vectorsearch_id = kwargs.get("vectorsearch_id")
        if not vectorsearch_id:
            raise Http404("Vectorsearch not found")
        queryset = Vectorsearch.objects.with_read_permission_for(user=request.user)  # type: ignore[attr-defined]
        queryset = queryset.select_related("vectorstore", "user_profile__account")
        vectorsearch = queryset.filter(pk=vectorsearch_id).first()
        if vectorsearch is None:
            raise Http404("Vectorsearch not found")
        return vectorsearch

    def get_service(self, vectorstore: VectorstoreMeta) -> VectorstoreService:
        """
        Return the service that searches a vectorstore, an instance of :attr:`service_class`.

        :param vectorstore: The vectorstore.
        :returns: Its service.
        """
        return self.service_class(vectorstore)

    @staticmethod
    def metadata_filter(vectorsearch: Vectorsearch, run: VectorsearchApiRun) -> SmarterDictType:
        """
        Return the metadata that every result must match: the request's, then the Vectorsearch's own.

        The Vectorsearch's filter wins where both name the same key, so that a caller can narrow a
        Vectorsearch, but never widen it.

        :param vectorsearch: The Vectorsearch.
        :param run: The request.
        :returns: The combined filter, which may be empty.
        """
        combined: SmarterDictType = {}
        if run.filter:
            combined.update(run.filter)
        if isinstance(vectorsearch.metadata_filter, dict):
            combined.update(vectorsearch.metadata_filter)
        return combined

    def post(self, request: Request, *args, **kwargs) -> Response:
        """
        Run the Vectorsearch with the JSON body's ``query``, and optional ``filter``.

        :param request: The request.
        :param kwargs: The url's arguments: ``hashed_id`` or ``vectorsearch_id``.
        :returns: The results, 400 if the request is not valid, the Vectorsearch is disabled or the
            search failed, or 402 if a budget forbids it.
        :raises Http404: If it does not exist, or the user may not read it.
        """
        vectorsearch = self.get_vectorsearch(request, **kwargs)
        data = request.data
        if not isinstance(data, dict):
            data = {}
        try:
            run = VectorsearchApiRun.model_validate(data)
        except ValidationError as e:
            return error(f"The request is not valid: {e.errors(include_url=False)}")
        if not vectorsearch.is_enabled:
            return error(f"Vectorsearch {vectorsearch.name} is disabled.")
        locators = [vectorsearch.record_locator]
        if self.user_profile is not None:
            locators.append(self.user_profile.record_locator)
        if self.account is not None:
            locators.append(self.account.record_locator)
        try:
            charge_authorization(locators, self.__class__.__name__)
        except SmarterBudgetExceeded as e:
            return error(e.message, HTTPStatus.PAYMENT_REQUIRED)
        vectorsearch_called.send(
            sender=self.__class__, vectorsearch=vectorsearch, request=request, args=args, kwargs=kwargs
        )
        logger.info("%s.post() running vectorsearch %s", self.formatted_class_name, vectorsearch.pk)
        metadata_filter = self.metadata_filter(vectorsearch, run)
        vectorstore = vectorsearch.vectorstore
        try:
            results = self.get_service(vectorstore).search(
                query=run.query,
                k=vectorsearch.k,
                search_type=vectorsearch.search_type,
                score_threshold=vectorsearch.score_threshold,
                fetch_k=vectorsearch.fetch_k,
                lambda_mult=vectorsearch.lambda_mult,
                metadata_filter=metadata_filter or None,
            )
        except (SmarterException, ValueError, TypeError) as e:
            return error(str(e))
        response = VectorsearchApiResults(
            vectorsearch=vectorsearch.name,
            vectorstore=vectorstore.name,
            results=[VectorstoreApiSearchResult.from_result(result) for result in results],
        )
        return Response(response.model_dump(mode="json"))


__all__ = ["DefaultVectorsearchApiView"]
