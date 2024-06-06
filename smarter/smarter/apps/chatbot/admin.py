# pylint: disable=W0212
"""Admin configuration for the chatbot app."""

from django.contrib import admin

from smarter.apps.account.models import UserProfile

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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatBotCustomDomainAdmin(admin.ModelAdmin):
    """ChatBotCustomDomain model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotCustomDomain._meta.fields]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatBotCustomDomainDNSAdmin(admin.ModelAdmin):
    """ChatBotCustomDomainDNS model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotCustomDomainDNS._meta.fields]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(custom_domain__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatBotAPIKeyAdmin(admin.ModelAdmin):
    """ChatBotAPIKey model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotAPIKey._meta.fields]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(chatbot__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatBotPluginAdmin(admin.ModelAdmin):
    """ChatBotPlugin model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(chatbot__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatBotFunctionsAdmin(admin.ModelAdmin):
    """ChatBotFunctions model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotFunctions._meta.fields]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(chatbot__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


admin.site.register(ChatBot, ChatBotAdmin)
admin.site.register(ChatBotCustomDomain, ChatBotCustomDomainAdmin)
admin.site.register(ChatBotCustomDomainDNS, ChatBotCustomDomainDNSAdmin)
admin.site.register(ChatBotAPIKey, ChatBotAPIKeyAdmin)
admin.site.register(ChatBotPlugin, ChatBotPluginAdmin)
admin.site.register(ChatBotFunctions, ChatBotFunctionsAdmin)
