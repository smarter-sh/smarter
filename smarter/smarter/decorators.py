# -*- coding: utf-8 -*-
"""Smarter Decorators"""
from django.contrib.auth.decorators import user_passes_test


def superuser_required(function=None, redirect_field_name=None, login_url=None):
    """
    Decorator for views that checks that the user is logged in and is a superuser,
    redirecting to the login page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.is_superuser, login_url=login_url, redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
