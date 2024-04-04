# -*- coding: utf-8 -*-
# pylint: disable=W0212
"""Admin configuration for the chatbot app."""

from django.contrib import admin

from .models import (
    ChatBot,
    ChatBotAPIKeys,
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
    ChatBotFunctions,
    ChatBotPlugins,
)


class ChatBotAdmin(admin.ModelAdmin):
    """ChatBot model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBot._meta.fields]


class ChatBotDNSHostAdmin(admin.ModelAdmin):
    """ChatBotCustomDomain model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotCustomDomain._meta.fields]


class ChatBotDNSRecordAdmin(admin.ModelAdmin):
    """ChatBotCustomDomainDNS model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotCustomDomainDNS._meta.fields]


class ChatBotAPIKeysAdmin(admin.ModelAdmin):
    """ChatBotAPIKeys model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotAPIKeys._meta.fields]


class ChatBotPluginsAdmin(admin.ModelAdmin):
    """ChatBotPlugins model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotPlugins._meta.fields]


class ChatBotFunctionsAdmin(admin.ModelAdmin):
    """ChatBotFunctions model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotFunctions._meta.fields]


admin.site.register(ChatBot, ChatBotAdmin)
admin.site.register(ChatBotCustomDomain, ChatBotDNSHostAdmin)
admin.site.register(ChatBotCustomDomainDNS, ChatBotDNSRecordAdmin)
admin.site.register(ChatBotAPIKeys, ChatBotAPIKeysAdmin)
admin.site.register(ChatBotPlugins, ChatBotPluginsAdmin)
admin.site.register(ChatBotFunctions, ChatBotFunctionsAdmin)
