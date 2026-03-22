# pylint: disable=C0115,W0212
"""Account admin."""

import logging
from typing import Optional

from django import forms
from django.contrib.auth.admin import UserAdmin

# from django.contrib import admin
from django.http.request import HttpRequest
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.dashboard.admin import (
    SmarterCustomerModelAdmin,
    SmarterStaffOnlyModelAdmin,
    SmarterSuperUserOnlyModelAdmin,
    smarter_filter_queryset_for_user,
    smarter_is_staff,
    smarter_restricted_admin_site,
)
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin

from .models import (
    Account,
    AccountContact,
    Charge,
    DailyBillingRecord,
    PaymentMethod,
    Secret,
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


class SecretAdminForm(forms.ModelForm):
    """Custom form for SecretAdmin to handle the transient 'value' field."""

    value = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text="Put your secret here...",
    )

    model = Secret
    list_display = ["name", "user_profile", "description", "expires_at", "value"]
    logger_prefix = formatted_text(f"{__name__}.SecretAdminForm()")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)  # Expecting the user to be passed in via kwargs
        logger.debug("%s Initializing SecretAdminForm with args: %s and kwargs: %s", self.logger_prefix, args, kwargs)
        super().__init__(*args, **kwargs)
        if not self.user or not isinstance(self.user, User) or not self.user.is_authenticated:
            logger.error(
                "%s SecretAdminForm initialized without an authenticated user. All fields will be read-only.",
                self.logger_prefix,
            )
            for field in self.fields.values():
                field.disabled = True
            return

        def has_permission():
            return False

        if self.instance and self.instance.pk:
            logger.debug("%s Initializing SecretAdminForm for existing Secret: %s", self.logger_prefix, self.instance)
            try:
                if has_permission():
                    instance: Secret = self.instance
                    self.fields["value"].initial = instance.get_secret(update_last_accessed=False)
                else:
                    logger.debug(
                        "%s User %s does not have permission to view the Secret value. Setting 'value' field to '********'.",
                        self.logger_prefix,
                        self.user,
                    )
                    self.fields["value"].initial = "********"
            # pylint: disable=broad-except
            except Exception as e:
                logger.exception(
                    "%s Failed to initialize 'value' field for Secret with id %s. Got the following error: %s",
                    self.logger_prefix,
                    self.instance.pk,
                    e,
                )
                self.fields["value"].initial = None

    def clean(self):
        """Ensure the transient 'value' field is included in cleaned_data."""
        cleaned_data = super().clean()
        if not cleaned_data or "value" not in cleaned_data:
            raise forms.ValidationError("The 'value' field is required.")
        return cleaned_data

    def clean_value(self):
        value = self.cleaned_data.get("value")
        if value and not isinstance(value, str):
            raise forms.ValidationError("The value must be a string.")
        return value


