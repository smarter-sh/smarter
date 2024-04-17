# pylint: disable=W0718,W0613
"""ChatBot api views."""
import logging
from http import HTTPStatus
from typing import List

from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from smarter.apps.account.models import Account, SmarterAuthToken, UserProfile
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotFunctions,
    ChatBotPlugin,
)
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.drf.view_helpers import SmarterAdminAPIView, SmarterAdminListAPIView

from .serializers import (
    ChatBotAPIKeySerializer,
    ChatBotCustomDomainSerializer,
    ChatBotFunctionsSerializer,
    ChatBotPluginSerializer,
    ChatBotSerializer,
)


logger = logging.getLogger(__name__)


###############################################################################
# base views
###############################################################################
class ViewBase(SmarterAdminAPIView):
    """Base class for all chatbot detail views."""

    user_profile: UserProfile = None
    account: Account = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff and not request.user.is_superuser:
            return JsonResponse({"error": "Unauthorized"}, status=HTTPStatus.UNAUTHORIZED)
        self.user_profile = get_object_or_404(UserProfile, user=request.user)
        self.account = self.user_profile.account
        response = super().dispatch(request, *args, **kwargs)
        return response


class ListViewBase(SmarterAdminListAPIView):
    """Base class for all chatbot list views."""

    user_profile: UserProfile = None
    account: Account = None

    def dispatch(self, request, *args, **kwargs):
        self.user_profile = get_object_or_404(UserProfile, user=request.user)
        self.account = self.user_profile.account
        response = super().dispatch(request, *args, **kwargs)
        return response


###############################################################################
# ChatBot views
###############################################################################


class ChatBotView(ViewBase):
    """ChatBot view for smarter api."""

    serializer_class = ChatBotSerializer

    def get(self, request, chatbot_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        serializer = self.serializer_class(chatbot)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request):
        try:
            data = request.data
            chatbot = ChatBot.objects.create(**data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(chatbot.id) + "/")

    def patch(self, request, chatbot_id: int = None):
        chatbot: ChatBot = None
        data: dict = None

        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)

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
                if hasattr(chatbot, key):
                    setattr(chatbot, key, value)
            chatbot.save()
        except ValidationError as e:
            return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect(request.path_info)

    def delete(self, request, chatbot_id: int = None):
        if chatbot_id and self.is_superuser_or_unauthorized():
            chatbot = get_object_or_404(ChatBot, pk=chatbot_id)
        else:
            chatbot = self.user_profile.chatbot

        try:
            chatbot.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class ChatBotListView(ListViewBase):
    """ChatBot list view for smarter api."""

    serializer_class = ChatBotSerializer
    chatbots: List[ChatBot] = []

    def dispatch(self, request, *args, **kwargs):
        self.chatbots = ChatBot.objects.filter(account=self.account)
        response = super().dispatch(request, *args, **kwargs)
        return response

    def get_queryset(self, *args, **kwargs):
        return ChatBot.objects.filter(account=self.account)


