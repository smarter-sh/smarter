"""Admin of the MCPServer app: the audit trail of the operations tools, for superusers, read-only."""

from smarter.apps.dashboard.admin import (
    SmarterSuperUserOnlyModelAdmin,
    smarter_restricted_admin_site,
)

from .models import OperationsToolCall


class OperationsToolCallAdmin(SmarterSuperUserOnlyModelAdmin):
    """
    The audit trail of the Smarter Operations MCP server's tools.

    The server writes it on every tool call, so it is read-only. A superuser may delete rows.
    """

    list_display = ["created_at", "username", "tool", "ticket", "is_error", "characters"]
    list_filter = ["tool", "is_error"]
    search_fields = ["ticket", "tool", "username"]
    # pylint: disable=W0212
    readonly_fields = [field.name for field in OperationsToolCall._meta.fields]

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


smarter_restricted_admin_site.register(OperationsToolCall, OperationsToolCallAdmin)
