# pylint: disable=missing-class-docstring,missing-function-docstring
"""Rebuild the admin site to restrict access to certain apps and models."""

from django import forms
from django.apps import apps
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from smarter.__version__ import __version__
from smarter.apps.account.admin import SecretAdmin
from smarter.apps.account.models import Account, PaymentMethod, Secret, UserProfile
from smarter.apps.chat.admin import (
    ChatAdmin,
    ChatHistoryAdmin,
    ChatPluginUsageAdmin,
    ChatToolCallHistoryAdmin,
)
from smarter.apps.chat.models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall
from smarter.apps.chatbot.admin import (
    ChatBotAdmin,
    ChatBotAPIKeyAdmin,
    ChatBotCustomDomainAdmin,
    ChatBotCustomDomainDNSAdmin,
    ChatBotFunctionsAdmin,
    ChatBotPluginAdmin,
    ChatBotRequestsAdmin,
)
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
    ChatBotFunctions,
    ChatBotPlugin,
    ChatBotRequests,
)
from smarter.apps.plugin.admin import (
    ApiConnectionAdmin,
    PluginApiAdmin,
    PluginSelectionHistoryAdmin,
    PluginSqlAdmin,
    PluginStaticAdmin,
    SqlConnectionAdmin,
)
from smarter.apps.plugin.models import (
    ApiConnection,
    PluginMeta,
    PluginSelectorHistory,
    SqlConnection,
)
from smarter.lib.django.admin import RestrictedModelAdmin, SuperUserOnlyModelAdmin
from smarter.lib.django.user import User
from smarter.lib.drf.admin import SmarterAuthTokenAdmin
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.journal.admin import SAMJournalAdmin
from smarter.lib.journal.models import SAMJournal

from .models import EmailContactList


class RestrictedAdminSite(admin.AdminSite):
    """
    Custom admin site that restricts access to certain apps and models
    and modifies the admin console header title.
    """

    # FIX NOTE: WIRE THESE INTO THE APP CONSTRAINTS
    blocked_apps = ["djstripe", "knox", "rest_framework", "smarter.apps.account"]
    role: str = "customer"
    site_header = "Smarter Admin Console v" + __version__ + " (" + role + ")"

    def each_context(self, request):
        if request.user.is_superuser:
            self.role = "superuser"
        elif request.user.is_staff:
            self.role = "account admin"
        self.site_header = "Smarter Admin Console v" + __version__ + " (" + self.role + ")"

        context = super().each_context(request)
        return context


class CustomPasswordWidget(forms.Widget):
    """Custom widget for the password field in the UserChangeForm."""

    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe('<a href="password/" style="color: blue;">CHANGE PASSWORD</a>')  # nosec


class UserChangeForm(forms.ModelForm):
    """Custom form for the User model that includes a link to change the password."""

    password = forms.CharField(widget=CustomPasswordWidget(), label=_("Password"))

    class Meta:
        model = User
        fields = "__all__"


class RestrictedUserAdmin(UserAdmin):
    """Custom User admin that restricts access to users based on their account."""

    form = UserChangeForm

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ("username", "last_login", "date_joined")
        return super().get_readonly_fields(request, obj)


class EmailContactListAdmin(RestrictedModelAdmin):
    """Custom admin for the EmailContactList model."""

    list_display = ["email", "created_at", "updated_at"]
    ordering = ("-created_at",)


# Register the custom admin site
restricted_site = RestrictedAdminSite(name="restricted_admin_site")

# Account Models
restricted_site.register(Account, RestrictedModelAdmin)
restricted_site.register(UserProfile, RestrictedModelAdmin)
restricted_site.register(User, RestrictedUserAdmin)
restricted_site.register(SmarterAuthToken, SmarterAuthTokenAdmin)
restricted_site.register(PaymentMethod, RestrictedModelAdmin)
restricted_site.register(EmailContactList, EmailContactListAdmin)
restricted_site.register(Secret, SecretAdmin)

# Chat Models
restricted_site.register(Chat, ChatAdmin)
restricted_site.register(ChatHistory, ChatHistoryAdmin)
restricted_site.register(ChatPluginUsage, ChatPluginUsageAdmin)
restricted_site.register(ChatToolCall, ChatToolCallHistoryAdmin)

# ChatBot
restricted_site.register(ChatBot, ChatBotAdmin)
restricted_site.register(ChatBotCustomDomain, ChatBotCustomDomainAdmin)
restricted_site.register(ChatBotCustomDomainDNS, ChatBotCustomDomainDNSAdmin)
restricted_site.register(ChatBotAPIKey, ChatBotAPIKeyAdmin)
restricted_site.register(ChatBotPlugin, ChatBotPluginAdmin)
restricted_site.register(ChatBotFunctions, ChatBotFunctionsAdmin)
restricted_site.register(ChatBotRequests, ChatBotRequestsAdmin)


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


restricted_site.register(PluginMetaStatic, PluginStaticAdmin)
restricted_site.register(PluginMetaApi, PluginApiAdmin)
restricted_site.register(PluginMetaSql, PluginSqlAdmin)
restricted_site.register(SqlConnection, SqlConnectionAdmin)
restricted_site.register(PluginSelectorHistory, PluginSelectionHistoryAdmin)
restricted_site.register(ApiConnection, ApiConnectionAdmin)


# Journal Models
restricted_site.register(SAMJournal, SAMJournalAdmin)

# All remaining models are registered with the SuperUserOnlyModelAdmin
# to restrict access to superusers only
models = apps.get_models()

for model in models:
    try:
        restricted_site.register(model, SuperUserOnlyModelAdmin)
    except admin.sites.AlreadyRegistered:
        pass
