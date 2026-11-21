# pylint: disable=W0212
"""Django admin configuration for the prompt app."""

from django.contrib import admin

from smarter.apps.account.models import get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_admin_user,
    smarter_restricted_admin_site,
)

from .models import (
    Provider,
    ProviderModel,
    ProviderModelVerification,
    ProviderVerification,
)


class ProviderModelVerificationAdmin(admin.StackedInline):
    """Provider model verification admin."""

    model = ProviderModelVerification

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["created_at", "provider_model", "verification_type", "is_successful", "is_valid"]

    def get_queryset(self, request):
        """
        Return every provider model verification to an authenticated user, and none otherwise.

        :param request: The admin request.
        :returns: The verifications queryset, or an empty queryset.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if user is None:
            return qs.none()
        if user.is_authenticated:
            return qs
        return qs.none()


class ProviderVerificationAdmin(admin.StackedInline):
    """Provider verification admin."""

    model = ProviderVerification

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["created_at", "provider", "verification_type", "is_successful", "is_valid"]

    def get_queryset(self, request):
        """
        Return every provider verification to an authenticated user, and none otherwise.

        :param request: The admin request.
        :returns: The verifications queryset, or an empty queryset.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)

        if user is None:
            return qs.none()
        if user.is_authenticated:
            return qs
        return qs.none()


class ProviderAdmin(SmarterCustomerModelAdmin):
    """
    Provider admin.

    This is a primary Smarter resource, that descends directly from
    MetaDataWithOwnershipModel. :class:`~smarter.apps.dashboard.admin.SmarterCustomerModelAdmin`
    shows staff the Providers of their own account.
    """

    model = Provider
    search_fields = ("name", "description", "base_url", "default_model", "user_profile__user__username")
    inlines = [ProviderVerificationAdmin]

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = ["name", "status", "is_active", "user_profile", "created_at", "updated_at"]


class ProviderModelAdmin(SmarterCustomerModelAdmin):
    """
    ProviderModel admin.

    This descends from Provider, so visibility
    is determined by the parent Provider's ownership.
    """

    model = ProviderModel
    search_fields = ("name", "provider__name")
    inlines = [ProviderModelVerificationAdmin]

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ["provider", "name", "created_at", "is_active"]

    def get_queryset(self, request):
        """
        Return the models of the Providers that the requesting user has ownership permission for.

        :param request: The admin request.
        :returns: The permitted rows, or an empty queryset if the request has no authenticated user.
        """
        user = smarter_admin_user(request)
        qs = super().get_queryset(request)
        if user is None:
            return qs.none()
        if user.is_superuser:
            return qs
        return qs.filter(provider__in=Provider.objects.with_ownership_permission_for(user=user))


# Provider Models
smarter_restricted_admin_site.register(Provider, ProviderAdmin)
smarter_restricted_admin_site.register(ProviderModel, ProviderModelAdmin)
