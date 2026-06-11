# pylint: disable=W0212
"""Django admin configuration for the chat app."""

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)

from .models import Chat, PromptHistory, PromptPluginUsage, PromptToolCall


class ChatAdmin(SmarterCustomerModelAdmin):
    """
    Chat model admin.

    This is a primary Smarter resource, that descends
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
        if not isinstance(user, User):
            return qs.none()
        return Chat.objects.with_ownership_permission_for(user=user).filter(id__in=qs)


class ChatHistoryAdmin(SmarterCustomerModelAdmin):
    """
    PromptHistory model admin.

    This descends from Chat, so visibility is
    determined by the parent Chat and role.
    """

    model = PromptHistory

    readonly_fields = (
        "created_at",
        "updated_at",
        "chat_history",
    )
    list_display = ["chat", "chat_history"]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        chats = Chat.objects.with_ownership_permission_for(user=user).filter(id__in=qs)
        return PromptHistory.objects.filter(chat__in=chats)


class ChatPluginUsageAdmin(SmarterCustomerModelAdmin):
    """Plugin selection history model admin."""

    model = PromptPluginUsage

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in PromptPluginUsage._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        chats = Chat.objects.with_ownership_permission_for(user=user).filter(id__in=qs)
        return PromptPluginUsage.objects.filter(chat__in=chats)


class ChatToolCallHistoryAdmin(SmarterCustomerModelAdmin):
    """Chat tool call history model admin."""

    model = PromptToolCall

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in PromptToolCall._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        chats = Chat.objects.with_ownership_permission_for(user=user).filter(id__in=qs)
        return PromptToolCall.objects.filter(chat__in=chats)


smarter_restricted_admin_site.register(Chat, ChatAdmin)
smarter_restricted_admin_site.register(PromptHistory, ChatHistoryAdmin)
smarter_restricted_admin_site.register(PromptPluginUsage, ChatPluginUsageAdmin)
smarter_restricted_admin_site.register(PromptToolCall, ChatToolCallHistoryAdmin)
