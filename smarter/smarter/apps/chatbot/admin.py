# -*- coding: utf-8 -*-
# pylint: disable=W0212
"""Admin configuration for the chatbot app."""

from django.contrib import admin

from .models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
    ChatBotFunctions,
    ChatBotPlugin,
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


class ChatBotAPIKeyAdmin(admin.ModelAdmin):
    """ChatBotAPIKey model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotAPIKey._meta.fields]


class ChatBotPluginAdmin(admin.ModelAdmin):
    """ChatBotPlugin model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotPlugin._meta.fields]


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
admin.site.register(ChatBotAPIKey, ChatBotAPIKeyAdmin)
admin.site.register(ChatBotPlugin, ChatBotPluginAdmin)
admin.site.register(ChatBotFunctions, ChatBotFunctionsAdmin)
