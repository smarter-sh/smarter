# pylint: disable=missing-class-docstring,missing-function-docstring,W0613
"""Rebuild the admin site to restrict access to certain apps and models."""

import logging
from typing import Optional

from django.contrib import admin
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import FieldError
from django.db.models.query import QuerySet
from django.http import HttpRequest

from smarter.__version__ import __version__
from smarter.apps.account.models import ResolvedUserType, UserProfile, get_resolved_user
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
)
from smarter.common.helpers.console_helpers import formatted_text

from .models import EmailContactList

logger = logging.getLogger(__name__)


def smarter_filter_queryset_for_user(
    user: ResolvedUserType,
    qs: QuerySet,
    account_filter: str = "user_profile__account",
    user_profile_filter: Optional[str] = "user_profile",
) -> QuerySet:
    """
    Helper method to filter a queryset based on the user's role and ownership
    of the objects in the queryset. Queryset is assumed to have a user_profile
    field that is a foreign key to the UserProfile model.

    .. warning::

        This function only works for models that inherit from
        smarter.apps.account.models.MetaDataWithOwnershipModel
    """
    if not user or not user.is_authenticated:
        logger.debug("smarter_filter_queryset_for_user: User is not authenticated, returning empty queryset")
        return qs.none()
    logger_prefix = formatted_text(f"{__file__}.smarter_filter_queryset_for_user()")
    logger.debug(
        "%s: Filtering queryset for user %s with role %s",
        logger_prefix,
        user,
        "superuser" if user.is_superuser else "staff" if user.is_staff else "customer",
    )

    # 1.) if the user is a superuser, return all chatbots.
    if user.is_superuser:
        logger.debug("%s: User %s is superuser, returning unfiltered queryset", logger_prefix, user)
        return qs

    user_profile = UserProfile.get_cached_object(user=user)  # type: ignore
    if not user_profile:
        logger.debug("%s: No user profile found for user %s, returning empty queryset", logger_prefix, user)
        return qs.none()

    # 2.) if user is staff then select all chatbots for the account of the user.
    if user.is_staff:
        logger.debug(
            "%s: User %s is staff, filtering queryset for account %s", logger_prefix, user, user_profile.account
        )
        try:
            return qs.filter(**{account_filter: user_profile.account})
        except FieldError as e:
            logger.error("Error filtering queryset for staff user %s: %s", user, e)
            return qs.none()

    # 3.) if the user is a Customer then select all chatbots owned by the
    # user + all chatbots shared with the user which are chatbots owned
    # by an admin user of the account (could be more than one).
    logger.debug("%s: User %s is customer, filtering queryset for owned and shared objects", logger_prefix, user)
    admin_user = get_cached_admin_user_for_account(account=user_profile.cached_account)  # type: ignore
    admin_profile = UserProfile.get_cached_object(user=admin_user)  # type: ignore
    if user_profile_filter:
        try:
            qs_owned = qs.filter(**{user_profile_filter: user_profile})
            logger.debug("%s: User %s owns %d objects in the queryset", logger_prefix, user, qs_owned.count())
        except FieldError as e:
            logger.error("Error filtering queryset for owned objects for user %s: %s", user, e)
            qs_owned = qs.none()

        try:
            qs_shared = qs.filter(**{user_profile_filter: admin_profile})
            logger.debug("%s: User %s has %d shared objects in the queryset", logger_prefix, user, qs_shared.count())
        except FieldError as e:
            logger.error("Error filtering queryset for shared objects for user %s: %s", user, e)
            qs_shared = qs.none()
    else:
        logger.debug(
            "%s: No user_profile_filter provided, filtering queryset based on account affiliation for user %s",
            logger_prefix,
            user,
        )
        return qs.filter(**{account_filter: user_profile.cached_account})

    logger.debug(
        "%s: Returning combined queryset with %d owned and %d shared objects for user %s",
        logger_prefix,
        qs_owned.count(),
        qs_shared.count(),
        user,
    )
    return qs_owned | qs_shared


def smarter_is_staff(request: HttpRequest) -> bool:
    """
    Helper method to determine if the user is a staff member.

    param request: HttpRequest object containing user information
    rtype: bool
    return: True if the user is a staff member, False otherwise
    """
    user = get_resolved_user(request.user)  # type: ignore
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return False


