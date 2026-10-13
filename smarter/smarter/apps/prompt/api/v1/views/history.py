# pylint: disable=W0707,W0718,C0115,W0613
"""
Prompt history views for smarter api.

They are mounted at ``/api/v1/prompts/history/``, and return the chat sessions, tool calls and
plugin usage of the sessions whose user the requesting user may manage, as the models of
:mod:`smarter.apps.prompt.contract.history`: their own sessions, the sessions of their account's
users for an account admin, and every session for a superuser. A session holds a user's
conversation, so a user never reads another account's, nor the platform's.
"""

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.prompt.api.v1.serializers import (
    PromptPluginUsageSerializer,
    PromptSerializer,
    PromptToolCallSerializer,
)
from smarter.apps.prompt.contract.history import (
    PromptHistoryApiPluginUsage,
    PromptHistoryApiSession,
    PromptHistoryApiToolCall,
)
from smarter.apps.prompt.models import Prompt, PromptPluginUsage, PromptToolCall
from smarter.lib.drf.views.contract import ContractListMixin
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)


def sessions_for_user(user) -> QuerySet[Prompt]:
    """
    The chat sessions whose user ``user`` may manage, newest first.

    :param user: The requesting user.
    :type user: django.contrib.auth.models.User
    :returns: The sessions.
    :rtype: QuerySet[Prompt]
    """
    return Prompt.objects.with_ownership_permission_for(user).order_by("-pk")


def tool_calls_for_user(user) -> QuerySet[PromptToolCall]:
    """
    The tool calls of the chat sessions whose user ``user`` may manage, newest first.

    :param user: The requesting user.
    :type user: django.contrib.auth.models.User
    :returns: The tool calls, with their sessions.
    :rtype: QuerySet[PromptToolCall]
    """
    return PromptToolCall.objects.filter(prompt__in=sessions_for_user(user)).select_related("prompt").order_by("-pk")


def plugin_usage_for_user(user) -> QuerySet[PromptPluginUsage]:
    """
    The plugin usage of the chat sessions whose user ``user`` may manage, newest first.

    :param user: The requesting user.
    :type user: django.contrib.auth.models.User
    :returns: The plugin usage, with their sessions and plugins.
    :rtype: QuerySet[PromptPluginUsage]
    """
    return (
        PromptPluginUsage.objects.filter(prompt__in=sessions_for_user(user))
        .select_related("prompt", "plugin__user_profile__user", "plugin__user_profile__account")
        .prefetch_related("plugin__tags")
        .order_by("-pk")
    )


class ChatToolCallHistoryListView(ContractListMixin, SmarterAuthenticatedListAPIView):
    """The tool calls of the user's chat sessions: :class:`PromptHistoryApiToolCall` models."""

    serializer_class = PromptToolCallSerializer
    contract_model = PromptHistoryApiToolCall

    def get_queryset(self):
        return tool_calls_for_user(self.request.user)


class ChatToolCallHistoryView(SmarterAuthenticatedAPIView):
    """A tool call of the user's chat sessions: a :class:`PromptHistoryApiToolCall`."""

    def get(self, request: Request, *args, **kwargs):
        instance = get_object_or_404(tool_calls_for_user(request.user), pk=kwargs["pk"])
        return Response(PromptHistoryApiToolCall.from_model(instance).model_dump(mode="json"))


class PluginUsageHistoryListView(ContractListMixin, SmarterAuthenticatedListAPIView):
    """The plugin usage of the user's chat sessions: :class:`PromptHistoryApiPluginUsage` models."""

    serializer_class = PromptPluginUsageSerializer
    contract_model = PromptHistoryApiPluginUsage

    def item(self, row):
        """A plugin usage of the response, whose plugin's ``canDelete`` is the requesting user's."""
        return PromptHistoryApiPluginUsage.from_model(row, self.request.user).model_dump(mode="json")

    def get_queryset(self):
        return plugin_usage_for_user(self.request.user)


class PluginUsageHistoryView(SmarterAuthenticatedAPIView):
    """A plugin usage of the user's chat sessions: a :class:`PromptHistoryApiPluginUsage`."""

    def get(self, request: Request, *args, **kwargs):
        instance = get_object_or_404(plugin_usage_for_user(request.user), pk=kwargs["pk"])
        return Response(PromptHistoryApiPluginUsage.from_model(instance, request.user).model_dump(mode="json"))


class ChatHistoryListView(ContractListMixin, SmarterAuthenticatedListAPIView):
    """The user's chat sessions: :class:`PromptHistoryApiSession` models."""

    serializer_class = PromptSerializer
    contract_model = PromptHistoryApiSession

    def get_queryset(self):
        return sessions_for_user(self.request.user)


class ChatHistoryView(SmarterAuthenticatedAPIView):
    """One of the user's chat sessions, by its id: a :class:`PromptHistoryApiSession`."""

    def get(self, request: Request, *args, **kwargs):
        instance = get_object_or_404(sessions_for_user(request.user), pk=kwargs["pk"])
        return Response(PromptHistoryApiSession.from_model(instance).model_dump(mode="json"))
