# -*- coding: utf-8 -*-
"""Plugin admin."""
from django.contrib import admin

from .models import PluginModel


# Register your models here.
class PluginModelAdmin(admin.ModelAdmin):
    """Plugin model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )


admin.site.register(PluginModel, PluginModelAdmin)
