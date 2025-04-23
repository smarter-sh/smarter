# pylint: disable=C0115,W0212
"""Account admin."""

import logging

from django import forms
from django.contrib import admin
from django.core.handlers.wsgi import WSGIRequest

from smarter.lib.django.admin import RestrictedModelAdmin

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


@admin.register(Account)
class AccountAdmin(RestrictedModelAdmin):
    """Account model admin."""

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
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(id=user_profile.account.id)
        except UserProfile.DoesNotExist:
            return qs.none()


@admin.register(AccountContact)
class AccountContactAdmin(RestrictedModelAdmin):
    """AccountContact model admin."""

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
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


@admin.register(Charge)
class ChargeAdmin(RestrictedModelAdmin):
    """Charge model admin."""

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


@admin.register(DailyBillingRecord)
class DailyBillingRecordAdmin(RestrictedModelAdmin):
    """DailyBillingRecord model admin."""

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


@admin.register(PaymentMethod)
class PaymentMethodModelAdmin(RestrictedModelAdmin):
    """Payment method model admin."""

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
            user_profile = UserProfile.objects.get(user=request.user)
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
        logger.info("Initializing SecretAdminForm with instance: %s", self.instance)
        if self.instance and self.instance.pk:
            try:
                instance: Secret = self.instance
                self.fields["value"].initial = instance.get_secret(update_last_accessed=False)
            except Exception:
                self.fields["value"].initial = None

    def clean(self):
        """Ensure the transient 'value' field is included in cleaned_data."""
        cleaned_data = super().clean()
        if "value" not in cleaned_data:
            raise forms.ValidationError("The 'value' field is required.")
            # cleaned_data["value"] = self.data.get("value", "")
        return cleaned_data

    def order_fields(self, field_order):
        super().order_fields(field_order)
        if "value" not in self.fields:
            raise ValueError("The 'value' field is missing from the form.")
        else:
            logger.info("The 'value' field is present in the form.")

    def get_initial_for_field(self, field, field_name):
        if field_name == "value":
            logger.info("Getting initial value for 'value' field.")
            instance: Secret = self.instance
            return instance.get_secret(update_last_accessed=False) if self.instance and self.instance.pk else ""
        return super().get_initial_for_field(field, field_name)

    def clean_value(self):
        value = self.cleaned_data.get("value")
        if value and not isinstance(value, str):
            raise forms.ValidationError("The value must be a string.")
        return value


@admin.register(Secret)
class SecretAdmin(RestrictedModelAdmin):
    """Secret model admin."""

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logger.info("Initializing SecretAdmin")

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
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()
