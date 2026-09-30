# pylint: disable=W0212
"""
Admin configuration for the mcpclient app.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)
from smarter.lib import logging

from .models import (
    MCPClient,
)

logger = logging.getLogger(__name__)


class MCPClientAdmin(SmarterCustomerModelAdmin):
    """
    MCPClient model admin.

    This is a primary Smarter resource, that descends directly from
    MetaDataWithOwnershipModel. Visibility of MCPClients is determined by ownership
    and role. MCPClients are configured with manifests, so the connection status
    fields, which Smarter records when it connects to the MCP server, are read only.
    """

    model = MCPClient

    readonly_fields = (
        "created_at",
        "updated_at",
        "status",
        "protocol_version",
        "server_name",
        "server_version",
        "tools",
        "last_connected_at",
        "last_error",
    )
    list_display = [
        "name",
        "user_profile",
        "transport",
        "endpoint_url",
        "auth_type",
        "is_active",
        "priority",
        "status",
        "last_connected_at",
        "updated_at",
    ]
    list_filter = ["transport", "auth_type", "is_active", "status"]
    search_fields = ["name", "endpoint_url", "server_name"]
    ordering = ["-updated_at"]

    def get_queryset(self, request):
        """Visibility is determined by ownership and role."""
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return qs.filter(id__in=MCPClient.objects.with_ownership_permission_for(user=user).values("id"))


smarter_restricted_admin_site.register(MCPClient, MCPClientAdmin)
