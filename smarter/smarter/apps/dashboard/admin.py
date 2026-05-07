# pylint: disable=missing-class-docstring,missing-function-docstring,W0613
"""
Custom Django admin site and model admin classes for the dashboard app.

This module rebuilds the Django admin site with fine-grained, role-based
access control. Instead of using Django's default ``AdminSite``, a
:class:`RestrictedAdminSite` instance is registered that enforces the
following permission tiers across all registered models:

- **Superuser** — full CRUD access to all models.
- **Staff / account admin** — read and update/delete access to owned objects;
  no add permission.
- **Customer (authenticated)** — read access to owned objects only.
- **Anonymous / unauthenticated** — no access.

Module-level helpers
--------------------
:func:`smarter_is_staff`
    Returns ``True`` if the requesting user is a staff member or superuser.

:func:`smarter_has_ud_permission`
    Returns ``True`` if the requesting user may update or delete the given
    object, based on ownership and account association.

Model admin classes
-------------------
:class:`SmarterCustomerModelAdmin`
    Grants authenticated customers read access to their own objects; restricts
    add/change/delete to owners and superusers.

:class:`SmarterStaffOnlyModelAdmin`
    Restricts all operations to staff members and superusers.

:class:`SmarterSuperUserOnlyModelAdmin`
    Restricts all operations to superusers only.

Admin site
----------
:class:`RestrictedAdminSite`
    Custom :class:`~django.contrib.admin.AdminSite` that dynamically updates
    the console header with the current user's role and version string.

:data:`smarter_restricted_admin_site`
    The singleton :class:`RestrictedAdminSite` instance used throughout the
    project (``name="restricted_admin_site"``).

Registered models
-----------------
- :class:`~smarter.apps.dashboard.models.EmailContactList` — registered with
  :class:`EmailContactListAdmin` (staff-only).
"""

import logging

from django.contrib import admin
from django.contrib.auth.models import AnonymousUser, User
from django.http import HttpRequest

from smarter.__version__ import __version__
from smarter.apps.account.models import (
    Account,
    MetaDataWithOwnershipModel,
    UserProfile,
    get_resolved_user,
)
from smarter.common.helpers.console_helpers import formatted_text

from .models import EmailContactList

logger = logging.getLogger(__name__)


def smarter_is_staff(request: HttpRequest) -> bool:
    """
    Helper method to determine if the user is a staff member.

    param request: HttpRequest object containing user information
    rtype: bool
    return: True if the user is a staff member, False otherwise
    """
    user = get_resolved_user(request.user)  # type: ignore
    if not isinstance(user, User):
        return False
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return False


def smarter_has_ud_permission(request: HttpRequest, obj=None) -> bool:
    """
    Helper method to determine if the user has permission
    to Update or Delete (UD) an object based on ownership and account association.

    param request: HttpRequest object containing user information
    param obj: The object for which update/delete permission is being checked (optional)
    rtype: bool
    return: True if the user has update/delete permission for the object, False otherwise
    """
    logger_prefix = formatted_text(f"{__file__}.smarter_has_ud_permission()")
    # First check if the user is authenticated
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return False
    user = request.user
    if not isinstance(user, User):
        logger.warning("%s Unexpected user: %s", logger_prefix, type(user))
        return False
    if user.is_superuser:
        return True

    if isinstance(obj, (Account, User, UserProfile)):
        return False

    try:
        if isinstance(obj, MetaDataWithOwnershipModel):
            return type(obj).objects.with_ownership_permission_for(user=user).filter(pk=obj.pk).exists()
        return False
    # pylint: disable=broad-except
    except Exception as e:
        logger.error("%s Error checking ownership permission: %s", logger_prefix, e)
    return False


