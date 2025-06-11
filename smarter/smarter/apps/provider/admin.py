# pylint: disable=W0212
"""Django admin configuration for the chat app."""

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_account_for_user
from smarter.lib.django.admin import RestrictedModelAdmin


class ProviderAdmin(RestrictedModelAdmin):
    """Provider admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["created_at", "account", "name", "status", "is_active"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ProviderModelAdmin(RestrictedModelAdmin):
    """Provider model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["created_at", "provider", "name", "is_active"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(provider_model__provider__account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ProviderModelVerificationAdmin(RestrictedModelAdmin):
    """provider model verification admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["created_at", "provider_model", "verification_type", "is_successful", "is_valid"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(chat__account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ProviderVerificationAdmin(RestrictedModelAdmin):
    """provider verification admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["created_at", "provider", "verification_type", "is_successful", "is_valid"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(provider__account=account)
        except UserProfile.DoesNotExist:
            return qs.none()
