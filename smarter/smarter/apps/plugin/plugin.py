# -*- coding: utf-8 -*-
"""A Compound Model class for managing plugins."""

import logging

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
from .signals import plugin_created, plugin_deleted, plugin_updated


User = get_user_model()
logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class Plugin:
    """A class for working with plugins."""

    user = None
    user_profile: UserProfile = None
    account: Account = None

    plugin_meta: PluginMeta = None
    plugin_selector: PluginSelector = None
    plugin_prompt: PluginPrompt = None
    plugin_data: PluginData = None

    plugin_data_serializer: PluginDataSerializer = None
    plugin_prompt_serializer: PluginPromptSerializer = None
    plugin_selector_serializer: PluginSelectorSerializer = None
    plugin_meta_serializer: PluginMetaSerializer = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        user_id: int = None,
        account_id: int = None,
        plugin_id: int = None,
        plugin_meta: PluginMeta = None,
        data=None,
    ):
        """
        Initialize the class.

        id: pk of PluginMeta
        plugin_meta: a PluginMeta instance
        data: yaml or dict representation of a plugin
        """
        if user_id:
            self.user = User.objects.get(pk=user_id)
            self.user_profile = UserProfile.objects.get(user_id=user_id)
            self.account = self.user_profile.account

        if account_id:
            account = Account.objects.get(pk=account_id)
            if self.account and account.id != self.account.id:
                raise ValidationError("Account provided does not match user account.")

        if self.user and self.account:
            # pylint: disable=W0707
            try:
                UserProfile.objects.get(user_id=self.user.id, account_id=self.account.id)
            except UserProfile.DoesNotExist:
                raise ValidationError("User is not associated with this account.")

        if plugin_id:
            self.id = plugin_id
            logger.debug("Initialized using plugin_id.")

        # creating a new plugin from data
        if data and not self.id:
            self.create(data)
            self.id = self.plugin_meta.id
            logger.debug("Initialed with data.")

        if plugin_meta and not self.id:
            self.id = plugin_meta.id
            logger.debug("Initialized with plugin_meta.")

        if self.user and self.account:
            if self.user.is_superuser:
                return

            if self.user.id != self.plugin_meta.author.id:
                raise ValidationError("User does not own this plugin.")

            if self.account.id != self.plugin_meta.account.id:
                raise ValidationError("Account provided does not own this plugin.")

    def __str__(self) -> str:
        """Return the name of the plugin."""
        return self.name

    @property
    def id(self) -> int:
        """Return the id of the plugin."""
        if self.plugin_meta:
            return self.plugin_meta.id
        return None

    @id.setter
    def id(self, value: int):
        """Set the id of the plugin."""
        self.plugin_meta = PluginMeta.objects.get(pk=value)
        self.plugin_meta_serializer = PluginMetaSerializer(self.plugin_meta)

        self.plugin_selector = PluginSelector.objects.get(pk=value)
        self.plugin_selector_serializer = PluginSelectorSerializer(self.plugin_selector)

        self.plugin_prompt = PluginPrompt.objects.get(pk=value)
        self.plugin_prompt_serializer = PluginPromptSerializer(self.plugin_prompt)

        self.plugin_data = PluginData.objects.get(pk=value)
        self.plugin_data_serializer = PluginDataSerializer(self.plugin_data)

        self.validate()

    @property
    def name(self) -> str:
        """Return the name of the plugin."""
        if self.plugin_meta:
            return self.plugin_meta.name
        return None

    @property
    # pylint: disable=too-many-return-statements
    def ready(self) -> bool:
        """Return whether the plugin is ready."""
        # validate the models
        if not isinstance(self.plugin_meta, PluginMeta):
            return False
        if not isinstance(self.plugin_selector, PluginSelector):
            return False
        if not isinstance(self.plugin_prompt, PluginPrompt):
            return False
        if not isinstance(self.plugin_data, PluginData):
            return False

        # validate the serializers
        if not isinstance(self.plugin_meta_serializer, PluginMetaSerializer):
            return False
        if not isinstance(self.plugin_selector_serializer, PluginSelectorSerializer):
            return False
        if not isinstance(self.plugin_prompt_serializer, PluginPromptSerializer):
            return False
        if not isinstance(self.plugin_data_serializer, PluginDataSerializer):
            return False

        return True

    @property
    def data(self) -> dict:
        """Return the plugin as a dictionary."""
        if self.ready:
            return self.to_json()
        return None

    @property
    def yaml(self) -> str:
        """Return the plugin as a yaml string."""
        if self.ready:
            return yaml.dump(self.to_json())
        return None

    def is_valid_yaml(self, data):
        """Validate a yaml string."""
        try:
            yaml.safe_load(data)
            return True
        except yaml.YAMLError:
            return False

    def validate(self):
        """Validate the plugin."""
        if not self.ready:
            raise ValidationError("Plugin is not ready.")

        # pylint: disable=W0707
        try:
            UserProfile.objects.get(user_id=self.plugin_meta.author.id, account=self.plugin_meta.account)
        except UserProfile.DoesNotExist:
            raise ValidationError("Plugin author is not associated with this account.")

    def validate_operation(self, data: dict) -> bool:
        """
        Validate business rules. Namely, we want to ensure that the user is
        associated with the account, or is a superuser, or is the author of the plugin.
        """
        user = self.user or data.get("user")
        user_profile = self.user_profile or UserProfile.objects.get(user_id=user.id)
        plugin = data.get("plugin")

        # plugin is optional, but if its provided then the account value supersedes
        # the account value passed in the data dictionary.
        if plugin:
            if not isinstance(plugin, PluginMeta):
                raise ValidationError("Invalid plugin. Must be a PluginMeta instance.")
            account = plugin.account
        else:
            account = self.account or data.get("account")

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

    def validate_write_operation(self, data: dict) -> bool:
        """Validate the structural integrity of the input dict."""
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

    def create(self, data):
        """Create a plugin from either yaml or a dictionary."""

        if not isinstance(data, dict):
            # assume that we received a yaml string.
            # validate it and convert it to a dictionary.
            if self.is_valid_yaml(data):
                data = yaml.safe_load(data)
            else:
                raise ValidationError("Invalid data: must be a dictionary or valid YAML.")

        self.validate_operation(data)
        self.validate_write_operation(data)

        account = self.account or data.get("account")

        # initialize the major sections of the plugin yaml file
        meta_data = data.get("meta_data")
        selector = data.get("selector")
        prompt = data.get("prompt")
        plugin_data = data.get("plugin_data")

        data_author = meta_data.get("author")
        data_user = data.get("user")
        data_account = data.get("account")
        if self.user and data_user and self.user.id != data_user.id:
            logger.warning(
                "Inconsistent User data received: %s != %s. Using %s",
                self.user.get_username(),
                data_user.username,
                self.user.get_username(),
            )

        if self.account and data_account and self.account.id != data_account.id:
            logger.warning(
                "Inconsistent Account data received: %s != %s. Using %s",
                self.account.company_name,
                data_account.company_name,
                self.account.company_name,
            )

        if self.user_profile and data_author and self.user_profile.id != data_author.id:
            logger.warning(
                "Inconsistent Author data received: %s != %s. Using %s",
                self.user_profile.user.get_username(),
                data_author.user.username,
                self.user_profile.user.get_username(),
            )

        # Convert author_id to author
        author_id = self.user_profile.id if self.user_profile else meta_data.get("author")
        author = UserProfile.objects.get(id=author_id)
        meta_data["author"] = author
        meta_data["account"] = account

        # account/name is unique, so if the plugin already exists,
        # then update it instead of creating a new one.
        plugin_meta = PluginMeta.objects.filter(account=account, name=meta_data["name"]).first()
        if plugin_meta:
            logger.info("Plugin %s already exists. Updating plugin %s.", meta_data["name"], plugin_meta.id)
            return self.update(data)

        with transaction.atomic():
            self.plugin_meta = PluginMeta.objects.create(**meta_data)

            selector["plugin_id"] = self.plugin_meta.id
            prompt["plugin_id"] = self.plugin_meta.id
            plugin_data["plugin_id"] = self.plugin_meta.id

            self.plugin_selector = PluginSelector.objects.create(**selector)
            self.plugin_prompt = PluginPrompt.objects.create(**prompt)
            self.plugin_data = PluginData.objects.create(**plugin_data)

            self.id = self.plugin_meta.id
            plugin_created.send(sender=self.__class__, plugin=self)
            logger.info("Created plugin %s: %s.", meta_data["name"], self.plugin_meta.id)

        return True

    def update(self, data: dict = None):
        """Update a plugin."""

        if not data:
            self.save()
            return True

        self.validate_operation(data)
        self.validate_write_operation(data)

        meta_data = data.get("meta_data")
        selector = data.get("selector")
        prompt = data.get("prompt")
        plugin_data = data.get("plugin_data")

        with transaction.atomic():
            for key, value in meta_data.items():
                setattr(self.plugin_meta, key, value)
            self.plugin_data.save()

            for key, value in selector.items():
                setattr(self.plugin_selector, key, value)
            self.plugin_selector.save()

            for key, value in prompt.items():
                setattr(self.plugin_prompt, key, value)
            self.plugin_prompt.save()

            for key, value in plugin_data.items():
                setattr(self.plugin_data, key, value)
            self.plugin_data.save()
            plugin_updated.send(sender=self.__class__, plugin=self)
            logger.info("Updated plugin %s: %s.", self.name, self.id)

        return True

    def save(self):
        """Save a plugin."""
        with transaction.atomic():
            self.plugin_meta.save()
            self.plugin_selector.save()
            self.plugin_prompt.save()
            self.plugin_data.save()
            logger.info("Saved plugin %s: %s.", self.name, self.id)
        return True

    def delete(self):
        """Delete a plugin."""
        plugin_id = self.id
        plugin_name = self.name
        with transaction.atomic():
            self.plugin_data.delete()
            self.plugin_prompt.delete()
            self.plugin_selector.delete()
            self.plugin_meta.delete()

            self.plugin_data = None
            self.plugin_prompt = None
            self.plugin_selector = None
            self.plugin_meta = None

            self.plugin_data_serializer = None
            self.plugin_prompt_serializer = None
            self.plugin_selector_serializer = None
            self.plugin_meta_serializer = None

            plugin_deleted.send(sender=self.__class__, plugin=self)
            logger.info("Updated plugin %s: %s.", plugin_id, plugin_name)

        return True

    def to_json(self) -> dict:
        """Return a plugin in JSON format."""
        if self.ready:
            retval = {
                "id": self.id,
                "meta_data": {**self.plugin_meta_serializer.data, "id": self.plugin_meta.id},
                "selector": {**self.plugin_selector_serializer.data, "id": self.plugin_selector.id},
                "prompt": {**self.plugin_prompt_serializer.data, "id": self.plugin_prompt.id},
                "plugin_data": {**self.plugin_data_serializer.data, "id": self.plugin_data.id},
            }
            return retval
        return None


class Plugins:
    """A class for working with multiple plugins."""

    account: Account = None
    plugins: list[Plugin] = []

    def __init__(self, user_id: int = None, account_id: int = None):

        if user_id:
            self.account = UserProfile.objects.get(user_id=user_id).account
        else:
            self.account = Account.objects.get(pk=account_id)

        self.plugins = []
        for plugin in PluginMeta.objects.filter(account_id=self.account.id):
            self.plugins.append(Plugin(plugin_id=plugin.id))

    @property
    def data(self) -> list[dict]:
        """Return a list of plugins in dictionary format."""
        retval = []
        for plugin in self.plugins:
            if plugin.ready:
                retval.append(plugin.data)
        return retval

    def to_json(self) -> list[dict]:
        """Return a list of plugins in JSON format."""
        retval = []
        for plugin in self.plugins:
            if plugin.ready:
                retval.append(plugin.to_json())
        return retval
