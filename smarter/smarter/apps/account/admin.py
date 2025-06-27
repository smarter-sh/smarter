# pylint: disable=C0115,W0212
"""Account admin."""

from django import forms
from django.contrib.auth.admin import UserAdmin

# from django.contrib import admin
from django.core.handlers.wsgi import WSGIRequest
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from smarter.apps.account.models import UserClass as User
from smarter.apps.account.models import get_resolved_user
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.dashboard.admin import (
    RestrictedModelAdmin,
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


# @admin.register(Account)
class AccountAdmin(RestrictedModelAdmin):
    """Account model admin."""

    class Meta:
        model = Account

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("company_name", "account_number", "created_at", "updated_at")

    def get_queryset(self, request: WSGIRequest):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = get_cached_user_profile(request.user)
            return qs.filter(id=user_profile.account.id)
        except UserProfile.DoesNotExist:
            return qs.none()


# @admin.register(AccountContact)
class AccountContactAdmin(RestrictedModelAdmin):
    """AccountContact model admin."""

    class Meta:
        model = AccountContact

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("account", "first_name", "last_name", "email", "phone", "is_primary")

    def get_queryset(self, request: WSGIRequest):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = get_cached_user_profile(request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


# @admin.register(Charge)
class ChargeAdmin(RestrictedModelAdmin):
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
        return qs.none()


# @admin.register(DailyBillingRecord)
class DailyBillingRecordAdmin(RestrictedModelAdmin):
    """DailyBillingRecord model admin."""

    class Meta:
        model = DailyBillingRecord

    def get_readonly_fields(self, request: WSGIRequest, obj=None):
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

    def get_queryset(self, request: WSGIRequest):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.none()


# @admin.register(PaymentMethod)
class PaymentMethodModelAdmin(RestrictedModelAdmin):
    """Payment method model admin."""

    class Meta:
        model = PaymentMethod

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("name", "created_at", "updated_at")

    def get_queryset(self, request: WSGIRequest):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = get_cached_user_profile(request.user)
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
        if "value" not in cleaned_data:
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
class SecretAdmin(RestrictedModelAdmin):
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

    def save_model(self, request: WSGIRequest, obj: Secret, form: SecretAdminForm, change):
        value = form.cleaned_data.get("value")
        if value:
            obj.encrypted_value = Secret.encrypt(value=value)
        super().save_model(request, obj, form, change)

    def get_queryset(self, request: WSGIRequest):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = get_cached_user_profile(request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class CustomPasswordWidget(forms.Widget):
    """Custom widget for the password field in the UserChangeForm."""

    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe('<a href="password/" style="color: blue;">CHANGE PASSWORD</a>')  # nosec


class UserChangeForm(forms.ModelForm):
    """Custom form for the User model that includes a link to change the password."""

    password = forms.CharField(widget=CustomPasswordWidget(), label=_("Password"))

    class Meta:
        model = User
        fields = "__all__"


class RestrictedUserAdmin(UserAdmin):
    """Custom User admin that restricts access to users based on their account."""

    form = UserChangeForm

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = get_resolved_user(request.user)
        if not user:
            return qs.none()
        if user and user.is_superuser:
            return qs
        try:
            if user.is_authenticated:
                user_profile = get_cached_user_profile(user=user)  # type: ignore
                return qs.filter(account=user_profile.account)  # type: ignore
        except UserProfile.DoesNotExist:
            return qs.none()

    def get_readonly_fields(self, request, obj=None):
        user = get_resolved_user(request.user)
        if not user:
            return ["username", "email", "first_name", "last_name", "is_staff", "is_active", "date_joined"]
        if user.is_superuser:
            return ("username", "last_login", "date_joined")
        return super().get_readonly_fields(request, obj)


smarter_restricted_admin_site.register(Account, AccountAdmin)
smarter_restricted_admin_site.register(AccountContact, AccountContactAdmin)
smarter_restricted_admin_site.register(Charge, ChargeAdmin)
smarter_restricted_admin_site.register(DailyBillingRecord, DailyBillingRecordAdmin)
smarter_restricted_admin_site.register(PaymentMethod, PaymentMethodModelAdmin)
smarter_restricted_admin_site.register(Secret, SecretAdmin)
smarter_restricted_admin_site.register(UserProfile, RestrictedModelAdmin)
