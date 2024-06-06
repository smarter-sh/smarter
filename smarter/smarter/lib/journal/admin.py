"""Account admin."""

from django.contrib import admin

from .models import SAMJournal


# Register your models here.
class SAMJournalAdmin(admin.ModelAdmin):
    """SAMJournal model admin."""

    readonly_fields = ("created_at",)
    list_display = ("created_at", "user", "thing", "command", "status_code")
    raw_id_fields = ("user",)


admin.site.register(SAMJournal, SAMJournalAdmin)