class ChatBotDeployView(ViewBase):
    """ChatBot deployment view for smarter api."""

    serializer_class = ChatBotSerializer

    def post(self, request, chatbot_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        try:
            deploy_default_api.delay(chatbot_id=chatbot.id)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return JsonResponse({}, status=HTTPStatus.OK)


###############################################################################
# ChatBotPlugin views
###############################################################################
class ChatBotPluginView(ViewBase):
    """ChatBotPlugin view for smarter api."""

    serializer_class = ChatBotPluginSerializer

    def get(self, request, chatbot_id: int, plugin_meta_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        plugin_meta = get_object_or_404(PluginMeta, pk=plugin_meta_id)
        plugin = get_object_or_404(ChatBotPlugin, chatbot=chatbot, plugin_meta=plugin_meta)
        serializer = self.serializer_class(plugin)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request, chatbot_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        try:
            data = request.data
            chatbot_plugin = ChatBotPlugin.load(chatbot, data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(chatbot_plugin.id) + "/")

    def patch(self, request, chatbot_id: int, plugin_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        chatbot_plugin = get_object_or_404(ChatBotPlugin, pk=plugin_id, chatbot=chatbot)
        try:
            data = request.data
            chatbot_plugin.load(data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info)

    def delete(self, request, chatbot_id: int, plugin_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        chatbot_plugin = get_object_or_404(ChatBotPlugin, pk=plugin_id, chatbot=chatbot)
        try:
            chatbot_plugin.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return HttpResponseRedirect(request.path_info.rsplit("/", 2)[0])


class ChatBotPluginListView(ListViewBase):
    """ChatBotPlugin list view for smarter api."""

    serializer_class = ChatBotPluginSerializer

    def get_queryset(self, *args, **kwargs):
        chatbot_id = self.kwargs.get("chatbot_id")
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        return ChatBotPlugin.objects.filter(chatbot=chatbot)


###############################################################################
# ChatBotAPIKey views
###############################################################################


class ChatBotAPIKeyView(ViewBase):
    """ChatBotAPIKey view for smarter api."""

    serializer_class = ChatBotAPIKeySerializer

    def get(self, request, chatbot_id: int, api_key_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        api_key = get_object_or_404(SmarterAuthToken, pk=api_key_id, chatbot=chatbot)
        serializer = self.serializer_class(api_key)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request, chatbot_id: int, api_key_id: int = None):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        api_key = get_object_or_404(ChatBotAPIKey, pk=api_key_id)
        try:
            chatbot_api_key = ChatBotAPIKey.objects.create(chatbot=chatbot, api_key=api_key)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(chatbot_api_key.id) + "/")

    def delete(self, request, chatbot_id: int, api_key_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        api_key = get_object_or_404(SmarterAuthToken, pk=api_key_id)
        chatbot_api_key = get_object_or_404(ChatBotAPIKey, chatbot=chatbot, api_key=api_key)
        try:
            chatbot_api_key.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return HttpResponseRedirect(request.path_info.rsplit("/", 2)[0])


class ChatBotAPIKeyListView(ListViewBase):
    """ChatBotAPIKey list view for smarter api."""

    serializer_class = ChatBotAPIKeySerializer

    def get_queryset(self, *args, **kwargs):
        chatbot_id = self.kwargs.get("chatbot_id")
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        return ChatBotAPIKey.objects.filter(chatbot=chatbot)


###############################################################################
# ChatBotCustomDomain views
###############################################################################


class ChatBotCustomDomainView(ViewBase):
    """ChatBotCustomDomain view for smarter api."""

    serializer_class = ChatBotCustomDomainSerializer

    def get(self, request, chatbot_id: int, custom_domain_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        custom_domain = get_object_or_404(ChatBotCustomDomain, pk=custom_domain_id, chatbot=chatbot)
        serializer = self.serializer_class(custom_domain)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request, chatbot_id: int, custom_domain_id: int = None):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        custom_domain = get_object_or_404(ChatBotCustomDomain, pk=custom_domain_id)
        try:
            chatbot_custom_domain = ChatBotCustomDomain.objects.create(chatbot=chatbot, custom_domain=custom_domain)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(chatbot_custom_domain.id) + "/")

    def delete(self, request, chatbot_id: int, custom_domain_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        custom_domain = get_object_or_404(ChatBotCustomDomain, pk=custom_domain_id)
        chatbot_custom_domain = get_object_or_404(ChatBotCustomDomain, chatbot=chatbot, custom_domain=custom_domain)
        try:
            chatbot_custom_domain.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return HttpResponseRedirect(request.path_info.rsplit("/", 2)[0])


class ChatBotCustomDomainListView(ListViewBase):
    """ChatBotCustomDomain list view for smarter api."""

    serializer_class = ChatBotCustomDomainSerializer

    def get_queryset(self, *args, **kwargs):
        chatbot_id = self.kwargs.get("chatbot_id")
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        return ChatBotCustomDomain.objects.filter(chatbot=chatbot)


###############################################################################
# ChatBotFunctions views
###############################################################################


class ChatBotFunctionsView(ViewBase):
    """ChatBotFunctions view for smarter api."""

    serializer_class = ChatBotFunctionsSerializer

    def get(self, request, chatbot_id: int, function_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        function = get_object_or_404(ChatBotFunctions, pk=function_id, chatbot=chatbot)
        serializer = self.serializer_class(function)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request, chatbot_id: int):
        # chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        raise NotImplementedError("Not implemented")

    def patch(self, request, chatbot_id: int, function_id: int):
        # chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        # function = get_object_or_404(ChatBotFunctions, pk=function_id, chatbot=chatbot)
        raise NotImplementedError("Not implemented")

    def delete(self, request, chatbot_id: int, function_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        function = get_object_or_404(ChatBotFunctions, pk=function_id, chatbot=chatbot)
        try:
            function.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )
        return HttpResponseRedirect(request.path_info.rsplit("/", 2)[0])


class ChatBotFunctionsListView(ListViewBase):
    """ChatBotFunctions list view for smarter api."""

    serializer_class = ChatBotFunctionsSerializer

    def get_queryset(self, *args, **kwargs):
        chatbot_id = self.kwargs.get("chatbot_id")
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        return ChatBotFunctions.objects.filter(chatbot=chatbot)
