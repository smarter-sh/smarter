"""A Compound Model class for managing plugins."""

# python stuff
import copy
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Type, Union

# 3rd party stuff
import yaml
from django.db import transaction
from django.db.models.query import QuerySet
from rest_framework import serializers

# smarter stuff
from smarter.apps.account.models import UserProfile
from smarter.apps.prompt.providers.const import OpenAIMessageKeys
from smarter.common.api import SmarterApiVersions
from smarter.common.classes import SmarterHelperMixin
from smarter.common.exceptions import SmarterException, SmarterValueError
from smarter.lib.django.user import UserType
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader

# plugin stuff
from ..manifest.enum import (
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
    SAMPluginSpecKeys,
)
from ..manifest.models.static_plugin.const import MANIFEST_KIND
from ..manifest.models.static_plugin.model import SAMStaticPlugin
from ..models import (
    PluginDataBase,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
    PluginSelectorHistory,
)
from ..nlp import does_refer_to
from ..serializers import (
    PluginMetaSerializer,
    PluginPromptSerializer,
    PluginSelectorSerializer,
)
from ..signals import (
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_deleting,
    plugin_ready,
    plugin_selected,
    plugin_updated,
)


logger = logging.getLogger(__name__)

SMARTER_API_MANIFEST_COMPATIBILITY = [SmarterApiVersions.V1]
SMARTER_API_MANIFEST_DEFAULT_VERSION = SmarterApiVersions.V1
PLUGIN_KEY = "plugin"


