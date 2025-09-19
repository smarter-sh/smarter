"""A Compound Model class for managing plugins."""

# python stuff
import copy
import datetime
import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Optional, Type, Union

# 3rd party stuff
import yaml
from django.db import transaction
from django.db.models.query import QuerySet
from rest_framework import serializers

# smarter stuff
from smarter.apps.account.models import User, UserProfile
from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.apps.prompt.providers.const import OpenAIMessageKeys
from smarter.common.api import SmarterApiVersions
from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import (
    SmarterConfigurationError,
    SmarterException,
    SmarterValueError,
)
from smarter.common.utils import camel_to_snake as util_camel_to_snake
from smarter.common.utils import snake_to_camel as util_snake_to_camel
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.openai.enum import OpenAIToolCall, OpenAIToolTypes

# plugin stuff
from ..manifest.enum import (
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
    SAMPluginSpecKeys,
)
from ..manifest.models.static_plugin.const import MANIFEST_KIND
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
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_deleting,
    plugin_ready,
    plugin_selected,
    plugin_updated,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

SMARTER_API_MANIFEST_COMPATIBILITY = [SmarterApiVersions.V1]
SMARTER_API_MANIFEST_DEFAULT_VERSION = SmarterApiVersions.V1
PLUGIN_KEY = "plugin"


class SmarterPluginError(SmarterException):
    """Base exception for Smarter API Plugin handling."""


