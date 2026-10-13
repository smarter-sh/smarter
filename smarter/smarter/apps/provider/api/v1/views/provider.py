# pylint: disable=R0801,W0613
"""
Provider api/v1/providers views.

Providers are created and updated by applying manifests, with ``smarter apply``, so these
views only read them:

- ``GET providers/``: the active Providers that the user may read.
- ``GET providers/<name>/``: an active Provider that the user may read.
- ``GET providers/<name>/models/``: the active models of that Provider.
- ``GET providers/<name>/models/<model_name>/``: one active model of that Provider.

A Provider or model that does not exist, is inactive, or belongs to another account answers
404, so that the Providers of other accounts are not disclosed.

The responses are built from the models of :mod:`smarter.apps.provider.contract.models`, which the
Smarter api's OpenAPI document publishes.
"""

from http import HTTPStatus

from django.db.models import QuerySet
from django.http import Http404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.provider.contract.models import ProviderApiModel, ProviderApiProvider
from smarter.apps.provider.models import Provider, ProviderModel
from smarter.apps.provider.serializers import (
    ProviderModelSerializer,
    ProviderSerializer,
)
from smarter.lib.drf.views.contract import ContractListMixin
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)


def readable_providers(request: Request) -> QuerySet[Provider]:
    """
    Return the active Providers that the request's user may read.

    :param request: The authenticated request.
    :returns: The Providers, ordered by name.
    """
    return (
        Provider.objects.with_read_permission_for(user=request.user)  # type: ignore[attr-defined]
        .filter(is_active=True)
        .select_related("user_profile__user", "user_profile__account", "api_key")
        .order_by("name")
    )


class ProviderViewBase(SmarterAuthenticatedAPIView):
    """
    Base class for views of one Provider, identified by its ``name``.

    :meth:`get_provider` returns the Provider only if it is active and the user may read it.
    Otherwise it raises :class:`~django.http.Http404`. Provider names are unique per account, so
    when the user may read several Providers of that name, their own account's wins.
    """

    def get_provider(self, request: Request, name: str) -> Provider:
        """Return the active Provider with this name that the user may read."""
        providers = list(readable_providers(request).filter(name=name).order_by("pk"))
        if not providers:
            raise Http404(f"Provider {name} not found.")
        account_id = getattr(self.user_profile, "account_id", None)
        own = [provider for provider in providers if provider.user_profile.account_id == account_id]
        return (own or providers)[0]


class ProvidersApiViewSet(ContractListMixin, SmarterAuthenticatedListAPIView):
    """The active Providers that the user may read."""

    serializer_class = ProviderSerializer
    contract_model = ProviderApiProvider

    def get_queryset(self, *args, **kwargs) -> QuerySet[Provider]:
        return readable_providers(self.request)

    def item(self, row):
        """A Provider of the response, whose ``canDelete`` is the requesting user's."""
        return ProviderApiProvider.from_model(row, self.request.user).model_dump(mode="json")


class ProviderApiViewSet(ProviderViewBase):
    """An active Provider that the user may read."""

    serializer_class = ProviderSerializer

    def get(self, request: Request, *args, name: str, **kwargs):
        """Return the Provider."""
        provider = self.get_provider(request, name)
        return Response(
            ProviderApiProvider.from_model(provider, request.user).model_dump(mode="json"), status=HTTPStatus.OK
        )


class ProviderModelsApiViewSet(ProviderViewBase):
    """The active models of an active Provider that the user may read."""

    serializer_class = ProviderModelSerializer

    def get(self, request: Request, *args, name: str, **kwargs):
        """Return the Provider's models."""
        provider = self.get_provider(request, name)
        provider_models = ProviderModel.objects.filter(provider=provider, is_active=True).order_by("name")
        items = [ProviderApiModel.from_model(row, request.user).model_dump(mode="json") for row in provider_models]
        return Response(items, status=HTTPStatus.OK)


class ProviderModelApiViewSet(ProviderViewBase):
    """An active model of an active Provider that the user may read."""

    serializer_class = ProviderModelSerializer

    def get(self, request: Request, *args, name: str, model_name: str, **kwargs):
        """Return the model."""
        provider = self.get_provider(request, name)
        provider_model = ProviderModel.objects.filter(provider=provider, name=model_name, is_active=True).first()
        if provider_model is None:
            raise Http404(f"Model {model_name} of Provider {name} not found.")
        return Response(
            ProviderApiModel.from_model(provider_model, request.user).model_dump(mode="json"), status=HTTPStatus.OK
        )
