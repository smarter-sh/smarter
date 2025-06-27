"""Account admin."""

from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.lib.django.admin import RestrictedModelAdmin
from smarter.lib.journal.models import SAMJournal


# Register your models here.
class SAMJournalAdmin(RestrictedModelAdmin):
    """SAMJournal model admin."""

    readonly_fields = ("created_at",)
    list_display = ("created_at", "user", "thing_display", "command_display", "status_code")
    raw_id_fields = ("user",)
    ordering = ("-created_at",)

    def thing_display(self, obj):
        return obj.get_thing_display()

    thing_display.admin_order_field = "thing"
    thing_display.short_description = "Thing"

    def command_display(self, obj):
        return obj.get_command_display()

    command_display.admin_order_field = "command"
    command_display.short_description = "Command"


smarter_restricted_admin_site.register(SAMJournal, SAMJournalAdmin)
