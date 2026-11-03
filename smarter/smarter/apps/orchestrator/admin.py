# pylint: disable=W0212
"""Admin configuration for the orchestrator app."""

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)
from smarter.lib import logging

from .models import (
    Orchestrator,
)

logger = logging.getLogger(__name__)


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


smarter_restricted_admin_site.register(Orchestrator, OrchestratorAdmin)
