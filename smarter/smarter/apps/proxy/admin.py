"""Admin configuration for the proxy app."""

from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)

from .models import Proxy


class ProxyAdmin(SmarterCustomerModelAdmin):
    """
    Proxy model admin.

    This is a primary Smarter resource, that descends directly from
    MetaDataWithOwnershipModel. Visibility of Proxies is determined by ownership and role.
    Proxies are configured with manifests, with ``smarter apply``.
    """

    model = Proxy

    readonly_fields = ("created_at", "updated_at")
    list_display = [
        "name",
        "user_profile",
        "provider",
        "base_url",
        "api_key_secret",
        "is_active",
        "updated_at",
    ]
    list_filter = ["is_active", "provider"]
    search_fields = ["name", "description", "base_url"]


smarter_restricted_admin_site.register(Proxy, ProxyAdmin)
