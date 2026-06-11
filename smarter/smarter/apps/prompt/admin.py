# pylint: disable=W0212
"""Django admin configuration for the prompt app."""

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)

from .models import Prompt, PromptHistory, PromptPluginUsage, PromptToolCall


class ChatAdmin(SmarterCustomerModelAdmin):
    """
    Prompt model admin.

    This is a primary Smarter resource, that descends
    directly from MetaDataWithOwnershipModel. Visibility of Chats is
    determined by ownership and role.
    """

    model = Prompt

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in Prompt._meta.fields]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return Prompt.objects.with_ownership_permission_for(user=user).filter(id__in=qs)


class ChatHistoryAdmin(SmarterCustomerModelAdmin):
    """
    PromptHistory model admin.

    This descends from Prompt, so visibility is
    determined by the parent Prompt and role.
    """

    model = PromptHistory

    readonly_fields = (
        "created_at",
        "updated_at",
        "prompt_history",
    )
    list_display = ["prompt", "prompt_history"]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        chats = Prompt.objects.with_ownership_permission_for(user=user).filter(id__in=qs)
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
        chats = Prompt.objects.with_ownership_permission_for(user=user).filter(id__in=qs)
        return PromptPluginUsage.objects.filter(chat__in=chats)


class ChatToolCallHistoryAdmin(SmarterCustomerModelAdmin):
    """Prompt tool call history model admin."""

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
        chats = Prompt.objects.with_ownership_permission_for(user=user).filter(id__in=qs)
        return PromptToolCall.objects.filter(chat__in=chats)


smarter_restricted_admin_site.register(Prompt, ChatAdmin)
smarter_restricted_admin_site.register(PromptHistory, ChatHistoryAdmin)
smarter_restricted_admin_site.register(PromptPluginUsage, ChatPluginUsageAdmin)
smarter_restricted_admin_site.register(PromptToolCall, ChatToolCallHistoryAdmin)
