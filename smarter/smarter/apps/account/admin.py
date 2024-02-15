# -*- coding: utf-8 -*-
"""Account admin."""
from django.contrib import admin

from .models import Account, PaymentMethodModel, UserProfile


# Register your models here.
class AccountModelAdmin(admin.ModelAdmin):
    """Account model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )


class UserProfileAdmin(admin.ModelAdmin):
    """User profile admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )


class PaymentMethodModelAdmin(admin.ModelAdmin):
    """Payment method model admin."""

    readonly_fields = (
        "created_at",
        "updated_at",
    )


admin.site.register(Account, AccountModelAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(PaymentMethodModel, PaymentMethodModelAdmin)
