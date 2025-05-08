"""Plug helper functions for plugin unit tests."""

from datetime import datetime, timedelta

import requests

from smarter.apps.account.models import Account, Secret, UserProfile
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    get_cached_user_profile,
)
from smarter.common.exceptions import SmarterValueError

from ..manifest.enum import SAMPluginStaticMetadataClassValues
from ..models import PluginMeta


def secret_factory(user_profile: UserProfile, name: str, value: str) -> Secret:
    """Create a secret for the test case."""
    encrypted_value = Secret.encrypt(value)
    try:
        secret = Secret.objects.get(user_profile=user_profile, name=name)
        secret.encrypted_value = encrypted_value
        secret.save()
    except Secret.DoesNotExist:
        # Create a new secret if it doesn't exist
        secret = Secret(
            user_profile=user_profile,
            name=name,
            encrypted_value=encrypted_value,
        )
        secret.save()

    secret.description = "Test secret"
    secret.expires_at = datetime.now() + timedelta(days=365)
    secret.save()
    return secret


def plugin_meta_factory(plugin_class: str, account: Account, user_profile: UserProfile = None) -> PluginMeta:

    if not user_profile:
        user = get_cached_admin_user_for_account(account=account)
        user_profile = get_cached_user_profile(user=user)

    if not plugin_class in SAMPluginStaticMetadataClassValues.all_values():
        raise SmarterValueError(
            f"Invalid plugin class: {plugin_class}. should be one of {SAMPluginStaticMetadataClassValues.all_values()}"
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
