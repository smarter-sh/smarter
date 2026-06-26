# pylint: disable=W0718,W0613
"""LLMClient api/v1/llm_clients CRUD views."""

from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.account.models import User, UserProfile
from smarter.apps.llm_client.models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientFunctions,
    LLMClientPlugin,
)
from smarter.apps.llm_client.serializers import (
    LLMClientAPIKeySerializer,
    LLMClientCustomDomainSerializer,
    LLMClientFunctionsSerializer,
    LLMClientPluginSerializer,
    LLMClientSerializer,
)
from smarter.apps.plugin.models import PluginMeta
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
    """Base class for all llm_client detail views."""

    def dispatch(self, request: Request, *args, **kwargs):
        retval = super().dispatch(request, *args, **kwargs)
        if isinstance(request.user, User):
            self.user_profile = get_object_or_404(UserProfile, user=request.user)
            self.account = self.user_profile.cached_account
        return retval


class ListViewBase(SmarterAdminListAPIView):
    """Base class for all llm_client list views."""

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.user_profile = get_object_or_404(UserProfile, user=request.user)
        self.account = self.user_profile.cached_account
        return response


###############################################################################
# LLMClient views
###############################################################################


class LLMClientView(ViewBase):
    """LLMClient view for smarter api."""

    serializer_class = LLMClientSerializer
    llm_client: Optional[LLMClient] = None
    hashed_id: Optional[str] = None
    llm_client_id: Optional[int] = None

    def get_queryset(self, *args, **kwargs):
        return LLMClient.objects.filter(id=self.llm_client.id)  # type: ignore[return-value]

    def dispatch(self, request: Request, *args, **kwargs):
        self.hashed_id = kwargs.pop("hashed_id", None)
        retval = super().dispatch(request, *args, **kwargs)
        if self.hashed_id:
            self.llm_client_id = LLMClient.id_from_hashed_id(self.hashed_id)
        else:
            self.llm_client_id = kwargs.get("llm_client_id")

        if self.llm_client_id:
            self.llm_client = get_object_or_404(LLMClient, pk=self.llm_client_id)
            if self.llm_client.user_profile and self._user_profile != self.llm_client.user_profile:
                self._user_profile = self.llm_client.user_profile
                self._account = self.llm_client.user_profile.account
                self._user = self.llm_client.user_profile.user
                logger.debug(
                    "%s.dispatch() - reinitializing user, account, and user_profile from llm_client.user_profile: %s",
                    self.formatted_class_name,
                    self.llm_client.user_profile,
                )
            logger.debug("%s.dispatch() - %s %s", self.formatted_class_name, self.llm_client, self.user_profile)
        return retval

    def get(self, request: Request, llm_client_id: Optional[int] = None):
        if self.llm_client:
            serializer = self.serializer_class(self.llm_client)
            return Response(serializer.data, status=HTTPStatus.OK)
        return HttpResponseNotFound("LLMClient not found")

    def post(self, request: Request, *args, **kwargs):
        try:
            data = request.data
            llm_client = LLMClient.objects.create(**data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(llm_client.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, *args, llm_client_id: Optional[int] = None, **kwargs):
        llm_client: Optional[LLMClient] = None
        data: Optional[dict] = None

        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)

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
                if hasattr(llm_client, key):
                    setattr(llm_client, key, value)
            llm_client.save()
        except ValidationError as e:
            return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect(request.path_info)

    def delete(self, request: Request, *args, llm_client_id: Optional[int] = None, **kwargs):
        if llm_client_id and self.is_superuser():
            llm_client = get_object_or_404(LLMClient, pk=llm_client_id)
        else:
            llm_client = self.llm_client

        try:
            if llm_client:
                llm_client.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class LLMClientListView(ListViewBase):
    """LLMClient list view for smarter api."""

    serializer_class = LLMClientSerializer
    llm_clients: Optional[QuerySet[LLMClient]]

    def dispatch(self, request: Request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.llm_clients = LLMClient.objects.with_read_permission_for(user=request.user)  # type: ignore[assignment]
        return response

    def get_queryset(self, *args, **kwargs):
        return LLMClient.objects.with_read_permission_for(user=self.user)  # type: ignore[return-value]


class LLMClientDeployView(ViewBase):
    """LLMClient deployment view for smarter api."""

    serializer_class = LLMClientSerializer

    def post(self, request: Request, llm_client_id: int):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        try:
            llm_client.deployed = True
            llm_client.save()
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return JsonResponse({}, status=HTTPStatus.OK)


###############################################################################
# LLMClientPlugin views
###############################################################################
class LLMClientPluginView(ViewBase):
    """LLMClientPlugin view for smarter api."""

    serializer_class = LLMClientPluginSerializer

    def get(self, request: Request, llm_client_id: int, plugin_meta_id: int):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        plugin_meta = get_object_or_404(PluginMeta, pk=plugin_meta_id)
        plugin = get_object_or_404(LLMClientPlugin, llm_client=llm_client, plugin_meta=plugin_meta)
        serializer = self.serializer_class(plugin)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llm_client_id: int):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        try:
            data = request.data
            llm_client_plugin = LLMClientPlugin.load(llm_client, data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(llm_client_plugin.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, llm_client_id: int, plugin_id: int):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        llm_client_plugin = get_object_or_404(LLMClientPlugin, pk=plugin_id, llm_client=llm_client)
        try:
            data = json.loads(request.body.decode("utf-8"))
            llm_client_plugin.load(llm_client, data)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info)

    def delete(self, request: Request, llm_client_id: int, plugin_id: int):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        llm_client_plugin = get_object_or_404(LLMClientPlugin, pk=plugin_id, llm_client=llm_client)
        try:
            llm_client_plugin.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return HttpResponseRedirect(request.path_info.rsplit("/", 2)[0])


