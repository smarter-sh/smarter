# pylint: disable=C0114,C0115
"""Plugin admin."""
import re

from django.contrib import admin

from smarter.apps.account.models import UserProfile

from .models import (
    PluginDataSqlConnection,
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)


# Register your models here.
class PluginSelectorInline(admin.StackedInline):
    """Inline form for Plugin"""

    model = PluginSelector
    extra = 0  # This will not show extra empty forms

    # pylint: disable=W0212
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


class PluginPromptInline(admin.StackedInline):
    """Inline form for Plugin"""

    model = PluginPrompt
    extra = 0  # This will not show extra empty forms

    # pylint: disable=W0212
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


class PluginDataInline(admin.StackedInline):
    """Inline form for Plugin"""

    model = PluginDataStatic
    extra = 0  # This will not show extra empty forms

    class Meta:
        verbose_name = "Plugin Data"
        verbose_name_plural = "Plugin Data"

    # pylint: disable=W0212
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


class PluginAdmin(admin.ModelAdmin):
    """Plugin model admin."""

    def plugin_name(self, obj):
        name = obj.name
        formatted_name = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
        return formatted_name

    inlines = [PluginSelectorInline, PluginPromptInline, PluginDataInline]

    # pylint: disable=W0212
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    list_display = ("id", "author", "plugin_name", "version", "created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class PluginDataSqlConnectionAdmin(admin.ModelAdmin):
    """Plugin Data SQL Connection model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = (
        "created_at",
        "account",
        "name",
        "db_engine",
        "hostname",
        "database",
        "username",
        "updated_at",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


admin.site.register(PluginMeta, PluginAdmin)
admin.site.register(PluginDataSqlConnection, PluginDataSqlConnectionAdmin)
