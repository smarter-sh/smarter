"""
The Django admin console of Smarter Extensions, for superusers only.

The Extensions page lists the installed extensions, with their versions, trust badges,
whether an update is available, and whether they are enabled. From it, a superuser can:

- **browse** the registry, read an extension's documentation, and install it;
- **upload** an extension archive (sideload it), which is badged ``Unverified``;
- **configure** an extension's settings, from a form generated from its ``pyproject.toml``;
- **enable** or **disable** it, **update** it, **roll back** to an earlier version, and
  **uninstall** it (the admin's delete).

Every action goes through :class:`~.installer.ExtensionInstaller`, so the admin validates,
runs lifecycle hooks and manages resources exactly as the management commands do.
"""

from typing import Optional

from django import forms
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.dashboard.admin import SmarterSuperUserOnlyModelAdmin
from smarter.apps.llmtool.models import (
    Extension,
    ExtensionResource,
    ExtensionSetting,
    ExtensionVersion,
)
from smarter.apps.secret.models import Secret
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from . import registry
from .docs import render_rst
from .exceptions import SmarterExtensionException
from .installer import ExtensionInstaller, SettingInput
from .loader import load_version
from .manifest import ExtensionManifest, ExtensionSettingSpec, ExtensionSettingType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])

TEMPLATES = "admin/llmtool/extension/"
FAILED = object()
"""What :meth:`ExtensionAdmin.run` returns when the function it runs fails."""
BADGE_COLORS = {"official": "#0b6e4f", "verified": "#1f5fbf", "community": "#6c757d", "unverified": "#b8860b"}


def badge_html(badge: str, label: str) -> str:
    """Return a trust badge as a small colored label."""
    return format_html(
        '<span style="background:{};color:#fff;border-radius:4px;padding:1px 6px;font-size:11px;white-space:nowrap">{}</span>',
        BADGE_COLORS.get(badge, "#6c757d"),
        label,
    )


def secret_name(slug: str, setting: str) -> str:
    """Return the name of the Secret that the admin creates for a secret setting's typed value."""
    return f"extension_{slug.replace('-', '_')}_{setting}"


class ExtensionUploadForm(forms.Form):
    """Upload an extension archive."""

    archive = forms.FileField(help_text="The extension's .zip archive, e.g. weather-1.0.0.zip.")


class ExtensionSettingsForm(forms.Form):
    """
    The form of an extension's settings, generated from its ``pyproject.toml``.

    A secret setting has two fields: an existing Secret to use, or a new value, which is
    saved in a Secret owned by the platform's admin user.
    """

    def __init__(self, *args, manifest: ExtensionManifest, extension: Extension, **kwargs):
        super().__init__(*args, **kwargs)
        self.manifest = manifest
        self.extension = extension
        rows = {row.name: row for row in ExtensionSetting.objects.filter(extension=extension).select_related("secret")}
        for spec in manifest.smarter.settings:
            row = rows.get(spec.name)
            label = spec.name.replace("_", " ").capitalize()
            help_text = spec.description + (" (required)" if spec.required else "")
            if spec.type == ExtensionSettingType.SECRET:
                self.fields[spec.name] = forms.ModelChoiceField(
                    queryset=Secret.objects.filter(user_profile=smarter_cached_objects.smarter_admin_user_profile),
                    required=False,
                    initial=row.secret if row else None,
                    label=label,
                    help_text=help_text,
                )
                self.fields[f"{spec.name}__new"] = forms.CharField(
                    required=False,
                    widget=forms.PasswordInput(render_value=False),
                    label=f"{label}: new value",
                    help_text=f"Or type a value, to save it in the Secret {secret_name(manifest.slug, spec.name)}.",
                )
                continue
            initial = row.value if row and row.value != "" else spec.default
            if spec.type == ExtensionSettingType.BOOLEAN:
                field: forms.Field = forms.BooleanField(required=False)
            elif spec.type == ExtensionSettingType.CHOICE:
                field = forms.ChoiceField(choices=[("", "---")] + [(choice, choice) for choice in spec.choices or []])
            elif spec.type == ExtensionSettingType.INTEGER:
                field = forms.IntegerField()
            elif spec.type == ExtensionSettingType.FLOAT:
                field = forms.FloatField()
            elif spec.type == ExtensionSettingType.URL:
                field = forms.URLField(assume_scheme="https")
            else:
                field = forms.CharField()
            field.required = False
            field.initial = initial
            field.label = label
            field.help_text = help_text + (f" Default: {spec.default}" if spec.default is not None else "")
            self.fields[spec.name] = field

    def values(self) -> dict[str, SettingInput]:
        """Return the cleaned values, as :meth:`ExtensionInstaller.configure` takes them."""
        values: dict[str, SettingInput] = {}
        for spec in self.manifest.smarter.settings:
            if spec.type == ExtensionSettingType.SECRET:
                values[spec.name] = self.secret_value(spec)
                continue
            value = self.cleaned_data.get(spec.name)
            values[spec.name] = None if value in (None, "") else value
        return values

    def secret_value(self, spec: ExtensionSettingSpec) -> Optional[Secret]:
        """Return the Secret of a secret setting: a new one from a typed value, or the one selected."""
        new_value = self.cleaned_data.get(f"{spec.name}__new")
        if new_value:
            owner = smarter_cached_objects.smarter_admin_user_profile
            name = secret_name(self.manifest.slug, spec.name)
            secret = Secret.objects.filter(user_profile=owner, name=name).first() or Secret(
                user_profile=owner,
                name=name,
                description=f"The {spec.name} setting of the {self.manifest.slug} extension.",
            )
            secret.encrypted_value = Secret.encrypt(new_value)
            secret.save()
            return secret
        return self.cleaned_data.get(spec.name)


