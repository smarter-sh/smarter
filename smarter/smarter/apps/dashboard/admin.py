# pylint: disable=missing-class-docstring,missing-function-docstring
"""Rebuild the admin site to restrict access to certain apps and models."""
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from smarter.__version__ import __version__
from smarter.apps.account.models import Account, PaymentMethod, UserProfile
from smarter.apps.chat.admin import (
    ChatAdmin,
    ChatHistoryAdmin,
    ChatToolCallHistoryAdmin,
    PluginSelectionHistoryAdmin,
)
from smarter.apps.chat.models import Chat, ChatHistory, ChatPluginUsage, ChatToolCall
from smarter.apps.chatbot.admin import (
    ChatBotAdmin,
    ChatBotAPIKeyAdmin,
    ChatBotCustomDomainAdmin,
    ChatBotCustomDomainDNSAdmin,
    ChatBotFunctionsAdmin,
    ChatBotPluginAdmin,
)
from smarter.apps.chatbot.models import (
    ChatBot,
    ChatBotAPIKey,
    ChatBotCustomDomain,
    ChatBotCustomDomainDNS,
    ChatBotFunctions,
    ChatBotPlugin,
)
from smarter.apps.plugin.admin import PluginAdmin, PluginDataSqlConnectionAdmin
from smarter.apps.plugin.models import PluginDataSqlConnection, PluginMeta
from smarter.lib.django.admin import RestrictedModelAdmin
from smarter.lib.django.user import User
from smarter.lib.drf.admin import SmarterAuthTokenAdmin
from smarter.lib.drf.models import SmarterAuthToken

from .models import EmailContactList


class RestrictedAdminSite(admin.AdminSite):
    # FIX NOTE: WIRE THESE INTO THE APP CONSTRAINTS
    blocked_apps = ["djstripe", "knox", "rest_framework", "smarter.apps.account"]
    site_header = "Smarter Admin Console v" + __version__


class CustomPasswordWidget(forms.Widget):

    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe('<a href="password/" style="color: blue;">CHANGE PASSWORD</a>')  # nosec


class UserChangeForm(forms.ModelForm):
    password = forms.CharField(widget=CustomPasswordWidget(), label=_("Password"))

    class Meta:
        model = User
        fields = "__all__"


class RestrictedUserAdmin(UserAdmin):
    form = UserChangeForm
    readonly_fields = (
        "username",
        "last_login",
        "date_joined",
        "is_superuser",
        "is_active",
        "groups",
        "user_permissions",
    )

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


class EmailContactListAdmin(RestrictedModelAdmin):
    list_display = ["email", "created_at", "updated_at"]
    ordering = ("-created_at",)


class RestrictedAPIKeyAdmin(RestrictedModelAdmin):

    list_display = [
        "created",
        "is_active",
        "last_used_at",
        "expiry",
        "token_key",
        "description",
        "user",
    ]
    readonly_fields = ("created", "token_key", "last_used_at", "digest", "user")
    ordering = ("-created",)


restricted_site = RestrictedAdminSite(name="restricted_admin_site")

# Account Models
restricted_site.register(Account, RestrictedModelAdmin)
restricted_site.register(UserProfile, RestrictedModelAdmin)
restricted_site.register(User, RestrictedUserAdmin)
restricted_site.register(SmarterAuthToken, SmarterAuthTokenAdmin)
restricted_site.register(PaymentMethod, RestrictedModelAdmin)
restricted_site.register(EmailContactList, EmailContactListAdmin)

# Chat Models
restricted_site.register(Chat, ChatAdmin)
restricted_site.register(ChatHistory, ChatHistoryAdmin)
restricted_site.register(ChatPluginUsage, PluginSelectionHistoryAdmin)
restricted_site.register(ChatToolCall, ChatToolCallHistoryAdmin)

# ChatBot

restricted_site.register(ChatBot, ChatBotAdmin)
restricted_site.register(ChatBotCustomDomain, ChatBotCustomDomainAdmin)
restricted_site.register(ChatBotCustomDomainDNS, ChatBotCustomDomainDNSAdmin)
restricted_site.register(ChatBotAPIKey, ChatBotAPIKeyAdmin)
restricted_site.register(ChatBotPlugin, ChatBotPluginAdmin)
restricted_site.register(ChatBotFunctions, ChatBotFunctionsAdmin)

# Plugin Models
restricted_site.register(PluginMeta, PluginAdmin)
restricted_site.register(PluginDataSqlConnection, PluginDataSqlConnectionAdmin)


# from django.apps import apps
# models = apps.get_models()

# # Register all remaining models with the custom admin site,
# # but using the regular ModelAdmin class
# for model in models:
#     try:
#         restricted_site.register(model, admin.ModelAdmin)
#     except admin.sites.AlreadyRegistered:
#         pass
