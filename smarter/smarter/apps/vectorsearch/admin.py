# pylint: disable=W0212
"""Admin configuration for the vectorsearch app."""

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)
from smarter.lib import logging

from .models import (
    Vectorsearch,
)

logger = logging.getLogger(__name__)


class VectorsearchAdmin(SmarterCustomerModelAdmin):
    """
    Vectorsearch model admin.

    This is a primary
    Smarter resource, that descends directly from MetaDataWithOwnershipModel.
    Visibility of Vectorsearchs is determined by ownership and role.
    """

    model = Vectorsearch

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

    def ready(self, obj: Vectorsearch) -> bool:
        """
        Whether the Vectorsearch is ready, for the admin list.

        :param obj: The Vectorsearch.
        :returns: The Vectorsearch's ``ready`` property.
        """
        return obj.ready

    def mode(self, obj: Vectorsearch) -> str:
        """
        The Vectorsearch's mode for its url, for the admin list.

        :param obj: The Vectorsearch.
        :returns: ``obj.mode(obj.url)``.
        """
        return obj.mode(obj.url)  # type: ignore

    def get_queryset(self, request):
        """
        Restrict the admin list to the Vectorsearchs that the requesting user has ownership permission for.

        :param request: The admin request.
        :returns: The Vectorsearchs with ownership permission for the user, or an empty queryset if the
            request has no resolved user.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()
        return Vectorsearch.objects.with_ownership_permission_for(user=user)


smarter_restricted_admin_site.register(Vectorsearch, VectorsearchAdmin)
