"""Account admin."""

from django.contrib import admin

from .models import SmarterAuthToken


# Register your models here.
class SmarterAuthTokenAdmin(admin.ModelAdmin):
    """Account model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = "__all__"


admin.site.register(SmarterAuthToken, SmarterAuthTokenAdmin)
