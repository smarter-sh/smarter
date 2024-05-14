# pylint: disable=C0114,C0115
"""Plugin admin."""
import re

from django.contrib import admin

from .models import PluginDataStatic, PluginMeta, PluginPrompt, PluginSelector


# Register your models here.
class PluginSelectorInline(admin.StackedInline):
    """Inline form for Plugin"""

    model = PluginSelector
    extra = 0  # This will not show extra empty forms


class PluginPromptInline(admin.StackedInline):
    """Inline form for Plugin"""

    model = PluginPrompt
    extra = 0  # This will not show extra empty forms


class PluginDataInline(admin.StackedInline):
    """Inline form for Plugin"""

    model = PluginDataStatic
    extra = 0  # This will not show extra empty forms

    class Meta:
        verbose_name = "Plugin Data"
        verbose_name_plural = "Plugin Data"


class PluginAdmin(admin.ModelAdmin):
    """Plugin model admin."""

    def author_company_name(self, obj):
        return obj.author

    def plugin_name(self, obj):
        name = obj.name
        formatted_name = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
        return formatted_name

    author_company_name.short_description = "Account-User"

    inlines = [PluginSelectorInline, PluginPromptInline, PluginDataInline]

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("id", "author_company_name", "plugin_name", "version", "created_at", "updated_at")


admin.site.register(PluginMeta, PluginAdmin)
