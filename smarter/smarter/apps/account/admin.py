"""Account admin."""

from django.contrib import admin

from smarter.lib.django.admin import RestrictedModelAdmin

from .models import Account, AccountContact, Charge, PaymentMethod, UserProfile


# Register your models here.
class AccountAdmin(RestrictedModelAdmin):
    """Account model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("company_name", "account_number", "created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(id=user_profile.account.id)
        except UserProfile.DoesNotExist:
            return qs.none()


class AccountContactAdmin(RestrictedModelAdmin):
    """AccountContact model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("account", "first_name", "last_name", "email", "phone", "is_primary")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class ChargeAdmin(RestrictedModelAdmin):
    """Charge model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("created_at", "account", "user", "charge_type", "total_tokens", "model")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


class PaymentMethodModelAdmin(RestrictedModelAdmin):
    """Payment method model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("name", "created_at", "updated_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            return qs.filter(account=user_profile.account)
        except UserProfile.DoesNotExist:
            return qs.none()


admin.site.register(Account, AccountAdmin)
admin.site.register(AccountContact, AccountContactAdmin)
admin.site.register(PaymentMethod, PaymentMethodModelAdmin)
admin.site.register(Charge, ChargeAdmin)
