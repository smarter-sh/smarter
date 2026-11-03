"""
Admin of the doodle app, for superusers.

A superuser can override a day's doodle: choosing another theme, or approving or rejecting it,
marks it as chosen by a person, and the planner leaves it alone from then on. Themes are loaded
from the catalog's files, so they are read-only here; artworks are their SVGs.
"""

from django.utils.html import format_html

from smarter.apps.dashboard.admin import (
    SmarterSuperUserOnlyModelAdmin,
    smarter_restricted_admin_site,
)

from .caching import artwork_url
from .models import Doodle, DoodleSource, DoodleTheme


class DoodleAdmin(SmarterSuperUserOnlyModelAdmin):
    """The planned doodles.

    Saving one marks it as chosen by a person.
    """

    list_display = ["date", "region", "theme", "status", "source", "title"]
    list_filter = ["region", "status", "source", "theme"]
    search_fields = ["title", "caption", "theme__slug"]
    readonly_fields = ["artwork", "source", "reason", "preview", "created_at", "updated_at"]
    date_hierarchy = "date"

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

    list_display = ["slug", "name", "category", "priority", "is_active"]
    list_filter = ["category", "is_active"]
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


smarter_restricted_admin_site.register(Doodle, DoodleAdmin)
smarter_restricted_admin_site.register(DoodleTheme, DoodleThemeAdmin)
