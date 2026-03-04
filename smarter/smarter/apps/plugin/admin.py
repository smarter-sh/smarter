# pylint: disable=C0114,C0115
"""Plugin admin."""

import re

from django.contrib import admin

from smarter.apps.account.utils import get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    smarter_filter_queryset_for_user,
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


class PluginStaticAdmin(SmarterCustomerModelAdmin):
    """
    Plugin model admin. This is a primary Smarter resource, that descends
    directly from MetaDataWithOwnershipModel. Visibility of Plugins is
    determined by ownership and role.
    """

    model = PluginMeta

    def plugin_name(self, obj):
        name = obj.name
        formatted_name = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
        return formatted_name

    inlines = [PluginSelectorInline, PluginPromptInline, PluginDataInline]

    # pylint: disable=W0212
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    list_display = ("id", "user_profile", "plugin_name", "version", "created_at", "updated_at")

    def get_queryset(self, request):
        """
        Visibility is determined by ownership and role.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user(user=user, qs=qs)


class PluginApiAdmin(SmarterCustomerModelAdmin):
    """
    Plugin model admin. This is a primary Smarter resource, that descends
    directly from MetaDataWithOwnershipModel. Visibility of Plugins is
    determined by ownership and role.
    """

    model = PluginMeta

    def plugin_name(self, obj):
        name = obj.name
        formatted_name = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
        return formatted_name

    inlines = [PluginSelectorInline, PluginPromptInline, PluginDataApiInline]

    # pylint: disable=W0212
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    list_display = ("id", "user_profile", "plugin_name", "version", "created_at", "updated_at")

    def get_queryset(self, request):
        """
        Visibility is determined by ownership and role.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user(user=user, qs=qs)


class PluginSqlAdmin(SmarterCustomerModelAdmin):
    """
    Plugin model admin. This is a primary Smarter resource, that descends
    directly from MetaDataWithOwnershipModel. Visibility of Plugins is
    determined by ownership and role.
    """

    model = PluginMeta

    def plugin_name(self, obj):
        name = obj.name
        formatted_name = re.sub(r"(?<!^)(?=[A-Z])", " ", name)
        return formatted_name

    inlines = [PluginSelectorInline, PluginPromptInline, PluginDataSqlInline]

    # pylint: disable=W0212
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    list_display = ("id", "user_profile", "plugin_name", "version", "created_at", "updated_at")

    def get_queryset(self, request):
        """
        Visibility is determined by ownership and role.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user(user=user, qs=qs)


class PluginSelectionHistoryAdmin(SmarterCustomerModelAdmin):
    """
    Plugin Selection History model admin. This descends from
    PluginSelector, so visibility is determined by the parent Plugin and role.
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
        """
        Visibility is determined by ownership of the parent Plugin and role.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
            account_filter="plugin_selector__plugin__user_profile__account",
            user_profile_filter="plugin_selector__plugin__user_profile",
        )


class SqlConnectionAdmin(SmarterCustomerModelAdmin):
    """
    PluginDataSql Connection model admin. This is a primary Smarter resource,
    that descends directly from MetaDataWithOwnershipModel. Visibility
    is determined by ownership and role.
    """

    model = SqlConnection

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = (
        "created_at",
        "user_profile",
        "name",
        "db_engine",
        "hostname",
        "database",
        "username",
        "updated_at",
    )

    def get_queryset(self, request):
        """
        Visibility is determined by ownership and role.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)

        return smarter_filter_queryset_for_user(user=user, qs=qs)


class ApiConnectionAdmin(SmarterCustomerModelAdmin):
    """
    PluginDataApi Connection model admin. This is a primary Smarter resource,
    that descends directly from MetaDataWithOwnershipModel. Visibility
    is determined by ownership and role.
    """

    model = ApiConnection

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_display = (
        "created_at",
        "user_profile",
        "name",
        "base_url",
        "api_key",
        "updated_at",
    )

    def get_queryset(self, request):
        """
        Visibility is determined by ownership and role.
        """
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)

        return smarter_filter_queryset_for_user(user=user, qs=qs)


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