def smarter_has_read_permission(request: HttpRequest, obj=None) -> bool:
    """
    Helper method to determine if the user has permission
    to Read an object based on ownership and account association. This
    is mostly a blunt-force analysis in that obj is only passed in
    exceptional situations.

    - Superusers can view any object.
    - Staff can view objects that they explicitly own or that belong to users
      within their account.
    - Customers can only view objects that they explicitly own or that are
      owned by an admin in their account.

    param request: HttpRequest object containing user information
    param obj: The object for which read permission is being checked (optional)
    rtype: bool
    return: True if the user has read permission for the object, False otherwise
    """
    logger_prefix = formatted_text(f"{__file__}.smarter_has_read_permission()")
    user = get_resolved_user(request.user)  # type: ignore
    obj_user = None
    logger.debug(
        "%s: Checking read permission for user %s and object %s of type %s", logger_prefix, user, obj, type(obj)
    )

    # most likely situation.
    if obj is None:
        logger.debug("%s: No object provided, granting read permission by default", logger_prefix)
        return True

    if not user or not user.is_authenticated:
        logger.debug("%s: User is not authenticated", logger_prefix)
        return False

    # superusers can view any object.
    if user.is_superuser:
        logger.debug("%s: User %s is superuser, granting read permission", logger_prefix, user)
        return True

    user_profile = UserProfile.get_cached_object(user=user)  # type: ignore
    obj_user_profile = None
    if not user_profile:
        logger.debug("%s: No user profile found for user %s", logger_prefix, user)
        return False

    # most likely ownership of the object is determined by a user profile
    if hasattr(obj, "user_profile"):
        obj_user_profile = obj.user_profile
        obj_user = obj_user_profile.user
    elif hasattr(obj, "user"):
        obj_user = obj.user

        if obj_user == user:
            logger.debug("%s: User %s is the owner of object %s, granting read permission", logger_prefix, user, obj)
            return True

        obj_user_profile = UserProfile.get_cached_object(user=obj_user)  # type: ignore

    if not isinstance(user_profile, UserProfile) or not isinstance(obj_user_profile, UserProfile):
        logger.debug("%s: user profiles not found for object user %s", logger_prefix, obj_user)
        return False

    # check account-level permissions
    if user_profile.cached_account == obj_user_profile.cached_account:
        if user.is_staff:
            logger.debug(
                "%s: User %s is staff and belongs to the same account as object user %s, granting read permission",
                logger_prefix,
                user,
                obj_user,
            )
            return True
        elif not user.is_staff and obj_user.is_superuser:
            logger.debug(
                "%s: User %s is a customer but object user %s is a superuser in the same account, granting read permission",
                logger_prefix,
                user,
                obj_user,
            )
            return True
    logger.debug("%s: User %s does not have permission to access object %s", logger_prefix, user, obj)
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
    user = get_resolved_user(request.user)  # type: ignore
    if not user or not user.is_authenticated:
        logger.debug("%s: User is not authenticated", logger_prefix)
        return False
    # superusers can change any object.
    if user.is_superuser:
        return True
    # customers can only change objects that they explicitly own.
    if hasattr(obj, "user"):
        obj_user = obj.user
    else:
        obj_user = None
    if obj_user == user:
        return True

    # staff users can change objects that belong to users within their account.
    if not user.is_staff:
        logger.debug("%s: User %s is not staff", logger_prefix, user)
        return False
    user_profile = UserProfile.get_cached_object(user=user)  # type: ignore
    if not user_profile:
        logger.debug("%s: No user profile found for user %s", logger_prefix, user)
        return False
    obj_user_profile = UserProfile.get_cached_object(user=obj_user)  # type: ignore
    if not obj_user_profile:
        logger.debug("%s: No user profile found for object user %s", logger_prefix, obj_user)
        return False
    if user_profile.cached_account == obj_user_profile.cached_account:
        return True
    if hasattr(obj, "account") and obj.account == user_profile.cached_account:
        return True
    if hasattr(obj, "user_profile") and obj.user_profile.cached_account == user_profile.cached_account:
        return True
    logger.debug("%s: User %s does not have permission to access object %s", logger_prefix, user, obj)
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
        return True

    def has_view_permission(self, request, obj=None):
        """
        Override the default view permission logic to implement
        role-based access control for the admin console. View
        permission is effectively granted to anyone who
        is authenticated, barring cases where obj is passed.
        """
        return smarter_has_read_permission(request, obj)

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default add permission logic to implement
        role-based access control for the admin console. Add
        permission is granted to superusers only.
        """
        user = get_resolved_user(request.user)  # type: ignore
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
        user = get_resolved_user(request.user)  # type: ignore
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
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        """
        Override the default view permission logic to restrict access
        to superusers only.
        """
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_superuser

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default add permission logic to restrict access
        to superusers only.
        """
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default change permission logic to restrict access
        to superusers only.
        """
        user = get_resolved_user(request.user)  # type: ignore
        return user.is_superuser

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """
        Override the default delete permission logic to restrict access
        to superusers only.
        """
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
