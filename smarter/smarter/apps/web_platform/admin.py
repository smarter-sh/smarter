# -*- coding: utf-8 -*-
# pylint: disable=missing-module-docstring,missing-class-docstring,missing-function-docstring
from django.apps import apps
from django.contrib import admin
from django.contrib.auth.models import Group, User

from smarter.__version__ import __version__


class RestrictedAdminSite(admin.AdminSite):
    # FIX NOTE: WIRE THESE INTO THE APP CONSTRAINTS
    blocked_apps = ["djstripe", "knox", "rest_framework", "smarter.apps.account"]
    site_header = "Smarter Admin Console v" + __version__


class RestrictedModelAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser


class CustomGroupAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser


restricted_site = RestrictedAdminSite(name="restricted_admin_site")

restricted_site.register(User, RestrictedModelAdmin)
restricted_site.register(Group, RestrictedModelAdmin)

# Get all models
models = apps.get_models()

# Register all models with the custom admin site
for model in models:
    try:
        restricted_site.register(model, RestrictedModelAdmin)
    except admin.sites.AlreadyRegistered:
        pass
