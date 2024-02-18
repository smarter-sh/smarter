# -*- coding: utf-8 -*-
"""Ultility functions for plugins."""

import os

import yaml

from smarter.apps.account.signals import new_user_created

from .plugin import Plugin


# pylint: disable=W0613
def user_init(sender, user_profile, **kwargs):
    """Create example plugins for a new user."""

    for file in os.listdir("./data/sample-plugins"):
        if file.endswith(".yaml"):
            with open(f"./data/sample-plugins/{file}", "r", encoding="utf-8") as file:
                data = file.read()
                if data:
                    try:
                        data = yaml.safe_load(data)
                    except yaml.YAMLError as exc:
                        print("Error in plugin file:", exc)

                    data["account"] = user_profile.account
                    data["user"] = user_profile.user
                    data["user_profile"] = user_profile
                    Plugin(data=data)


# pylint: disable=E1120
new_user_created.connect(user_init)