class SmarterPluginError(SmarterException):
    """Base exception for Smarter API Plugin handling."""


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class PluginBase(ABC, SmarterHelperMixin):
    """An abstract base class for working with plugins."""

    _api_version: str = SMARTER_API_MANIFEST_DEFAULT_VERSION
    _metadata_class: str = None
    _manifest: SAMStaticPlugin = None
    _pydantic_model: Type[SAMStaticPlugin] = SAMStaticPlugin

    _plugin_meta: PluginMeta = None
    _plugin_selector: PluginSelector = None
    _plugin_prompt: PluginPrompt = None
    _plugin_selector_history: QuerySet = None
    _plugin_data: PluginDataBase = None

    _plugin_prompt_serializer: dict = None
    _plugin_selector_serializer: dict = None
    _plugin_meta_serializer: dict = None
    _plugin_data_serializer: serializers = None

    _selected: bool = False
    _params: dict = None

    _user_profile: UserProfile = None

    # pylint: disable=too-many-arguments,too-many-branches
    def __init__(
        self,
        *args,
        user_profile: UserProfile = None,
        selected: bool = False,
        api_version: str = None,
        manifest: SAMStaticPlugin = None,
        plugin_id: int = None,
        plugin_meta: PluginMeta = None,
        data: Union[dict, str] = None,
        **kwargs,
    ):
        """
        Options for initialization are:
        - Pydantic model created by a manifest broker (preferred method).
        - django model plugin id.
        - yaml manifest or json representation of a yaml manifest
        see ./data/sample-plugins/everlasting-gobstopper.yaml for an example.
        """
        super().__init__(*args, **kwargs)
        if sum([bool(data), bool(manifest), bool(plugin_id), bool(plugin_meta)]) != 1:
            raise SmarterPluginError(
                f"Must specify one and only one of: manifest, data, plugin_id, or plugin_meta. "
                f"Received: data {bool(data)}, manifest {bool(manifest)}, "
                f"plugin_id {bool(plugin_id)}, plugin_meta {bool(plugin_meta)}."
            )
        self._api_version = api_version or self.api_version
        self._selected = selected
        self._user_profile = user_profile

        self._metadata_class = None
        self._manifest = None
        self._pydantic_model = None

        self.reinitialize_plugin()

        self._params = None
        self._plugin_data = None
        self._plugin_data_serializer = None

        #######################################################################
        # identifiers for existing plugins
        #######################################################################
        if plugin_id:
            self.id = plugin_id

        if plugin_meta:
            self.id = plugin_meta.id

        #######################################################################
        # Smarter API Manifest based initialization
        #######################################################################
        if manifest:
            # we received a Pydantic model from a manifest broker.
            self._manifest = manifest
            self.create()

        if data:
            # we received a yaml or json string representation of a manifest.
            self.api_version = data.get("apiVersion", self.api_version)
            if data.get(SAMKeys.KIND.value) != self.kind:
                raise SAMValidationError(f"Expected kind of {self.kind}, but got {data.get('kind')}.")
            loader = SAMLoader(
                api_version=data[SAMKeys.APIVERSION.value],
                kind=self.kind,
                manifest=data,
            )
            if not loader.ready:
                raise SAMValidationError(f"Loader is not ready. SAMLoader is not ready.")
            self._manifest = SAMStaticPlugin(**loader.pydantic_model_dump())
            self.create()

        if self.ready:
            plugin_ready.send(sender=self.__class__, plugin=self)

    def __str__(self) -> str:
        """Return the name of the plugin."""
        return str(self.name)

    def __repr__(self) -> str:
        """Return the name of the plugin."""
        return self.__str__()

    def reinitialize_plugin(self):
        """Set all plugin properties to None."""
        self._plugin_meta = None
        self._plugin_selector = None
        self._plugin_prompt = None
        self._plugin_selector_history = None
        self._plugin_data = None
        self._plugin_prompt_serializer = None
        self._plugin_selector_serializer = None
        self._plugin_meta_serializer = None

    ###########################################################################
    # Abstract properties
    ###########################################################################
    @property
    @abstractmethod
    def plugin_data_class(self) -> type[PluginDataBase]:
        """
        Return the plugin data Django ORM base class for all descendants
        of PluginBase.
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def plugin_data(self) -> PluginDataBase:
        """
        Return the plugin data as a Django ORM instance.
        """
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

    @property
    @abstractmethod
    def plugin_data_django_model(self) -> dict:
        """Return the plugin data definition as a json object."""
        raise NotImplementedError()

    @classmethod
    def example_manifest(cls, kwargs: dict = None) -> dict:
        raise NotImplementedError()

    ###########################################################################
    # Base class properties
    ###########################################################################
    @property
    def metadata_class(self) -> str:
        """Return the metadata class."""
        return self._metadata_class

    @property
    def params(self) -> dict:
        """Return the plugin parameters."""
        return self._params

    @params.setter
    def params(self, value: dict):
        """Set the plugin parameters."""
        logger.info("Setting plugin parameters: %s", value)
        self._params = value

    @property
    def api_version(self) -> str:
        """Return the api version of the plugin."""
        return self._api_version

    @api_version.setter
    def api_version(self, value: str):
        """Set the api version of the plugin."""
        if value not in SMARTER_API_MANIFEST_COMPATIBILITY:
            raise SAMValidationError(
                f"Invalid api version: {value}. Must be one of: {SMARTER_API_MANIFEST_COMPATIBILITY}"
            )
        self._api_version = value

    @property
    def kind(self) -> str:
        """Return the kind of the plugin."""
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMStaticPlugin:
        """Return the Pydandic model of the plugin."""
        if not self._manifest and self.ready:
            # if we don't have a manifest but we do have Django ORM data then
            # we can work backwards to the Pydantic model
            self._manifest = SAMStaticPlugin(**self.to_json())
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
            raise SmarterPluginError(
                "Configuration error: UserProfile must be set before initializing a plugin instance by its ORM model id."
            )
        self.reinitialize_plugin()
        try:
            self._plugin_meta = PluginMeta.objects.get(pk=value)
        except PluginMeta.DoesNotExist as e:
            raise SmarterPluginError("PluginMeta.DoesNotExist") from e

    @property
    def plugin_meta(self) -> PluginMeta:
        """Return the plugin meta."""
        if self._plugin_meta:
            return self._plugin_meta
        if self.user_profile and self._manifest:
            try:
                self._plugin_meta = PluginMeta.objects.get(
                    account=self.user_profile.account, name=self.manifest.metadata.name
                )
            except PluginMeta.DoesNotExist:
                logger.warning(
                    "%s.plugin_meta() PluginMeta for %s does not exist. "
                    "This is expected if the plugin has not been created yet or if this is a delete() operation, but otherwise would indicate a configuration error.",
                    self.formatted_class_name,
                    self.manifest.metadata.name,
                )

        return self._plugin_meta

    @property
    def plugin_meta_serializer(self) -> PluginMetaSerializer:
        """Return the plugin meta serializer."""
        if not self._plugin_meta_serializer:

            self._plugin_meta_serializer = PluginMetaSerializer(self.plugin_meta)
        return self._plugin_meta_serializer

    @property
    def plugin_meta_django_model(self) -> dict:
        """Return a dict for loading the plugin meta Django ORM model."""
        if self.user_profile and self._manifest:
            return {
                "id": self.id,
                "account": self.user_profile.account,
                "name": self.manifest.metadata.name,
                "description": self.manifest.metadata.description,
                "plugin_class": self.manifest.metadata.pluginClass,
                "version": self.manifest.metadata.version,
                "author": self.user_profile,
                "tags": self.manifest.metadata.tags,
            }

    @property
    def plugin_selector_history(self) -> QuerySet:
        """Return the plugin selector history serializer."""
        if self._plugin_selector_history:
            return self._plugin_selector_history
        try:
            self._plugin_selector_history = PluginSelectorHistory.objects.filter(plugin_selector=self.plugin_selector)
            return self._plugin_selector_history
        except PluginSelectorHistory.DoesNotExist:
            self._plugin_selector_history = None

    @property
    def plugin_selector(self) -> PluginSelector:
        """Return the plugin selector."""
        if self._plugin_selector:
            return self._plugin_selector

        try:
            self._plugin_selector = PluginSelector.objects.get(plugin=self.plugin_meta)
            return self._plugin_selector
        except PluginSelector.DoesNotExist as e:
            raise SmarterPluginError("PluginSelector.DoesNotExist") from e

    @property
    def plugin_selector_serializer(self) -> PluginSelectorSerializer:
        """Return the plugin selector serializer."""
        if not self._plugin_selector_serializer:

            self._plugin_selector_serializer = PluginSelectorSerializer(self.plugin_selector)
        return self._plugin_selector_serializer

    @property
    def plugin_selector_django_model(self) -> dict:
        """Return the plugin selector definition as a json object."""
        if self._manifest:
            return {
                PLUGIN_KEY: self.plugin_meta,
                "directive": self.manifest.spec.selector.directive,
                "search_terms": self.manifest.spec.selector.searchTerms,
            }

    @property
    def plugin_prompt(self) -> PluginPrompt:
        """Return the plugin prompt."""
        if self._plugin_prompt:
            return self._plugin_prompt
        try:
            self._plugin_prompt = PluginPrompt.objects.get(plugin=self.plugin_meta)
            return self._plugin_prompt
        except PluginPrompt.DoesNotExist as e:
            raise SmarterPluginError("PluginPrompt.DoesNotExist") from e

    @property
    def plugin_prompt_serializer(self) -> PluginPromptSerializer:
        """Return the plugin prompt serializer."""
        if not self._plugin_prompt_serializer:

            self._plugin_prompt_serializer = PluginPromptSerializer(self.plugin_prompt)
        return self._plugin_prompt_serializer

    @property
    def plugin_prompt_django_model(self) -> dict:
        """Return the plugin prompt definition as a json object."""
        if self._manifest:
            return {
                PLUGIN_KEY: self.plugin_meta,
                "system_role": self.manifest.spec.prompt.systemRole,
                "model": self.manifest.spec.prompt.model,
                "temperature": self.manifest.spec.prompt.temperature,
                "max_tokens": self.manifest.spec.prompt.maxTokens,
            }

    @property
    def user_profile(self) -> UserProfile:
        """Return the user profile."""
        if not self._user_profile:
            logger.warning(
                "%s.user_profile() was accessed prior to being set.",
                self.formatted_class_name,
            )
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
            raise SmarterPluginError("UserProfile is not set.")

        if not isinstance(self.user_profile, UserProfile):
            raise SmarterPluginError(
                f"Expected type of {UserProfile} for self.user_profile, but got {type(self.user_profile)}."
            )

        # ---------------------------------------------------------------------
        # validate the Pydantic model if it exists. This is only set
        # if we arrived here via the cli.
        # ---------------------------------------------------------------------
        if self._manifest:
            self._manifest.model_validate(self._manifest.model_dump())

        # ---------------------------------------------------------------------
        # validate the Django ORM models
        # ---------------------------------------------------------------------
        if self._plugin_meta and not isinstance(self.plugin_meta, PluginMeta):
            raise SmarterPluginError(
                f"Expected type of {PluginMeta} for self.plugin_meta, but got {type(self.plugin_meta)}."
            )
        if self._plugin_meta:
            self.plugin_meta.validate()
        else:
            # Plugin doesn't exist in Django ORM, so we're done.
            return True

        if self._plugin_selector and not isinstance(self.plugin_selector, PluginSelector):
            raise SmarterPluginError(
                f"Expected type of {PluginSelector} for self.plugin_selector, but got {type(self.plugin_selector)}."
            )
        self.plugin_selector.validate()

        if self._plugin_prompt and not isinstance(self.plugin_prompt, PluginPrompt):
            raise SmarterPluginError(
                f"Expected type of {PluginPrompt} for self.plugin_prompt, but got {type(self.plugin_prompt)}."
            )
        self.plugin_prompt.validate()

        if self._plugin_data and not isinstance(self.plugin_data, self.plugin_data_class):
            raise SmarterPluginError(
                f"Expected type of {self.plugin_data_class} for self.plugin_data, but got {type(self.plugin_data)}."
            )
        self.plugin_data.validate()

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

        if self.plugin_selector.directive == SAMPluginCommonSpecSelectorKeyDirectiveValues.ALWAYS.value:
            self._selected = True
            return self._selected

        search_terms = self.plugin_selector.search_terms

        # check the input text
        if input_text:
            for search_term in search_terms:
                if does_refer_to(prompt=input_text, search_term=search_term):
                    self._selected = True
                    plugin_selected.send(
                        sender=self.selected,
                        plugin=self,
                        user=self.user_profile.user if self.user_profile else None,
                        input_text=input_text,
                        search_term=search_term,
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
                                sender=self.selected,
                                plugin=self,
                                user=user,
                                messages=messages,
                                search_term=search_term,
                            )
                            return True

        return False

    def customize_prompt(self, messages: list[dict]) -> list[dict]:
        """Modify the system prompt based on the plugin object"""

        if not self.ready:
            raise SmarterPluginError("Plugin is not ready.")
        if not messages:
            raise SmarterValueError("Messages is empty.")

        messages_copy = messages.copy()
        for i, message in enumerate(messages_copy):
            if message.get(OpenAIMessageKeys.MESSAGE_ROLE_KEY) == OpenAIMessageKeys.SYSTEM_MESSAGE_KEY:
                system_role = message.get(OpenAIMessageKeys.MESSAGE_CONTENT_KEY)
                custom_prompt = {
                    OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY,
                    OpenAIMessageKeys.MESSAGE_CONTENT_KEY: system_role
                    + "\n\nAnd also:\n"
                    + self.plugin_prompt.system_role,
                }
                messages_copy[i] = custom_prompt
                break

        return messages_copy

    def function_calling_plugin(self, inquiry_type: str) -> str:
        """Return select info from custom plugin object"""
        if not self.ready:
            return None

        try:
            return_data = self.plugin_data.sanitized_return_data(self.params)
            retval = return_data[inquiry_type]
            retval = json.dumps(retval)
            plugin_called.send(
                sender=self.function_calling_plugin,
                plugin=self,
                inquiry_type=inquiry_type,
                inquiry_return=retval,
            )
            return retval
        except KeyError:
            plugin_called.send(
                sender=self.function_calling_plugin,
                plugin=self,
                inquiry_type=inquiry_type,
                inquiry_return="KeyError",
            )

        raise KeyError(f"Invalid inquiry_type: {inquiry_type}")

    def yaml_to_json(self, yaml_string: str) -> dict:
        """Convert a yaml string to a dictionary."""

        if self.is_valid_yaml(yaml_string):
            return yaml.safe_load(yaml_string)
        raise SmarterPluginError("Invalid data: must be a dictionary or valid YAML.")

    def is_valid_yaml(self, data):
        """Validate a yaml string."""
        try:
            yaml.safe_load(data)
            return True
        except yaml.YAMLError:
            return False

    def create(self):
        """Create a plugin from either yaml or a dictionary."""
        if not self._manifest:
            raise SmarterPluginError("Plugin manifest is not set.")
        logger.info("%s.create() creating plugin %s", self.formatted_class_name, self.manifest.metadata.name)

        def committed(plugin_id: int):
            self.id = plugin_id
            plugin_created.send(sender=self.__class__, plugin=self)
            logger.info(
                "%s.create() created and committed plugin %s: %s.",
                self.formatted_class_name,
                self.plugin_meta.name,
                self.plugin_meta.id,
            )

        meta_data = self.plugin_meta_django_model
        selector = self.plugin_selector_django_model
        prompt = self.plugin_prompt_django_model
        plugin_data = self.plugin_data_django_model

        if self.plugin_meta:
            self.id = self.plugin_meta.id
            logger.info(
                "%s.create() Plugin %s already exists. Updating plugin %s.",
                meta_data["name"],
                self.formatted_class_name,
                self.plugin_meta.id,
            )
            return self.update()

        with transaction.atomic():
            plugin_meta = PluginMeta.objects.create(**meta_data)
            logger.info("%s.create() created PluginMeta: %s", self.formatted_class_name, plugin_meta)

            selector[PLUGIN_KEY] = plugin_meta
            prompt[PLUGIN_KEY] = plugin_meta
            plugin_data[PLUGIN_KEY] = plugin_meta

            plugin_selector = PluginSelector.objects.create(**selector)
            logger.info("%s.create() created PluginSelector: %s", self.formatted_class_name, plugin_selector)
            plugin_prompt = PluginPrompt.objects.create(**prompt)
            logger.info("%s.create() created PluginPrompt: %s", self.formatted_class_name, plugin_prompt)
            self.plugin_data_class.objects.create(**plugin_data)

        transaction.on_commit(lambda: committed(plugin_id=plugin_meta.id))

        return True

    def update(self):
        """Update a plugin."""

        def committed():
            plugin_updated.send(sender=self.__class__, plugin=self)
            self.id = self.plugin_meta.id
            logger.debug("Updated plugin %s: %s.", self.name, self.id)

        if not self.manifest:
            raise SmarterPluginError("Plugin manifest is not set.")

        plugin_meta_django_model = self.plugin_meta_django_model
        if not plugin_meta_django_model:
            raise SmarterPluginError(
                f"Plugin {self.manifest.metadata.name} for account {self.user_profile.account.account_number} does not exist."
            )

        plugin_selector_django_model = self.plugin_selector_django_model
        plugin_prompt_django_model = self.plugin_prompt_django_model
        plugin_data_django_model = self.plugin_data_django_model

        with transaction.atomic():
            for attr, value in plugin_meta_django_model.items():
                setattr(self.plugin_meta, attr, value)
            self.plugin_meta.save()

            for attr, value in plugin_selector_django_model.items():
                setattr(self.plugin_selector, attr, value)
            self.plugin_selector.save()

            for attr, value in plugin_prompt_django_model.items():
                setattr(self.plugin_prompt, attr, value)
            self.plugin_prompt.save()

            for attr, value in plugin_data_django_model.items():
                setattr(self.plugin_data, attr, value)
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
            plugin_deleted.send(
                sender=self.__class__, plugin=self, plugin_meta=self.plugin_meta, plugin_name=plugin_name
            )
            logger.debug("Deleted plugin %s: %s.", plugin_id, plugin_name)

        if not self.ready:
            return False

        plugin_id = self.id
        plugin_name = self.name
        with transaction.atomic():
            plugin_deleting.send(sender=self.__class__, plugin=self, plugin_meta=self.plugin_meta)
            self.plugin_selector_history.delete()

            # plugin data
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
            plugin_cloned.send(sender=self.__class__, plugin=self)
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

    def to_json(self, version: str = "v1") -> dict:
        """
        Serialize a plugin in JSON format that is importable by Pydantic. This
        is used to create a Pydantic model from a Django ORM model
        for purposes of rendering a Plugin manifest for the Smarter API.
        """
        data = {**self.plugin_data_serializer.data, "id": self.plugin_data.id}
        description = data.pop("description")
        if self.ready:
            if version == "v1":
                retval = {
                    SAMKeys.APIVERSION.value: self.api_version,
                    SAMKeys.KIND.value: self.kind,
                    SAMKeys.METADATA.value: self.plugin_meta_serializer.data,
                    SAMKeys.SPEC.value: {
                        SAMPluginSpecKeys.SELECTOR.value: self.plugin_selector_serializer.data,
                        SAMPluginSpecKeys.PROMPT.value: self.plugin_prompt_serializer.data,
                        SAMPluginSpecKeys.DATA.value: {
                            "description": description,
                            f"{self.metadata_class}": self.plugin_data_serializer.data,
                        },
                    },
                    SAMKeys.STATUS.value: {
                        "id": self.plugin_meta.id,
                        "accountNumber": self.user_profile.account.account_number,
                        "username": self.user_profile.user.get_username(),
                        "created": self.plugin_meta.created_at.isoformat(),
                        "modified": self.plugin_meta.updated_at.isoformat(),
                    },
                }
                return json.loads(json.dumps(retval))
            raise SmarterPluginError(f"Invalid version: {version}")
        return None