class ExtensionVersionInline(admin.TabularInline):
    """An extension's installed versions, read-only."""

    model = ExtensionVersion
    extra = 0
    can_delete = False
    fields = ("version", "sha256", "source_url", "installed_by", "created_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class ExtensionResourceInline(admin.TabularInline):
    """The SAM resources that an extension created, read-only."""

    model = ExtensionResource
    extra = 0
    can_delete = False
    fields = ("kind", "name", "user_profile", "version", "managed")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


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
    """The admin console of installed extensions."""

    change_list_template = TEMPLATES + "change_list.html"
    change_form_template = TEMPLATES + "change_form.html"
    inlines = (ExtensionVersionInline, ExtensionResourceInline)
    list_display = (
        "display_name",
        "slug",
        "installed",
        "update",
        "badge",
        "enabled",
        "source",
        "has_error",
    )
    list_filter = ("enabled", "trust_badge", "source", UpdateAvailableFilter)
    search_fields = ("slug", "display_name", "publisher", "description")
    actions = ("enable_selected", "disable_selected", "check_updates")
    fieldsets = (
        (None, {"fields": ("display_name", "slug", "description", "publisher", "badge", "source", "enabled", "error")}),
        ("Versions", {"fields": ("installed", "latest_version", "latest_checked_at")}),
        ("Availability", {"fields": ("all_accounts", "accounts")}),
        ("Tools and settings", {"fields": ("tools", "settings_summary", "switches")}),
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
        "tools",
        "settings_summary",
        "switches",
        "documentation",
    )
    filter_horizontal = ("accounts",)

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

    @admin.display(description="tools")
    def tools(self, obj: Extension) -> str:
        if obj.installed_version is None:
            return "-"
        try:
            loaded = load_version(obj.installed_version)
        except SmarterExtensionException as e:
            return format_html('<span style="color:#ba2121">{}</span>', e.message)
        return format_html_join(
            mark_safe("<br>"),  # nosec B308: a constant
            "<code>{}</code>: {}",
            ((tool.name, tool.tool_description()) for tool in loaded.tools.values()),
        )

    @admin.display(description="settings")
    def settings_summary(self, obj: Extension) -> str:
        if obj.installed_version is None:
            return "-"
        rows = {row.name: row for row in obj.settings.select_related("secret").all()}  # type: ignore[attr-defined]
        lines = []
        for spec in obj.installed_version.parsed_manifest.smarter.settings:
            row = rows.get(spec.name)
            if spec.type == ExtensionSettingType.SECRET:
                value = f"Secret {row.secret.name}" if row and row.secret else "not set"
            else:
                value = row.value if row and row.value != "" else f"default ({spec.default})"
            lines.append((spec.name, value, " (required)" if spec.required else ""))
        separator = mark_safe("<br>")  # nosec B308: a constant
        return format_html_join(separator, "<code>{}</code>: {}{}", lines) or "-"

    @admin.display(description="waffle switches")
    def switches(self, obj: Extension) -> str:
        if obj.installed_version is None:
            return "-"
        # pylint: disable=import-outside-toplevel
        from .protocol import switch_name

        names = [switch_name(obj.slug, spec.name) for spec in obj.installed_version.parsed_manifest.smarter.switches]
        return ", ".join(names) or "-"

    @admin.display(description="documentation")
    def documentation(self, obj: Extension) -> str:
        if obj.installed_version is None:
            return "-"
        # docs_html is rendered with raw html and file inclusion disabled: see .docs.
        return mark_safe(obj.installed_version.docs_html or "-")  # nosec B308 B703

    # -------------------------------------------------------------------------
    # permissions: extensions are installed by upload or from the registry, and uninstalled by delete
    # -------------------------------------------------------------------------
    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def delete_model(self, request: HttpRequest, obj: Extension) -> None:
        ExtensionInstaller(user=request.user).uninstall(obj)  # type: ignore[arg-type]

    def delete_queryset(self, request: HttpRequest, queryset) -> None:
        installer = ExtensionInstaller(user=request.user)  # type: ignore[arg-type]
        for extension in queryset:
            installer.uninstall(extension)

    # -------------------------------------------------------------------------
    # actions
    # -------------------------------------------------------------------------
    @admin.action(description="Enable the selected extensions")
    def enable_selected(self, request: HttpRequest, queryset) -> None:
        installer = ExtensionInstaller(user=request.user)  # type: ignore[arg-type]
        for extension in queryset:
            self.run(request, f"Enabled {extension.slug}.", installer.enable, extension)

    @admin.action(description="Disable the selected extensions")
    def disable_selected(self, request: HttpRequest, queryset) -> None:
        installer = ExtensionInstaller(user=request.user)  # type: ignore[arg-type]
        for extension in queryset:
            self.run(request, f"Disabled {extension.slug}.", installer.disable, extension)

    @admin.action(description="Check the registry for updates now")
    def check_updates(self, request: HttpRequest, queryset=None) -> None:
        updates = self.run(request, None, registry.check_for_updates, True)
        if updates is not FAILED:
            names = ", ".join(f"{extension.slug} {extension.latest_version}" for extension in updates)
            self.message_user(
                request, f"Updates are available: {names}." if updates else "Every extension is up to date."
            )

    def run(self, request: HttpRequest, success: Optional[str], function, *args):
        """Run an installer function, report its success or error as a message, and return its result, or FAILED."""
        try:
            result = function(*args)
        except SmarterExtensionException as e:
            self.message_user(request, e.message, level=messages.ERROR)
            return FAILED
        # a lifecycle hook is the extension's code, which can fail in any way at all.
        # pylint: disable=broad-exception-caught
        except Exception as e:
            logger.exception("%s.run() %s failed", self.formatted_class_name, getattr(function, "__name__", function))
            self.message_user(request, f"{type(e).__name__}: {e}", level=messages.ERROR)
            return FAILED
        if success:
            self.message_user(request, success)
        return result

    @property
    def formatted_class_name(self) -> str:
        """The class name, for logging."""
        return logging.formatted_text(f"{__name__}.{self.__class__.__name__}")

    # -------------------------------------------------------------------------
    # views
    # -------------------------------------------------------------------------
    def get_urls(self):
        view = self.admin_site.admin_view
        return [
            path("upload/", view(self.upload_view), name="llmtool_extension_upload"),
            path("browse/", view(self.browse_view), name="llmtool_extension_browse"),
            path("browse/<slug:slug>/", view(self.browse_detail_view), name="llmtool_extension_browse_detail"),
            path("install/<slug:slug>/", view(require_POST(self.install_view)), name="llmtool_extension_install"),
            path("check-updates/", view(require_POST(self.check_updates_view)), name="llmtool_extension_check_updates"),
            path("<int:pk>/configure/", view(self.configure_view), name="llmtool_extension_configure"),
            path("<int:pk>/enable/", view(require_POST(self.enable_view)), name="llmtool_extension_enable"),
            path("<int:pk>/disable/", view(require_POST(self.disable_view)), name="llmtool_extension_disable"),
            path("<int:pk>/update/", view(require_POST(self.update_view)), name="llmtool_extension_update"),
            path(
                "<int:pk>/rollback/<int:version_pk>/",
                view(require_POST(self.rollback_view)),
                name="llmtool_extension_rollback",
            ),
        ] + super().get_urls()

    def context(self, request: HttpRequest, title: str, **kwargs) -> dict:
        """Return the context of one of the custom views."""
        return {**self.admin_site.each_context(request), "opts": self.model._meta, "title": title, **kwargs}

    def change_url(self, extension: Extension) -> str:
        """Return the url of an extension's change page."""
        return reverse(f"{self.admin_site.name}:llmtool_extension_change", args=[extension.pk])

    def changelist_url(self) -> str:
        """Return the url of the Extensions page."""
        return reverse(f"{self.admin_site.name}:llmtool_extension_changelist")

    def forbidden(self, request: HttpRequest) -> bool:
        """Return whether the user may not change extensions."""
        return not self.has_change_permission(request)

    def upload_view(self, request: HttpRequest) -> HttpResponse:
        """Upload an extension archive, and install it."""
        if self.forbidden(request):
            return HttpResponseRedirect(self.changelist_url())
        form = ExtensionUploadForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            extension = self.run(
                request,
                None,
                ExtensionInstaller(user=request.user).install,  # type: ignore[arg-type]
                form.cleaned_data["archive"].read(),
            )
            if extension is not FAILED:
                self.message_user(
                    request,
                    f"Installed {extension.slug} {extension.installed_version.version}. "
                    "Configure its settings, then enable it.",
                )
                return HttpResponseRedirect(self.change_url(extension))
        return TemplateResponse(
            request, TEMPLATES + "upload.html", self.context(request, "Upload an extension", form=form)
        )

    def browse_view(self, request: HttpRequest) -> HttpResponse:
        """List the registry's extensions, with their badges and their state on this platform."""
        query = request.GET.get("q", "").strip().lower()
        badge = request.GET.get("badge", "")
        cards, error = [], None
        try:
            index = registry.get_index()
        except SmarterExtensionException as e:
            index, error = None, e.message
        if index is not None:
            installed = {
                extension.slug: extension for extension in Extension.objects.select_related("installed_version")
            }
            for entry in sorted(index.extensions, key=lambda item: item.display_name.lower()):
                publisher = index.publisher(entry.publisher)
                entry_badge = index.badge_of(entry)
                text = " ".join(
                    [entry.slug, entry.display_name, entry.description, publisher.name if publisher else ""]
                ).lower()
                if (query and query not in text) or (badge and badge != entry_badge):
                    continue
                cards.append(
                    {
                        "entry": entry,
                        "publisher": publisher,
                        "badge": badge_html(
                            entry_badge, dict(Extension._meta.get_field("trust_badge").choices)[entry_badge]
                        ),
                        "latest": entry.latest_compatible(),
                        "installed": installed.get(entry.slug),
                    }
                )
        return TemplateResponse(
            request,
            TEMPLATES + "browse.html",
            self.context(request, "Browse extensions", cards=cards, error=error, q=query, badge=badge),
        )

    def browse_detail_view(self, request: HttpRequest, slug: str) -> HttpResponse:
        """Show a registry extension's documentation and versions, before it is installed."""
        try:
            index = registry.get_index()
        except SmarterExtensionException as e:
            self.message_user(request, e.message, level=messages.ERROR)
            return HttpResponseRedirect(reverse(f"{self.admin_site.name}:llmtool_extension_browse"))
        entry = index.extension(slug)
        if entry is None:
            self.message_user(request, f"The registry has no extension {slug}.", level=messages.ERROR)
            return HttpResponseRedirect(reverse(f"{self.admin_site.name}:llmtool_extension_browse"))
        context = self.context(
            request,
            entry.display_name,
            entry=entry,
            publisher=index.publisher(entry.publisher),
            badge=badge_html(
                index.badge_of(entry), dict(Extension._meta.get_field("trust_badge").choices)[index.badge_of(entry)]
            ),
            latest=entry.latest_compatible(),
            versions=sorted(entry.versions, key=lambda version: version.sort_key(), reverse=True),
            installed=Extension.objects.filter(slug=slug).select_related("installed_version").first(),
            documentation=mark_safe(render_rst(entry.docs_rst)),  # nosec B308 B703
        )
        return TemplateResponse(request, TEMPLATES + "browse_detail.html", context)

    def install_view(self, request: HttpRequest, slug: str) -> HttpResponse:
        """Install, or update, an extension from the registry."""
        if self.forbidden(request):
            return HttpResponseRedirect(self.changelist_url())
        version = request.POST.get("version") or None
        extension = self.run(request, None, registry.install_from_registry, slug, version, request.user)
        if extension is FAILED:
            return HttpResponseRedirect(reverse(f"{self.admin_site.name}:llmtool_extension_browse_detail", args=[slug]))
        self.message_user(request, f"Installed {slug} {extension.installed_version.version}.")
        return HttpResponseRedirect(self.change_url(extension))

    def check_updates_view(self, request: HttpRequest) -> HttpResponse:
        """Check the registry for updates, from the Extensions page's button."""
        if not self.forbidden(request):
            self.check_updates(request)
        return HttpResponseRedirect(self.changelist_url())

    def configure_view(self, request: HttpRequest, pk: int) -> HttpResponse:
        """Edit an extension's settings."""
        extension = get_object_or_404(Extension.objects.select_related("installed_version"), pk=pk)
        if self.forbidden(request) or extension.installed_version is None:
            return HttpResponseRedirect(self.changelist_url())
        manifest = extension.installed_version.parsed_manifest
        form = ExtensionSettingsForm(request.POST or None, manifest=manifest, extension=extension)
        if request.method == "POST" and form.is_valid():
            installer = ExtensionInstaller(user=request.user)  # type: ignore[arg-type]
            result = self.run(
                request, f"Saved the settings of {extension.slug}.", installer.configure, extension, form.values()
            )
            if result is not FAILED:
                return HttpResponseRedirect(self.change_url(extension))
        return TemplateResponse(
            request,
            TEMPLATES + "configure.html",
            self.context(
                request, f"Configure {extension.display_name}", form=form, extension=extension, original=extension
            ),
        )

    def enable_view(self, request: HttpRequest, pk: int) -> HttpResponse:
        extension = get_object_or_404(Extension, pk=pk)
        if not self.forbidden(request):
            self.run(request, f"Enabled {extension.slug}.", ExtensionInstaller(user=request.user).enable, extension)  # type: ignore[arg-type]
        return HttpResponseRedirect(self.change_url(extension))

    def disable_view(self, request: HttpRequest, pk: int) -> HttpResponse:
        extension = get_object_or_404(Extension, pk=pk)
        if not self.forbidden(request):
            self.run(request, f"Disabled {extension.slug}.", ExtensionInstaller(user=request.user).disable, extension)  # type: ignore[arg-type]
        return HttpResponseRedirect(self.change_url(extension))

    def update_view(self, request: HttpRequest, pk: int) -> HttpResponse:
        """Update an extension to the registry's newest compatible version."""
        extension = get_object_or_404(Extension, pk=pk)
        if not self.forbidden(request):
            updated = self.run(request, None, registry.install_from_registry, extension.slug, None, request.user)
            if updated is not FAILED:
                self.message_user(request, f"Updated {extension.slug} to {updated.installed_version.version}.")
        return HttpResponseRedirect(self.change_url(extension))

    def rollback_view(self, request: HttpRequest, pk: int, version_pk: int) -> HttpResponse:
        """Make an earlier version of an extension the installed one."""
        extension = get_object_or_404(Extension, pk=pk)
        version = get_object_or_404(ExtensionVersion, pk=version_pk, extension=extension)
        if not self.forbidden(request):
            installer = ExtensionInstaller(user=request.user)  # type: ignore[arg-type]
            self.run(
                request, f"Rolled {extension.slug} back to {version.version}.", installer.rollback, extension, version
            )
        return HttpResponseRedirect(self.change_url(extension))

    def change_view(self, request: HttpRequest, object_id: str, form_url: str = "", extra_context=None):
        extension = Extension.objects.filter(pk=object_id).select_related("installed_version").first()
        extra_context = {
            **(extra_context or {}),
            "extension": extension,
            "other_versions": (
                ExtensionVersion.objects.filter(extension=extension).exclude(pk=extension.installed_version_id).defer("archive")  # type: ignore[union-attr]
                if extension
                else []
            ),
        }
        return super().change_view(request, object_id, form_url, extra_context)

    def changelist_view(self, request: HttpRequest, extra_context=None):
        extra_context = {**(extra_context or {}), "registry_enabled": registry.is_enabled()}
        return super().changelist_view(request, extra_context)


__all__ = ["ExtensionAdmin", "ExtensionSettingsForm", "ExtensionUploadForm"]
