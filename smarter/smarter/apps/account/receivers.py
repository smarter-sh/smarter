# -*- coding: utf-8 -*-
# pylint: disable=unused-argument
"""Django signal receivers for account app."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Account, UserProfile


@receiver(post_save, sender=UserProfile)
def user_profile_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of UserProfile model."""


@receiver(post_save, sender=Account)
def account_post_save(sender, instance, created, **kwargs):
    """Signal receiver for created/saved of Account model."""
