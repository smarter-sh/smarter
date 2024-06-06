# pylint: disable=W0212
"""Django admin configuration for the chat app."""

from django.contrib import admin

from smarter.apps.account.models import UserProfile

from .models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall


class ChatAdmin(admin.ModelAdmin):
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


class ChatHistoryAdmin(admin.ModelAdmin):
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


class PluginSelectionHistoryAdmin(admin.ModelAdmin):
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


class ChatToolCallHistoryAdmin(admin.ModelAdmin):
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


admin.site.register(Chat, ChatAdmin)
admin.site.register(ChatHistory, ChatHistoryAdmin)
admin.site.register(ChatPluginUsage, PluginSelectionHistoryAdmin)
admin.site.register(ChatToolCall, ChatToolCallHistoryAdmin)
