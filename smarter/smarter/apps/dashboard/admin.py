# pylint: disable=missing-class-docstring,missing-function-docstring
"""Rebuild the admin site to restrict access to certain apps and models."""

import logging

from django.contrib import admin
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest

from smarter.__version__ import __version__
from smarter.apps.account.models import get_resolved_user
from smarter.apps.account.utils import get_cached_user_profile

from .models import EmailContactList

logger = logging.getLogger(__name__)


def smarter_staff_only_module_permission(request: HttpRequest) -> bool:
    user = get_resolved_user(request.user)  # type: ignore
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    # Prevent access for non-staff users.
    return False


def smarter_staff_only_change_permission(request: HttpRequest, obj=None) -> bool:
    user = get_resolved_user(request.user)  # type: ignore
    if not user.is_authenticated:
        return False
    if not obj or not hasattr(obj, "user"):
        return False
    if user.is_superuser:
        return True
    user_profile = get_cached_user_profile(user)  # type: ignore
    obj_user_profile = get_cached_user_profile(obj.user)  # type: ignore
    if user_profile and obj_user_profile and user_profile.account == obj_user_profile.account:
        return True
    return False


class SmarterCustomerModelAdmin(admin.ModelAdmin):
    """
    Customized Django Admin console model class that provides
    access to customers.
    """

    def has_module_permission(self, request: HttpRequest) -> bool:
        user = get_resolved_user(request.user)  # type: ignore
        if not user.is_authenticated:
            return False
        logger.debug("Checking module permission for user: %s", user)
        return True

    def has_view_permission(self, request, obj=None):
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_authenticated

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return smarter_staff_only_change_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_superuser


class SmarterStaffOnlyModelAdmin(admin.ModelAdmin):
    """
    Customized Django Admin console model class that restricts access to the
    model and prevents adding new instances of the model.
    """

    def has_module_permission(self, request: HttpRequest) -> bool:
        return smarter_staff_only_module_permission(request)

    def has_view_permission(self, request, obj=None):
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_staff or user.is_superuser

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return smarter_staff_only_change_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_superuser


class SmarterSuperUserOnlyModelAdmin(admin.ModelAdmin):
    """
    Customized Django Admin console model class that restricts
    module access to superusers only.
    """

    def has_module_permission(self, request: HttpRequest) -> bool:
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_superuser

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_superuser

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_superuser


class RestrictedAdminSite(admin.AdminSite):
    """
    Custom admin site that restricts access to certain apps and models
    and modifies the admin console header title.
    """

    def has_permission(self, request):
        return request.user.is_authenticated

    role: str = "customer"
    site_header = "Smarter Admin Console v" + __version__ + " (" + role + ")"

    def each_context(self, request: HttpRequest):
        user = get_resolved_user(request.user)  # type: ignore
        if isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
            self.role = "guest"
            return super().each_context(request)
        if user.is_superuser:
            self.role = "superuser"
        elif user.is_staff:
            self.role = "account admin"
        else:
            self.role = (
                "customer - "
                + (user.first_name if user.first_name else "")
                + " "
                + (user.last_name if user.last_name else "")
            )
        self.site_header = "Smarter Admin Console v" + __version__ + " (" + self.role + ")"

        context = super().each_context(request)
        return context


# Register the custom admin site
smarter_restricted_admin_site = RestrictedAdminSite(name="restricted_admin_site")


class EmailContactListAdmin(SmarterStaffOnlyModelAdmin):
    """Custom admin for the EmailContactList model."""

    list_display = ["email", "created_at", "updated_at"]
    ordering = ("-created_at",)


smarter_restricted_admin_site.register(EmailContactList, EmailContactListAdmin)


# All remaining models are registered with the SmarterSuperUserOnlyModelAdmin
# to restrict access to superusers only
#
# try:
#     # Unregister the Know AuthToken model since we subclassed this
#     # and created our own admin for it.
#     smarter_restricted_admin_site.unregister(AuthToken)
# except NotRegistered as e:
#     logger.warning("Could not unregister AuthToken model because it is not registered: %s", e)
