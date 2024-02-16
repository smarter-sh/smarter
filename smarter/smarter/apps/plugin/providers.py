# -*- coding: utf-8 -*-
"""A Pythonic interface for working with plugins."""

import yaml
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from smarter.apps.account.models import Account, UserProfile

from .models import PluginData, PluginMeta, PluginPrompt, PluginSelector
from .serializers import (
    PluginDataSerializer,
    PluginMetaSerializer,
    PluginPromptSerializer,
    PluginSelectorSerializer,
)


User = get_user_model()


# pylint: disable=too-many-instance-attributes
class Plugin:
    """A class for working with plugins."""

    plugin: PluginMeta
    plugin_meta_serializer: PluginMetaSerializer
    plugin_selector: PluginSelector
    plugin_selector_serializer: PluginSelectorSerializer
    plugin_prompt: PluginPrompt
    plugin_prompt_serializer: PluginPromptSerializer
    plugin_data: PluginData
    plugin_data_serializer: PluginDataSerializer

    def __init__(self, plugin_id: int = None):
        """Initialize the class."""

        if not plugin_id:
            return

        self.plugin_id = plugin_id

        self.plugin = PluginMeta.objects.get(pk=plugin_id)
        self.plugin_meta_serializer = PluginMetaSerializer(self.plugin)

        self.plugin_selector = PluginSelector.objects.get(pk=plugin_id)
        self.plugin_selector_serializer = PluginSelectorSerializer(self.plugin_selector)

        self.plugin_prompt = PluginPrompt.objects.get(pk=plugin_id)
        self.plugin_prompt_serializer = PluginPromptSerializer(self.plugin_prompt)

        self.plugin_data = PluginData.objects.get(pk=plugin_id)
        self.plugin_data_serializer = PluginDataSerializer(self.plugin_data)

    @classmethod
    def is_valid_yaml(cls, data):
        try:
            yaml.safe_load(data)
            return True
        except yaml.YAMLError:
            return False

    @classmethod
    def validate_operation(cls, data: dict) -> bool:
        """Validate a plugin."""
        user = data.get("user")
        user_profile = UserProfile.objects.get(user_id=user.id)
        plugin = data.get("plugin")

        # plugin is optional, but if its provided then the account value supersedes
        # the account value passed in the data dictionary.
        if plugin:
            if not isinstance(plugin, PluginMeta):
                raise ValidationError("Invalid plugin. Must be a PluginMeta instance.")
            account = plugin.account
        else:
            account = data.get("account")

        if not isinstance(user, User):
            raise ValidationError("Invalid user. Must be a User instance.")
        if not user_profile:
            raise ValidationError("User not found.")

        if not isinstance(account, Account):
            raise ValidationError("Invalid account. Must be an Account instance.")
        if not account:
            raise ValidationError("Account not found.")

        # Ensure the user is associated with the account, or is a superuser, or is
        # the author of the plugin.
        if not UserProfile.objects.get(user_id=user_profile.user.id, account=account):
            if not user.is_superuser and not user.id == plugin.author.id:
                raise ValidationError("User is not associated with this account.")

        return True

    @classmethod
    def validate_write_operation(cls, data: dict) -> bool:
        meta_data = data.get("meta_data")
        selector = data.get("selector")
        prompt = data.get("prompt")
        plugin_data = data.get("plugin_data")

        # Validate plugin meta_data
        plugin_meta_serializer = PluginMetaSerializer(data=meta_data)
        if not plugin_meta_serializer:
            raise ValidationError("Invalid plugin.")
        if not plugin_meta_serializer.is_valid():
            raise serializers.ValidationError(plugin_meta_serializer.errors)

        # Validate plugin selector
        selector = data.get("selector")
        plugin_selector_serializer = PluginSelectorSerializer(data=selector)
        if not plugin_selector_serializer:
            raise ValidationError("Invalid plugin selector.")
        if not plugin_selector_serializer.is_valid():
            raise ValidationError(plugin_selector_serializer.errors)

        # Validate plugin prompt
        prompt = data.get("prompt")
        plugin_prompt_serializer = PluginPromptSerializer(data=prompt)
        if not plugin_prompt_serializer:
            raise ValidationError("Invalid plugin prompt.")
        if not plugin_prompt_serializer.is_valid():
            raise ValidationError(plugin_prompt_serializer.errors)

        # Validate plugin plugin_data
        plugin_data = data.get("plugin_data")
        plugin_data_serializer = PluginDataSerializer(data=plugin_data)
        if not plugin_data_serializer:
            raise ValidationError("Invalid plugin plugin_data.")
        if not plugin_data_serializer.is_valid():
            raise ValidationError(plugin_data_serializer.errors)

    @classmethod
    def create(cls, data):
        """Create a plugin"""

        if not isinstance(data, dict):
            if cls.is_valid_yaml(data):
                data = yaml.safe_load(data)
            else:
                raise ValidationError("Invalid data: must be a dictionary or valid YAML.")

        cls.validate_operation(data)
        cls.validate_write_operation(data)

        account = data.get("account")
        plugin = data.get("plugin")

        meta_data = data.get("meta_data")
        selector = data.get("selector")
        prompt = data.get("prompt")
        plugin_data = data.get("plugin_data")

        # Convert author_id to author
        author_id = meta_data.get("author")
        author = UserProfile.objects.get(id=author_id)
        meta_data["author"] = author
        meta_data["account"] = account

        # remove search_terms from selector
        del selector["search_terms"]

        with transaction.atomic():
            plugin = PluginMeta.objects.create(**meta_data)
            selector["plugin_id"] = plugin.id
            PluginSelector.objects.create(**selector)

            prompt["plugin_id"] = plugin.id
            PluginPrompt.objects.create(**prompt)

            plugin_data["plugin_id"] = plugin.id
            PluginData.objects.create(**plugin_data)

        return plugin

    @classmethod
    def update(cls, data: dict):
        """Update a plugin."""
        cls.validate_operation(data)
        cls.validate_write_operation(data)

        meta_data = data.get("meta_data")
        selector = data.get("selector")
        prompt = data.get("prompt")
        plugin_data = data.get("plugin_data")

        with transaction.atomic():
            plugin_id = PluginMeta.objects.update(**meta_data)
            PluginSelector.objects.update(**selector)
            PluginPrompt.objects.update(**prompt)
            PluginData.objects.update(**plugin_data)

        return cls(plugin_id=plugin_id)

    @classmethod
    def delete(cls, data: dict):
        """Delete a plugin."""
        cls.validate_operation(data)
        plugin_id = data.get("plugin_id")
        plugin = PluginMeta.objects.get(pk=plugin_id)
        if not plugin:
            raise ValidationError("PluginMeta not found.")

        with transaction.atomic():
            selector = PluginSelector.objects.get(plugin=plugin)
            prompt = PluginPrompt.objects.get(plugin=plugin)
            data = PluginData.objects.get(plugin=plugin)
            selector.delete()
            prompt.delete()
            data.delete()
            plugin.delete()

        return True

    def to_json(self) -> dict:
        """Return a plugin in JSON format."""

        retval = {
            "meta_data": self.plugin_meta_serializer.data,
            "selector": self.plugin_selector_serializer.data,
            "prompt": self.plugin_prompt_serializer.data,
            "plugin_data": self.plugin_data_serializer.data,
        }

        return retval


class AccountProvider:
    """A class for working with plugins."""

    def __init__(self, account_id: int):
        """Initialize the class."""
        self.account_id = account_id

    @property
    def plugins(self) -> list[Plugin]:
        """Return a list of plugins for an account."""
        plugins = PluginMeta.objects.filter(account_id=self.account_id)

        retval = []
        for plugin in plugins:
            retval.append(Plugin(plugin_id=plugin.id).to_json)

        return retval
