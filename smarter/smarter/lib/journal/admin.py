"""Account admin."""

from smarter.lib.django.admin import RestrictedModelAdmin


# Register your models here.
class SAMJournalAdmin(RestrictedModelAdmin):
    """SAMJournal model admin."""

    readonly_fields = ("created_at",)
    list_display = ("created_at", "user", "thing", "command", "status_code")
    raw_id_fields = ("user",)
