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
    SmarterStaffOnlyModelAdmin,
    SmarterSuperUserOnlyModelAdmin,
    smarter_is_staff,
    smarter_restricted_admin_site,
)

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

    class Meta:
        model = Account

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("company_name", "account_number", "created_at", "updated_at")

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = get_cached_user_profile(request.user)  # type: ignore
            return qs.filter(id=user_profile.account.id)
        except UserProfile.DoesNotExist:
            logger.error("UserProfile does not exist for user %s", request.user.username)
            return qs.none()


# @admin.register(AccountContact)
class AccountContactAdmin(SmarterStaffOnlyModelAdmin):
    """AccountContact model admin."""

    class Meta:
        model = AccountContact

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("account", "first_name", "last_name", "email", "phone", "is_primary")

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = get_cached_user_profile(request.user)  # type: ignore
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            logger.error("UserProfile does not exist for user %s", request.user.username)
            return qs.none()


# @admin.register(Charge)
class ChargeAdmin(SmarterStaffOnlyModelAdmin):
    """Charge model admin."""

    class Meta:
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
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.is_staff:
            user_profile = get_cached_user_profile(request.user)  # type: ignore
            return qs.filter(account=user_profile.account)
        return qs.none()


# @admin.register(DailyBillingRecord)
class DailyBillingRecordAdmin(SmarterStaffOnlyModelAdmin):
    """DailyBillingRecord model admin."""

    class Meta:
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
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        if request.user.is_staff:
            user_profile = get_cached_user_profile(request.user)  # type: ignore
            return qs.filter(account=user_profile.account)
        return qs.none()


# @admin.register(PaymentMethod)
class PaymentMethodModelAdmin(SmarterStaffOnlyModelAdmin):
    """Payment method model admin."""

    class Meta:
        model = PaymentMethod

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("name", "created_at", "updated_at")

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = get_cached_user_profile(request.user)  # type: ignore
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class SecretAdminForm(forms.ModelForm):
    """Custom form for SecretAdmin to handle the transient 'value' field."""

    value = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text="Put your secret here...",
    )

    class Meta:
        model = Secret
        fields = ("name", "user_profile", "description", "expires_at", "value")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                instance: Secret = self.instance
                self.fields["value"].initial = instance.get_secret(update_last_accessed=False)
            # pylint: disable=broad-except
            except Exception:
                self.fields["value"].initial = None

    def clean(self):
        """Ensure the transient 'value' field is included in cleaned_data."""
        cleaned_data = super().clean()
        if not cleaned_data or "value" not in cleaned_data:
            raise forms.ValidationError("The 'value' field is required.")
        return cleaned_data

    def get_initial_for_field(self, field, field_name):
        if field_name == "value":
            instance: Secret = self.instance
            return instance.get_secret(update_last_accessed=False) if self.instance and self.instance.pk else ""
        return super().get_initial_for_field(field, field_name)

    def clean_value(self):
        value = self.cleaned_data.get("value")
        if value and not isinstance(value, str):
            raise forms.ValidationError("The value must be a string.")
        return value


# @admin.register(Secret)
class SecretAdmin(SmarterStaffOnlyModelAdmin):
    """Secret model admin."""

    class Meta:
        model = Secret

    form = SecretAdminForm
    readonly_fields = (
        "created_at",
        "updated_at",
        "last_accessed",
        "encrypted_value",
    )
    fields = (
        "name",
        "user_profile",
        "description",
        "expires_at",
        "value",
    )
    list_display = ("user_profile", "name", "description", "created_at", "updated_at", "last_accessed", "expires_at")

    def save_model(self, request: HttpRequest, obj: Secret, form: SecretAdminForm, change):
        value = form.cleaned_data.get("value")
        if value:
            obj.encrypted_value = Secret.encrypt(value=value)
        super().save_model(request, obj, form, change)

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = get_cached_user_profile(request.user)  # type: ignore
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class CustomPasswordWidget(forms.Widget):
    """Custom widget for the password field in the UserChangeForm."""

    def render(self, name, value, attrs=None, renderer=None):
        """
        use a placeholder and let the admin render the anchor correctly
        This works because the admin will replace __pk__ with the actual user id
        """
        url = "../password/"  # relative to the change page, works in Django admin
        return mark_safe(f'<a href="{url}" style="color: blue;">CHANGE PASSWORD</a>')  # nosec


class UserChangeForm(forms.ModelForm):
    """Custom form for the User model that includes a link to change the password."""

    password = forms.CharField(widget=CustomPasswordWidget(), label=_("Password"))

    class Meta:
        model = User
        fields = "__all__"


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
    form = UserChangeForm

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
                if user_profile.account == obj_user_profile.account:
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
        if not user:
            return qs.none()
        if user and user.is_superuser:
            return qs
        if user and user.is_staff:
            try:
                user_profile = get_cached_user_profile(user)  # type: ignore
                return qs.filter(
                    id__in=UserProfile.objects.filter(account=user_profile.account).values_list("user_id", flat=True)
                )
            except UserProfile.DoesNotExist as e:
                logger.error("UserProfile does not exist for user %s, %s", user.username, e)
                return qs.none()
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

    class Meta:
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
