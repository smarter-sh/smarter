# pylint: disable=W0212
"""Admin configuration for the chatbot app."""

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.lib.django.admin import RestrictedModelAdmin

from .models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
    ChatBotFunctions,
    ChatBotPlugin,
    ChatBotRequests,
)


class ChatBotAdmin(RestrictedModelAdmin):
    """ChatBot model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [
        "created_at",
        "updated_at",
        "url",
        "account",
        "name",
        "deployed",
        "mode",
        "ready",
        "dns_verification_status",
        "tls_certificate_issuance_status",
    ]

    def ready(self, obj: ChatBot) -> bool:
        return obj.ready()

    def mode(self, obj: ChatBot) -> str:
        return obj.mode(obj.url)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = get_cached_user_profile(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatBotRequestsAdmin(RestrictedModelAdmin):
    """
    ChatBotRequests model admin.
    """

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [field.name for field in ChatBotRequests._meta.fields]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = get_cached_user_profile(user=request.user)
            return qs.filter(chatbot__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatBotCustomDomainAdmin(RestrictedModelAdmin):
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
            user_profile = get_cached_user_profile(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatBotCustomDomainDNSAdmin(RestrictedModelAdmin):
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
            user_profile = get_cached_user_profile(user=request.user)
            return qs.filter(custom_domain__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatBotAPIKeyAdmin(RestrictedModelAdmin):
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
            user_profile = get_cached_user_profile(user=request.user)
            return qs.filter(chatbot__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatBotPluginAdmin(RestrictedModelAdmin):
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
            user_profile = get_cached_user_profile(user=request.user)
            return qs.filter(chatbot__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChatBotFunctionsAdmin(RestrictedModelAdmin):
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
            user_profile = get_cached_user_profile(user=request.user)
            return qs.filter(chatbot__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


# ChatBot
smarter_restricted_admin_site.register(ChatBot, ChatBotAdmin)
smarter_restricted_admin_site.register(ChatBotCustomDomain, ChatBotCustomDomainAdmin)
smarter_restricted_admin_site.register(ChatBotCustomDomainDNS, ChatBotCustomDomainDNSAdmin)
smarter_restricted_admin_site.register(ChatBotAPIKey, ChatBotAPIKeyAdmin)
smarter_restricted_admin_site.register(ChatBotPlugin, ChatBotPluginAdmin)
smarter_restricted_admin_site.register(ChatBotFunctions, ChatBotFunctionsAdmin)
smarter_restricted_admin_site.register(ChatBotRequests, ChatBotRequestsAdmin)
