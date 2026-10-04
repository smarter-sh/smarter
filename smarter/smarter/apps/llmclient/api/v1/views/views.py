# pylint: disable=W0718,W0613
"""LLMClient api/v1/llmclients CRUD views."""

from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientFunctions,
    LLMClientPlugin,
)
from smarter.apps.llmclient.serializers import (
    LLMClientAPIKeySerializer,
    LLMClientCustomDomainSerializer,
    LLMClientFunctionsSerializer,
    LLMClientPluginSerializer,
    LLMClientSerializer,
)
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


###############################################################################
# base views
###############################################################################
class ViewBase(SmarterAdminAPIView):
    """Base class for all llmclient detail views."""

    # SmarterRequestMixin sets user, user_profile and account from the request,
    # which are immutable once set.


class ListViewBase(SmarterAdminListAPIView):
    """Base class for all llmclient list views."""

    # SmarterRequestMixin sets user, user_profile and account from the request,
    # which are immutable once set.


###############################################################################
# LLMClient views
###############################################################################


class LLMClientView(ViewBase):
    """LLMClient view for smarter api."""

    serializer_class = LLMClientSerializer
    llmclient: Optional[LLMClient] = None
    hashed_id: Optional[str] = None
    llmclient_id: Optional[int] = None

    def get_queryset(self, *args, **kwargs):
        return LLMClient.objects.filter(id=self.llmclient.id)  # type: ignore[return-value]

    def dispatch(self, request: Request, *args, **kwargs):
        self.hashed_id = kwargs.pop("hashed_id", None)
        return super().dispatch(request, *args, **kwargs)

    def initial(self, request: Request, *args, **kwargs):
        """Find the LLMClient, after DRF has authenticated the request and before the handler runs."""
        super().initial(request, *args, **kwargs)
        if self.hashed_id:
            self.llmclient_id = LLMClient.id_from_hashed_id(self.hashed_id)
        else:
            self.llmclient_id = kwargs.get("llmclient_id")

        if self.llmclient_id:
            self.llmclient = get_object_or_404(LLMClient, pk=self.llmclient_id)
            if self.llmclient.user_profile and self._user_profile != self.llmclient.user_profile:
                self._user_profile = self.llmclient.user_profile
                self._account = self.llmclient.user_profile.account
                self._user = self.llmclient.user_profile.user
                logger.debug(
                    "%s.initial() - reinitializing user, account, and user_profile from llmclient.user_profile: %s",
                    self.formatted_class_name,
                    self.llmclient.user_profile,
                )
            logger.debug("%s.initial() - %s %s", self.formatted_class_name, self.llmclient, self.user_profile)

    def get(self, request: Request, llmclient_id: Optional[int] = None):
        if self.llmclient:
            serializer = self.serializer_class(self.llmclient)
            return Response(serializer.data, status=HTTPStatus.OK)
        return HttpResponseNotFound("LLMClient not found")

    def post(self, request: Request, *args, **kwargs):
        try:
            data = request.data
            llmclient = LLMClient.objects.create(**data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(llmclient.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, *args, llmclient_id: Optional[int] = None, **kwargs):
        llmclient: Optional[LLMClient] = None
        data: Optional[dict] = None

        llmclient = self.llmclient
        if not llmclient:
            return HttpResponseNotFound("LLMClient not found")

        try:
            data = request.data
            if not isinstance(data, dict):
                return JsonResponse(
                    {"error": f"Invalid request data. Expected a JSON dict in request body but received {type(data)}"},
                    status=HTTPStatus.BAD_REQUEST,
                )
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

        try:
            for key, value in data.items():
                if hasattr(llmclient, key):
                    setattr(llmclient, key, value)
            llmclient.save()
        except ValidationError as e:
            return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect(request.path_info)

    def delete(self, request: Request, *args, llmclient_id: Optional[int] = None, **kwargs):
        if llmclient_id and self.is_superuser():
            llmclient = get_object_or_404(LLMClient, pk=llmclient_id)
        else:
            llmclient = self.llmclient

        try:
            if llmclient:
                llmclient.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class LLMClientListView(ListViewBase):
    """LLMClient list view for smarter api."""

    serializer_class = LLMClientSerializer
    llmclients: Optional[QuerySet[LLMClient]]

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.llmclients = LLMClient.objects.with_read_permission_for(user=request.user)  # type: ignore[assignment]
        return response

    def get_queryset(self, *args, **kwargs):
        return LLMClient.objects.with_read_permission_for(user=self.user)  # type: ignore[return-value]


class LLMClientDeployView(ViewBase):
    """LLMClient deployment view for smarter api."""

    serializer_class = LLMClientSerializer

    def post(self, request: Request, llmclient_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        try:
            llmclient.deployed = True
            llmclient.save()
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return JsonResponse({}, status=HTTPStatus.OK)


###############################################################################
# LLMClientPlugin views
###############################################################################
class LLMClientPluginView(ViewBase):
    """LLMClientPlugin view for smarter api."""

    serializer_class = LLMClientPluginSerializer

    def get(self, request: Request, llmclient_id: int, plugin_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        plugin = get_object_or_404(LLMClientPlugin, pk=plugin_id, llmclient=llmclient)
        serializer = self.serializer_class(plugin)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llmclient_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        try:
            data = request.data
            llmclient_plugin = LLMClientPlugin.load(llmclient, data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(llmclient_plugin.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, llmclient_id: int, plugin_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        llmclient_plugin = get_object_or_404(LLMClientPlugin, pk=plugin_id, llmclient=llmclient)
        try:
            data = json.loads(request.body.decode("utf-8"))
            llmclient_plugin.load(llmclient, data)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info)

    def delete(self, request: Request, llmclient_id: int, plugin_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        llmclient_plugin = get_object_or_404(LLMClientPlugin, pk=plugin_id, llmclient=llmclient)
        try:
            llmclient_plugin.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return HttpResponseRedirect(request.path_info.rsplit("/", 2)[0])


class LLMClientPluginListView(ListViewBase):
    """LLMClientPlugin list view for smarter api."""

    serializer_class = LLMClientPluginSerializer

    def get_queryset(self, *args, **kwargs):
        llmclient_id = self.kwargs.get("llmclient_id")
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        return LLMClientPlugin.objects.filter(llmclient=llmclient)


###############################################################################
# LLMClientAPIKey views
###############################################################################


class LLMClientAPIKeyView(ViewBase):
    """LLMClientAPIKey view for smarter api."""

    serializer_class = LLMClientAPIKeySerializer

    def get(self, request: Request, llmclient_id: int, apikey_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        api_key = get_object_or_404(LLMClientAPIKey, pk=apikey_id, llmclient=llmclient)
        serializer = self.serializer_class(api_key)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llmclient_id: int, apikey_id: Optional[int] = None):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        api_key = get_object_or_404(SmarterAuthToken, pk=apikey_id)
        try:
            llmclient_api_key = LLMClientAPIKey.objects.create(llmclient=llmclient, api_key=api_key)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(llmclient_api_key.id) + "/")  # type: ignore[return-value]

    def delete(self, request: Request, llmclient_id: int, apikey_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        llmclient_api_key = get_object_or_404(LLMClientAPIKey, pk=apikey_id, llmclient=llmclient)
        try:
            llmclient_api_key.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return HttpResponseRedirect(request.path_info.rsplit("/", 2)[0])


class LLMClientAPIKeyListView(ListViewBase):
    """LLMClientAPIKey list view for smarter api."""

    serializer_class = LLMClientAPIKeySerializer

    def get_queryset(self, *args, **kwargs):
        llmclient_id = self.kwargs.get("llmclient_id")
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        return LLMClientAPIKey.objects.filter(llmclient=llmclient)


###############################################################################
# LLMClientCustomDomain views
###############################################################################


class LLMClientCustomDomainView(ViewBase):
    """LLMClientCustomDomain view for smarter api."""

    serializer_class = LLMClientCustomDomainSerializer

    def get(self, request: Request, llmclient_id: int, customdomain_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        custom_domain = get_object_or_404(LLMClientCustomDomain, pk=customdomain_id, llmclient=llmclient)
        serializer = self.serializer_class(custom_domain)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llmclient_id: int, customdomain_id: int):
        """Attach the custom domain to the LLMClient, through LLMClient.custom_domain."""
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        custom_domain = get_object_or_404(LLMClientCustomDomain, pk=customdomain_id)
        # LLMClient.custom_domain is one-to-one, so a domain belongs to at most one LLMClient.
        if LLMClient.objects.filter(custom_domain=custom_domain).exclude(pk=llmclient.pk).exists():
            return JsonResponse(
                {"error": f"Custom domain {custom_domain.domain_name} is already used by another LLMClient."},
                status=HTTPStatus.CONFLICT,
            )
        llmclient.custom_domain = custom_domain
        llmclient.save(update_fields=["custom_domain"])
        return HttpResponseRedirect(request.path_info)

    def delete(self, request: Request, llmclient_id: int, customdomain_id: int):
        """
        Detach the custom domain from the LLMClient.

        The domain itself is kept: LLMClient.custom_domain is on_delete=CASCADE, so deleting
        the domain would delete the LLMClient too.
        """
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        if llmclient.custom_domain_id != customdomain_id:  # type: ignore[attr-defined]
            return HttpResponseNotFound("Custom domain not found for this LLMClient")
        llmclient.custom_domain = None
        llmclient.save(update_fields=["custom_domain"])
        # these urls have no trailing slash, so the list url is the parent path.
        return HttpResponseRedirect(request.path_info.rsplit("/", 1)[0])


class LLMClientCustomDomainListView(ListViewBase):
    """LLMClientCustomDomain list view for smarter api."""

    serializer_class = LLMClientCustomDomainSerializer

    def get_queryset(self, *args, **kwargs):
        llmclient_id = self.kwargs.get("llmclient_id")
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        return LLMClientCustomDomain.objects.filter(llmclient=llmclient)


###############################################################################
# LLMClientFunctions views
###############################################################################


class LLMClientFunctionsView(ViewBase):
    """LLMClientFunctions view for smarter api."""

    serializer_class = LLMClientFunctionsSerializer

    def get(self, request: Request, llmclient_id: int, function_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        function = get_object_or_404(LLMClientFunctions, pk=function_id, llmclient=llmclient)
        serializer = self.serializer_class(function)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llmclient_id: int):
        # llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        raise NotImplementedError("Not implemented")

    def patch(self, request: Request, llmclient_id: int, function_id: int):
        # llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        # function = get_object_or_404(LLMClientFunctions, pk=function_id, llmclient=llmclient)
        raise NotImplementedError("Not implemented")

    def delete(self, request: Request, llmclient_id: int, function_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        function = get_object_or_404(LLMClientFunctions, pk=function_id, llmclient=llmclient)
        try:
            function.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return HttpResponseRedirect(request.path_info.rsplit("/", 2)[0])


class LLMClientFunctionsListView(ListViewBase):
    """LLMClientFunctions list view for smarter api."""

    serializer_class = LLMClientFunctionsSerializer

    def get_queryset(self, *args, **kwargs):
        llmclient_id = self.kwargs.get("llmclient_id")
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, user_profile__account=self.account)
        return LLMClientFunctions.objects.filter(llmclient=llmclient)