# pylint: disable=too-many-instance-attributes,too-many-public-methods
class PluginBase(ABC, SmarterHelperMixin):
    """An abstract base class for working with plugins."""

    SAMPluginType = SAMPluginCommon
    _api_version: str = SMARTER_API_MANIFEST_DEFAULT_VERSION
    _manifest: Optional[SAMPluginType] = None
    _pydantic_model: Optional[Type[SAMPluginType]] = SAMPluginType

    _plugin_meta: Optional[PluginMeta] = None
    _plugin_selector: Optional[PluginSelector] = None
    _plugin_prompt: Optional[PluginPrompt] = None
    _plugin_selector_history: Optional[QuerySet] = None
    _plugin_data: Optional[PluginDataBase] = None

    _plugin_prompt_serializer: Optional[PluginPromptSerializer] = None
    _plugin_selector_serializer: Optional[PluginSelectorSerializer] = None
    _plugin_meta_serializer: Optional[PluginMetaSerializer] = None
    _plugin_data_serializer: Optional[serializers.Serializer] = None

    _selected: bool = False
    _params: Optional[dict[str, Any]] = None

    _user_profile: Optional[UserProfile] = None

    # pylint: disable=too-many-arguments,too-many-branches
    def __init__(
        self,
        *args,
        user_profile: Optional[UserProfile] = None,
        selected: bool = False,
        api_version: Optional[str] = None,
        manifest: Optional[SAMPluginCommon] = None,
        plugin_id: Optional[int] = None,
        plugin_meta: Optional[PluginMeta] = None,
        data: Union[dict[str, Any], str, None] = None,
        name: Union[str, None] = None,
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
        msg = (
            f"{self.formatted_class_name}__init__() Received: data {bool(data)}, manifest {bool(manifest)}, "
            f"plugin_id {bool(plugin_id)}, plugin_meta {bool(plugin_meta)}, name {bool(name)}."
        )
        logger.info(msg)
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
        elif plugin_meta:
            self.id = plugin_meta.id  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
        elif name and self.user_profile:
            try:
                self._plugin_meta = PluginMeta.objects.get(account=self.user_profile.account, name=name)
                self.id = self._plugin_meta.id  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
            except PluginMeta.DoesNotExist:
                logger.warning(
                    "%s.__init__() PluginMeta with name %s does not exist for account %s.",
                    self.formatted_class_name,
                    name,
                    self.user_profile.account if self.user_profile else "unknown",
                )

        #######################################################################
        # Smarter API Manifest based initialization
        #######################################################################
        if manifest:
            if not isinstance(manifest, self.SAMPluginType):
                raise TypeError(
                    f"{self.formatted_class_name}__init__() expected manifest of type {self.SAMPluginType.__name__} but received {type(manifest)}."
                )

            # we received a Pydantic model from a manifest broker.
            self._manifest = manifest
            self.create()
        elif data is not None:
            # we received a yaml or json string representation of a manifest.
            data = self.data_to_dict(data)
            self.api_version = data.get("apiVersion", self.api_version)
            if data.get(SAMKeys.KIND.value) != self.kind:
                raise SAMValidationError(f"Expected kind of {self.kind}, but got {data.get('kind')}.")
            loader = SAMLoader(
                api_version=data[SAMKeys.APIVERSION.value],
                kind=self.kind,
                manifest=json.dumps(data) if isinstance(data, dict) else data,
            )
            if not loader.ready:
                raise SAMValidationError("Loader is not ready. SAMLoader is not ready.")
            self._manifest = self.SAMPluginType(**loader.pydantic_model_dump())
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
    def plugin_data_django_model(self) -> dict:
        """Return the plugin data definition as a json object."""
        raise NotImplementedError()

    @property
    def custom_tool(self) -> dict[str, Any]:
        """
        Return the plugin tool. see https://platform.openai.com/docs/assistants/tools/function-calling/quickstart

        example:
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "get_current_temperature",
                    "description": "Get the current temperature for a specific location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g., San Francisco, CA"
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["Celsius", "Fahrenheit"],
                                "description": "The temperature unit to use. Infer this from the user's location."
                            }
                        },
                        "required": ["location", "unit"]
                    }
                }
            }
        ]
        """
        if not self.ready:
            raise SmarterPluginError(
                f"{self.formatted_class_name}.custom_tool() error: {self.name} plugin is not ready."
            )
        if not self.plugin_data:
            raise SmarterPluginError(
                f"{self.formatted_class_name}.custom_tool() error: {self.name} plugin data is not available."
            )
        if not isinstance(self.plugin_data.parameters, dict):
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}.custom_tool() error: {self.name} parameters must be a dictionary."
            )

        return {
            OpenAIToolCall.TYPE.value: OpenAIToolTypes.FUNCTION.value,
            OpenAIToolCall.FUNCTION.value: {
                OpenAIToolCall.NAME.value: self.function_calling_identifier,
                OpenAIToolCall.DESCRIPTION.value: self.plugin_data.description,
                OpenAIToolCall.PARAMETERS.value: self.function_parameters,
            },
        }

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict[str, Any]] = None) -> dict:
        raise NotImplementedError()

    ###########################################################################
    # Base class properties
    ###########################################################################
    @property
    def metadata_class(self) -> Optional[str]:
        """Return the metadata class."""
        return self.plugin_meta.plugin_class if self.plugin_meta else None

    @property
    def params(self) -> Optional[dict[str, Any]]:
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
    def manifest(self) -> SAMPluginCommon:
        """Return the Pydandic model of the plugin."""
        raise NotImplementedError

    @property
    def id(self) -> Optional[int]:
        """Return the id of the plugin."""
        return self._plugin_meta.id if self._plugin_meta else None  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]

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
    def plugin_meta(self) -> Optional[PluginMeta]:
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
    def plugin_meta_serializer(self) -> Optional[PluginMetaSerializer]:
        """Return the plugin meta serializer."""
        if not self._plugin_meta_serializer:

            self._plugin_meta_serializer = PluginMetaSerializer(self.plugin_meta)
        return self._plugin_meta_serializer

    @property
    def plugin_meta_django_model(self) -> Optional[dict[str, Any]]:
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
    def plugin_selector_history(self) -> Optional[QuerySet]:
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
    def plugin_selector_serializer(self) -> Optional[PluginSelectorSerializer]:
        """Return the plugin selector serializer."""
        if not self._plugin_selector_serializer:

            self._plugin_selector_serializer = PluginSelectorSerializer(self.plugin_selector)
        return self._plugin_selector_serializer

    @property
    def plugin_selector_django_model(self) -> Optional[dict[str, Any]]:
        """Return the plugin selector definition as a json object."""
        if self._manifest:
            return {
                PLUGIN_KEY: self.plugin_meta,
                "directive": self.manifest.spec.selector.directive if self.manifest and self.manifest.spec else None,
                SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value: (
                    self.manifest.spec.selector.searchTerms if self.manifest and self.manifest.spec else None
                ),
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
    def plugin_prompt_serializer(self) -> Optional[PluginPromptSerializer]:
        """Return the plugin prompt serializer."""
        if not self._plugin_prompt_serializer:

            self._plugin_prompt_serializer = PluginPromptSerializer(self.plugin_prompt)
        return self._plugin_prompt_serializer

    @property
    def plugin_prompt_django_model(self) -> Optional[dict[str, Any]]:
        """Return the plugin prompt definition as a json object."""
        if self._manifest:
            return {
                PLUGIN_KEY: self.plugin_meta,
                "system_role": self.manifest.spec.prompt.systemRole if self.manifest and self.manifest.spec else None,
                "model": self.manifest.spec.prompt.model if self.manifest and self.manifest.spec else None,
                "temperature": self.manifest.spec.prompt.temperature if self.manifest and self.manifest.spec else None,
                "max_completion_tokens": (
                    self.manifest.spec.prompt.maxTokens if self.manifest and self.manifest.spec else None
                ),
            }

    @property
    def user_profile(self) -> Optional[UserProfile]:
        """Return the user profile."""
        if not self._user_profile:
            logger.warning(
                "%s.user_profile() was accessed prior to being set.",
                self.formatted_class_name,
            )
        return self._user_profile

    @property
    def name(self) -> Optional[str]:
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
        plugin_meta = self._plugin_meta
        if plugin_meta is not None:
            plugin_meta.validate()
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
    def data(self) -> Optional[dict]:
        """Return the plugin as a dictionary."""
        if self.ready:
            return self.to_json()
        return None

    @property
    def yaml(self) -> str:
        """Return the plugin as a yaml string."""
        if not self.ready:
            raise SmarterPluginError("Plugin is not ready.")
        return yaml.dump(self.to_json())

    @property
    def function_calling_identifier(self) -> str:
        """Return the function calling plugin."""
        if not self.ready:
            raise SmarterPluginError("Plugin is not ready.")
        suffix = str(self.id).zfill(10)
        return f"{smarter_settings.function_calling_identifier_prefix}_{suffix}"

    def refresh(self):
        """Refresh the plugin."""
        if self.ready and self.id is not None:
            self.id = self.id
            return self.ready
        return False

    def selected(self, user: User, input_text: Optional[str] = None, messages: Optional[list[dict]] = None) -> bool:
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

        search_terms = self.plugin_selector.search_terms or []

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
                system_role = message.get(OpenAIMessageKeys.MESSAGE_CONTENT_KEY, "")
                custom_prompt = {
                    OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY,
                    OpenAIMessageKeys.MESSAGE_CONTENT_KEY: system_role
                    + "\n\nAnd also:\n"
                    + self.plugin_prompt.system_role,
                }
                messages_copy[i] = custom_prompt
                break

        return messages_copy

    @abstractmethod
    def tool_call_fetch_plugin_response(self, function_args: dict[str, Any]) -> Optional[str]:
        """
        Fetch information from a Plugin object.
        """
        raise NotImplementedError("tool_call_fetch_plugin_response() must be implemented in a subclass of PluginBase.")

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

    @property
    def function_parameters(self) -> Optional[dict[str, Any]]:
        """
        Fetch the function parameters from the Django model.
        - format according to the OpenAI function calling schema.
        """
        if not self.plugin_data:
            raise SmarterPluginError(
                f"{self.formatted_class_name}.function_parameters() error: {self.name} plugin data is not available."
            )
        retval = self.plugin_data.parameters
        if not isinstance(retval, dict):
            raise SmarterConfigurationError(
                f"{self.formatted_class_name}.function_parameters() error: {self.name} parameters must be a dictionary."
            )

        if "required" not in retval.keys():
            retval["required"] = []  # type: ignore[index]

        return retval

    def create(self):
        """Create a plugin from either yaml or a dictionary."""
        if not self._manifest:
            raise SmarterPluginError("Plugin manifest is not set.")
        logger.info("%s.create() creating plugin %s", self.formatted_class_name, self.manifest.metadata.name)

        def committed(plugin: PluginMeta):
            plugin_id: int = plugin.id if isinstance(plugin, PluginMeta) else None  # type: ignore[reportOptionalMemberAccess]
            self.id = plugin_id
            plugin_created.send(sender=self.__class__, plugin=self)
            plugin_meta = self._plugin_meta
            logger.info(
                "%s.create() created and committed plugin %s: %s.",
                self.formatted_class_name,
                self.plugin_meta.name if self.plugin_meta else "Unknown",
                plugin_meta.id if isinstance(plugin_meta, PluginMeta) else "Unknown",  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
            )

        meta_data = self.plugin_meta_django_model
        selector = self.plugin_selector_django_model
        prompt = self.plugin_prompt_django_model
        plugin_data = self.plugin_data_django_model

        if self.plugin_meta:
            self.id = self.plugin_meta.id  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
            logger.info(
                "%s.create() Plugin %s already exists. Updating plugin %s.",
                meta_data["name"] if meta_data else "Unknown",
                self.formatted_class_name,
                self.plugin_meta.id if self._plugin_meta else "Unknown",  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
            )
            return self.update()

        with transaction.atomic():
            if meta_data:
                plugin_meta = PluginMeta.objects.create(**meta_data)
                logger.info("%s.create() created PluginMeta: %s", self.formatted_class_name, plugin_meta)

                if selector is not None:
                    selector[PLUGIN_KEY] = plugin_meta
                if prompt is not None:
                    prompt[PLUGIN_KEY] = plugin_meta
                if plugin_data is not None:
                    plugin_data[PLUGIN_KEY] = plugin_meta

                if selector is not None:
                    plugin_selector = PluginSelector.objects.create(**selector)
                    logger.info("%s.create() created PluginSelector: %s", self.formatted_class_name, plugin_selector)
                if prompt is not None:
                    plugin_prompt = PluginPrompt.objects.create(**prompt)
                    logger.info("%s.create() created PluginPrompt: %s", self.formatted_class_name, plugin_prompt)
                if plugin_data is not None:
                    logger.info("%s.create() creating PluginData: %s", self.formatted_class_name, plugin_data)
                    self.plugin_data_class.objects.create(**plugin_data)

        transaction.on_commit(lambda: committed(plugin=plugin_meta))

        return True

    def update(self):
        """Update a plugin."""

        def committed():
            plugin_updated.send(sender=self.__class__, plugin=self)
            plugin_id: Optional[int] = self.plugin_meta.id if isinstance(self.plugin_meta, PluginMeta) else None  # type: ignore[reportOptionalMemberAccess]
            self.id = plugin_id  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
            logger.debug("Updated plugin %s: %s.", self.name, self.id)

        if not self.manifest:
            raise SmarterPluginError("Plugin manifest is not set.")

        plugin_meta_django_model = self.plugin_meta_django_model
        if not plugin_meta_django_model:
            account_number = self.user_profile.account.account_number if self.user_profile else "Unknown"
            raise SmarterPluginError(
                f"Plugin {self.manifest.metadata.name} for account {account_number} does not exist."
            )

        plugin_selector_django_model = self.plugin_selector_django_model
        plugin_prompt_django_model = self.plugin_prompt_django_model
        plugin_data_django_model = self.plugin_data_django_model

        with transaction.atomic():
            if isinstance(self.plugin_meta, PluginMeta):
                for attr, value in plugin_meta_django_model.items():
                    setattr(self.plugin_meta, attr, value)
                self.plugin_meta.save()
            else:
                raise SmarterPluginError("PluginMeta is not set or is not a PluginMeta instance.")

            if isinstance(plugin_selector_django_model, dict) and isinstance(self.plugin_selector, PluginSelector):
                for attr, value in plugin_selector_django_model.items():
                    setattr(self.plugin_selector, attr, value)
                self.plugin_selector.save()
            else:
                raise SmarterPluginError("PluginSelector is not set or is not a PluginSelector instance.")

            if isinstance(plugin_prompt_django_model, dict) and isinstance(self.plugin_prompt, PluginPrompt):
                for attr, value in plugin_prompt_django_model.items():
                    setattr(self.plugin_prompt, attr, value)
                self.plugin_prompt.save()
            else:
                raise SmarterPluginError("PluginPrompt is not set or is not a PluginPrompt instance.")

            if isinstance(plugin_data_django_model, dict) and isinstance(self.plugin_data, self.plugin_data_class):
                for attr, value in plugin_data_django_model.items():
                    setattr(self.plugin_data, attr, value)
                self.plugin_data.save()
            else:
                raise SmarterPluginError("PluginData is not set or is not a PluginData instance.")

        transaction.on_commit(committed)

        return True

    def save(self):
        """Save a plugin."""

        def committed():
            plugin_updated.send(sender=self.__class__, plugin=self)
            logger.debug("Saved plugin %s: %s.", self.name, self.id)

        if not self.ready:
            logger.warning("%s.save() Plugin is not ready. Cannot save.", self.formatted_class_name)
            return False

        with transaction.atomic():
            if isinstance(self.plugin_meta, PluginMeta):
                self.plugin_meta.save()
            else:
                raise SmarterPluginError("PluginMeta is not set or is not a PluginMeta instance.")

            if isinstance(self.plugin_selector, PluginSelector):
                self.plugin_selector.save()
            else:
                raise SmarterPluginError("PluginSelector is not set or is not a PluginSelector instance.")

            if isinstance(self.plugin_prompt, PluginPrompt):
                self.plugin_prompt.save()
            else:
                raise SmarterPluginError("PluginPrompt is not set or is not a PluginPrompt instance.")

            if isinstance(self.plugin_data, self.plugin_data_class):
                self.plugin_data.save()
            else:
                raise SmarterPluginError("PluginData is not set or is not a PluginData instance.")

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
            if isinstance(self.plugin_selector_history, QuerySet):
                self.plugin_selector_history.delete()

            if isinstance(self.plugin_data, self.plugin_data_class):
                self.plugin_data.delete()

            if isinstance(self.plugin_prompt, PluginPrompt):
                self.plugin_prompt.delete()

            if isinstance(self.plugin_selector, PluginSelector):
                self.plugin_selector.delete()

            if isinstance(self.plugin_meta, PluginMeta):
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

    def clone(self, new_name: Optional[str] = None):
        """Clone a plugin."""

        # pylint: disable=W0613
        def committed(new_plugin: Optional[PluginMeta]):
            plugin_cloned.send(sender=self.__class__, plugin=self)
            logger.info(
                "Cloned plugin %s: %s to %s: %s",
                self.id,
                self.name,
                new_plugin,
                new_plugin.name if new_plugin else "Unknown",
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
            if isinstance(plugin_meta_copy, PluginMeta):
                plugin_meta_copy.id = None  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
                plugin_meta_copy.name = new_name or get_new_name(plugin_name=self.name)
                plugin_meta_copy.save()
                if isinstance(self.plugin_meta, PluginMeta):
                    plugin_meta_copy.tags.set(self.plugin_meta.tags.all())
                plugin_meta_copy.refresh_from_db()

            # for each 1:1 relationship, create a new instance
            # setting the pk to None so that the new isn't
            # simply the old instance re-assigned to a new plugin_meta.
            # also, set the fk plugin_id to the new plugin_meta id.
            plugin_selector_copy = copy.deepcopy(self.plugin_selector)
            if isinstance(plugin_selector_copy, PluginSelector) and isinstance(plugin_meta_copy, PluginMeta):
                plugin_selector_copy.id = None  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
                plugin_selector_copy.plugin = plugin_meta_copy
                plugin_selector_copy.save()

            plugin_prompt_copy = copy.deepcopy(self.plugin_prompt)
            if isinstance(plugin_prompt_copy, PluginPrompt) and isinstance(plugin_meta_copy, PluginMeta):
                plugin_prompt_copy.id = None  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
                plugin_prompt_copy.plugin = plugin_meta_copy
                plugin_prompt_copy.save()

            plugin_data_copy = copy.deepcopy(self.plugin_data)
            if isinstance(plugin_data_copy, self.plugin_data_class) and isinstance(plugin_meta_copy, PluginMeta):
                plugin_data_copy.id = None  # type: ignore[reportAttributeAccessIssue,reportOptionalMemberAccess]
                plugin_data_copy.plugin = plugin_meta_copy
                plugin_data_copy.save()

        transaction.on_commit(lambda: committed(new_plugin=plugin_meta_copy))
        return plugin_meta_copy.id if plugin_meta_copy else None  # type: ignore[reportOptionalMemberAccess]

    @classmethod
    def parameter_factory(
        cls,
        name: str,
        data_type: str,
        description: str,
        enum: Optional[list] = None,
        required: Optional[bool] = False,
        default: Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Factory method to create a parameter dictionary for the SQL plugin.
        """
        retval = {
            "name": name,
            "type": data_type,
            "description": description,
            "required": required,
            "default": default,
        }
        if enum:
            if not isinstance(enum, list):
                raise SmarterConfigurationError(
                    f"{cls.formatted_class_name}.parameter_factory() error: {name} enum must be a list."
                )
            retval["enum"] = enum
        return retval

    def snake_to_camel(
        self, data: Union[str, dict, list], convert_values: bool = False
    ) -> Optional[Union[str, dict, list]]:
        """Convert snake_case to camelCase."""
        return util_snake_to_camel(data, convert_values)

    def camel_to_snake(self, data: Union[str, dict, list]) -> Optional[Union[str, dict, list]]:
        """Convert camelCase to snake_case."""
        return util_camel_to_snake(data)

    def to_json(self, version: str = "v1") -> Optional[dict[str, Any]]:
        """
        Serialize a plugin in JSON format that is importable by Pydantic. This
        is used to create a Pydantic model from a Django ORM model
        for purposes of rendering a Plugin manifest for the Smarter API.
        """

        # note: doing this to ensure that we can actually serialize the plugin data
        # pylint: disable=W0104
        {**self.plugin_data_serializer.data, "id": self.plugin_data.id if self.plugin_data else None}  # type: ignore[reportOptionalMemberAccess]

        if self.ready:
            if version == "v1":
                retval = {
                    SAMKeys.APIVERSION.value: self.api_version,
                    SAMKeys.KIND.value: self.kind,
                    SAMKeys.METADATA.value: self.plugin_meta_serializer.data if self.plugin_meta_serializer else None,
                    SAMKeys.SPEC.value: {
                        SAMPluginSpecKeys.SELECTOR.value: (
                            self.plugin_selector_serializer.data if self.plugin_selector_serializer else None
                        ),
                        SAMPluginSpecKeys.PROMPT.value: (
                            self.plugin_prompt_serializer.data if self.plugin_prompt_serializer else None
                        ),
                        SAMPluginSpecKeys.DATA.value: self.plugin_data_serializer.data,
                    },
                    SAMKeys.STATUS.value: {
                        "id": self.plugin_meta.id if self.plugin_meta else None,  # type: ignore[reportOptionalMemberAccess]
                        "accountNumber": (
                            self.user_profile.account.account_number
                            if isinstance(self.user_profile, UserProfile)
                            else None
                        ),
                        "username": (
                            self.user_profile.user.get_username()
                            if isinstance(self.user_profile, UserProfile)
                            else None
                        ),
                        "created": (
                            self.plugin_meta.created_at.isoformat()
                            if self.plugin_meta
                            and self.plugin_meta.created_at
                            and isinstance(self.plugin_meta.created_at, datetime.datetime)
                            else None
                        ),
                        "updated": (
                            self.plugin_meta.updated_at.isoformat()
                            if self.plugin_meta
                            and self.plugin_meta.updated_at
                            and isinstance(self.plugin_meta.updated_at, datetime.datetime)
                            else None
                        ),
                    },
                }
                if not isinstance(retval, dict):
                    raise SmarterConfigurationError(f"{self.formatted_class_name}.to_json() error: {self.name}.")
                if not isinstance(self.plugin_data_serializer.data, dict):
                    raise SmarterConfigurationError(
                        f"{self.formatted_class_name}.to_json() error: {self.name} plugin_data_serializer.data is not a dict."
                    )
                return json.loads(json.dumps(retval))
            raise SmarterPluginError(f"Invalid version: {version}")
        return None
