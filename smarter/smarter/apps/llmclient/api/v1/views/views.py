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

from smarter.apps.account.models import User, UserProfile
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
    """Base class for all llmclient detail views."""

    def dispatch(self, request: Request, *args, **kwargs):
        retval = super().dispatch(request, *args, **kwargs)
        if isinstance(request.user, User):
            self.user_profile = get_object_or_404(UserProfile, user=request.user)
            self.account = self.user_profile.cached_account
        return retval


class ListViewBase(SmarterAdminListAPIView):
    """Base class for all llmclient list views."""

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
    llmclient: Optional[LLMClient] = None
    hashed_id: Optional[str] = None
    llmclient_id: Optional[int] = None

    def get_queryset(self, *args, **kwargs):
        return LLMClient.objects.filter(id=self.llmclient.id)  # type: ignore[return-value]

    def dispatch(self, request: Request, *args, **kwargs):
        self.hashed_id = kwargs.pop("hashed_id", None)
        retval = super().dispatch(request, *args, **kwargs)
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
                    "%s.dispatch() - reinitializing user, account, and user_profile from llmclient.user_profile: %s",
                    self.formatted_class_name,
                    self.llmclient.user_profile,
                )
            logger.debug("%s.dispatch() - %s %s", self.formatted_class_name, self.llmclient, self.user_profile)
        return retval

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

        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)

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
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
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

    def get(self, request: Request, llmclient_id: int, plugin_meta_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        plugin_meta = get_object_or_404(PluginMeta, pk=plugin_meta_id)
        plugin = get_object_or_404(LLMClientPlugin, llmclient=llmclient, plugin_meta=plugin_meta)
        serializer = self.serializer_class(plugin)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llmclient_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        try:
            data = request.data
            llmclient_plugin = LLMClientPlugin.load(llmclient, data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(llmclient_plugin.id) + "/")  # type: ignore[return-value]

    def patch(self, request: Request, llmclient_id: int, plugin_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
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
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
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
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        return LLMClientPlugin.objects.filter(llmclient=llmclient)


###############################################################################
# LLMClientAPIKey views
###############################################################################


class LLMClientAPIKeyView(ViewBase):
    """LLMClientAPIKey view for smarter api."""

    serializer_class = LLMClientAPIKeySerializer

    def get(self, request: Request, llmclient_id: int, api_key_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        api_key = get_object_or_404(SmarterAuthToken, pk=api_key_id, llmclient=llmclient)
        serializer = self.serializer_class(api_key)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llmclient_id: int, api_key_id: Optional[int] = None):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        api_key = get_object_or_404(LLMClientAPIKey, pk=api_key_id)
        try:
            llmclient_api_key = LLMClientAPIKey.objects.create(llmclient=llmclient, api_key=api_key)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(llmclient_api_key.id) + "/")  # type: ignore[return-value]

    def delete(self, request: Request, llmclient_id: int, api_key_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        api_key = get_object_or_404(SmarterAuthToken, pk=api_key_id)
        llmclient_api_key = get_object_or_404(LLMClientAPIKey, llmclient=llmclient, api_key=api_key)
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
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        return LLMClientAPIKey.objects.filter(llmclient=llmclient)


###############################################################################
# LLMClientCustomDomain views
###############################################################################


class LLMClientCustomDomainView(ViewBase):
    """LLMClientCustomDomain view for smarter api."""

    serializer_class = LLMClientCustomDomainSerializer

    def get(self, request: Request, llmclient_id: int, custom_domain_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        custom_domain = get_object_or_404(LLMClientCustomDomain, pk=custom_domain_id, llmclient=llmclient)
        serializer = self.serializer_class(custom_domain)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llmclient_id: int, custom_domain_id: Optional[int] = None):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        custom_domain = get_object_or_404(LLMClientCustomDomain, pk=custom_domain_id)
        try:
            llmclient_custom_domain = LLMClientCustomDomain.objects.create(
                llmclient=llmclient, custom_domain=custom_domain
            )
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(llmclient_custom_domain.id) + "/")  # type: ignore[return-value]

    def delete(self, request: Request, llmclient_id: int, custom_domain_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        custom_domain = get_object_or_404(LLMClientCustomDomain, pk=custom_domain_id)
        llmclient_custom_domain = get_object_or_404(
            LLMClientCustomDomain, llmclient=llmclient, custom_domain=custom_domain
        )
        try:
            llmclient_custom_domain.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return HttpResponseRedirect(request.path_info.rsplit("/", 2)[0])


class LLMClientCustomDomainListView(ListViewBase):
    """LLMClientCustomDomain list view for smarter api."""

    serializer_class = LLMClientCustomDomainSerializer

    def get_queryset(self, *args, **kwargs):
        llmclient_id = self.kwargs.get("llmclient_id")
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        return LLMClientCustomDomain.objects.filter(llmclient=llmclient)


###############################################################################
# LLMClientFunctions views
###############################################################################


class LLMClientFunctionsView(ViewBase):
    """LLMClientFunctions view for smarter api."""

    serializer_class = LLMClientFunctionsSerializer

    def get(self, request: Request, llmclient_id: int, function_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        function = get_object_or_404(LLMClientFunctions, pk=function_id, llmclient=llmclient)
        serializer = self.serializer_class(function)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request: Request, llmclient_id: int):
        # llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        raise NotImplementedError("Not implemented")

    def patch(self, request: Request, llmclient_id: int, function_id: int):
        # llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        # function = get_object_or_404(LLMClientFunctions, pk=function_id, llmclient=llmclient)
        raise NotImplementedError("Not implemented")

    def delete(self, request: Request, llmclient_id: int, function_id: int):
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
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
        llmclient = get_object_or_404(LLMClient, pk=llmclient_id, account=self.account)
        return LLMClientFunctions.objects.filter(llmclient=llmclient)
