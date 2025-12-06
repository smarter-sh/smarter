# pylint: disable=missing-class-docstring,missing-function-docstring
"""Rebuild the admin site to restrict access to certain apps and models."""

from django.contrib import admin
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest

from smarter.__version__ import __version__

from .models import EmailContactList


# pylint: disable=W0613
class RestrictedModelAdmin(admin.ModelAdmin):
    """
    Customized Django Admin console model class that restricts access to the
    model and prevents adding new instances of the model.
    """

    def has_module_permission(self, request: HttpRequest):
        return request.user.is_superuser or request.user.is_staff

    def has_add_permission(self, request: HttpRequest, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request: HttpRequest, obj=None):
        return request.user.is_superuser


class SuperUserOnlyModelAdmin(admin.ModelAdmin):
    """
    Customized Django Admin console model class that restricts
    module access to superusers only.
    """

    def has_module_permission(self, request: HttpRequest):
        return request.user.is_superuser


class RestrictedAdminSite(admin.AdminSite):
    """
    Custom admin site that restricts access to certain apps and models
    and modifies the admin console header title.
    """

    # TODO: WIRE THESE INTO THE APP CONSTRAINTS
    blocked_apps = ["djstripe", "knox", "rest_framework", "smarter.apps.account"]
    role: str = "customer"
    site_header = "Smarter Admin Console v" + __version__ + " (" + role + ")"

    def each_context(self, request: HttpRequest):
        user = request.user
        if isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
            self.role = "guest"
            return super().each_context(request)
        if getattr(user, "is_superuser", False):
            self.role = "superuser"
        elif getattr(user, "is_staff", False):
            self.role = "account admin"
        self.site_header = "Smarter Admin Console v" + __version__ + " (" + self.role + ")"

        context = super().each_context(request)
        return context


# Register the custom admin site
smarter_restricted_admin_site = RestrictedAdminSite(name="restricted_admin_site")


class EmailContactListAdmin(RestrictedModelAdmin):
    """Custom admin for the EmailContactList model."""

    list_display = ["email", "created_at", "updated_at"]
    ordering = ("-created_at",)


smarter_restricted_admin_site.register(EmailContactList, EmailContactListAdmin)


# All remaining models are registered with the SuperUserOnlyModelAdmin
# to restrict access to superusers only
#
# try:
#     # Unregister the Know AuthToken model since we subclassed this
#     # and created our own admin for it.
#     smarter_restricted_admin_site.unregister(AuthToken)
# except NotRegistered as e:
#     logger.warning("Could not unregister AuthToken model because it is not registered: %s", e)
