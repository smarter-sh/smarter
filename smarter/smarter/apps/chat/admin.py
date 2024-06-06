# pylint: disable=W0212
"""Django admin configuration for the chat app."""

from smarter.apps.account.models import UserProfile
from smarter.lib.django.admin import RestrictedModelAdmin

from .models import Chat, ChatPluginUsage, ChatToolCall


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
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatHistoryAdmin(RestrictedModelAdmin):
    """chat history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["chat", "request", "response"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(chat__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class PluginSelectionHistoryAdmin(RestrictedModelAdmin):
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
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(chat__account=user_profile.account)
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
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(chat__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()
