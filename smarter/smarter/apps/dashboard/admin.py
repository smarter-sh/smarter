# -*- coding: utf-8 -*-
# pylint: disable=missing-class-docstring,missing-function-docstring
"""Rebuild the admin site to restrict access to certain apps and models."""
from django.apps import apps
from django.contrib import admin
from django.contrib.auth.models import Group, Permission, User

from smarter.__version__ import __version__
from smarter.apps.account.models import Account, APIKey, PaymentMethod, UserProfile
from smarter.apps.dashboard.models import EmailContactList


class RestrictedAdminSite(admin.AdminSite):
    # FIX NOTE: WIRE THESE INTO THE APP CONSTRAINTS
    blocked_apps = ["djstripe", "knox", "rest_framework", "smarter.apps.account"]
    site_header = "Smarter Admin Console v" + __version__


class RestrictedModelAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser


class EmailContactListAdmin(RestrictedModelAdmin):
    list_display = ["email", "created_at", "updated_at"]
    ordering = ("-created_at",)


class RestrictedAPIKeyAdmin(RestrictedModelAdmin):

    list_display = [
        "created_at",
        "is_active",
        "last_used_at",
        "expiry",
        "token_key",
        "description",
        "user",
    ]
    readonly_fields = ("created_at", "updated_at", "token_key", "last_used_at", "digest", "user", "account")
    ordering = ("-created_at",)


restricted_site = RestrictedAdminSite(name="restricted_admin_site")

restricted_site.register(User, RestrictedModelAdmin)
restricted_site.register(Group, RestrictedModelAdmin)
restricted_site.register(Permission, RestrictedModelAdmin)
restricted_site.register(Account, RestrictedModelAdmin)
restricted_site.register(UserProfile, RestrictedModelAdmin)
restricted_site.register(PaymentMethod, RestrictedModelAdmin)
restricted_site.register(APIKey, RestrictedAPIKeyAdmin)
restricted_site.register(EmailContactList, EmailContactListAdmin)

models = apps.get_models()

# Register all remaining models with the custom admin site,
# but using the regular ModelAdmin class
for model in models:
    try:
        restricted_site.register(model, admin.ModelAdmin)
    except admin.sites.AlreadyRegistered:
        pass
