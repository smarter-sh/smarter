# -*- coding: utf-8 -*-
"""Account admin."""
from django.contrib import admin

from smarter.apps.web_platform.admin import RestrictedModelAdmin

from .models import Account, PaymentMethod, UserProfile


# Register your models here.
class AccountAdmin(RestrictedModelAdmin):
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


admin.site.register(Account, AccountAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(PaymentMethod, PaymentMethodModelAdmin)
