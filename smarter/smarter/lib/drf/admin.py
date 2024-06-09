"""SmarterAuthToken admin."""

from smarter.lib.django.admin import RestrictedModelAdmin


# Register your models here.
class SmarterAuthTokenAdmin(RestrictedModelAdmin):
    """SmarterAuthToken model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.list_display = [field.name for field in model._meta.fields]
