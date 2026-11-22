# pylint: disable=W0212
"""Admin configuration for the orchestrator app."""

from django.contrib import admin

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)
from smarter.lib import logging

from .models import (
    OrchestrationRun,
    OrchestrationStep,
    Orchestrator,
)

logger = logging.getSmarterLogger(__name__)


class OrchestratorAdmin(SmarterCustomerModelAdmin):
    """
    Orchestrator model admin.

    This is a primary
    Smarter resource, that descends directly from MetaDataWithOwnershipModel.
    Visibility of Orchestrators is determined by ownership and role.
    """

    model = Orchestrator

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = [
        "name",
        "user_profile",
        "description",
        "created_at",
        "updated_at",
    ]
    ordering = ["-updated_at"]

    def ready(self, obj: Orchestrator) -> bool:
        """
        Whether the Orchestrator is ready, for the admin list.

        :param obj: The Orchestrator.
        :returns: The Orchestrator's ``ready`` property.
        """
        return obj.ready

    def mode(self, obj: Orchestrator) -> str:
        """
        The Orchestrator's mode for its url, for the admin list.

        :param obj: The Orchestrator.
        :returns: ``obj.mode(obj.url)``.
        """
        return obj.mode(obj.url)  # type: ignore

    def get_queryset(self, request):
        """
        Restrict the admin list to the Orchestrators that the requesting user has ownership permission for.

        :param request: The admin request.
        :returns: The Orchestrators with ownership permission for the user, or an empty queryset if the
            request has no resolved user.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return Orchestrator.objects.with_ownership_permission_for(user=user)


class OrchestrationStepInline(admin.TabularInline):
    """A run's steps, in order: each LLMClient invocation of the run, read-only."""

    model = OrchestrationStep
    extra = 0
    fields = ("sequence", "harness", "prompt", "status", "error_message", "created_at")
    readonly_fields = fields
    can_delete = False
    ordering = ("sequence",)

    def has_add_permission(self, request, obj=None) -> bool:
        """
        Never add a step in the admin: the orchestrator records them as it runs.

        :param request: The admin request.
        :param obj: The run, or None.
        :returns: False.
        """
        return False


class OrchestrationRunAdmin(SmarterCustomerModelAdmin):
    """
    OrchestrationRun model admin: the audit trail of each Orchestrator's runs, read-only.

    A run's page shows its steps. Visibility is determined by ownership of the run's Orchestrator, and role.
    """

    model = OrchestrationRun
    inlines = [OrchestrationStepInline]

    list_display = [
        "created_at",
        "orchestrator",
        "status",
        "iteration_count",
        "started_by",
        "started_at",
        "completed_at",
    ]
    list_filter = ["status"]
    search_fields = ["orchestrator__name", "objective"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    def get_readonly_fields(self, request, obj=None):
        """
        Make every field read-only: the orchestrator writes runs.

        :param request: The admin request.
        :param obj: The run, or None.
        :returns: Every field's name.
        """
        return [field.name for field in OrchestrationRun._meta.fields]

    def has_add_permission(self, request, obj=None) -> bool:
        """
        Never add a run in the admin: runs are started from the Orchestrator.

        :param request: The admin request.
        :param obj: Unused.
        :returns: False.
        """
        return False

    def get_queryset(self, request):
        """
        Return the runs of the Orchestrators that the requesting user has ownership permission for.

        :param request: The admin request.
        :returns: The permitted runs, or an empty queryset if the request has no resolved user.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        orchestrators = Orchestrator.objects.with_ownership_permission_for(user=user)
        return qs.filter(orchestrator__in=orchestrators)


smarter_restricted_admin_site.register(Orchestrator, OrchestratorAdmin)
smarter_restricted_admin_site.register(OrchestrationRun, OrchestrationRunAdmin)
