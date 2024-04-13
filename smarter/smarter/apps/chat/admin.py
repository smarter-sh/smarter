# pylint: disable=W0212
"""Django admin configuration for the chat app."""

from django.contrib import admin

from .models import ChatHistory, ChatToolCallHistory, PluginUsageHistory


class ChatHistoryAdmin(admin.ModelAdmin):
    """chat history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatHistory._meta.fields]


class PluginSelectionHistoryAdmin(admin.ModelAdmin):
    """plugin selection history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in PluginUsageHistory._meta.fields]


class ChatToolCallHistoryAdmin(admin.ModelAdmin):
    """chat tool call history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatToolCallHistory._meta.fields]


admin.site.register(ChatHistory, ChatHistoryAdmin)
admin.site.register(PluginUsageHistory, PluginSelectionHistoryAdmin)
admin.site.register(ChatToolCallHistory, ChatToolCallHistoryAdmin)
