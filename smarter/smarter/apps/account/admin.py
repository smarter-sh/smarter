# -*- coding: utf-8 -*-
"""Account admin."""
from django.contrib import admin

from .models import Account, APIKey, PaymentMethod, UserProfile


# Register your models here.
class AccountAdmin(admin.ModelAdmin):
    """Account model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("company_name", "account_number", "created_at", "updated_at")


class UserProfileAdmin(admin.ModelAdmin):
    """User profile admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("user", "account", "created_at", "updated_at")


class PaymentMethodModelAdmin(admin.ModelAdmin):
    """Payment method model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )
    list_display = ("name", "created_at", "updated_at")


class APIKeyModelAdmin(admin.ModelAdmin):
    """API Key model admin."""

    readonly_fields = ("created",)
    # pylint: disable=W0212
    list_display = [field.name for field in APIKey._meta.get_fields()]


admin.site.register(Account, AccountAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(PaymentMethod, PaymentMethodModelAdmin)
admin.site.register(APIKey, APIKeyModelAdmin)
