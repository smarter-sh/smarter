# pylint: disable=W0212
"""
Admin configuration for the vectorstore app.
"""

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_filter_queryset_for_user,
    smarter_restricted_admin_site,
)

from .models import VectorDatabase


class VectorDatabaseAdmin(SmarterCustomerModelAdmin):
    """
    VectorDatabase model admin. This is a primary
    Smarter resource, that descends directly from MetaDataWithOwnershipModel.
    Visibility of VectorDatabases is determined by ownership and role.
    """

    model = VectorDatabase

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [
        "name",
        "user_profile",
        "backend",
        "host",
        "status",
        "provider",
        "provider_model",
        "created_at",
        "updated_at",
    ]
    ordering = ["-updated_at"]

    def provider(self, obj):
        return obj.provider.name if obj.provider else None

    provider.admin_order_field = "provider"
    provider.short_description = "Provider Name"

    def provider_model(self, obj):
        return obj.provider_model.name if obj.provider_model else None

    provider_model.admin_order_field = "provider_model"
    provider_model.short_description = "Provider Model Name"

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()

        return smarter_filter_queryset_for_user(user=user, qs=qs)


smarter_restricted_admin_site.register(VectorDatabase, VectorDatabaseAdmin)
