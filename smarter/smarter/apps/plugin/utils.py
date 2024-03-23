# -*- coding: utf-8 -*-
"""Ultility functions for plugins."""

import os

import yaml
from django.contrib.auth import get_user_model

from smarter.apps.account.models import UserProfile

from .plugin import Plugin, PluginExamples, Plugins


HERE = os.path.abspath(os.path.dirname(__file__))
User = get_user_model()


# pylint: disable=W0613,C0415
def add_example_plugins(user_profile: UserProfile) -> bool:
    """Create example plugins for a new user."""

    plugin_examples = PluginExamples()
    data: dict = None

    for plugin in plugin_examples.plugins:
        data = plugin.to_yaml()
        data = yaml.safe_load(data)
        data["user_profile"] = user_profile
        Plugin(data=data)


def plugins_for_user(user: User) -> list[Plugin]:
    """
    Return the plugins for a user. If the user is associated with an account,
    return the plugins for that account. If the user is not associated with an
    account, return the plugins for the user.
    """
    try:
        user_profile = UserProfile.objects.get(user=user)
    except UserProfile.DoesNotExist:
        return Plugins(user=user).plugins

    return Plugins(account=user_profile.account).plugins
