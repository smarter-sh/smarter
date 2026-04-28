# pylint: disable=C0114,C0115
"""Connection admin."""

import logging

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_restricted_admin_site,
)

from .models import (
    ApiConnection,
    SqlConnection,
)

logger = logging.getLogger(__name__)


# Register your models here.


class SqlConnectionAdmin(SmarterCustomerModelAdmin):
    """
    Connection SQL model admin. This is a primary Smarter resource,
    that descends directly from MetaDataWithOwnershipModel. Visibility
    is determined by ownership and role.
    """

    model = SqlConnection

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = (
        "created_at",
        "user_profile",
        "name",
        "db_engine",
        "hostname",
        "database",
        "username",
        "updated_at",
    )

    def get_queryset(self, request):
        """
        Visibility is determined by ownership and role.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()

        return SqlConnection.objects.with_ownership_permission_for(user=user).filter(id__in=qs)


class ApiConnectionAdmin(SmarterCustomerModelAdmin):
    """
    ApiConnection model admin. This is a primary Smarter resource,
    that descends directly from MetaDataWithOwnershipModel. Visibility
    is determined by ownership and role.
    """

    model = ApiConnection

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = (
        "created_at",
        "user_profile",
        "name",
        "base_url",
        "api_key",
        "updated_at",
    )

    def get_queryset(self, request):
        """
        Visibility is determined by ownership and role.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        if not isinstance(user, User):
            return qs.none()

        return ApiConnection.objects.with_ownership_permission_for(user=user).filter(id__in=qs)


smarter_restricted_admin_site.register(SqlConnection, SqlConnectionAdmin)
smarter_restricted_admin_site.register(ApiConnection, ApiConnectionAdmin)
