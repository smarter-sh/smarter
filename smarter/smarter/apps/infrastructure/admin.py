"""Admin of the infrastructure app: the ledger of cloud resources, for superusers, read-only."""

from smarter.apps.dashboard.admin import (
    SmarterSuperUserOnlyModelAdmin,
    smarter_restricted_admin_site,
)

from .models import InfrastructureResource


class InfrastructureResourceAdmin(SmarterSuperUserOnlyModelAdmin):
    """The ledger of cloud resources.

    The infrastructure signals' receivers write it, so it is read-only.
    """

    list_display = [
        "created_at",
        "provider",
        "service",
        "resource_type",
        "resource_name",
        "billable",
        "status",
        "destroyed_at",
    ]
    list_filter = ["provider", "service", "resource_type", "billable", "status"]
    search_fields = ["resource_name", "resource_id"]
    readonly_fields = [field.name for field in InfrastructureResource._meta.fields]

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


smarter_restricted_admin_site.register(InfrastructureResource, InfrastructureResourceAdmin)
