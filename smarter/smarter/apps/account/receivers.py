# -*- coding: utf-8 -*-
# pylint: disable=unused-argument
"""Django signal receivers for account app."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Account, UserProfile


@receiver(post_save, sender=UserProfile)
def user_profile_post_save(sender, instance, created, **kwargs):
    if created:
        # This code will run after a new instance of MyModel is created
        print(f"A new instance of {sender.__name__} was created!")
    else:
        # This code will run after an existing instance of MyModel is saved
        print(f"An instance of {sender.__name__} was saved!")


@receiver(post_save, sender=Account)
def account_post_save(sender, instance, created, **kwargs):
    if created:
        # This code will run after a new instance of MyModel is created
        print(f"A new instance of {sender.__name__} was created!")
    else:
        # This code will run after an existing instance of MyModel is saved
        print(f"An instance of {sender.__name__} was saved!")
