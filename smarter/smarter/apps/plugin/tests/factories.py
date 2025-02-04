"""Plug helper functions for plugin unit tests."""

import requests

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    get_cached_user_profile,
)
from smarter.common.exceptions import SmarterValueError

from ..manifest.enum import SAMPluginMetadataClassValues
from ..models import PluginMeta


def plugin_meta_factory(plugin_class: str, account: Account, user_profile: UserProfile = None) -> PluginMeta:

    if not user_profile:
        user = get_cached_admin_user_for_account(account=account)
        user_profile = get_cached_user_profile(user=user)

    if not plugin_class in SAMPluginMetadataClassValues.all_values():
        raise SmarterValueError(
            f"Invalid plugin class: {plugin_class}. should be one of {SAMPluginMetadataClassValues.all_values()}"
        )

    meta_data = PluginMeta(
        account=account,
        name="Test Plugin",
        description="Test Plugin Description",
        plugin_class=plugin_class,
        version="1.0.0",
        author=user_profile,
    )
    meta_data.save()

    return meta_data


def create_generic_request():
    url = "http://example.com"
    headers = {"Content-Type": "application/json"}
    data = {}

    request = requests.Request("GET", url, headers=headers, data=data)
    prepared_request = request.prepare()

    return prepared_request
