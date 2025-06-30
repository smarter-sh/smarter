# pylint: disable=W0718,W0613
"""ChatBot api/v1/chatbots CRUD views."""
import json
import logging
from http import HTTPStatus
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from smarter.apps.account.models import User, UserProfile
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotFunctions,
    ChatBotPlugin,
)
from smarter.apps.chatbot.serializers import (
    ChatBotAPIKeySerializer,
    ChatBotCustomDomainSerializer,
    ChatBotFunctionsSerializer,
    ChatBotPluginSerializer,
    ChatBotSerializer,
)
from smarter.apps.chatbot.tasks import deploy_default_api
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAdminAPIView,
    SmarterAdminListAPIView,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


###############################################################################
# base views
###############################################################################
class ViewBase(SmarterAdminAPIView):
    """Base class for all chatbot detail views."""

    def dispatch(self, request, *args, **kwargs):
        if isinstance(request.user, User):
            self.user_profile = get_object_or_404(UserProfile, user=request.user)
            self.account = self.user_profile.account
        return super().dispatch(request, *args, **kwargs)


class ListViewBase(SmarterAdminListAPIView):
    """Base class for all chatbot list views."""

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.user_profile = get_object_or_404(UserProfile, user=request.user)
        self.account = self.user_profile.account
        return response


###############################################################################
# ChatBot views
###############################################################################


class ChatbotView(ViewBase):
    """ChatBot view for smarter api."""

    serializer_class = ChatBotSerializer
    chatbot: Optional[ChatBot] = None

    def get_queryset(self, *args, **kwargs):
        return ChatBot.objects.filter(id=self.chatbot.id)  # type: ignore[return-value]

    def dispatch(self, request, *args, **kwargs):
        chatbot_id = kwargs.get("chatbot_id")
        if chatbot_id:
            kwargs.pop("chatbot_id")
            self.chatbot = get_object_or_404(ChatBot, pk=chatbot_id)
            self.account = self.chatbot.account
            logger.info("ChatbotView.dispatch() chatbot_id: %s", chatbot_id)
            logger.info("ChatbotView.dispatch() account: %s", self.account)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, chatbot_id: int):
        serializer = self.serializer_class(self.chatbot)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request):
        try:
            data = request.data
            chatbot = ChatBot.objects.create(**data)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(chatbot.id) + "/")  # type: ignore[return-value]

    def patch(self, request, chatbot_id: Optional[int] = None):
        chatbot: Optional[ChatBot] = None
        data: Optional[dict] = None

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

    def delete(self, request, chatbot_id: Optional[int] = None):
        if chatbot_id and self.is_superuser_or_unauthorized():
            chatbot = get_object_or_404(ChatBot, pk=chatbot_id)
        else:
            chatbot = self.chatbot

        try:
            if chatbot:
                chatbot.delete()
        except Exception as e:
            return JsonResponse(
                {"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

        plugins_path = request.path_info.rsplit("/", 2)[0]
        return HttpResponseRedirect(plugins_path)


class ChatbotListView(ListViewBase):
    """ChatBot list view for smarter api."""

    serializer_class = ChatBotSerializer
    chatbots: Optional[QuerySet[ChatBot]]

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if response.status_code > 299:
            return response
        self.chatbots = ChatBot.objects.filter(account=self.account)
        return response

    def get_queryset(self, *args, **kwargs):
        return ChatBot.objects.filter(account=self.account)


class ChatBotDeployView(ViewBase):
    """ChatBot deployment view for smarter api."""

    serializer_class = ChatBotSerializer

    def post(self, request, chatbot_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        try:
            deploy_default_api.delay(chatbot_id=chatbot.id)  # type: ignore[arg-type]
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return JsonResponse({}, status=HTTPStatus.OK)


###############################################################################
# ChatBotPlugin views
###############################################################################
class ChatbotPluginView(ViewBase):
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
        return HttpResponseRedirect(request.path_info + str(chatbot_plugin.id) + "/")  # type: ignore[return-value]

    def patch(self, request, chatbot_id: int, plugin_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        chatbot_plugin = get_object_or_404(ChatBotPlugin, pk=plugin_id, chatbot=chatbot)
        try:
            data = json.loads(request.body.decode("utf-8"))
            chatbot_plugin.load(chatbot, data)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=HTTPStatus.BAD_REQUEST)
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


class ChatbotPluginListView(ListViewBase):
    """ChatBotPlugin list view for smarter api."""

    serializer_class = ChatBotPluginSerializer

    def get_queryset(self, *args, **kwargs):
        chatbot_id = self.kwargs.get("chatbot_id")
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        return ChatBotPlugin.objects.filter(chatbot=chatbot)


###############################################################################
# ChatBotAPIKey views
###############################################################################


class ChatbotAPIKeyView(ViewBase):
    """ChatBotAPIKey view for smarter api."""

    serializer_class = ChatBotAPIKeySerializer

    def get(self, request, chatbot_id: int, api_key_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        api_key = get_object_or_404(SmarterAuthToken, pk=api_key_id, chatbot=chatbot)
        serializer = self.serializer_class(api_key)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request, chatbot_id: int, api_key_id: Optional[int] = None):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        api_key = get_object_or_404(ChatBotAPIKey, pk=api_key_id)
        try:
            chatbot_api_key = ChatBotAPIKey.objects.create(chatbot=chatbot, api_key=api_key)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(chatbot_api_key.id) + "/")  # type: ignore[return-value]

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


class ChatbotAPIKeyListView(ListViewBase):
    """ChatBotAPIKey list view for smarter api."""

    serializer_class = ChatBotAPIKeySerializer

    def get_queryset(self, *args, **kwargs):
        chatbot_id = self.kwargs.get("chatbot_id")
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        return ChatBotAPIKey.objects.filter(chatbot=chatbot)


###############################################################################
# ChatBotCustomDomain views
###############################################################################


class ChatbotCustomDomainView(ViewBase):
    """ChatBotCustomDomain view for smarter api."""

    serializer_class = ChatBotCustomDomainSerializer

    def get(self, request, chatbot_id: int, custom_domain_id: int):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        custom_domain = get_object_or_404(ChatBotCustomDomain, pk=custom_domain_id, chatbot=chatbot)
        serializer = self.serializer_class(custom_domain)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request, chatbot_id: int, custom_domain_id: Optional[int] = None):
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        custom_domain = get_object_or_404(ChatBotCustomDomain, pk=custom_domain_id)
        try:
            chatbot_custom_domain = ChatBotCustomDomain.objects.create(chatbot=chatbot, custom_domain=custom_domain)
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)
        return HttpResponseRedirect(request.path_info + str(chatbot_custom_domain.id) + "/")  # type: ignore[return-value]

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


class ChatbotCustomDomainListView(ListViewBase):
    """ChatBotCustomDomain list view for smarter api."""

    serializer_class = ChatBotCustomDomainSerializer

    def get_queryset(self, *args, **kwargs):
        chatbot_id = self.kwargs.get("chatbot_id")
        chatbot = get_object_or_404(ChatBot, pk=chatbot_id, account=self.account)
        return ChatBotCustomDomain.objects.filter(chatbot=chatbot)


###############################################################################
# ChatBotFunctions views
###############################################################################


class ChatbotFunctionsView(ViewBase):
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
