"""
Admin of the doodle app, for superusers.

A superuser can override a day's doodle: editing it, e.g. choosing another theme, marks it as
chosen by a person, and neither the planner nor the Smarter Doodle Editor changes it from then on.
The list's actions approve or reject doodles, e.g. those that the Smarter Doodle Artist drew, which
await approval, without taking the credit from the AI. Themes are loaded from the catalog's files,
or drawn by the artist, so they are read-only here. The editor's runs are its audit trail: what it
was asked, what it answered, and which of its choices were refused.
"""

from django.contrib import admin
from django.utils.html import format_html

from smarter.apps.dashboard.admin import (
    SmarterSuperUserOnlyModelAdmin,
    smarter_restricted_admin_site,
)

from .caching import artwork_url, doodle_of_the_day
from .models import (
    Doodle,
    DoodleEditorRun,
    DoodleSource,
    DoodleStatus,
    DoodleTheme,
)


def set_status(queryset, status: str) -> int:
    """
    Set the status of doodles, and forget their cached doodle of the day.

    :param queryset: The doodles.
    :param status: The new status.
    :returns: The number of doodles changed.
    :rtype: int
    """
    changed = 0
    for doodle in queryset:
        doodle.status = status
        doodle.save(update_fields=["status", "updated_at"])
        doodle_of_the_day.invalidate(doodle.date.isoformat(), doodle.region)
        changed += 1
    return changed


class DoodleAdmin(SmarterSuperUserOnlyModelAdmin):
    """The planned doodles.

    Saving one marks it as chosen by a person.
    """

    list_display = ["date", "region", "theme", "status", "source", "title"]
    list_filter = ["region", "status", "source", "theme"]
    search_fields = ["title", "caption", "theme__slug"]
    readonly_fields = ["artwork", "source", "reason", "preview", "created_at", "updated_at"]
    date_hierarchy = "date"
    actions = ["approve", "reject"]

    @admin.action(description="Approve the selected doodles")
    def approve(self, request, queryset) -> None:
        """
        Approve doodles, so that visitors see them.

        :param request: The admin request.
        :param queryset: The doodles.
        """
        changed = set_status(queryset, DoodleStatus.APPROVED)
        self.message_user(request, f"Approved {changed} doodles.")

    @admin.action(description="Reject the selected doodles")
    def reject(self, request, queryset) -> None:
        """
        Reject doodles, so that visitors see the calendar's choice instead.

        :param request: The admin request.
        :param queryset: The doodles.
        """
        changed = set_status(queryset, DoodleStatus.REJECTED)
        self.message_user(request, f"Rejected {changed} doodles.")

    @staticmethod
    def preview(obj: Doodle) -> str:
        """
        Show the doodle's artwork.

        :param obj: The doodle.
        :returns: An ``<img>`` of its artwork.
        :rtype: str
        """
        url = artwork_url(obj.artwork.sha256)
        html = format_html('<img src="{}" alt="{}" style="width: 520px; background: #241a4f;">', url, obj.alt_text)
        return html

    def save_model(self, request, obj: Doodle, form, change) -> None:
        """
        Save a doodle that a person changed, with its theme's artwork.

        :param request: The admin request.
        :param obj: The doodle.
        :param form: The form.
        :param change: Whether it is a change of an existing doodle.
        """
        obj.source = DoodleSource.HUMAN
        if "theme" in form.changed_data:
            obj.artwork = obj.theme.artwork
            obj.title = obj.theme.name
            obj.caption = obj.theme.caption
            obj.alt_text = obj.theme.alt_text
            obj.link_url = obj.theme.link_url
        obj.reason = f"Chosen by {request.user.username} in the admin."
        super().save_model(request, obj, form, change)


class DoodleThemeAdmin(SmarterSuperUserOnlyModelAdmin):
    """The theme catalog, loaded from its files by manage.py load_doodle_themes."""

    list_display = ["slug", "name", "category", "priority", "is_active", "is_generated"]
    list_filter = ["category", "is_active", "is_generated"]
    search_fields = ["slug", "name"]

    def has_add_permission(self, request, obj=None) -> bool:
        """
        Never add a theme here: add its file to the catalog.

        :param request: The admin request.
        :param obj: The object, if any.
        :returns: False.
        """
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """
        Never change a theme here: change its file in the catalog.

        :param request: The admin request.
        :param obj: The object, if any.
        :returns: False.
        """
        return False


class DoodleEditorRunAdmin(SmarterSuperUserOnlyModelAdmin):
    """The Smarter Doodle Editor's runs, read-only: its audit trail."""

    list_display = ["created_at", "date", "status"]
    list_filter = ["status"]
    readonly_fields = ["date", "status", "request", "response", "error", "created_at", "updated_at"]

    def has_add_permission(self, request, obj=None) -> bool:
        """
        Never add a run here: the planner records them.

        :param request: The admin request.
        :param obj: The object, if any.
        :returns: False.
        """
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """
        Never change a run: it is a record.

        :param request: The admin request.
        :param obj: The object, if any.
        :returns: False.
        """
        return False


smarter_restricted_admin_site.register(Doodle, DoodleAdmin)
smarter_restricted_admin_site.register(DoodleEditorRun, DoodleEditorRunAdmin)
smarter_restricted_admin_site.register(DoodleTheme, DoodleThemeAdmin)
