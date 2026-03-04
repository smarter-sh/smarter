# pylint: disable=W0212
"""Django admin configuration for the chat app."""

from smarter.apps.account.utils import get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_filter_queryset_for_user,
    smarter_restricted_admin_site,
)

from .models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall


class ChatAdmin(SmarterCustomerModelAdmin):
    """
    Chat model admin. This is a primary Smarter resource, that descends
    directly from MetaDataWithOwnershipModel. Visibility of Chats is
    determined by ownership and role.
    """

    model = Chat

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in Chat._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)

        return smarter_filter_queryset_for_user(user=user, qs=qs)


class ChatHistoryAdmin(SmarterCustomerModelAdmin):
    """
    ChatHistory model admin. This descends from Chat, so visibility is
    determined by the parent Chat and role.
    """

    model = ChatHistory

    readonly_fields = (
        "created_at",
        "updated_at",
        "chat_history",
    )
    list_display = ["chat", "chat_history"]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user(
            user=user, qs=qs, account_filter="chat__user_profile__account", user_profile_filter="chat__user_profile"
        )


class ChatPluginUsageAdmin(SmarterCustomerModelAdmin):
    """plugin selection history model admin."""

    model = ChatPluginUsage

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatPluginUsage._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
            account_filter="chat__user_profile__account",
            user_profile_filter="chat__user_profile",
        )


class ChatToolCallHistoryAdmin(SmarterCustomerModelAdmin):
    """chat tool call history model admin."""

    model = ChatToolCall

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatToolCall._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
            account_filter="chat__user_profile__account",
            user_profile_filter="chat__user_profile",
        )


smarter_restricted_admin_site.register(Chat, ChatAdmin)
smarter_restricted_admin_site.register(ChatHistory, ChatHistoryAdmin)
smarter_restricted_admin_site.register(ChatPluginUsage, ChatPluginUsageAdmin)
smarter_restricted_admin_site.register(ChatToolCall, ChatToolCallHistoryAdmin)
