# pylint: disable=C0114,C0115
"""Plugin admin."""
import re

from django.contrib import admin

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_account_for_user
from smarter.lib.django.admin import RestrictedModelAdmin

from .models import (
    PluginDataApi,
    PluginDataApiConnection,
    PluginDataSql,
    PluginDataSqlConnection,
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
    PluginSelectorHistory,
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


class PluginAdmin(RestrictedModelAdmin):
    """Plugin model admin."""

    model = PluginMeta

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
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class PluginSelectionHistoryAdmin(RestrictedModelAdmin):
    """
    Plugin Selection History model admin.
    """

    model = PluginSelectorHistory

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = (
        "created_at",
        "updated_at",
        "plugin_selector",
        "search_term",
        "session_key",
        "messages",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            plugins = PluginSelector.objects.filter(plugin__account=account)
            return qs.filter(plugin_selector__in=plugins)
        except UserProfile.DoesNotExist:
            return qs.none()


class PluginDataSqlConnectionAdmin(RestrictedModelAdmin):
    """Plugin Data SQL Connection model admin."""

    model = PluginDataApiConnection

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
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class PluginDataApiConnectionAdmin(RestrictedModelAdmin):
    """Plugin Data API Connection model admin."""

    model = PluginDataApiConnection

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = (
        "created_at",
        "account",
        "name",
        "root_domain",
        "api_key",
        "updated_at",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class PluginDataApiAdmin(RestrictedModelAdmin):
    """Plugin Data API model admin."""

    model = PluginDataApi

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = (
        "created_at",
        "account",
        "name",
        "root_domain",
        "url",
        "updated_at",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(account=account)
        except UserProfile.DoesNotExist:
            return qs.none()


class PluginDataSqlAdmin(RestrictedModelAdmin):
    """Plugin Data SQL model admin."""

    model = PluginDataSql

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = (
        "created_at",
        "account",
        "name",
        "connection",
        "updated_at",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(account=account)
        except UserProfile.DoesNotExist:
            return qs.none()
