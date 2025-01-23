# pylint: disable=W0212
"""Admin configuration for the chatbot app."""

from smarter.apps.account.models import UserProfile
from smarter.lib.django.admin import RestrictedModelAdmin

from .models import (
    ChatBot,
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
    list_display = [field.name for field in ChatBot._meta.fields if field.name != "default_system_role"] + [
        "short_default_system_role"
    ]

    def short_default_system_role(self, obj):
        return obj.default_system_role[:50]

    short_default_system_role.short_description = "Default System Role"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
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
            user_profile = UserProfile.objects.get(user=request.user)
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
            user_profile = UserProfile.objects.get(user=request.user)
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
            user_profile = UserProfile.objects.get(user=request.user)
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
            user_profile = UserProfile.objects.get(user=request.user)
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
            user_profile = UserProfile.objects.get(user=request.user)
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
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(chatbot__account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()
