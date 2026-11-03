"""Account admin."""

from django.contrib import admin

from smarter.apps.dashboard.admin import (
    SmarterStaffOnlyModelAdmin,
    smarter_restricted_admin_site,
)
from smarter.lib.journal.models import SAMJournal


# Register your models here.
class SAMJournalAdmin(SmarterStaffOnlyModelAdmin):
    """SAMJournal model admin."""

    readonly_fields = ("created_at",)
    list_display = ("created_at", "user", "thing_display", "command_display", "status_code")
    raw_id_fields = ("user",)
    ordering = ("-created_at",)

    @admin.display(description="Thing", ordering="thing")
    def thing_display(self, obj):
        """
        Return the entry's thing, as its display label.

        :param obj: The journal entry.
        """
        return obj.get_thing_display()

    @admin.display(description="Command", ordering="command")
    def command_display(self, obj):
        """
        Return the entry's command, as its display label.

        :param obj: The journal entry.
        """
        return obj.get_command_display()


smarter_restricted_admin_site.register(SAMJournal, SAMJournalAdmin)