class SmarterCustomerModelAdmin(admin.ModelAdmin):
    """
    Customized Django Admin console model class that provides
    access to customers.
    """

    def has_module_permission(self, request: HttpRequest) -> bool:
        user = get_resolved_user(request.user)  # type: ignore
        logger_prefix = formatted_text(f"{__name__}.SmarterCustomerModelAdmin.has_module_permission()")
        if not isinstance(user, User):
            logger.warning("%s Unexpected user type: %s", logger_prefix, type(user))
            return False
        if not user.is_authenticated:
            return False
        return True

    def has_view_permission(self, request, obj=None):
        """
        Override the default view permission logic to implement
        role-based access control for the admin console. View
        permission is effectively granted to anyone who
        is authenticated, barring cases where obj is passed.
        """
        logger_prefix = formatted_text(f"{__name__}.SmarterCustomerModelAdmin.has_view_permission()")
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return False
        user = request.user
        if not isinstance(user, User):
            logger.warning("%s Unexpected user type: %s", logger_prefix, type(user))
            return False
        if user.is_superuser:
            return True

        if isinstance(obj, (Account, User, UserProfile)):
            return False

        try:
            if isinstance(obj, MetaDataWithOwnershipModel):
                return type(obj).objects.with_read_permission_for(user=user).filter(pk=obj.pk).exists()
            return False
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("%s Error checking read permission: %s", logger_prefix, e)
            return False

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default add permission logic to implement
        role-based access control for the admin console. Add
        permission is granted to superusers only.
        """
        user = get_resolved_user(request.user)  # type: ignore
        logger_prefix = formatted_text(f"{__name__}.SmarterCustomerModelAdmin.has_add_permission()")
        if not isinstance(user, User):
            logger.warning("%s Unexpected user type: %s", logger_prefix, type(user))
            return False
        return user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default change permission logic to implement
        role-based access control for the admin console. Change
        permission is granted based on the user's role and ownership
        of the object.
        """
        return smarter_has_ud_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default delete permission logic to implement
        role-based access control for the admin console. Delete
        permission is granted based on the user's role and ownership
        of the object.
        """
        return smarter_has_ud_permission(request, obj)


class SmarterStaffOnlyModelAdmin(admin.ModelAdmin):
    """
    Customized Django Admin console model class that restricts access to the
    model and prevents adding new instances of the model.
    """

    def has_module_permission(self, request: HttpRequest) -> bool:
        """
        Override the default module permission logic to restrict access
        to staff users and superusers only.
        """
        return smarter_is_staff(request)

    def has_view_permission(self, request, obj=None):
        """
        Override the default view permission logic to restrict access
        to staff users and superusers only.
        """
        if not smarter_is_staff(request):
            return False
        return smarter_has_ud_permission(request, obj)

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default add permission logic to restrict access
        to superusers only.
        """
        logger_prefix = formatted_text(f"{__name__}.SmarterStaffOnlyModelAdmin.has_add_permission()")
        user = get_resolved_user(request.user)  # type: ignore
        if not isinstance(user, User):
            logger.warning("%s Unexpected user type: %s", logger_prefix, type(user))
            return False
        return user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default change permission logic to restrict access
        to staff users and superusers only.
        """
        if not smarter_is_staff(request):
            return False
        return smarter_has_ud_permission(request, obj)

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default delete permission logic to restrict access
        to staff users and superusers only.
        """
        if not smarter_is_staff(request):
            return False
        return smarter_has_ud_permission(request, obj)


class SmarterSuperUserOnlyModelAdmin(admin.ModelAdmin):
    """
    Customized Django Admin console model class that restricts
    module access to superusers only.
    """

    def has_module_permission(self, request: HttpRequest) -> bool:
        """
        Override the default module permission logic to restrict access
        to superusers only.
        """
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser  # type: ignore

    def has_view_permission(self, request, obj=None):
        """
        Override the default view permission logic to restrict access
        to superusers only.
        """
        logger_prefix = formatted_text(f"{__name__}.SmarterSuperUserOnlyModelAdmin.has_view_permission()")
        user = get_resolved_user(request.user)  # type: ignore
        if not isinstance(user, User):
            logger.warning("%s Unexpected user type: %s", logger_prefix, type(user))
            return False
        return user.is_superuser

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default add permission logic to restrict access
        to superusers only.
        """
        logger_prefix = formatted_text(f"{__name__}.SmarterSuperUserOnlyModelAdmin.has_add_permission()")
        user = get_resolved_user(request.user)  # type: ignore
        if not isinstance(user, User):
            logger.warning("%s Unexpected user type: %s", logger_prefix, type(user))
            return False
        return user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default change permission logic to restrict access
        to superusers only.
        """
        logger_prefix = formatted_text(f"{__name__}.SmarterSuperUserOnlyModelAdmin.has_change_permission()")
        user = get_resolved_user(request.user)  # type: ignore
        if not isinstance(user, User):
            logger.warning("%s Unexpected user type: %s", logger_prefix, type(user))
            return False
        return user.is_superuser

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default delete permission logic to restrict access
        to superusers only.
        """
        logger_prefix = formatted_text(f"{__name__}.SmarterSuperUserOnlyModelAdmin.has_delete_permission()")
        user = get_resolved_user(request.user)  # type: ignore
        if not isinstance(user, User):
            logger.warning("%s Unexpected user type: %s", logger_prefix, type(user))
            return False
        return user.is_superuser


class RestrictedAdminSite(admin.AdminSite):
    """
    Custom admin site that restricts access to certain apps and models
    and modifies the admin console header title.
    """

    def has_all_permission(self, request):
        return request.user.is_authenticated

    role: str = "customer"
    site_header = "Smarter Admin Console v" + __version__ + " (" + role + ")"

    def each_context(self, request: HttpRequest):
        user = get_resolved_user(request.user)  # type: ignore
        if isinstance(user, AnonymousUser) or not getattr(user, "is_authenticated", False):
            self.role = "guest"
            return super().each_context(request)
        if not isinstance(user, User):
            logger_prefix = formatted_text(f"{__name__}.RestrictedAdminSite.each_context()")
            logger.warning("%s Unexpected user type: %s", logger_prefix, type(user))
            self.role = "unknown"
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
