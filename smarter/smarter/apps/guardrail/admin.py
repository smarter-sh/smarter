# pylint: disable=W0212
"""
Admin configuration for the guardrail app.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.contrib import admin
from django.db.models import Q

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)
from smarter.lib import logging

from .models import Guardrail, GuardrailEvent

logger = logging.getLogger(__name__)


class GuardrailAdmin(SmarterCustomerModelAdmin):
    """
    Guardrail model admin.

    This is a primary Smarter resource, that descends directly from
    MetaDataWithOwnershipModel. Visibility of Guardrails is determined by ownership and role.
    Guardrails are configured with manifests.
    """

    model = Guardrail

    readonly_fields = ("created_at", "updated_at")
    list_display = [
        "name",
        "user_profile",
        "stage",
        "category",
        "strategy",
        "action",
        "mode",
        "severity",
        "priority",
        "is_active",
        "updated_at",
    ]
    list_filter = ["stage", "category", "strategy", "action", "mode", "is_active"]
    search_fields = ["name", "description"]
    ordering = ["priority", "name"]

    def get_queryset(self, request):
        """Visibility is determined by ownership and role."""
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return qs.filter(id__in=Guardrail.objects.with_ownership_permission_for(user=user).values("id"))


class GuardrailEventAdmin(SmarterCustomerModelAdmin):
    """
    GuardrailEvent model admin: the review queue of guardrails.

    Events are read only, except ``reviewed``. A user sees the events of the guardrails, and of
    the LLMClients, that they own.
    """

    model = GuardrailEvent

    list_display = [
        "created_at",
        "guardrail_name",
        "llmclient",
        "stage",
        "category",
        "disposition",
        "severity",
        "confidence",
        "reviewed",
    ]
    list_filter = ["disposition", "reviewed", "stage", "category", "severity", "mode"]
    search_fields = ["guardrail_name", "session_key", "rationale"]
    ordering = ["-created_at"]
    actions = ["mark_reviewed"]

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in GuardrailEvent._meta.fields if field.name != "reviewed"]

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        """Visibility is determined by ownership of the guardrail or the LLMClient, and role."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.llmclient.models import LLMClient

        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        guardrails = Guardrail.objects.with_ownership_permission_for(user=user).values("id")
        llmclients = LLMClient.objects.with_ownership_permission_for(user=user).values("id")
        return qs.filter(Q(guardrail__in=guardrails) | Q(llmclient__in=llmclients))

    @admin.action(description="Mark the selected events as reviewed")
    def mark_reviewed(self, request, queryset):
        """Mark events as reviewed."""
        updated = queryset.update(reviewed=True)
        self.message_user(request, f"{updated} event(s) marked as reviewed.")


smarter_restricted_admin_site.register(Guardrail, GuardrailAdmin)
smarter_restricted_admin_site.register(GuardrailEvent, GuardrailEventAdmin)
