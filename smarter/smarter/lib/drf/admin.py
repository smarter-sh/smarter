"""SmarterAuthToken admin."""

from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.lib.django.admin import RestrictedModelAdmin
from smarter.lib.drf.models import SmarterAuthToken


# Register your models here.
class SmarterAuthTokenAdmin(RestrictedModelAdmin):
    """SmarterAuthToken model admin."""

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
        super().__init__(model, admin_site)
        self.list_display = [field.name for field in model._meta.fields]


smarter_restricted_admin_site.register(SmarterAuthToken, SmarterAuthTokenAdmin)
