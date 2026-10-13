"""
A mixin of the REST api's list views whose rows are built from api contract models.

The REST api's responses are built from Pydantic models of their rows, e.g.
:mod:`smarter.apps.llmclient.contract.models`, which the Smarter api's OpenAPI document
(:mod:`smarter.apps.api.v1.contract.openapi`) publishes. A list view that mixes in
:class:`ContractListMixin` sets :attr:`~ContractListMixin.contract_model`, the model of one row, and
its ``GET`` returns its queryset's rows, each built by the model's ``from_model()``.
"""

from http import HTTPStatus

from pydantic import BaseModel, JsonValue
from rest_framework.request import Request
from rest_framework.response import Response


class ContractListMixin:
    """
    The ``list()`` of a DRF ``ListAPIView`` whose rows are built from :attr:`contract_model`.

    A view whose rows need the request, e.g. for their ``canDelete``, overrides :meth:`item`.
    """

    contract_model: type[BaseModel]
    """The contract model of one row.

    It must have a ``from_model(row)`` classmethod.
    """

    def item(self, row) -> JsonValue:
        """
        The response's item for a row: its contract model, dumped as JSON.

        :param row: A row of the view's queryset.
        :type row: django.db.models.Model
        :returns: The row's JSON.
        :rtype: JsonValue
        """
        return self.contract_model.from_model(row).model_dump(mode="json")  # type: ignore[attr-defined]

    def list(self, request: Request, *args, **kwargs) -> Response:  # pylint: disable=unused-argument
        """
        The rows of the view's queryset, each built by :meth:`item`.

        :param request: The request.
        :type request: rest_framework.request.Request
        :returns: The response, a JSON list.
        :rtype: rest_framework.response.Response
        """
        return Response([self.item(row) for row in self.get_queryset()], status=HTTPStatus.OK)  # type: ignore[attr-defined]


__all__ = ["ContractListMixin"]
