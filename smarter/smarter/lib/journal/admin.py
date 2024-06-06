"""Account admin."""

from django.contrib import admin

from smarter.lib.django.admin import RestrictedModelAdmin

from .models import SAMJournal


# Register your models here.
class SAMJournalAdmin(RestrictedModelAdmin):
    """SAMJournal model admin."""

    readonly_fields = ("created_at",)
    list_display = ("created_at", "user", "thing", "command", "status_code")
    raw_id_fields = ("user",)


admin.site.register(SAMJournal, SAMJournalAdmin)
