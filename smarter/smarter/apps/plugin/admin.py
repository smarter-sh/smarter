# pylint: disable=C0114,C0115
"""Plugin admin."""
import re

from django.contrib import admin

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_account_for_user
from smarter.apps.dashboard.admin import (
    RestrictedModelAdmin,
    smarter_restricted_admin_site,
)

from .models import (
    ApiConnection,
    PluginDataApi,
    PluginDataSql,
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
    PluginSelectorHistory,
    SqlConnection,
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


class PluginDataApiInline(admin.StackedInline):
    """Inline form for Plugin"""

    model = PluginDataApi
    extra = 0  # This will not show extra empty forms

    class Meta:
        verbose_name = "ApiPlugin Data"
        verbose_name_plural = "ApiPlugin Data"

    # pylint: disable=W0212
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


class PluginDataSqlInline(admin.StackedInline):
    """Inline form for Plugin"""

    model = PluginDataSql
    extra = 0  # This will not show extra empty forms

    class Meta:
        verbose_name = "SqlPlugin Data"
        verbose_name_plural = "SqlPlugin Data"

    # pylint: disable=W0212
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


class PluginStaticAdmin(RestrictedModelAdmin):
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
            return qs.filter(plugin_class="static").distinct()
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(account=account, plugin_class="static").distinct()
        except UserProfile.DoesNotExist:
            return qs.none()


class PluginApiAdmin(RestrictedModelAdmin):
    """Plugin model admin."""

    model = PluginMeta

    def plugin_name(self, obj):
        name = obj.name
        formatted_name = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
        return formatted_name

    inlines = [PluginSelectorInline, PluginPromptInline, PluginDataApiInline]

    # pylint: disable=W0212
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    list_display = ("id", "author", "plugin_name", "version", "created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs.filter(plugin_class="api").distinct()
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(account=account, plugin_class="api").distinct()
        except UserProfile.DoesNotExist:
            return qs.none()


class PluginSqlAdmin(RestrictedModelAdmin):
    """Plugin model admin."""

    model = PluginMeta

    def plugin_name(self, obj):
        name = obj.name
        formatted_name = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
        return formatted_name

    inlines = [PluginSelectorInline, PluginPromptInline, PluginDataSqlInline]

    # pylint: disable=W0212
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    list_display = ("id", "author", "plugin_name", "version", "created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs.filter(plugin_class="sql").distinct()
        try:
            account = get_cached_account_for_user(user=request.user)
            return qs.filter(account=account, plugin_class="sql").distinct()
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


class SqlConnectionAdmin(RestrictedModelAdmin):
    """PluginDataSql Connection model admin."""

    model = SqlConnection

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


class ApiConnectionAdmin(RestrictedModelAdmin):
    """PluginDataApi Connection model admin."""

    model = ApiConnection

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = (
        "created_at",
        "account",
        "name",
        "base_url",
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


# Plugin Models
class PluginMetaStatic(PluginMeta):
    class Meta:
        proxy = True
        verbose_name = "Plugin Meta (Static)"
        verbose_name_plural = "Plugin Meta (Static)"


class PluginMetaApi(PluginMeta):
    class Meta:
        proxy = True
        verbose_name = "Plugin Meta (API)"
        verbose_name_plural = "Plugin Meta (API)"


class PluginMetaSql(PluginMeta):
    class Meta:
        proxy = True
        verbose_name = "Plugin Meta (SQL)"
        verbose_name_plural = "Plugin Meta (SQL)"


smarter_restricted_admin_site.register(PluginMetaStatic, PluginStaticAdmin)
smarter_restricted_admin_site.register(PluginMetaApi, PluginApiAdmin)
smarter_restricted_admin_site.register(PluginMetaSql, PluginSqlAdmin)
smarter_restricted_admin_site.register(SqlConnection, SqlConnectionAdmin)
smarter_restricted_admin_site.register(PluginSelectorHistory, PluginSelectionHistoryAdmin)
smarter_restricted_admin_site.register(ApiConnection, ApiConnectionAdmin)
