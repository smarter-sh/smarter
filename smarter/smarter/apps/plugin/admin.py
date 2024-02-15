# -*- coding: utf-8 -*-
"""Plugin admin."""
from django.contrib import admin

from .models import (
    Plugin,
    PluginFunction,
    PluginPrompt,
    PluginSelector,
    PluginSelectorSearchStrings,
)


# Register your models here.
class PluginSelectorSearchStringsInline(admin.TabularInline):
    """Inline form for Plugin"""

    model = PluginSelectorSearchStrings
    extra = 0  # This will not show extra empty forms


class PluginSelectorInline(admin.StackedInline):
    """Inline form for Plugin"""

    model = PluginSelector
    extra = 0  # This will not show extra empty forms
    inlines = [PluginSelectorSearchStringsInline]


class PluginSelectorAdmin(admin.ModelAdmin):
    """Multi-part form for PluginSelector"""

    inlines = [PluginSelectorSearchStringsInline]


class PluginPromptInline(admin.StackedInline):
    """Inline form for Plugin"""

    model = PluginPrompt
    extra = 0  # This will not show extra empty forms


class PluginFunctionInline(admin.StackedInline):
    """Inline form for Plugin"""

    model = PluginFunction
    extra = 0  # This will not show extra empty forms


class PluginAdmin(admin.ModelAdmin):
    """Plugin model admin."""

    inlines = [PluginSelectorInline, PluginPromptInline, PluginFunctionInline]

    readonly_fields = (
        "created_at",
        "updated_at",
    )


admin.site.register(Plugin, PluginAdmin)
admin.site.register(PluginSelector, PluginSelectorAdmin)
