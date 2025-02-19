# pylint: disable=W0212
"""Admin configuration for the chatbot app."""

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.lib.django.admin import RestrictedModelAdmin

from .models import (
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
    ChatBotFunctions,
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
        "ready",
        "deployed",
        "dns_verification_status",
        "tls_certificate_issuance_status",
        "short_default_system_role",
    ]

    def ready(self, obj):
        return obj.ready()

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
