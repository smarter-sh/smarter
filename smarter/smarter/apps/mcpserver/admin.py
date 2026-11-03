"""
Django admin of the MCPServer app: the audit trail of the operations tools, for superusers, read-only.

Every call to a staff-only tool of the MCPServer
(:mod:`smarter.apps.mcpserver.protocol.operations`) is recorded as an
:class:`~smarter.apps.mcpserver.models.OperationsToolCall`. This module registers that model on
the restricted admin site, so that a superuser can see who called which tool, for which help desk
ticket, and whether it failed. The rows are evidence, so they cannot be added or changed here.

The repository indexes, :class:`~smarter.apps.mcpserver.models.RepositoryIndex` and
:class:`~smarter.apps.mcpserver.models.RepositoryFile`, are not registered: they are rebuilt by the
indexing tasks, and are not edited by hand.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from smarter.apps.dashboard.admin import (
    SmarterSuperUserOnlyModelAdmin,
    smarter_restricted_admin_site,
)

from .models import OperationsToolCall


class OperationsToolCallAdmin(SmarterSuperUserOnlyModelAdmin):
    """
    The admin of the audit trail of the MCPServer's staff-only tools.

    The server writes a row on every tool call, so the admin is read-only: every field is
    read-only, and rows cannot be added or changed. Only superusers see it, through
    :class:`~smarter.apps.dashboard.admin.SmarterSuperUserOnlyModelAdmin`, and a superuser may
    delete rows, e.g. when they are no longer needed.
    """

    #: The columns of the list of tool calls.
    list_display = ["created_at", "username", "tool", "ticket", "is_error", "characters"]

    #: The filters in the list's sidebar.
    list_filter = ["tool", "is_error"]

    #: The fields that the list's search box searches.
    search_fields = ["ticket", "tool", "username"]

    #: Every field of the model, so that a tool call can be read but not edited.
    readonly_fields = [field.name for field in OperationsToolCall._meta.fields]  # pylint: disable=W0212

    def has_add_permission(self, request, obj=None) -> bool:
        """
        Refuse to add a tool call by hand: only the MCP server writes them.

        :param request: The admin request.
        :param obj: Unused.
        :returns: Always False.
        """
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """
        Refuse to change a tool call, so that the audit trail stays as the server wrote it.

        :param request: The admin request.
        :param obj: The tool call, or None for the list.
        :returns: Always False.
        """
        return False


smarter_restricted_admin_site.register(OperationsToolCall, OperationsToolCallAdmin)
