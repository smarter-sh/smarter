# pylint: disable=W0212
"""Django admin configuration for the chat app."""

from django.contrib import admin

from .models import Chat, ChatPluginUsage, ChatToolCall


class ChatHistoryAdmin(admin.ModelAdmin):
    """chat history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in Chat._meta.fields]


class PluginSelectionHistoryAdmin(admin.ModelAdmin):
    """plugin selection history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatPluginUsage._meta.fields]


class ChatToolCallHistoryAdmin(admin.ModelAdmin):
    """chat tool call history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatToolCall._meta.fields]


admin.site.register(Chat, ChatHistoryAdmin)
admin.site.register(ChatPluginUsage, PluginSelectionHistoryAdmin)
admin.site.register(ChatToolCall, ChatToolCallHistoryAdmin)
