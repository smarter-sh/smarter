"""
The Django admin console of Smarter Extensions: a read-only view, for superusers only.

Extensions are managed in the web console's Extensions pages, at ``/extensions/``
(:mod:`smarter.apps.llmtool.extension.views`): browsing the registry, installing,
uploading, configuring, enabling, updating, rolling back and uninstalling. The admin
lists the installed extensions, with their versions, trust badges and resources, and
links each one to its page in the console.
"""

from django.contrib import admin
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from smarter.apps.dashboard.admin import SmarterSuperUserOnlyModelAdmin
from smarter.apps.llmtool.models import Extension, ExtensionResource, ExtensionVersion

from .views import detail_url, list_url

TEMPLATES = "admin/llmtool/extension/"
BADGE_COLORS = {"official": "#0b6e4f", "verified": "#1f5fbf", "community": "#6c757d", "unverified": "#b8860b"}


def badge_html(badge: str, label: str) -> str:
    """Return a trust badge as a small colored label."""
    return format_html(
        '<span style="background:{};color:#fff;border-radius:4px;padding:1px 6px;font-size:11px;white-space:nowrap">{}</span>',
        BADGE_COLORS.get(badge, "#6c757d"),
        label,
    )


class ReadOnlyInline(admin.TabularInline):
    """An inline that can't be added to, changed or deleted."""

    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ExtensionVersionInline(ReadOnlyInline):
    """An extension's installed versions."""

    model = ExtensionVersion
    fields = ("version", "sha256", "source_url", "installed_by", "created_at")
    readonly_fields = fields


class ExtensionResourceInline(ReadOnlyInline):
    """The SAM resources that an extension created."""

    model = ExtensionResource
    fields = ("kind", "name", "user_profile", "version", "managed")
    readonly_fields = fields


class UpdateAvailableFilter(admin.SimpleListFilter):
    """Filter extensions by whether the registry offers an update."""

    title = "update available"
    parameter_name = "update_available"

    def lookups(self, request, model_admin):
        return (("yes", "Yes"),)

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(pk__in=[extension.pk for extension in queryset if extension.update_available])
        return queryset


class ExtensionAdmin(SmarterSuperUserOnlyModelAdmin):
    """The installed extensions, read-only, each linked to its page in the web console."""

    change_list_template = TEMPLATES + "change_list.html"
    change_form_template = TEMPLATES + "change_form.html"
    inlines = (ExtensionVersionInline, ExtensionResourceInline)
    list_display = ("display_name", "slug", "installed", "update", "badge", "enabled", "source", "has_error", "manage")
    list_filter = ("enabled", "trust_badge", "source", UpdateAvailableFilter)
    search_fields = ("slug", "display_name", "publisher", "description")
    actions = None
    fieldsets = (
        (None, {"fields": ("display_name", "slug", "description", "publisher", "badge", "source", "enabled", "error")}),
        ("Versions", {"fields": ("installed", "latest_version", "latest_checked_at")}),
        ("Availability", {"fields": ("all_accounts", "accounts")}),
        ("Documentation", {"fields": ("documentation",)}),
    )
    readonly_fields = (
        "display_name",
        "slug",
        "description",
        "publisher",
        "badge",
        "source",
        "enabled",
        "error",
        "installed",
        "latest_version",
        "latest_checked_at",
        "all_accounts",
        "accounts",
        "documentation",
    )

    # -------------------------------------------------------------------------
    # columns and read-only fields
    # -------------------------------------------------------------------------
    @admin.display(description="installed")
    def installed(self, obj: Extension) -> str:
        return obj.installed_version.version if obj.installed_version else "-"

    @admin.display(description="update")
    def update(self, obj: Extension) -> str:
        if obj.update_available:
            return format_html('<strong style="color:#b8860b">{} available</strong>', obj.latest_version)
        return "-"

    @admin.display(description="trust", ordering="trust_badge")
    def badge(self, obj: Extension) -> str:
        return badge_html(obj.trust_badge, obj.get_trust_badge_display())  # type: ignore[attr-defined]

    @admin.display(description="error", boolean=True)
    def has_error(self, obj: Extension) -> bool:
        return bool(obj.error)

    @admin.display(description="console")
    def manage(self, obj: Extension) -> str:
        return format_html('<a href="{}">Manage</a>', detail_url(obj.slug))

    @admin.display(description="documentation")
    def documentation(self, obj: Extension) -> str:
        if obj.installed_version is None:
            return "-"
        # docs_html is rendered with raw html and file inclusion disabled: see .docs.
        return mark_safe(obj.installed_version.docs_html or "-")  # nosec B308 B703

    # -------------------------------------------------------------------------
    # permissions: extensions are managed in the web console
    # -------------------------------------------------------------------------
    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def change_view(self, request: HttpRequest, object_id: str, form_url: str = "", extra_context=None):
        extension = Extension.objects.filter(pk=object_id).first()
        extra_context = {**(extra_context or {}), "console_url": detail_url(extension.slug) if extension else None}
        return super().change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request: HttpRequest, extra_context=None):
        extra_context = {**(extra_context or {}), "console_url": list_url()}
        return super().changelist_view(request, extra_context)


__all__ = ["ExtensionAdmin"]
