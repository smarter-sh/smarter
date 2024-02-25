# -*- coding: utf-8 -*-
# pylint: disable=W0212
"""Django admin configuration for the chat app."""

from django.contrib import admin

from smarter.apps.chat.models import (
    ChatHistory,
    ChatToolCallHistory,
    PluginSelectionHistory,
)


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
    list_display = [field.name for field in PluginSelectionHistory._meta.fields]


class ChatToolCallHistoryAdmin(admin.ModelAdmin):
    """chat tool call history model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatToolCallHistory._meta.fields]


admin.site.register(ChatHistory, ChatHistoryAdmin)
admin.site.register(PluginSelectionHistory, PluginSelectionHistoryAdmin)
admin.site.register(ChatToolCallHistory, ChatToolCallHistoryAdmin)
