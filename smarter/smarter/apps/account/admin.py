# pylint: disable=C0115,W0212
"""Account admin."""

import logging
from typing import Optional

from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import FieldError
from django.db.models import QuerySet
from django.http.request import HttpRequest
from django.utils.translation import gettext_lazy as _

from smarter.apps.account.models import User, UserProfile, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    SmarterStaffOnlyModelAdmin,
    SmarterSuperUserOnlyModelAdmin,
    smarter_is_staff,
    smarter_restricted_admin_site,
)
from smarter.common.helpers.console_helpers import formatted_text

from .models import (
    Account,
    AccountContact,
    Charge,
    DailyBillingRecord,
    UserProfile,
)

logger = logging.getLogger(__name__)


def smarter_filter_queryset_for_user_profile(
    user_profile: UserProfile,
    qs: QuerySet,
    account_filter=None,
    user_profile_filter: Optional[str] = "user_profile",
) -> QuerySet:
    """
    Helper method to filter a queryset based on the user's role and ownership
    of the objects in the queryset. Queryset is assumed to have a user_profile
    field that is a foreign key to the UserProfile model.

    FIX NOTE: refactor this to use SmarterQuerySetWithPermissions()

    .. warning::

        This function only works for models that inherit from
        smarter.apps.account.models.MetaDataWithOwnershipModel
    """
    logger_prefix = formatted_text(f"{__file__}.smarter_filter_queryset_for_user_profile()")
    logger.debug(
        "%s: Filtering queryset for user %s with role %s",
        logger_prefix,
        user_profile.user,
        "superuser" if user_profile.user.is_superuser else "staff" if user_profile.user.is_staff else "customer",
    )

    # 1.) no user_profile, no queryset.
    if not user_profile:
        logger.debug(
            "%s: No user profile found for user %s, returning empty queryset", logger_prefix, user_profile.user
        )
        return qs.none()

    # 2.) if the user is a superuser, return all chatbots.
    if user_profile.user.is_superuser:
        logger.debug("%s: User %s is superuser, returning unfiltered queryset", logger_prefix, user_profile.user)
        return qs

    # 3.) if user is staff then select all chatbots for the account of the user.
    if user_profile.user.is_staff:
        logger.debug(
            "%s: User %s is staff, filtering queryset for account %s",
            logger_prefix,
            user_profile.user,
            user_profile.account,
        )
        try:
            if user_profile_filter is not None:
                return qs.filter(**{user_profile_filter: user_profile})
            else:
                logger.error("user_profile_filter is None, cannot filter queryset")
                return qs.none()
        except FieldError as e:
            logger.error("Error filtering queryset for staff user %s: %s", user_profile.user, e)
            return qs.none()

    # 4.) if the user is a Customer then select all chatbots owned by the
    # user + all chatbots shared with the user which are chatbots owned
    # by an admin user of the account (could be more than one).
    logger.debug(
        "%s: User %s is customer, filtering queryset for owned and shared objects", logger_prefix, user_profile.user
    )
    admin_user = UserProfile.admin_for_account(account=user_profile.account)
    admin_profile = UserProfile.get_cached_object(user=admin_user)  # type: ignore
    if user_profile_filter:
        try:
            qs_owned = qs.filter(**{user_profile_filter: user_profile})
            logger.debug(
                "%s: User %s owns %d objects in the queryset", logger_prefix, user_profile.user, qs_owned.count()
            )
        except FieldError as e:
            logger.error("Error filtering queryset for owned objects for user %s: %s", user_profile.user, e)
            qs_owned = qs.none()

        try:
            qs_shared = qs.filter(**{user_profile_filter: admin_profile})
            logger.debug(
                "%s: User %s has %d shared objects in the queryset", logger_prefix, user_profile.user, qs_shared.count()
            )
        except FieldError as e:
            logger.error("Error filtering queryset for shared objects for user %s: %s", user_profile.user, e)
            qs_shared = qs.none()
    else:
        logger.debug(
            "%s: No user_profile_filter provided, filtering queryset based on account affiliation for user %s",
            logger_prefix,
            user_profile.user,
        )
        return qs.filter(**{user_profile_filter: user_profile}) if user_profile_filter is not None else qs.none()

    if account_filter:
        try:
            qs_owned = qs_owned.filter(**{account_filter: user_profile.cached_account})  # type: ignore
            qs_shared = qs_shared.filter(**{account_filter: user_profile.cached_account})  # type: ignore
            logger.debug(
                "%s: After applying account filter, user %s has %d owned and %d shared objects in the queryset",
                logger_prefix,
                user_profile.user,
                qs_owned.count(),
                qs_shared.count(),
            )
        except FieldError as e:
            logger.error("Error applying account filter for user %s: %s", user_profile.user, e)
            return qs.none()

    logger.debug(
        "%s: Returning combined queryset with %d owned and %d shared objects for user %s",
        logger_prefix,
        qs_owned.count(),
        qs_shared.count(),
        user_profile.user,
    )
    return qs_owned | qs_shared


# @admin.register(Account)
class AccountAdmin(SmarterStaffOnlyModelAdmin):
    """Account model admin."""

    model = Account

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("company_name", "account_number", "created_at", "updated_at")

    def get_queryset(self, request: HttpRequest):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user_profile(
            user_profile=UserProfile.get_cached_object(user=user) if user else None,  # type: ignore
            qs=qs,
        )


# @admin.register(AccountContact)
class AccountContactAdmin(SmarterStaffOnlyModelAdmin):
    """AccountContact model admin."""

    model = AccountContact

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("account", "first_name", "last_name", "email", "phone", "is_primary")

    def get_queryset(self, request: HttpRequest):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user_profile(
            user_profile=UserProfile.get_cached_object(user=user) if user else None,  # type: ignore
            qs=qs,
        )


