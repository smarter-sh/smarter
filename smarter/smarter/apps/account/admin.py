"""Account admin."""

from django.contrib import admin

from smarter.lib.django.user import User

from .models import Account, AccountContact, Charge, PaymentMethod, UserProfile


class UserAdmin(admin.ModelAdmin):
    """User model admin."""

    readonly_fields = ("date_joined",)
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff", "is_superuser")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            same_account_users = UserProfile.objects.filter(account=user_profile.account)
            return qs.filter(id__in=[user.user_id for user in same_account_users])
        except UserProfile.DoesNotExist:
            return qs.none()


# Register your models here.
class AccountAdmin(admin.ModelAdmin):
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


class AccountContactAdmin(admin.ModelAdmin):
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


class ChargeAdmin(admin.ModelAdmin):
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


class PaymentMethodModelAdmin(admin.ModelAdmin):
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


# Unregister default Django User, Group, and Permission models
admin.site.unregister(User)

admin.site.register(User, UserAdmin)
admin.site.register(Account, AccountAdmin)
admin.site.register(AccountContact, AccountContactAdmin)
admin.site.register(PaymentMethod, PaymentMethodModelAdmin)
admin.site.register(Charge, ChargeAdmin)
