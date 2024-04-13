"""A Compound Model class for managing plugins."""

import copy
import json
import logging
import os
import re

import requests
import yaml
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from smarter.apps.account.models import Account, UserProfile

from .api.v0.serializers import (
    PluginDataSerializer,
    PluginMetaSerializer,
    PluginPromptSerializer,
    PluginSelectorSerializer,
)
from .models import PluginData, PluginMeta, PluginPrompt, PluginSelector
from .nlp import does_refer_to
from .signals import (
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_ready,
    plugin_selected,
    plugin_selected_called,
    plugin_updated,
)


User = get_user_model()
logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class Plugin:
    """A class for working with plugins."""

    _user_profile: UserProfile = None

    _plugin_meta: PluginMeta = None
    _plugin_selector: PluginSelector = None
    _plugin_prompt: PluginPrompt = None
    _plugin_data: PluginData = None

    _plugin_data_serializer: PluginDataSerializer = None
    _plugin_prompt_serializer: PluginPromptSerializer = None
    _plugin_selector_serializer: PluginSelectorSerializer = None
    _plugin_meta_serializer: PluginMetaSerializer = None

    _selected: bool = False

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        plugin_id: int = None,
        user_profile: UserProfile = None,
        plugin_meta: PluginMeta = None,
        data=None,
        selected: bool = False,
        url=None,
    ):
        """
        Initialize the class.
        data: yaml or dict representation of a plugin.
              see ./data/sample-plugins/everlasting-gobstopper.yaml for an example.
        """
        if plugin_id:
            self.id = plugin_id
            return

        if user_profile and plugin_meta:
            if plugin_meta.author != user_profile:
                raise ValidationError("User is not the author of this plugin.")

        if plugin_meta:
            self.id = plugin_meta.id
            return

        if user_profile:
            self._user_profile = user_profile

        self._selected = selected

        if data and url:
            raise ValidationError("Cannot specify both data and url.")
        if not data and not url:
            raise ValidationError("Must specify either data or url.")

        # creating a new plugin or updating an existing plugin from
        # yaml or json data.
        if data is not None:
            self.create(data)
            if self.ready:
                plugin_ready.send(sender=self.__class__, plugin=self)

        if url:
            if not self.user_profile:
                raise ValidationError("User profile is required to create a plugin from a URL.")

            response = requests.get(url, timeout=15)
            data = response.text
            data["user"] = self.user_profile.user
            data["account"] = self.user_profile.account
            data["user_profile"] = user_profile
            data["meta_data"]["author"] = self.user_profile.id

            self.create(data)
            if self.ready:
                plugin_ready.send(sender=self.__class__, plugin=self)

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
        self._plugin_meta = PluginMeta.objects.get(pk=value)
        self._plugin_meta_serializer = PluginMetaSerializer(self.plugin_meta)
        self._user_profile = self.plugin_meta.author

        # we expect that all of these 1:1 relationships exist. but, there's
        # no benefit to raising an exception if they don't as this will
        # result in the 'ready' property returning False, and the plugin
        # being excluded in results from Plugins.data.
        try:
            self._plugin_selector = PluginSelector.objects.get(plugin=self.plugin_meta)
            self._plugin_selector_serializer = PluginSelectorSerializer(self.plugin_selector)
        except PluginSelector.DoesNotExist:
            self._plugin_selector = None
            self._plugin_selector_serializer = None

        try:
            self._plugin_prompt = PluginPrompt.objects.get(plugin=self.plugin_meta)
            self._plugin_prompt_serializer = PluginPromptSerializer(self.plugin_prompt)
        except PluginPrompt.DoesNotExist:
            self._plugin_prompt = None
            self._plugin_prompt_serializer = None

        try:
            self._plugin_data = PluginData.objects.get(plugin=self.plugin_meta)
            self._plugin_data_serializer = PluginDataSerializer(self.plugin_data)
        except PluginData.DoesNotExist:
            self._plugin_data = None
            self._plugin_data_serializer = None

    @property
    def plugin_meta(self) -> PluginMeta:
        """Return the plugin meta."""
        return self._plugin_meta

    @property
    def plugin_meta_serializer(self) -> PluginMetaSerializer:
        """Return the plugin meta serializer."""
        return self._plugin_meta_serializer

    @property
    def plugin_selector(self) -> PluginSelector:
        """Return the plugin selector."""
        return self._plugin_selector

    @property
    def plugin_selector_serializer(self) -> PluginSelectorSerializer:
        """Return the plugin selector serializer."""
        return self._plugin_selector_serializer

    @property
    def plugin_prompt(self) -> PluginPrompt:
        """Return the plugin prompt."""
        return self._plugin_prompt

    @property
    def plugin_prompt_serializer(self) -> PluginPromptSerializer:
        """Return the plugin prompt serializer."""
        return self._plugin_prompt_serializer

    @property
    def plugin_data(self) -> PluginData:
        """Return the plugin data."""
        return self._plugin_data

    @property
    def plugin_data_serializer(self) -> PluginDataSerializer:
        """Return the plugin data serializer."""
        return self._plugin_data_serializer

    @property
    def user_profile(self) -> UserProfile:
        """Return the user profile."""
        return self._user_profile

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
        if not self.user_profile:
            return False
        if not isinstance(self.user_profile, UserProfile):
            return False
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

    @property
    def function_calling_identifier(self) -> str:
        """Return the function calling plugin."""
        if self.ready:
            suffix = str(self.id).zfill(4)
            return f"function_calling_plugin_{suffix}"
        return None

    @property
    def custom_tool(self) -> dict:
        """Return the plugin tool."""
        if self.ready:
            return {
                "type": "function",
                "function": {
                    "name": self.function_calling_identifier,
                    "description": self.plugin_data.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "inquiry_type": {
                                "type": "string",
                                "enum": self.plugin_data.return_data_keys,
                            },
                        },
                        "required": ["inquiry_type"],
                    },
                },
            }
        return None

    def refresh(self):
        """Refresh the plugin."""
        if self.ready:
            self.id = self.id
            return self.ready
        return False

    def selected(self, user: User, messages: list[dict]) -> bool:
        """
        Return True the user has mentioned Lawrence McDaniel or FullStackWithLawrence
        at any point in the history of the conversation.

        messages: [{"role": "user", "content": "some text"}]
        search_terms: ["Lawrence McDaniel", "FullStackWithLawrence"]
        search_pairs: [["Lawrence", "McDaniel"], ["FullStackWithLawrence", "Lawrence McDaniel"]]
        """

        plugin_selected_called.send(sender=self.selected, plugin=self, messages=messages)

        if not self.ready:
            return False
        if self._selected:
            return True

        search_terms = self.plugin_selector.search_terms
        for message in messages:
            if "role" in message and str(message["role"]).lower() == "user":
                content = message["content"]
                for search_term in search_terms:
                    if does_refer_to(prompt=content, search_term=search_term):
                        self._selected = True
                        plugin_selected.send(
                            sender=self.selected, plugin=self, user=user, messages=messages, search_term=search_term
                        )
                        return True

        return False

    def customize_prompt(self, messages: list[dict]) -> list[dict]:
        """Modify the system prompt based on the plugin object"""

        if not self.ready:
            raise ValidationError("Plugin is not ready.")

        for i, message in enumerate(messages):
            if message.get("role") == "system":
                system_role = message.get("content")
                custom_prompt = {
                    "role": "system",
                    "content": system_role + "\n\n and also " + self.plugin_prompt.system_role,
                }
                messages[i] = custom_prompt
                break

        return messages

    def function_calling_plugin(self, user: User, inquiry_type: str) -> str:
        """Return select info from custom plugin object"""
        if not self.ready:
            return None

        try:
            return_data = self.plugin_data.return_data
            retval = return_data[inquiry_type]
            retval = json.dumps(retval)
            plugin_called.send(
                sender=self.function_calling_plugin,
                user=user,
                plugin=self.plugin_meta,
                inquiry_type=inquiry_type,
                inquiry_return=retval,
            )
            return retval
        except KeyError:
            plugin_called.send(
                sender=self.function_calling_plugin,
                user=user,
                plugin=self.plugin_meta,
                inquiry_type=inquiry_type,
                inquiry_return="KeyError",
            )

        raise KeyError(f"Invalid inquiry_type: {inquiry_type}")

    def yaml_to_json(self, yaml_string: str) -> dict:
        """Convert a yaml string to a dictionary."""

        if self.is_valid_yaml(yaml_string):
            return yaml.safe_load(yaml_string)
        raise ValidationError("Invalid data: must be a dictionary or valid YAML.")

    def is_valid_yaml(self, data):
        """Validate a yaml string."""
        try:
            yaml.safe_load(data)
            return True
        except yaml.YAMLError:
            return False

    def validate_data_structure(self, data: dict) -> bool:
        """Validate the data dict."""

        def validate_key(data, key, subkeys=None):
            if key not in data:
                raise ValidationError(f"Invalid data. Missing {key}.")
            if subkeys:
                for subkey in subkeys:
                    if subkey not in data[key]:
                        raise ValidationError(f"Invalid data: missing {key}['{subkey}']")

        # top-level required keys
        if not isinstance(data, dict):
            raise ValidationError("Invalid data. Must be a dictionary.")
        if not data.get("user_profile"):
            raise ValidationError("Invalid data. Missing data['user_profile'].")
        if not isinstance(data["user_profile"], UserProfile):
            raise ValidationError("Invalid data. data['user_profile'] must be a UserProfile instance.")

        # plugin required keys
        if not data.get("meta_data"):
            raise ValidationError("Invalid data. Missing meta_data.")
        if not data.get("selector"):
            raise ValidationError("Invalid data. Missing selector.")
        if not data.get("prompt"):
            raise ValidationError("Invalid data. Missing prompt.")
        if not data.get("plugin_data"):
            raise ValidationError("Invalid data. Missing plugin_data.")

        # validate the structure of the data
        validate_key(data, "meta_data", ["name", "description", "version", "tags"])
        validate_key(data, "selector", ["search_terms"])
        validate_key(data, "prompt", ["system_role", "model", "temperature", "max_tokens"])
        validate_key(data, "plugin_data", ["description", "return_data"])

        return True

    def validate_data_policy(self, data: dict) -> bool:
        """Validate the data dict."""

        # top-level prohibited keys
        if data.get("id"):
            raise ValidationError("Invalid data. dict key data['id'] is not writable.")
        meta_data = data.get("meta_data")
        if meta_data.get("author"):
            raise ValidationError("Invalid data. dict key data['meta_data']['author'] is not writable.")

        return True

    def validate_data_types(self, data: dict) -> bool:
        """Validate the data dict."""

        def validate_data_type(data, key, data_type, required=True):
            if required and key not in data:
                raise ValidationError(f"Invalid data. Missing {key}.")
            if required and not data[key]:
                # Python interprets zero values as None in this case.
                if data_type in [int, float]:
                    return True
                raise ValidationError(f"Invalid data: {key} is required but is empty.")

            if not required and key not in data:
                return True

            if not isinstance(data[key], data_type):
                raise ValidationError(
                    f"Invalid data: {key} must be a {data_type} but received {type(data[key])}: {data[key]}"
                )
            return True

        # validate the data types
        validate_data_type(data["meta_data"], "name", str)
        validate_data_type(data["meta_data"], "description", str)
        validate_data_type(data["meta_data"], "version", str)
        validate_data_type(data["meta_data"], "tags", list, required=False)

        validate_data_type(data["selector"], "directive", str)
        validate_data_type(data["selector"], "search_terms", list)

        validate_data_type(data["prompt"], "system_role", str)
        validate_data_type(data["prompt"], "model", str)
        validate_data_type(data["prompt"], "temperature", float)
        validate_data_type(data["prompt"], "max_tokens", int)

        validate_data_type(data["plugin_data"], "description", str)

        # finally, validate the return_data, which should be yaml, json or a string.
        return_data = data["plugin_data"]["return_data"]
        if isinstance(return_data, str):
            logger.debug("Data is valid.")
            return True
        if isinstance(return_data, dict):
            logger.debug("Data is valid.")
            return True
        if isinstance(return_data, list):
            logger.debug("Data is valid.")
            return True

        try:
            yaml.safe_load(return_data)
            logger.debug("Data is valid.")
            return True
        except yaml.YAMLError:
            pass

        try:
            json.loads(return_data)
            logger.debug("Data is valid.")
            return True
        except json.JSONDecodeError:
            pass

        raise ValidationError("Invalid data: return_data must be a string, json or yaml.")

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

        logger.debug("Write operation is valid.")
        return True

    def create(self, data):
        """Create a plugin from either yaml or a dictionary."""

        def committed(plugin_id: int):
            self.id = plugin_id
            plugin_created.send(sender=self.__class__, plugin=self)
            logger.debug("Created plugin %s: %s.", self.plugin_meta.name, self.plugin_meta.id)

        def proper_name(name: str) -> str:
            """Return a proper name."""

            # convert a string like 'HR policy update'
            # to HR-Policy-Update
            return name.title().replace(" ", "-").strip()

        # expected use case is that we received a yaml string.
        # validate it and convert it to a dictionary.
        if not isinstance(data, dict):
            data = self.yaml_to_json(yaml_string=data)

        # extract anything that might have been set
        # in the constructor.
        if self.user_profile:
            data["user_profile"] = self.user_profile
        else:
            if data.get("user_profile"):
                self._user_profile = data.get("user_profile")

        self.validate_data_structure(data)
        self.validate_data_types(data)
        self.validate_write_operation(data)

        # initialize the major sections of the plugin yaml file
        meta_data = data.get("meta_data")
        meta_data["name"] = proper_name(meta_data["name"])
        selector = data.get("selector")
        prompt = data.get("prompt")
        plugin_data = data.get("plugin_data")

        # account/name is unique, so if the plugin already exists,
        # then update it instead of creating a new one.
        plugin_meta = PluginMeta.objects.filter(account=self.user_profile.account, name=meta_data["name"]).first()
        if plugin_meta:
            self.id = plugin_meta.id
            logger.info("Plugin %s already exists. Updating plugin %s.", meta_data["name"], plugin_meta.id)
            return self.update(data)

        meta_data["account"] = self.user_profile.account
        meta_data["author"] = self.user_profile
        meta_data_tags = meta_data.pop("tags")

        with transaction.atomic():
            plugin_meta = PluginMeta.objects.create(**meta_data)
            plugin_meta.tags.add(*meta_data_tags)

            selector["plugin_id"] = plugin_meta.id
            prompt["plugin_id"] = plugin_meta.id
            plugin_data["plugin_id"] = plugin_meta.id

            PluginSelector.objects.create(**selector)
            PluginPrompt.objects.create(**prompt)
            PluginData.objects.create(**plugin_data)

        transaction.on_commit(lambda: committed(plugin_id=plugin_meta.id))

        return True

    def update(self, data: dict = None):
        """Update a plugin."""

        def committed():
            plugin_updated.send(sender=self.__class__, plugin=self)
            logger.debug("Updated plugin %s: %s.", self.name, self.id)

        if not data:
            return self.save()

        self.validate_data_structure(data)
        self.validate_data_types(data)
        self.validate_write_operation(data)

        # don't want the author field to be writable.
        meta_data = data.get("meta_data")
        meta_data.pop("author", None)
        meta_data_tags = meta_data.pop("tags")

        selector = data.get("selector")
        prompt = data.get("prompt")
        plugin_data = data.get("plugin_data")

        self.validate_data_policy(data)

        plugin_meta = PluginMeta.objects.filter(account=self.user_profile.account, name=meta_data["name"]).first()
        self.id = plugin_meta.id

        with transaction.atomic():
            for key, value in meta_data.items():
                setattr(self.plugin_meta, key, value)
            self.plugin_meta.tags.set(meta_data_tags)
            self.plugin_meta.save()

            for key, value in selector.items():
                setattr(self.plugin_selector, key, value)
            self.plugin_selector.save()

            for key, value in prompt.items():
                setattr(self.plugin_prompt, key, value)
            self.plugin_prompt.save()

            for key, value in plugin_data.items():
                setattr(self.plugin_data, key, value)
            self.plugin_data.save()

        transaction.on_commit(committed)

        return True

    def save(self):
        """Save a plugin."""

        def committed():
            plugin_updated.send(sender=self.__class__, plugin=self)
            logger.debug("Saved plugin %s: %s.", self.name, self.id)

        if not self.ready:
            return False

        with transaction.atomic():
            self.plugin_meta.save()
            self.plugin_selector.save()
            self.plugin_prompt.save()
            self.plugin_data.save()

        transaction.on_commit(committed)
        return True

    def delete(self):
        """Delete a plugin."""

        def committed():
            plugin_deleted.send(sender=self.__class__, plugin_id=plugin_id, plugin_name=plugin_name)
            logger.debug("Deleted plugin %s: %s.", plugin_id, plugin_name)

        if not self.ready:
            return False

        plugin_id = self.id
        plugin_name = self.name
        with transaction.atomic():
            self.plugin_data.delete()
            self.plugin_prompt.delete()
            self.plugin_selector.delete()
            self.plugin_meta.delete()

            self._plugin_data = None
            self._plugin_prompt = None
            self._plugin_selector = None
            self._plugin_meta = None

            self._plugin_data_serializer = None
            self._plugin_prompt_serializer = None
            self._plugin_selector_serializer = None
            self._plugin_meta_serializer = None

        transaction.on_commit(committed)
        return True

    def clone(self, new_name: str = None):
        """Clone a plugin."""

        def committed(new_plugin_id: int):
            plugin_cloned.send(sender=self.__class__, plugin_id=new_plugin_id)
            logger.debug(
                "Cloned plugin %s: %s to %s: %s", self.id, self.name, plugin_meta_copy.id, plugin_meta_copy.name
            )

        def get_new_name(plugin_name, new_name=None):
            """Get a new name for the plugin."""
            if new_name is None:
                match = re.search(r"\(copy(\d*)\)$", plugin_name)
                if match:
                    copy_number = match.group(1)
                    if copy_number == "":
                        new_name = re.sub(r"\(copy\)$", "(copy2)", plugin_name)
                    else:
                        new_name = re.sub(r"\(copy\d*\)$", f"(copy{int(copy_number)+1})", plugin_name)
                else:
                    new_name = f"{plugin_name} (copy)"
            return new_name

        if not self.ready:
            return False

        with transaction.atomic():
            plugin_meta_copy = copy.deepcopy(self.plugin_meta)
            plugin_meta_copy.id = None
            plugin_meta_copy.name = new_name or get_new_name(plugin_name=self.name)
            plugin_meta_copy.save()
            plugin_meta_copy.tags.set(self.plugin_meta.tags.all())
            plugin_meta_copy.refresh_from_db()

            # for each 1:1 relationship, create a new instance
            # setting the pk to None so that the new isn't
            # simply the old instance re-assigned to a new plugin_meta.
            # also, set the fk plugin_id to the new plugin_meta id.
            plugin_selector_copy = copy.deepcopy(self.plugin_selector)
            plugin_selector_copy.id = None
            plugin_selector_copy.plugin_id = plugin_meta_copy.id
            plugin_selector_copy.save()

            plugin_prompt_copy = copy.deepcopy(self.plugin_prompt)
            plugin_prompt_copy.id = None
            plugin_prompt_copy.plugin_id = plugin_meta_copy.id
            plugin_prompt_copy.save()

            plugin_data_copy = copy.deepcopy(self.plugin_data)
            plugin_data_copy.id = None
            plugin_data_copy.plugin_id = plugin_meta_copy.id
            plugin_data_copy.save()

        transaction.on_commit(lambda: committed(new_plugin_id=plugin_meta_copy.id))
        return plugin_meta_copy.id

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
            return json.loads(json.dumps(retval))
        return None