# @admin.register(Secret)
class SecretAdmin(SmarterCustomerModelAdmin, SmarterHelperMixin):
    """
    Secret model admin. This is a primary Smarter resource, that descends
    directly from MetaDataWithOwnershipModel. Visibility of Secrets is
    determined by ownership and role.
    """

    logger_prefix = formatted_text(f"{__name__}.SecretAdmin()")
    request: HttpRequest
    user: User
    user_profile: UserProfile

    model = Secret

    form = SecretAdminForm
    readonly_fields = (
        "created_at",
        "updated_at",
        "last_accessed",
        "display_value",
    )
    fields = (
        "name",
        "user_profile",
        "description",
        "expires_at",
        "display_value",
    )
    list_display = ("user_profile", "name", "description", "created_at", "updated_at", "last_accessed", "expires_at")

    def changelist_view(self, request, extra_context=None):
        self.request = request
        return super().changelist_view(request, extra_context=extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        self.request = request
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def display_value(self, obj: Secret):
        """
        Display the secret value as '********' for users who do not have
        permission to view it.
        """

        def has_permission() -> bool:
            """
            Determine if the current user has permission to view the Secret value.
             - Superusers can view all secrets.
             - The owner of the secret can view it.
             - All other users cannot view the secret value.
            """
            logger.debug(
                "%s.has_permission() Checking permissions for user %s to view Secret %s",
                self.logger_prefix,
                self.user,
                str(obj),
            )
            if not isinstance(obj, Secret):
                logger.error(
                    "%s.has_permission() called with an object that is not a Secret instance: %s",
                    self.logger_prefix,
                    obj,
                )
                return False
            if not self.user.is_authenticated:
                logger.debug(
                    "%s.has_permission() User %s is not authenticated and does not have permission to view the Secret value.",
                    self.logger_prefix,
                    self.user,
                )
                return False
            obj_user_profile: UserProfile = obj.user_profile
            if self.user.is_superuser:
                logger.debug(
                    "%s.has_permission() User %s is a superuser and has permission to view the Secret value.",
                    self.logger_prefix,
                    self.user,
                )
                return True
            if obj_user_profile.user == self.user:
                logger.debug(
                    "%s.has_permission() User %s is the owner of the Secret and has permission to view the Secret value.",
                    self.logger_prefix,
                    self.user,
                )
                return True
            logger.debug(
                "%s.has_permission() User %s does not have permission to view the Secret value.",
                self.logger_prefix,
                self.user,
            )
            return False

        logger.debug("%s.display_value() called for Secret: %s", self.logger_prefix, str(obj))
        if not isinstance(obj, Secret):
            logger.error(
                "%s.display_value() called with an object that is not a Secret instance: %s",
                self.logger_prefix,
                obj,
            )
            return "********"

        if not hasattr(self.request, "user"):
            logger.error(
                "%s.display_value() called without a request user. Cannot determine permissions to display Secret value.",
                self.logger_prefix,
            )
            return "********"

        self.user = self.request.user
        self.user_profile = get_cached_user_profile(self.user)  # type: ignore
        retval = obj.get_secret(update_last_accessed=False)
        logger.debug(
            "%s.display_value() Retrieved secret value for Secret %s. Checking permissions for user %s. Actual value: %s",
            self.logger_prefix,
            str(obj),
            self.user,
            self.mask_string(retval),
        )

        if has_permission():
            logger.debug(
                "%s.display_value() User %s has permission to view the Secret value. Displaying actual value.",
                self.logger_prefix,
                self.user,
            )
            return retval

        logger.debug(
            "%s.display_value() User %s does not have permission to view the Secret value. Displaying masked value.",
            self.logger_prefix,
            self.user,
        )

        return self.mask_string(retval)

    display_value.short_description = "Value"

    def get_form(self, request, obj=None, change=False, **kwargs):
        # Get the base form class
        form = super().get_form(request, obj, change=change, **kwargs)

        # Create a dynamic subclass to inject the request/user at initialization
        class CustomForm(form):
            def __init__(self, *args, **kwargs):
                # Inject custom kwargs here
                kwargs["user"] = request.user
                super().__init__(*args, **kwargs)

        return CustomForm

    def save_model(self, request: HttpRequest, obj: Secret, form: SecretAdminForm, change):
        value = form.cleaned_data.get("value")
        if value:
            obj.encrypted_value = Secret.encrypt(value=value)
        super().save_model(request, obj, form, change)

    def get_queryset(self, request: HttpRequest):
        user = get_resolved_user(request.user)  # type: ignore
        qs = super().get_queryset(request)
        return smarter_filter_queryset_for_user(
            user=user,
            qs=qs,
        )


class CustomPasswordWidget(forms.Widget):
    """Custom widget for the password field in the UserChangeForm."""

    def render(self, name, value, attrs=None, renderer=None):
        """
        use a placeholder and let the admin render the anchor correctly
        This works because the admin will replace __pk__ with the actual user id
        """
        url = "../password/"  # relative to the change page, works in Django admin
        return mark_safe(f'<a href="{url}" style="color: blue;">CHANGE PASSWORD</a>')  # nosec


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
        if request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """
        Allow change permissions for superusers and to
        staff users if they are changing a user within their own account.
        """
        if request.user.is_superuser:
            return True
        if request.user.is_staff:
            try:
                if not obj:
                    return False
                user_profile = get_cached_user_profile(request.user)  # type: ignore
                obj_user_profile = get_cached_user_profile(obj)  # type: ignore
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
        userprofile = get_cached_user_profile(user=obj)
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
            user_profile = get_cached_user_profile(user)  # type: ignore
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
        if request.user.is_superuser:
            return qs
        return qs.none()


smarter_restricted_admin_site.register(Account, AccountAdmin)
smarter_restricted_admin_site.register(AccountContact, AccountContactAdmin)
smarter_restricted_admin_site.register(Charge, ChargeAdmin)
smarter_restricted_admin_site.register(DailyBillingRecord, DailyBillingRecordAdmin)
smarter_restricted_admin_site.register(PaymentMethod, PaymentMethodModelAdmin)
smarter_restricted_admin_site.register(Secret, SecretAdmin)
smarter_restricted_admin_site.register(UserProfile, RestrictedUserProfileAdmin)
smarter_restricted_admin_site.register(User, RestrictedUserAdmin)
