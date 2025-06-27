# pylint: disable=W0212
"""Django admin configuration for the chat app."""

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_account_for_user
from smarter.apps.dashboard.admin import (
    RestrictedModelAdmin,
    smarter_restricted_admin_site,
)

from .models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall


class ChatAdmin(RestrictedModelAdmin):
    """chat history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in Chat._meta.fields]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatHistoryAdmin(RestrictedModelAdmin):
    """chat history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
        "chat_history",
    )
    list_display = ["chat", "chat_history"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(chat__account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatPluginUsageAdmin(RestrictedModelAdmin):
    """plugin selection history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatPluginUsage._meta.fields]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(chat__account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatToolCallHistoryAdmin(RestrictedModelAdmin):
    """chat tool call history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatToolCall._meta.fields]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(chat__account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


smarter_restricted_admin_site.register(Chat, ChatAdmin)
smarter_restricted_admin_site.register(ChatHistory, ChatHistoryAdmin)
smarter_restricted_admin_site.register(ChatPluginUsage, ChatPluginUsageAdmin)
smarter_restricted_admin_site.register(ChatToolCall, ChatToolCallHistoryAdmin)
