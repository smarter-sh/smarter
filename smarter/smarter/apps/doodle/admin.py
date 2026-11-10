"""
Admin of the doodle app, for superusers.

A superuser can override a day's doodle: editing it, e.g. choosing another theme, marks it as
chosen by a person, and neither the planner nor the Smarter Doodle Editor changes it from then on.
The list's actions approve or reject doodles, e.g. those that the Smarter Doodle Artist drew, which
await approval, without taking the credit from the AI. The list links to the week's preview, a grid
of every region's doodle of every planned day, with the same approve and reject buttons on each. Themes are loaded from the catalog's files,
or drawn by the artist, so they are read-only here. The editor's runs are its audit trail: what it
was asked, what it answered, and which of its choices were refused.
"""

import datetime
from dataclasses import dataclass
from typing import Optional

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from smarter.apps.dashboard.admin import (
    SmarterSuperUserOnlyModelAdmin,
    smarter_restricted_admin_site,
)

from .caching import artwork_url, doodle_of_the_day
from .const import DEFAULT_THEME_SLUG
from .models import (
    Doodle,
    DoodleEditorRun,
    DoodleSource,
    DoodleStatus,
    DoodleTheme,
)
from .regions import DoodleRegion

TEMPLATES = "admin/doodle/doodle/"
"""The doodle admin's templates: the list, with its link to the week's preview, and the preview."""

PREVIEW_URL_NAME = "doodle_doodle_preview"
"""The url name of the week's preview, in the admin site's namespace."""


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


@dataclass(frozen=True)
class DoodlePreviewCell:
    """One region's doodle of one day, in the week's preview."""

    region: str
    doodle: Optional[Doodle]
    image_url: str = ""
    change_url: str = ""
    is_default: bool = False


@dataclass(frozen=True)
class DoodlePreviewDay:
    """One day of the week's preview: a cell for each region."""

    date: datetime.date
    cells: list[DoodlePreviewCell]


class DoodleAdmin(SmarterSuperUserOnlyModelAdmin):
    """The planned doodles.

    Saving one marks it as chosen by a person.
    """

    change_list_template = TEMPLATES + "change_list.html"
    list_display = ["date", "region", "theme", "status", "source", "title"]
    list_select_related = ["theme"]
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

    def get_urls(self):
        """
        Add the week's preview to the doodles' urls.

        :returns: The urls, with ``preview/`` first, so that it isn't read as a doodle's id.
        """
        preview = path("preview/", self.admin_site.admin_view(self.week_preview_view), name=PREVIEW_URL_NAME)
        urls = [preview] + super().get_urls()
        return urls

    def preview_url(self) -> str:
        """
        Return the url of the week's preview.

        :returns: Its path, in this admin site.
        :rtype: str
        """
        url = reverse(f"{self.admin_site.name}:{PREVIEW_URL_NAME}")
        return url

    def changelist_view(self, request: HttpRequest, extra_context=None) -> HttpResponse:
        """
        Show the doodles, with a link to the week's preview.

        :param request: The admin request.
        :param extra_context: More context for the template.
        :returns: The list.
        :rtype: HttpResponse
        """
        context = dict(extra_context or {})
        context["preview_url"] = self.preview_url()
        response = super().changelist_view(request, extra_context=context)
        return response

    def preview_days(self, first: datetime.date) -> list[DoodlePreviewDay]:
        """
        Return the planned doodles from a day on, as a grid of days and regions.

        :param first: The first day.
        :returns: One row per planned day, with a cell for each region, in the regions' order.
        :rtype: list[DoodlePreviewDay]
        """
        doodles = Doodle.objects.filter(date__gte=first).select_related("theme", "artwork")
        # the cells link to each artwork by its hash: the SVG text isn't needed.
        doodles = doodles.defer("theme__props_svg", "artwork__svg").order_by("date")
        by_day: dict[datetime.date, dict[str, Doodle]] = {}
        for row in doodles:
            by_day.setdefault(row.date, {})[row.region] = row

        days = []
        for date, doodles_of_day in by_day.items():
            cells = []
            for region in DoodleRegion.values:
                doodle = doodles_of_day.get(region)
                if doodle is None:
                    cells.append(DoodlePreviewCell(region=region, doodle=None))
                    continue
                change_url = reverse(f"{self.admin_site.name}:doodle_doodle_change", args=[doodle.pk])
                cell = DoodlePreviewCell(
                    region=region,
                    doodle=doodle,
                    image_url=artwork_url(doodle.artwork.sha256),
                    change_url=change_url,
                    is_default=doodle.theme.slug == DEFAULT_THEME_SLUG,
                )
                cells.append(cell)
            days.append(DoodlePreviewDay(date=date, cells=cells))
        return days

    def week_preview_view(self, request: HttpRequest) -> HttpResponse:
        """
        Show every region's doodle of every planned day, and approve or reject them.

        A ``POST`` with a doodle's ``doodle_id`` and an ``action``, ``approve`` or ``reject``,
        changes its status, as the list's actions do, then shows the preview again.

        :param request: The admin request.
        :returns: The preview, or a redirect to it after a change.
        :rtype: HttpResponse
        :raises PermissionDenied: If the user may not view the doodles, or change one.
        """
        if not self.has_view_permission(request):
            raise PermissionDenied

        if request.method == "POST":
            if not self.has_change_permission(request):
                raise PermissionDenied
            action = request.POST.get("action")
            statuses = {"approve": DoodleStatus.APPROVED, "reject": DoodleStatus.REJECTED}
            status = statuses.get(str(action))
            doodle_id = request.POST.get("doodle_id")
            doodles = Doodle.objects.filter(pk=doodle_id) if doodle_id else Doodle.objects.none()
            doodle = doodles.first()
            if status is None or doodle is None:
                messages.error(request, "Choose a doodle, and approve or reject it.")
            else:
                set_status(doodles, status)
                messages.success(request, f"The doodle of {doodle.date} in {doodle.region} is {status}.")
            return HttpResponseRedirect(self.preview_url())

        # yesterday in UTC is still today west of UTC, as the planner's window starts.
        first = timezone.now().date() - datetime.timedelta(days=1)
        context = {
            **self.admin_site.each_context(request),
            "title": "Doodles of the week",
            # the grid needs the width of the page: twelve regions.
            "is_nav_sidebar_enabled": False,
            "opts": self.model._meta,
            "days": self.preview_days(first),
            "regions": DoodleRegion.choices,
            "changelist_url": reverse(f"{self.admin_site.name}:doodle_doodle_changelist"),
        }
        response = TemplateResponse(request, TEMPLATES + "preview.html", context)
        return response

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

    list_display = ["created_at", "date", "status", "with_trends"]
    list_filter = ["status", "with_trends"]
    readonly_fields = ["date", "status", "with_trends", "request", "response", "error", "created_at", "updated_at"]

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
