"""A Compound Model class for managing plugins."""

import copy
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any

import yaml
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from smarter.apps.account.models import UserProfile
from smarter.apps.api.v0.manifests.exceptions import SAMValidationError
from smarter.apps.plugin.api.v0.manifests.broker import SAMPluginBroker
from smarter.apps.plugin.api.v0.manifests.models.plugin import SAMPlugin
from smarter.apps.plugin.api.v0.serializers import (
    PluginMetaSerializer,
    PluginPromptSerializer,
    PluginSelectorSerializer,
)
from smarter.apps.plugin.models import PluginMeta, PluginPrompt, PluginSelector
from smarter.apps.plugin.nlp import does_refer_to
from smarter.apps.plugin.signals import (
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_ready,
    plugin_selected,
    plugin_updated,
)
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.user import UserType


logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class PluginBase(ABC):
    """An abstract base class for working with plugins."""

    _manifest: SAMPlugin = None

    _plugin_meta: PluginMeta = None
    _plugin_selector: PluginSelector = None
    _plugin_prompt: PluginPrompt = None

    _plugin_prompt_serializer: PluginPromptSerializer = None
    _plugin_selector_serializer: PluginSelectorSerializer = None
    _plugin_meta_serializer: PluginMetaSerializer = None

    _selected: bool = False

    # abstract properties
    _plugin_data: Any = TimestampedModel
    _plugin_data_serializer: serializers = None

    # pylint: disable=too-many-arguments,too-many-branches
    def __init__(
        self,
        user_profile: UserProfile = None,
        selected: bool = False,
        manifest: SAMPlugin = None,
        plugin_id: int = None,
        plugin_meta: PluginMeta = None,
        data=None,
    ):
        """
        Options for initialization are:
        - Pydantic model created by a manifest broker (preferred method).
        - django model plugin id.
        - yaml manifest or json representation of a yaml manifest
        see ./data/sample-plugins/everlasting-gobstopper.yaml for an example.
        """
        if sum([bool(data), bool(manifest), bool(plugin_id), bool(plugin_meta)]) != 1:
            raise ValidationError("Must specify one and only one of: manifest, data, plugin_id, or plugin_meta")

        self._selected = selected
        self._user_profile = user_profile

        #######################################################################
        # identifiers for existing plugins
        #######################################################################
        if plugin_id:
            self.id = plugin_id

        if plugin_meta:
            self.id = plugin_meta.id

        #######################################################################
        # manifests
        #######################################################################
        if manifest:
            self._manifest = manifest

        # creating a new plugin or updating an existing plugin from
        # yaml or json data.
        if data:
            # work backwards to the Pydantic model.
            self._manifest = SAMPluginBroker(
                account_number=self.user_profile.account.account_number, manifest=data
            ).manifest

        if self.manifest:
            self._user_profile = self.manifest.metadata.userProfile
            data = manifest.model_dump_json()
            self.create(data)

        if self.ready:
            plugin_ready.send(sender=self.__class__, plugin=self)

    def __str__(self) -> str:
        """Return the name of the plugin."""
        return str(self.name)

    def __repr__(self) -> str:
        """Return the name of the plugin."""
        return self.__str__()

    ###########################################################################
    # Abstract properties
    ###########################################################################
    @property
    @abstractmethod
    def plugin_data(self) -> TimestampedModel:
        """Return the plugin data Django ORM."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def plugin_data_class(self) -> type[TimestampedModel]:
        """Return the plugin data Django ORM class."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def plugin_data_serializer(self) -> serializers.ModelSerializer:
        """Return the plugin data serializer for the plugin data Django ORM."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def plugin_data_serializer_class(self) -> type[serializers.ModelSerializer]:
        """Return the plugin data serializer class for the plugin data Django ORM."""
        raise NotImplementedError()

    @property
    @abstractmethod
    def custom_tool(self) -> dict:
        """Return the plugin tool."""
        raise NotImplementedError()

    ###########################################################################
    # Base class properties
    ###########################################################################
    @property
    def manifest(self) -> SAMPlugin:
        """Return the Pydandic model of the plugin."""
        return self._manifest

    @property
    def id(self) -> int:
        """Return the id of the plugin."""
        if self.plugin_meta:
            return self.plugin_meta.id
        return None

    @id.setter
    def id(self, value: int):
        """Set the id of the plugin."""
        if not self.user_profile:
            raise SAMValidationError(
                "Configuration error: UserProfile must be set before initializing a plugin instance by its ORM model id."
            )

        try:
            self._plugin_meta = PluginMeta.objects.get(pk=value)
            self._plugin_meta_serializer = PluginMetaSerializer(self.plugin_meta)
        except PluginMeta.DoesNotExist as e:
            raise SAMValidationError("PluginMeta.DoesNotExist") from e

        try:
            self._plugin_selector = PluginSelector.objects.get(plugin=self.plugin_meta)
            self._plugin_selector_serializer = PluginSelectorSerializer(self.plugin_selector)
        except PluginSelector.DoesNotExist as e:
            raise SAMValidationError("PluginSelector.DoesNotExist") from e

        try:
            self._plugin_prompt = PluginPrompt.objects.get(plugin=self.plugin_meta)
            self._plugin_prompt_serializer = PluginPromptSerializer(self.plugin_prompt)
        except PluginPrompt.DoesNotExist as e:
            raise SAMValidationError("PluginPrompt.DoesNotExist") from e

        try:
            self._plugin_data = self.plugin_data_class.objects.get(plugin=self.plugin_meta)
            self._plugin_data_serializer = self.plugin_data_serializer_class(self.plugin_data)
        except self.plugin_data_class.DoesNotExist as e:
            raise SAMValidationError(f"{self.plugin_data_class.__name__}.DoesNotExist") from e

        self._manifest = SAMPluginBroker(
            account_number=self.user_profile.account.account_number, manifest=self.to_json()
        ).manifest

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
    def user_profile(self) -> UserProfile:
        """Return the user profile."""
        return self.manifest.metadata.userProfile

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

        # ---------------------------------------------------------------------
        # validate the Pydantic model
        # ---------------------------------------------------------------------
        if not self.manifest:
            raise SAMValidationError("Plugin manifest is not set.")
        self.manifest.model_validate()
        if not self.user_profile:
            raise SAMValidationError("UserProfile is not set.")
        if not isinstance(self.user_profile, UserProfile):
            raise SAMValidationError(
                f"Expected type of {UserProfile} for self.user_profile, but got {type(self.user_profile)}."
            )

        # ---------------------------------------------------------------------
        # validate the Django ORM models
        # ---------------------------------------------------------------------
        if not isinstance(self.plugin_meta, PluginMeta):
            raise SAMValidationError(
                f"Expected type of {PluginMeta} for self.plugin_meta, but got {type(self.plugin_meta)}."
            )
        self.plugin_meta.validate()

        if not isinstance(self.plugin_selector, PluginSelector):
            raise SAMValidationError(
                f"Expected type of {PluginSelector} for self.plugin_selector, but got {type(self.plugin_selector)}."
            )
        self.plugin_selector.validate()

        if not isinstance(self.plugin_prompt, PluginPrompt):
            raise SAMValidationError(
                f"Expected type of {PluginPrompt} for self.plugin_prompt, but got {type(self.plugin_prompt)}."
            )
        self.plugin_prompt.validate()

        if not isinstance(self.plugin_data, self.plugin_data_class):
            raise SAMValidationError(
                f"Expected type of {self.plugin_data_class} for self.plugin_data, but got {type(self.plugin_data)}."
            )
        self.plugin_data.validate()

        # ---------------------------------------------------------------------
        # validate the serializers
        # ---------------------------------------------------------------------
        if not isinstance(self.plugin_meta_serializer, PluginMetaSerializer):
            raise SAMValidationError(
                f"Expected type of {PluginMetaSerializer} for self.plugin_meta_serializer, but got {type(self.plugin_meta_serializer)}."
            )
        if not self.plugin_meta_serializer.is_valid():
            raise SAMValidationError("PluginMetaSerializer is not valid.")

        if not isinstance(self.plugin_selector_serializer, PluginSelectorSerializer):
            raise SAMValidationError(
                f"Expected type of {PluginSelectorSerializer} for self.plugin_selector_serializer, but got {type(self.plugin_selector_serializer)}."
            )
        if not self.plugin_selector_serializer.is_valid():
            raise SAMValidationError("PluginSelectorSerializer is not valid.")

        if not isinstance(self.plugin_prompt_serializer, PluginPromptSerializer):
            raise SAMValidationError(
                f"Expected type of {PluginPromptSerializer} for self.plugin_prompt_serializer, but got {type(self.plugin_prompt_serializer)}."
            )
        if not self.plugin_prompt_serializer.is_valid():
            raise SAMValidationError("PluginPromptSerializer is not valid.")

        if not isinstance(self.plugin_data_serializer, self.plugin_data_serializer_class):
            raise SAMValidationError(
                f"Expected type of {self.plugin_data_serializer_class} for self.plugin_data_serializer, but got {type(self.plugin_data_serializer)}."
            )
        if not self.plugin_data_serializer.is_valid():
            raise SAMValidationError("PluginDataSerializer is not valid.")

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

    def refresh(self):
        """Refresh the plugin."""
        if self.ready:
            self.id = self.id
            return self.ready
        return False

    def selected(self, user: UserType, input_text: str = None, messages: list[dict] = None) -> bool:
        """
        Return True the user has mentioned Lawrence McDaniel or FullStackWithLawrence
        at any point in the history of the conversation.

        messages: [{"role": "user", "content": "some text"}]
        search_terms: ["Lawrence McDaniel", "FullStackWithLawrence"]
        search_pairs: [["Lawrence", "McDaniel"], ["FullStackWithLawrence", "Lawrence McDaniel"]]
        """

        if not self.ready:
            return False
        if self._selected:
            return True

        search_terms = self.plugin_selector.search_terms

        # check the input text
        if input_text:
            for search_term in search_terms:
                if does_refer_to(prompt=input_text, search_term=search_term):
                    self._selected = True
                    plugin_selected.send(
                        sender=self.selected, plugin=self, input_text=input_text, search_term=search_term
                    )
                    return True

        # check the messages list
        if messages:
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

    def function_calling_plugin(self, inquiry_type: str) -> str:
        """Return select info from custom plugin object"""
        if not self.ready:
            return None

        try:
            return_data = self.plugin_data.sanitized_return_data
            retval = return_data[inquiry_type]
            retval = json.dumps(retval)
            plugin_called.send(
                sender=self.function_calling_plugin,
                plugin=self.plugin_meta,
                inquiry_type=inquiry_type,
                inquiry_return=retval,
            )
            return retval
        except KeyError:
            plugin_called.send(
                sender=self.function_calling_plugin,
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

    def validate_write_operation(self, data: dict) -> bool:
        """Validate the structural integrity of the dict."""
        try:
            SAMPluginBroker(account_number=self.user_profile.account.account_number, manifest=data)
        except SAMValidationError:
            return False
        return True

    def create(self, data: dict = None, manifest: SAMPlugin = None):
        """Create a plugin from either yaml or a dictionary."""

        def committed(plugin_id: int):
            self.id = plugin_id
            plugin_created.send(sender=self.__class__, plugin=self)
            logger.debug("Created plugin %s: %s.", self.plugin_meta.name, self.plugin_meta.id)

        if sum(bool(data), bool(manifest)) != 1:
            raise SAMValidationError("Must specify either data or manifest.")

        if data:
            # validate and recast the data from a manifest broker.
            manifest = SAMPluginBroker(account_number=self.user_profile.account.account_number, manifest=data).manifest
        data = manifest.model_dump_json()
        if not data:
            raise SAMValidationError("Invalid data: expected a manifest broker or a manifest in json or yaml format.")
        self.validate_write_operation(data)

        meta_data = manifest.metadata.model_dump_json()
        selector = manifest.spec.selector.model_dump_json()
        prompt = manifest.spec.prompt.model_dump_json()
        plugin_data = manifest.spec.data.model_dump_json()

        # account/name is unique, so if the plugin already exists, then update it instead of creating a new one.
        plugin_meta = PluginMeta.objects.filter(account=self.user_profile.account, name=manifest.metadata.name).first()
        if plugin_meta:
            self.id = plugin_meta.id
            logger.info("Plugin %s already exists. Updating plugin %s.", meta_data["name"], plugin_meta.id)
            return self.update(manifest=manifest)

        with transaction.atomic():
            plugin_meta = PluginMeta.objects.create(**meta_data)

            selector["plugin_id"] = plugin_meta.id
            prompt["plugin_id"] = plugin_meta.id
            plugin_data["plugin_id"] = plugin_meta.id

            PluginSelector.objects.create(**selector)
            PluginPrompt.objects.create(**prompt)
            self.plugin_data_class.objects.create(**plugin_data)

        transaction.on_commit(lambda: committed(plugin_id=plugin_meta.id))

        return True

    def update(self, data: dict = None, manifest: SAMPlugin = None):
        """Update a plugin."""

        def committed():
            plugin_updated.send(sender=self.__class__, plugin=self)
            logger.debug("Updated plugin %s: %s.", self.name, self.id)

        if sum(bool(data), bool(manifest)) != 1:
            raise SAMValidationError("Must specify either data or manifest.")

        if data:
            # validate and recast the data from a manifest broker.
            manifest = SAMPluginBroker(account_number=self.user_profile.account.account_number, manifest=data).manifest
        data = manifest.model_dump_json()
        if not data:
            raise SAMValidationError("Invalid data: expected a manifest broker or a manifest in json or yaml format.")

        self.validate_write_operation(data)

        # don't want the author field to be writable.
        meta_data = manifest.metadata.model_dump_json()
        selector = manifest.spec.selector.model_dump_json()
        prompt = manifest.spec.prompt.model_dump_json()
        plugin_data = manifest.spec.data.model_dump_json()

        meta_data_tags = meta_data.pop("tags")

        plugin_meta = PluginMeta.objects.filter(account=self.user_profile.account, name=manifest.metadata.name).first()
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
                "metadata": {**self.plugin_meta_serializer.data, "id": self.plugin_meta.id},
                "selector": {**self.plugin_selector_serializer.data, "id": self.plugin_selector.id},
                "prompt": {**self.plugin_prompt_serializer.data, "id": self.plugin_prompt.id},
                "plugin_data": {**self.plugin_data_serializer.data, "id": self.plugin_data.id},
            }
            return json.loads(json.dumps(retval))
        return None
