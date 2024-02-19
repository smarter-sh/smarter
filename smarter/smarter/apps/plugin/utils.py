# -*- coding: utf-8 -*-
"""Ultility functions for plugins."""

import os

import yaml

from smarter.apps.account.models import UserProfile


HERE = os.path.abspath(os.path.dirname(__file__))
PLUGINS_PATH = os.path.join(HERE, "data", "sample-plugins")


# pylint: disable=W0613,C0415
def add_example_plugins(user_profile: UserProfile) -> bool:
    """Create example plugins for a new user."""
    from .plugin import Plugin

    data: dict = None

    for file in os.listdir(PLUGINS_PATH):
        if file.endswith(".yaml"):
            with open(os.path.join(PLUGINS_PATH, file), "r", encoding="utf-8") as file:
                data = yaml.safe_load(file.read())

            data["meta_data"]["author"] = user_profile.id
            data["account"] = user_profile.account
            data["user"] = user_profile.user
            data["user_profile"] = user_profile

            Plugin(data=data)
