# pylint: disable=W0212
"""Django admin configuration for the chat app."""

from django.contrib import admin

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_account_for_user
from smarter.apps.dashboard.admin import (
    RestrictedModelAdmin,
    smarter_restricted_admin_site,
)

from .models import (
    Provider,
    ProviderModel,
    ProviderModelVerification,
    ProviderVerification,
)


class ProviderModelVerificationAdmin(admin.StackedInline):
    """provider model verification admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["created_at", "provider_model", "verification_type", "is_successful", "is_valid"]
    model = ProviderModelVerification

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(chat__account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ProviderVerificationAdmin(admin.StackedInline):
    """provider verification admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["created_at", "provider", "verification_type", "is_successful", "is_valid"]
    model = ProviderVerification

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(provider__account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ProviderAdmin(RestrictedModelAdmin):
    """Provider admin."""

    inlines = [ProviderVerificationAdmin]

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = ["created_at", "account", "name", "status", "is_active"]
    model = Provider

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

    inlines = [ProviderModelVerificationAdmin]

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["created_at", "provider", "name", "is_active"]
    model = ProviderModel

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(provider_model__provider__account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


# Provider Models
smarter_restricted_admin_site.register(Provider, ProviderAdmin)
smarter_restricted_admin_site.register(ProviderModel, ProviderModelAdmin)