# @admin.register(Charge)
class ChargeAdmin(SmarterCustomerModelAdmin):
    """Charge model admin."""

    model = Charge

    def get_readonly_fields(self, request, obj=None):
        # pylint: disable=protected-access
        return [field.name for field in self.model._meta.fields]

    list_display = (
        "created_at",
        "user_profile",
        "provider",
        "model",
        "charge_type",
        "total_tokens",
    )

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user_profile(
            user_profile=UserProfile.get_cached_object(user=user) if user else None,  # type: ignore
            qs=qs,
        )


# @admin.register(DailyBillingRecord)
class DailyBillingRecordAdmin(SmarterCustomerModelAdmin):
    """DailyBillingRecord model admin."""

    model = DailyBillingRecord

    def get_readonly_fields(self, request: HttpRequest, obj=None):
        return [field.name for field in self.model._meta.fields]

    list_display = (
        "created_at",
        "account",
        "user",
        "provider",
        "model",
        "charge_type",
        "total_tokens",
    )

    def get_queryset(self, request: HttpRequest):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user_profile(
            user_profile=UserProfile.get_cached_object(user=user) if user else None,  # type: ignore
            qs=qs,
        )


class RestrictedUserAdmin(UserAdmin):
    """
    Custom User admin that restricts access to users based on their account.

    - Superusers can see and edit all users
    - Staff users can see and edit users within their own account.
    - Non-staff users cannot see or edit any users.
    """

    list_display = (
        "profile_account",
        "username",
        "email",
        "first_name",
        "last_name",
        "is_superuser",
        "is_staff",
        "is_active",
        "date_joined",
        "last_login",
    )

    def has_add_permission(self, request) -> bool:
        """
        force all adds to the manage.py command, because
        this adds UserProfile and sends the welcome email.
        """
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """
        Prevent deletion for non-superusers.
        """
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return False
        if not isinstance(request.user, User):
            logger.warning("Unexpected user type in RestrictedUserAdmin.has_delete_permission: %s", type(request.user))
            return False
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """
        Allow change permissions for superusers and to
        staff users if they are changing a user within their own account.
        """
        if not hasattr(request, "user"):
            return False
        if not isinstance(request.user, User):
            logger.warning("Unexpected user type in RestrictedUserAdmin.has_change_permission: %s", type(request.user))
            return False
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if request.user.is_staff:
            try:
                if not obj:
                    return False
                user_profile = UserProfile.get_cached_object(user=request.user)  # type: ignore
                if not user_profile:
                    return False
                obj_user_profile = UserProfile.get_cached_object(user=obj)  # type: ignore
                if not obj_user_profile:
                    return False
                if user_profile.cached_account == obj_user_profile.cached_account:
                    return True
                return False
            except UserProfile.DoesNotExist:
                return False
        return False

    def has_module_permission(self, request: HttpRequest) -> bool:
        return smarter_is_staff(request)

    def profile_account(self, obj) -> Optional[Account]:
        """Custom method to display the account associated with the user's profile."""
        userprofile = UserProfile.get_cached_object(user=obj)
        if userprofile:
            return userprofile.account
        return None

    profile_account.short_description = "Account"

    def get_queryset(self, request):
        """
        Customize the queryset based on whether the user is_staff or is_superuser.
        """
        qs = super().get_queryset(request)
        user = get_resolved_user(request.user)
        if not smarter_is_staff(request):
            return qs.none()
        if not user:
            return qs.none()
        if user and user.is_superuser:
            return qs
        if user.is_staff:
            user_profile = UserProfile.get_cached_object(user=user)  # type: ignore
            if not user_profile:
                return qs.none()
            return qs.filter(
                id__in=UserProfile.objects.filter(account=user_profile.cached_account).values_list("user_id", flat=True)
            )
        # For non-staff users, return an empty queryset to prevent access to any user records.
        return qs.none()

    def get_readonly_fields(self, request, obj=None):
        user = get_resolved_user(request.user)
        if not user:
            return [field.name for field in self.model._meta.fields]
        if user.is_superuser:
            return ("username", "last_login", "date_joined")
        if user.is_staff:
            return ("username", "last_login", "date_joined", "is_superuser", "is_staff")
        # For non-staff users, make all fields read-only to prevent any modifications.
        return [field.name for field in self.model._meta.fields]


class RestrictedUserProfileAdmin(SmarterSuperUserOnlyModelAdmin):
    """
    Custom UserProfile admin that restricts access to users based on their account.

    - Superusers can see and edit all user_profiles
    - Anyone else cannot see or edit any user_profiles.
    """

    model = UserProfile

    list_display = ("user", "account", "created_at", "updated_at")

    # this probably is not necessary since the module
    # permission is limited to superusers.
    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        if not isinstance(request.user, User):
            logger.warning("Unexpected user type in RestrictedUserProfileAdmin.get_queryset: %s", type(request.user))
            return qs.none()
        if not request.user.is_authenticated:
            return qs.none()

        if request.user.is_superuser:
            return qs
        return qs.none()


smarter_restricted_admin_site.register(Account, AccountAdmin)
smarter_restricted_admin_site.register(AccountContact, AccountContactAdmin)
smarter_restricted_admin_site.register(Charge, ChargeAdmin)
smarter_restricted_admin_site.register(DailyBillingRecord, DailyBillingRecordAdmin)
smarter_restricted_admin_site.register(UserProfile, RestrictedUserProfileAdmin)
smarter_restricted_admin_site.register(User, RestrictedUserAdmin)
