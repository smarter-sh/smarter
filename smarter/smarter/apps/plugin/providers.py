# -*- coding: utf-8 -*-
"""A Pythonic interface for working with plugins."""
import json

import yaml
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from smarter.apps.account.models import Account, UserProfile

from .models import (
    Plugin,
    PluginFunction,
    PluginPrompt,
    PluginSelector,
    PluginSelectorSearchStrings,
)
from .serializers import (
    PluginFunctionSerializer,
    PluginPromptSerializer,
    PluginSelectorSearchStringsSerializer,
    PluginSelectorSerializer,
    PluginSerializer,
)


User = settings.AUTH_USER_MODEL


# pylint: disable=too-many-instance-attributes
class PluginProvider:
    """A class for working with plugins."""

    plugin: Plugin
    plugin_serializer: PluginSerializer
    plugin_selector: PluginSelector
    plugin_selector_serializer: PluginSelectorSerializer
    plugin_selector_search_strings: PluginSelectorSearchStrings
    plugin_selector_search_strings_serializer: PluginSelectorSearchStringsSerializer
    plugin_prompt: PluginPrompt
    plugin_prompt_serializer: PluginPromptSerializer
    plugin_function: PluginFunction
    plugin_function_serializer: PluginFunctionSerializer

    def __init__(self, plugin_id: int = None):
        """Initialize the class."""

        if not plugin_id:
            return

        self.plugin_id = plugin_id

        self.plugin = Plugin.objects.get(pk=plugin_id)
        self.plugin_serializer = PluginSerializer(self.plugin)

        self.plugin_selector = PluginSelector.objects.get(pk=plugin_id)
        self.plugin_selector_serializer = PluginSelectorSerializer(self.plugin_selector)

        self.plugin_selector_search_strings = PluginSelectorSearchStrings.objects.get(pk=plugin_id)
        self.plugin_selector_search_strings_serializer = PluginSelectorSearchStringsSerializer(
            self.plugin_selector_search_strings
        )

        self.plugin_prompt = PluginPrompt.objects.get(pk=plugin_id)
        self.plugin_prompt_serializer = PluginPromptSerializer(self.plugin_prompt)

        self.plugin_function = PluginFunction.objects.get(pk=plugin_id)
        self.plugin_function_serializer = PluginFunctionSerializer(self.plugin_function)

    @classmethod
    def validate_operation(cls, data: dict) -> bool:
        """Validate a plugin."""
        meta = data.get("meta", {})

        user_id = meta.get("user_id")
        account_id = meta.get("account_id")
        plugin_id = meta.get("plugin_id")

        user = UserProfile.objects.get(pk=user_id)
        if not user:
            raise ValidationError("User not found.")

        account = Account.objects.get(pk=account_id)
        if not account:
            raise ValidationError("Account not found.")

        if not UserProfile.objects.filter(account=account, user=user):
            user = User.objects.get(pk=user_id)
            if not user.is_superuser:
                raise ValidationError("User is not associated with this account.")

        if plugin_id:
            plugin = Plugin.objects.get(pk=plugin_id)
            if not plugin:
                raise ValidationError("Plugin not found.")
            if plugin.account_id != account_id:
                raise ValidationError("Plugin is not associated with this account.")

        return True

    @classmethod
    def validate_write_operation(cls, data: dict) -> bool:
        meta = data.get("meta", {})
        selector = data.get("selector", {})
        search_terms = selector.get("search_terms", {})
        prompt = data.get("prompt", {})
        function = data.get("function", {})

        plugin_serializer = PluginSerializer(data=meta)
        if not plugin_serializer:
            raise ValidationError("Invalid plugin.")
        if not plugin_serializer.is_valid():
            raise ValidationError(plugin_serializer.errors)

        selector = data.get("selector", {})
        plugin_selector_serializer = PluginSelectorSerializer(data=selector)
        if not plugin_selector_serializer:
            raise ValidationError("Invalid plugin selector.")
        if not plugin_selector_serializer.is_valid():
            raise ValidationError(plugin_selector_serializer.errors)

        search_terms = selector.get("search_terms", {})
        plugin_selector_search_strings_serializer = PluginSelectorSearchStringsSerializer(data=search_terms)
        if not plugin_selector_search_strings_serializer:
            raise ValidationError("Invalid plugin selector search strings.")
        if not plugin_selector_search_strings_serializer.is_valid():
            raise ValidationError(plugin_selector_search_strings_serializer.errors)

        prompt = data.get("prompt", {})
        plugin_prompt_serializer = PluginPromptSerializer(data=prompt)
        if not plugin_prompt_serializer:
            raise ValidationError("Invalid plugin prompt.")
        if not plugin_prompt_serializer.is_valid():
            raise ValidationError(plugin_prompt_serializer.errors)

        function = data.get("function", {})
        plugin_function_serializer = PluginFunctionSerializer(data=function)
        if not plugin_function_serializer:
            raise ValidationError("Invalid plugin function.")
        if not plugin_function_serializer.is_valid():
            raise ValidationError(plugin_function_serializer.errors)

    @classmethod
    def create(cls, data: dict):
        """Create a plugin."""
        cls.validate_operation(data)
        cls.validate_write_operation(data)

        meta = data.get("meta", {})
        selector = data.get("selector", {})
        search_terms = selector.get("search_terms", {})
        prompt = data.get("prompt", {})
        function = data.get("function", {})

        with transaction.atomic():
            plugin_id = Plugin.objects.create(**meta)
            PluginSelector.objects.create(**selector)
            PluginSelectorSearchStrings.objects.create(**search_terms)
            PluginPrompt.objects.create(**prompt)
            PluginFunction.objects.create(**function)

        return cls(plugin_id=plugin_id)

    @classmethod
    def update(cls, data: dict):
        """Update a plugin."""
        cls.validate_operation(data)
        cls.validate_write_operation(data)

        meta = data.get("meta", {})
        selector = data.get("selector", {})
        search_terms = selector.get("search_terms", {})
        prompt = data.get("prompt", {})
        function = data.get("function", {})

        with transaction.atomic():
            plugin_id = Plugin.objects.update(**meta)
            PluginSelector.objects.update(**selector)
            PluginSelectorSearchStrings.objects.update(**search_terms)
            PluginPrompt.objects.update(**prompt)
            PluginFunction.objects.update(**function)

        return cls(plugin_id=plugin_id)

    @classmethod
    def delete(cls, data: dict):
        """Delete a plugin."""
        cls.validate_operation(data)
        plugin_id = data.get("plugin_id")
        plugin = Plugin.objects.get(pk=plugin_id)
        if not plugin:
            raise ValidationError("Plugin not found.")

        with transaction.atomic():
            Plugin.objects.delete(plugin)
            selector = PluginSelector.objects.get(plugin_id=plugin.id)
            selector.pluginselectorsearchstrings_set.all().delete()
            PluginSelector.objects.delete(plugin=plugin)
            PluginPrompt.objects.delete(plugin=plugin)
            PluginFunction.objects.delete(plugin=plugin)

        return True

    def to_json(self) -> dict:
        """Return a plugin in JSON format."""

        retval = {
            "meta": self.plugin_serializer.data,
            "selector": self.plugin_selector_serializer.data
            + {
                "search_terms": self.plugin_selector_search_strings_serializer.data,
            },
            "prompt": self.plugin_prompt_serializer.data,
            "function": self.plugin_function_serializer.data,
        }

        return retval

    def to_yaml(self) -> str:
        """Return a plugin in YAML format."""

        json_data = self.plugin_json(plugin_id=self.plugin_id)
        yaml_data = yaml.dump(json.loads(json_data))

        return yaml_data


class AccountProvider:
    """A class for working with plugins."""

    def __init__(self, account_id: int):
        """Initialize the class."""
        self.account_id = account_id

    @property
    def plugins(self) -> list[PluginProvider]:
        """Return a list of plugins for an account."""
        plugins = Plugin.objects.filter(account_id=self.account_id)

        retval = []
        for plugin in plugins:
            retval.append(PluginProvider(plugin_id=plugin.id).to_json)

        return retval
