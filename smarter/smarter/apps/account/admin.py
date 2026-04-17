# pylint: disable=C0115,W0212
"""Account admin."""

import logging
from typing import Optional

from django.contrib.auth.admin import UserAdmin

# from django.contrib import admin
from django.http.request import HttpRequest
from django.utils.translation import gettext_lazy as _

from smarter.apps.account.models import User, UserProfile, get_resolved_user
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    SmarterStaffOnlyModelAdmin,
    SmarterSuperUserOnlyModelAdmin,
    smarter_filter_queryset_for_user,
    smarter_is_staff,
    smarter_restricted_admin_site,
)

from .models import (
    Account,
    AccountContact,
    Charge,
    DailyBillingRecord,
    PaymentMethod,
    UserProfile,
)

logger = logging.getLogger(__name__)


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
        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
            account_filter="id",
            user_profile_filter=None,
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
        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
            account_filter="account",
            user_profile_filter=None,
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
        "account",
        "user",
        "provider",
        "model",
        "charge_type",
        "total_tokens",
    )

    def get_queryset(self, request):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
            account_filter="account",
            user_profile_filter=None,
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
        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
            account_filter="account",
            user_profile_filter=None,
        )


# @admin.register(PaymentMethod)
class PaymentMethodModelAdmin(SmarterStaffOnlyModelAdmin):
    """Payment method model admin."""

    model = PaymentMethod

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("name", "created_at", "updated_at")

    def get_queryset(self, request: HttpRequest):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
            account_filter="account",
            user_profile_filter=None,
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
smarter_restricted_admin_site.register(PaymentMethod, PaymentMethodModelAdmin)
smarter_restricted_admin_site.register(UserProfile, RestrictedUserProfileAdmin)
smarter_restricted_admin_site.register(User, RestrictedUserAdmin)
