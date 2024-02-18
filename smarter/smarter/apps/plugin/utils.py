# -*- coding: utf-8 -*-
"""Ultility functions for plugins."""

import logging
import os

import yaml


logger = logging.getLogger(__name__)
HERE = os.path.abspath(os.path.dirname(__file__))
PLUGINS_PATH = os.path.join(HERE, "data", "sample-plugins")


# pylint: disable=W0613,C0415
def user_init(sender, user_profile, **kwargs):
    """Create example plugins for a new user."""
    from .plugin import Plugin

    data: dict = None

    logger.info("Creating example plugins for user %s", user_profile.user.username)
    logger.info("Plugins path: %s", PLUGINS_PATH)
    for file in os.listdir(PLUGINS_PATH):
        if file.endswith(".yaml"):
            with open(os.path.join(PLUGINS_PATH, file), "r", encoding="utf-8") as file:
                data = yaml.safe_load(file.read())

            data["account"] = user_profile.account
            data["user"] = user_profile.user
            data["user_profile"] = user_profile

            logger.info(
                "user_profile %s, %s creating plugin %s",
                user_profile.account.company_name,
                user_profile.user.username,
                data["meta_data"]["name"],
            )
            Plugin(data=data)
