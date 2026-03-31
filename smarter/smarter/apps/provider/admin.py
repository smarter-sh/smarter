# pylint: disable=W0212
"""Django admin configuration for the chat app."""

from django.contrib import admin

from smarter.apps.account.models import get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)

from .models import (
    Provider,
    ProviderModel,
    ProviderModelVerification,
    ProviderVerification,
)


class ProviderModelVerificationAdmin(admin.StackedInline):
    """
    provider model verification admin.
    """

    model = ProviderModelVerification

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["created_at", "provider_model", "verification_type", "is_successful", "is_valid"]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if user.is_authenticated:
            return qs
        return qs.none()


class ProviderVerificationAdmin(admin.StackedInline):
    """provider verification admin."""

    model = ProviderVerification

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["created_at", "provider", "verification_type", "is_successful", "is_valid"]

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)

        if user.is_authenticated:
            return qs
        return qs.none()


class ProviderAdmin(SmarterCustomerModelAdmin):
    """
    Provider admin. This is a primary Smarter resource, that descends directly from
    MetaDataWithOwnershipModel. Visibility of Providers is granted to any
    authenticated user.
    """

    model = Provider
    inlines = [ProviderVerificationAdmin]

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = ["name", "status", "is_active", "user_profile", "created_at", "updated_at"]

    def get_queryset(self, request):
        """
        Visibility is granted to authenticated users.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if user.is_authenticated:
            return qs
        return qs.none()


class ProviderModelAdmin(SmarterCustomerModelAdmin):
    """
    ProviderModel admin. This descends from Provider, so visibility
    is determined by the parent Provider. Provider visibility is granted to any
    authenticated user.
    """

    model = ProviderModel
    inlines = [ProviderModelVerificationAdmin]

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["provider", "name", "created_at", "is_active"]

    def get_queryset(self, request):
        """
        Visibility is granted to authenticated users.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if user.is_authenticated:
            return qs
        return qs.none()


# Provider Models
smarter_restricted_admin_site.register(Provider, ProviderAdmin)
smarter_restricted_admin_site.register(ProviderModel, ProviderModelAdmin)