class LLMClientPluginListView(ListViewBase):
    """LLMClientPlugin list view for smarter api."""

    serializer_class = LLMClientPluginSerializer

    def get_queryset(self, *args, **kwargs):
        llm_client_id = self.kwargs.get("llm_client_id")
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        return LLMClientPlugin.objects.filter(llm_client=llm_client)


###############################################################################
# LLMClientAPIKey views
###############################################################################


class LLMClientAPIKeyView(ViewBase):
    """LLMClientAPIKey view for smarter api."""

    serializer_class = LLMClientAPIKeySerializer

    def get(self, request: Request, llm_client_id: int, api_key_id: int):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        api_key = get_object_or_404(SmarterAuthToken, pk=api_key_id, llm_client=llm_client)
        serializer = self.serializer_class(api_key)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llm_client_id: int, api_key_id: Optional[int] = None):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        api_key = get_object_or_404(LLMClientAPIKey, pk=api_key_id)
        try:
            llm_client_api_key = LLMClientAPIKey.objects.create(llm_client=llm_client, api_key=api_key)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(llm_client_api_key.id) + "/")  # type: ignore[return-value]

    def delete(self, request: Request, llm_client_id: int, api_key_id: int):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        api_key = get_object_or_404(SmarterAuthToken, pk=api_key_id)
        llm_client_api_key = get_object_or_404(LLMClientAPIKey, llm_client=llm_client, api_key=api_key)
        try:
            llm_client_api_key.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return HttpResponseRedirect(request.path_info.rsplit("/", 2)[0])


class LLMClientAPIKeyListView(ListViewBase):
    """LLMClientAPIKey list view for smarter api."""

    serializer_class = LLMClientAPIKeySerializer

    def get_queryset(self, *args, **kwargs):
        llm_client_id = self.kwargs.get("llm_client_id")
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        return LLMClientAPIKey.objects.filter(llm_client=llm_client)


###############################################################################
# LLMClientCustomDomain views
###############################################################################


class LLMClientCustomDomainView(ViewBase):
    """LLMClientCustomDomain view for smarter api."""

    serializer_class = LLMClientCustomDomainSerializer

    def get(self, request: Request, llm_client_id: int, custom_domain_id: int):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        custom_domain = get_object_or_404(LLMClientCustomDomain, pk=custom_domain_id, llm_client=llm_client)
        serializer = self.serializer_class(custom_domain)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llm_client_id: int, custom_domain_id: Optional[int] = None):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        custom_domain = get_object_or_404(LLMClientCustomDomain, pk=custom_domain_id)
        try:
            llm_client_custom_domain = LLMClientCustomDomain.objects.create(
                llm_client=llm_client, custom_domain=custom_domain
            )
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(llm_client_custom_domain.id) + "/")  # type: ignore[return-value]

    def delete(self, request: Request, llm_client_id: int, custom_domain_id: int):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        custom_domain = get_object_or_404(LLMClientCustomDomain, pk=custom_domain_id)
        llm_client_custom_domain = get_object_or_404(
            LLMClientCustomDomain, llm_client=llm_client, custom_domain=custom_domain
        )
        try:
            llm_client_custom_domain.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return HttpResponseRedirect(request.path_info.rsplit("/", 2)[0])


class LLMClientCustomDomainListView(ListViewBase):
    """LLMClientCustomDomain list view for smarter api."""

    serializer_class = LLMClientCustomDomainSerializer

    def get_queryset(self, *args, **kwargs):
        llm_client_id = self.kwargs.get("llm_client_id")
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        return LLMClientCustomDomain.objects.filter(llm_client=llm_client)


###############################################################################
# LLMClientFunctions views
###############################################################################


class LLMClientFunctionsView(ViewBase):
    """LLMClientFunctions view for smarter api."""

    serializer_class = LLMClientFunctionsSerializer

    def get(self, request: Request, llm_client_id: int, function_id: int):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        function = get_object_or_404(LLMClientFunctions, pk=function_id, llm_client=llm_client)
        serializer = self.serializer_class(function)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llm_client_id: int):
        # llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        raise NotImplementedError("Not implemented")

    def patch(self, request: Request, llm_client_id: int, function_id: int):
        # llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        # function = get_object_or_404(LLMClientFunctions, pk=function_id, llm_client=llm_client)
        raise NotImplementedError("Not implemented")

    def delete(self, request: Request, llm_client_id: int, function_id: int):
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        function = get_object_or_404(LLMClientFunctions, pk=function_id, llm_client=llm_client)
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
        llm_client_id = self.kwargs.get("llm_client_id")
        llm_client = get_object_or_404(LLMClient, pk=llm_client_id, account=self.account)
        return LLMClientFunctions.objects.filter(llm_client=llm_client)
