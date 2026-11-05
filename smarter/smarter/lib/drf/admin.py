"""The Django admin of API keys, SmarterAuthToken, on Smarter's restricted admin site."""

from smarter.apps.dashboard.admin import (
    SmarterStaffOnlyModelAdmin,
    smarter_restricted_admin_site,
)

from .models import SmarterAuthToken


# Register your models here.
class SmarterAuthTokenAdmin(SmarterStaffOnlyModelAdmin):
    """
    Staff-only Django admin of SmarterAuthToken.

    Its list shows every model field: ``__init__()`` replaces ``list_display``.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "CLI API Keys"

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = (
        "created_at",
        "account",
        "name",
        "description",
        "last_used_at",
        "is_active",
        "expiry",
    )

    def __init__(self, model, admin_site):
        """
        Initialize the admin, listing every field of the model.

        :param model: The SmarterAuthToken model.
        :param admin_site: The admin site.
        """
        super().__init__(model, admin_site)
        self.list_display = [field.name for field in model._meta.fields]


smarter_restricted_admin_site.register(SmarterAuthToken, SmarterAuthTokenAdmin)
