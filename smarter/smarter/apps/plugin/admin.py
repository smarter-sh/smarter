# -*- coding: utf-8 -*-
"""Plugin admin."""
from django.contrib import admin

from .models import Plugin, PluginData, PluginPrompt, PluginSelector


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

    model = PluginData
    extra = 0  # This will not show extra empty forms


class PluginAdmin(admin.ModelAdmin):
    """Plugin model admin."""

    inlines = [PluginSelectorInline, PluginPromptInline, PluginDataInline]

    readonly_fields = (
        "created_at",
        "updated_at",
    )


admin.site.register(Plugin, PluginAdmin)