class Plugins:
    """A class for working with multiple plugins."""

    account: Account = None
    plugins: list[Plugin] = []

    def __init__(self, user: User = None, account: Account = None):

        self.plugins = []
        if user or account:
            self.account = account or UserProfile.objects.get(user=user).account

            for plugin in PluginMeta.objects.filter(account=self.account):
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


class PluginExample:
    """A class for working with built-in yaml-based plugin examples."""

    _name: str = None
    _json: json = None
    _yaml: str = None

    def __init__(self, filepath: str, filename: str):
        """Initialize the class from a yaml file"""
        with open(os.path.join(filepath, filename), encoding="utf-8") as file:
            self._yaml = file.read()
            self._json = yaml.safe_load(self._yaml)

        self._name = filename

    @property
    def name(self) -> str:
        """Return the name of the plugin."""
        return self._name

    def to_yaml(self) -> str:
        """Return the plugin as a yaml string."""
        return self._yaml

    # FIX NOTE: this fails on Plugin.create() due to missing tags
    # django.core.exceptions.ValidationError: ["Invalid data: missing meta_data['tags']"]
    def to_json(self) -> dict:
        """Return the plugin as a dictionary."""
        return self._json


class PluginExamples:
    """A class for working with a collection of PluginExample instances."""

    _plugin_examples: list[PluginExample] = []
    HERE = os.path.abspath(os.path.dirname(__file__))
    PLUGINS_PATH = os.path.join(HERE, "data", "sample-plugins")

    def __init__(self):
        """Initialize the class."""
        self._plugin_examples = []
        for file in os.listdir(self.PLUGINS_PATH):
            if file.endswith(".yaml"):
                plugin_example = PluginExample(filepath=self.PLUGINS_PATH, filename=file)
                self._plugin_examples.append(plugin_example)

    def count(self) -> int:
        """Return the number of plugins."""
        return len(self._plugin_examples)

    @property
    def plugins(self) -> list[PluginExample]:
        """Return a list of plugins in dictionary format."""
        return self._plugin_examples
