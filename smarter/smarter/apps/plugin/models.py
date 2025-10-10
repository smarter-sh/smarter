# pylint: disable=C0114,C0115,C0302
"""PluginMeta app models."""

# python stuff
import ast
import io
import logging
import re
import tempfile
from abc import abstractmethod
from functools import lru_cache
from http import HTTPStatus
from socket import socket
from typing import Any, Optional, Union, cast
from urllib.parse import urljoin

import paramiko
import requests

# django stuff
from django.core.exceptions import ImproperlyConfigured
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import DatabaseError, models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.utils import ConnectionHandler

# 3rd party stuff
from pydantic import ValidationError
from rest_framework import serializers
from taggit.managers import TaggableManager

from smarter.apps.account.models import Account, Secret, User, UserProfile
from smarter.apps.account.utils import get_cached_account_for_user

# smarter stuff
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import SettingsDefaults
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import camel_to_snake, rfc1034_compliant_str
from smarter.lib import json
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .manifest.enum import (
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
)

# plugin stuff
from .manifest.models.common import RequestHeader, TestValue, UrlParam
from .manifest.models.sql_connection.enum import DbEngines, DBMSAuthenticationMethods
from .signals import (
    plugin_api_connection_attempted,
    plugin_api_connection_failed,
    plugin_api_connection_query_attempted,
    plugin_api_connection_query_failed,
    plugin_api_connection_query_success,
    plugin_api_connection_success,
    plugin_sql_connection_attempted,
    plugin_sql_connection_failed,
    plugin_sql_connection_query_attempted,
    plugin_sql_connection_query_failed,
    plugin_sql_connection_query_success,
    plugin_sql_connection_success,
    plugin_sql_connection_validated,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

SMARTER_PLUGIN_MAX_DATA_RESULTS = 50


class PluginDataValueError(SmarterValueError):
    """Custom exception for PluginData SQL errors."""


def validate_no_spaces(value) -> None:
    """Validate that the string does not contain spaces."""
    if " " in value:
        raise SmarterValueError(f"Value must not contain spaces: {value}")


def validate_openai_parameters_dict(value):
    """
    example:

    'parameters': {
        'type': 'object',
        'properties': {
            'max_cost': {
                'type': 'float',
                'description': 'the maximum cost that a student is willing to pay for a course.'
            },
            'description': {
                'type': 'string',
                'description': 'areas of specialization for courses in the catalogue.',
                'enum': ['AI', 'mobile', 'web', 'database', 'network', 'neural networks']
            }
        },
        'required': ['max_cost']
        'additionalProperties': False
    }
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except (SyntaxError, ValueError) as e:
            raise PluginDataValueError(f"This field must be a valid dict. received: {value}") from e

    if not isinstance(value, dict):
        raise PluginDataValueError(f"This field must contain valid dicts. received: {value}")

    # validations
    if not isinstance(value, dict):
        raise PluginDataValueError("data parameters must be a dictionary.")
    if "properties" not in value.keys():
        raise PluginDataValueError("data parameters missing 'properties' key.")
    if "required" not in value.keys():
        raise PluginDataValueError("data parameters missing 'required' key.")
    else:
        if not isinstance(value["required"], list):
            raise PluginDataValueError("data parameters 'required' must be a list.")
        for item in value["required"]:
            if not isinstance(item, str):
                raise PluginDataValueError("data parameters 'required' items must be strings.")
            if not value["properties"].get(item):
                raise PluginDataValueError(
                    f"data parameters 'required' item '{item}' does not exist as a 'properties' dict."
                )

    # validate each property
    properties = value.get("properties", {})
    if not isinstance(properties, dict):
        raise PluginDataValueError("data parameters 'properties' must be a dictionary.")

    for key, value in properties.items():

        if not isinstance(key, str):
            raise PluginDataValueError("data parameters 'properties' keys must be strings.")
        if not isinstance(value, dict):
            raise PluginDataValueError(f"data parameters 'properties' value for key '{key}' must be a dictionary.")

        for k, _ in value.items():
            valid_keys = ["type", "enum", "description", "default"]
            if k not in valid_keys:
                raise PluginDataValueError(
                    f"data parameters 'properties' key '{k}' is not a valid key. Valid keys are: {valid_keys}"
                )

        if "type" not in value:
            raise PluginDataValueError(f"data parameters 'properties' value for key '{key}' missing 'type' key.")
        if value["type"] not in PluginDataSql.DataTypes.all():
            raise PluginDataValueError(
                f"data parameters 'properties' value for key '{key}' invalid 'type': {value['type']}"
            )
        if "description" not in value:
            raise PluginDataValueError(f"data parameters 'properties' value for key '{key}' missing 'description' key.")
        if "default" in value and value["default"] is not None:
            if value["type"] == "string" and not isinstance(value["default"], str):
                raise PluginDataValueError(
                    f"data parameters 'properties' value for key '{key}' 'default' must be a string."
                )
            if value["type"] == "number" and not isinstance(value["default"], (int, float)):
                raise PluginDataValueError(
                    f"data parameters 'properties' value for key '{key}' 'default' must be a number."
                )
            if value["type"] == "boolean" and not isinstance(value["default"], bool):
                raise PluginDataValueError(
                    f"data parameters 'properties' value for key '{key}' 'default' must be a boolean."
                )
            if value["type"] == "array" and not isinstance(value["default"], list):
                raise PluginDataValueError(
                    f"data parameters 'properties' value for key '{key}' 'default' must be an array."
                )
            if value["type"] == "object" and not isinstance(value["default"], dict):
                raise PluginDataValueError(
                    f"data parameters 'properties' value for key '{key}' 'default' must be an object."
                )


def dict_key_cleaner(key: str) -> str:
    """Clean a key by replacing spaces with underscores."""
    return str(key).replace("\n", "").replace("\r", "").replace("\t", "").replace(" ", "_")


def dict_keys_to_list(data: dict, keys=None) -> list[str]:
    """recursive function to extract all keys from a nested dictionary."""
    if keys is None:
        keys = []
    for key, value in data.items():
        keys.append(key)
        if isinstance(value, dict):
            dict_keys_to_list(value, keys)
    return keys


def list_of_dicts_to_list(data: list[dict]) -> Optional[list[str]]:
    """Convert a list of dictionaries into a single dict with keys extracted
    from the first key in the first dict."""
    if not data or not isinstance(data[0], dict):
        return None
    logger.warning("list_of_dicts_to_list() converting list of dicts to a single dict")
    retval = []
    key = next(iter(data[0]))
    for d in data:
        if key in d:
            cleaned_key = dict_key_cleaner(d[key])
            retval.append(cleaned_key)
    return retval


def list_of_dicts_to_dict(data: list[dict]) -> Optional[dict]:
    """Convert a list of dictionaries into a single dict with keys extracted
    from the first key in the first dict."""
    if not data or not isinstance(data[0], dict):
        return None
    retval = {}
    key = next(iter(data[0]))
    for d in data:
        if key in d:
            cleaned_key = dict_key_cleaner(d[key])
            retval[cleaned_key] = d[key]
    return retval


class PluginMeta(TimestampedModel, SmarterHelperMixin):
    """
    Stores metadata for a Smarter plugin.

    This model contains core information about a plugin, including its name, description,
    class type (static, SQL, or API), version, author, and associated tags. Each plugin
    is linked to an account and an author profile. The model enforces unique plugin names
    per account and validates that the plugin name is in snake_case format.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        unique_together = (
            "account",
            "name",
        )
        verbose_name = "Plugin"
        verbose_name_plural = "Plugins"

    PLUGIN_CLASSES = [
        (SAMPluginCommonMetadataClassValues.STATIC.value, SAMPluginCommonMetadataClassValues.STATIC.value),
        (SAMPluginCommonMetadataClassValues.SQL.value, SAMPluginCommonMetadataClassValues.SQL.value),
        (SAMPluginCommonMetadataClassValues.API.value, SAMPluginCommonMetadataClassValues.API.value),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="plugin_meta_account")
    name = models.CharField(
        help_text="The name of the plugin. Example: 'HR Policy Update' or 'Public Relation Talking Points'.",
        max_length=255,
        validators=[SmarterValidator.validate_snake_case, validate_no_spaces],
    )

    @property
    def rfc1034_compliant_name(self) -> Optional[str]:
        """
        Returns a url friendly name for the chatbot.
        This is a convenience property that returns
        a RFC 1034 compliant name for the chatbot.

        example:
        - self.name: 'Example ChatBot 1'
        - self.rfc1034_compliant_name: 'example-chatbot-1'
        """
        if self.name:
            return rfc1034_compliant_str(self.name)
        return None

    description = models.TextField(
        help_text="A brief description of the plugin. Be verbose, but not too verbose.",
    )
    plugin_class = models.CharField(
        choices=PLUGIN_CLASSES, help_text="The class name of the plugin", max_length=255, default="PluginMeta"
    )
    version = models.CharField(max_length=255, default="1.0.0")
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="plugin_meta_author")
    tags = TaggableManager(blank=True)

    def __str__(self):
        return str(self.name) or ""

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        if isinstance(self.name, str) and not SmarterValidator.is_valid_snake_case(self.name):
            snake_case_name = camel_to_snake(self.name)
            logger.warning(
                "%s.save(): name %s was not in snake_case. Converted to snake_case: %s",
                self.formatted_class_name,
                self.name,
                snake_case_name,
            )
            self.name = snake_case_name
        self.validate()
        super().save(*args, **kwargs)

    @property
    def kind(self) -> SAMKinds:
        """
        Return the kind of the plugin based on its class.
        This is used to determine how the plugin should be handled.
        """
        if self.plugin_class == SAMPluginCommonMetadataClassValues.STATIC.value:
            return SAMKinds.STATIC_PLUGIN
        elif self.plugin_class == SAMPluginCommonMetadataClassValues.SQL.value:
            return SAMKinds.SQL_PLUGIN
        elif self.plugin_class == SAMPluginCommonMetadataClassValues.API.value:
            return SAMKinds.API_PLUGIN
        else:
            raise SmarterValueError(f"Unsupported plugin class: {self.plugin_class}")

    @property
    def rfc1034_compliant_kind(self) -> Optional[str]:
        """
        Returns a url friendly kind for the chatbot.
        This is a convenience property that returns
        a RFC 1034 compliant kind for the chatbot.

        example:
        - self.kind: 'Static'
        - self.rfc1034_compliant_kind: 'static'
        """
        if self.kind:
            return rfc1034_compliant_str(self.kind.value)
        return None

    @classmethod
    @cache_results()
    def get_cached_plugins_for_user(cls, user: User) -> list["PluginMeta"]:
        """
        Return a list of all instances of PluginMeta for the given user.
        This method caches the results to improve performance.
        """
        account = get_cached_account_for_user(user)
        if not account:
            return []
        plugins = cls.objects.filter(account=account).order_by("name")
        return list(plugins) or []

    @classmethod
    def get_cached_plugin_by_name(cls, user: User, name: str) -> Union["PluginMeta", None]:
        """
        Return a single instance of PluginMeta by name for the given user.
        This method caches the results to improve performance.
        """
        account = get_cached_account_for_user(user)
        if not account:
            return None
        try:
            return cls.objects.get(account=account, name=name)
        except cls.DoesNotExist:
            logger.warning(
                "%s.get_cached_plugin_by_name: Plugin not found for name: %s", cls.formatted_class_name, name
            )
            return None


class PluginSelector(TimestampedModel, SmarterHelperMixin):
    """
    Stores plugin selection strategies for a Smarter plugin.

    This model defines Smarter chat prompt selection strategy for a plugin. That is,
    whether or not a plugin is included in the prompt sent to the LLM.
    Each PluginSelector is linked to a PluginMeta instance and specifies a directive
    (such as 'search_terms') and a set of search terms in JSON format. If any of the
    search terms are detected in the user prompt, Smarter will prioritize loading this plugin.

    """

    SELECT_DIRECTIVES = [
        (
            SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
            SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
        ),
        (
            SAMPluginCommonSpecSelectorKeyDirectiveValues.ALWAYS.value,
            SAMPluginCommonSpecSelectorKeyDirectiveValues.ALWAYS.value,
        ),
        (
            SAMPluginCommonSpecSelectorKeyDirectiveValues.LLM.value,
            SAMPluginCommonSpecSelectorKeyDirectiveValues.LLM.value,
        ),
    ]

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_selector_plugin")
    directive = models.CharField(
        help_text="The selection strategy to use for this plugin.",
        max_length=255,
        default=SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
        choices=SELECT_DIRECTIVES,
    )
    search_terms = models.JSONField(
        help_text="search terms in JSON format that, if detected in the user prompt, will incentivize Smarter to load this plugin.",
        default=list,
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        search_terms = json.dumps(self.search_terms)[:50]
        return f"{str(self.directive)} - {search_terms}"


class PluginSelectorSerializer(serializers.ModelSerializer):

    class Meta:
        model = PluginSelector
        fields = "__all__"


class PluginSelectorHistory(TimestampedModel, SmarterHelperMixin):
    """
    Stores the history of plugin selector activations.

    This model persists each Plugin selection, including the search term
    that caused the activation, the user prompt messages, and the session key. It is useful
    for auditing, analytics, and understanding how plugins are selected in response to user input.
    """

    plugin_selector = models.ForeignKey(
        PluginSelector, on_delete=models.CASCADE, related_name="plugin_selector_history_plugin_selector"
    )
    search_term = models.CharField(max_length=255, blank=True, null=True, default="")
    messages = models.JSONField(help_text="The user prompt messages.", default=list, blank=True, null=True)
    session_key = models.CharField(max_length=255, blank=True, null=True, default="")

    def __str__(self) -> str:
        return f"{str(self.plugin_selector.plugin.name)} - {self.search_term}"

    class Meta:
        verbose_name_plural = "Plugin Selector History"


class PluginSelectorHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for the PluginSelectorHistory model.

    Serializes all fields of PluginSelectorHistory, including a nested representation
    of the related PluginSelector.
    """

    plugin_selector = PluginSelectorSerializer()

    class Meta:
        model = PluginSelectorHistory
        fields = "__all__"


class PluginPrompt(TimestampedModel, SmarterHelperMixin):
    """
    Stores LLM prompt model configuration for a Smarter plugin.

    This model defines the prompt settings for a plugin, including the LLM provider,
    system role, model, temperature, and maximum tokens. Each PluginPrompt is linked
    to a PluginMeta instance and customizes how the plugin interacts with the LLM.
    """

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_prompt_plugin")
    provider = models.TextField(
        help_text="The name of the LLM provider for the plugin. Example: 'openai'.",
        null=True,
        blank=True,
        default=SettingsDefaults.LLM_DEFAULT_PROVIDER,
    )
    system_role = models.TextField(
        help_text="The role of the system in the conversation.",
        null=True,
        blank=True,
        default="You are a helful assistant.",
    )
    model = models.CharField(
        help_text="The model to use for the completion.", max_length=255, default=SettingsDefaults.LLM_DEFAULT_MODEL
    )
    temperature = models.FloatField(
        help_text="The higher the temperature, the more creative the result.",
        default=SettingsDefaults.LLM_DEFAULT_TEMPERATURE,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    max_completion_tokens = models.IntegerField(
        help_text="The maximum number of tokens for both input and output.",
        default=SettingsDefaults.LLM_DEFAULT_MAX_TOKENS,
        validators=[MinValueValidator(0), MaxValueValidator(8192)],
    )

    def __str__(self) -> str:
        return str(self.plugin.name)


class PluginDataBase(TimestampedModel, SmarterHelperMixin):
    """PluginData base model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_data_base_plugin")

    description = models.TextField(
        help_text="A brief description of what this plugin returns. Be verbose, but not too verbose.",
    )
    parameters = models.JSONField(
        help_text="A JSON dict containing parameter names and data types. Example: {'required': [], 'properties': {'max_cost': {'type': 'float', 'description': 'the maximum cost that a student is willing to pay for a course.'}, 'description': {'enum': ['AI', 'mobile', 'web', 'database', 'network', 'neural networks'], 'type': 'string', 'description': 'areas of specialization for courses in the catalogue.'}}}",
        default=dict,
        blank=True,
        null=True,
        validators=[validate_openai_parameters_dict],
    )
    test_values = models.JSONField(
        help_text="A JSON dict containing test values for each parameter. Example: {'city': 'San Francisco'}",
        blank=True,
        null=True,
    )

    @abstractmethod
    def sanitized_return_data(self, params: Optional[dict] = None) -> dict:
        """Returns a dict of custom data return results."""
        raise NotImplementedError

    @abstractmethod
    def data(self, params: Optional[dict] = None) -> dict:
        """Returns a dict of custom data return results."""
        raise NotImplementedError

    def validate_all_parameters_in_test_values(self) -> None:
        """
        Validate if all parameters are present in the test values.
        'test_values': [{'name': 'description', 'value': 'AI'}, {'name': 'max_cost', 'value': '500.0'}]
        """
        if self.parameters is None or self.test_values is None:
            return None
        parameters: dict[str, Any] = {}

        try:
            if not isinstance(self.parameters, dict):
                parameters = json.loads(self.parameters)
            else:
                parameters = self.parameters
        except json.JSONDecodeError as e:
            raise SmarterValueError(f"Invalid JSON in parameters. This is a bug: {e}") from e
        if "properties" not in parameters or not isinstance(parameters["properties"], dict):
            raise SmarterValueError(
                "Parameters must be a dict with a 'properties' key containing parameter definitions."
            )
        try:
            if not isinstance(self.test_values, list):
                test_values = json.loads(self.test_values)
            else:
                test_values = self.test_values
        except json.JSONDecodeError as e:
            raise SmarterValueError(f"Invalid JSON in test_values. This is a bug: {e}") from e
        if not isinstance(test_values, list):
            raise SmarterValueError(f"test_values must be a list but got: {type(test_values)}")

        properties = parameters["properties"]

        if isinstance(test_values, list):
            test_values_names = [tv["name"] for tv in test_values if isinstance(tv, dict) and "name" in tv]
            for param_name in properties:
                if param_name not in test_values_names:
                    raise SmarterValueError(
                        f"Parameter '{param_name}' is defined in parameters but not in test_values. "
                        "Ensure all parameters have corresponding test values."
                    )
                if not any(tv["name"] == param_name for tv in test_values):
                    raise SmarterValueError(
                        f"Test value for parameter '{param_name}' is missing. "
                        "Ensure all parameters have corresponding test values."
                    )


class PluginDataStatic(PluginDataBase):
    """
    Stores the configuration and static data set for a Smarter plugin
    which is based on static data.

    This model is used for plugins that return static (predefined) data.
    The static_data field holds the JSON data that will be returned to the LLM
    when the plugin is invoked. The model provides methods for returning sanitized
    data and extracting keys from the static data.
    """

    static_data = models.JSONField(
        help_text="The JSON data that this plugin returns to OpenAI API when invoked by the user prompt.", default=dict
    )

    def sanitized_return_data(self, params: Optional[dict] = None) -> Optional[Union[dict, list]]:
        """Returns a dict or list of self.static_data."""
        retval: Union[dict, list, None] = None
        if isinstance(self.static_data, dict):
            return self.static_data
        if isinstance(self.static_data, list):
            retval = self.static_data
            if isinstance(retval, list) and len(retval) > 0:
                if len(retval) > SMARTER_PLUGIN_MAX_DATA_RESULTS:
                    logger.warning(
                        "%s.sanitized_return_data: Truncating static_data to %s items.",
                        self.formatted_class_name,
                        {SMARTER_PLUGIN_MAX_DATA_RESULTS},
                    )
                retval = retval[:SMARTER_PLUGIN_MAX_DATA_RESULTS]  # pylint: disable=E1136
                retval = list_of_dicts_to_dict(data=retval)
        else:
            raise SmarterValueError("static_data must be a dict or a list or None")

        return retval

    @property
    @lru_cache(maxsize=128)
    def return_data_keys(self) -> Optional[list[str]]:
        """Return all keys in the static_data."""

        retval: Optional[list[Any]] = []
        if isinstance(self.static_data, dict):
            retval = dict_keys_to_list(data=self.static_data)
            retval = list(retval) if retval else None
        elif isinstance(self.static_data, list):
            retval = self.static_data
            if isinstance(retval, list) and len(retval) > 0:
                if len(retval) > SMARTER_PLUGIN_MAX_DATA_RESULTS:
                    logger.warning(
                        "%s.return_data_keys: Truncating static_data to %s items.",
                        self.formatted_class_name,
                        {SMARTER_PLUGIN_MAX_DATA_RESULTS},
                    )
                retval = retval[:SMARTER_PLUGIN_MAX_DATA_RESULTS]  # pylint: disable=E1136
                retval = list_of_dicts_to_list(data=retval)
        else:
            raise SmarterValueError("static_data must be a dict or a list or None")

        return retval[:SMARTER_PLUGIN_MAX_DATA_RESULTS] if isinstance(retval, list) else retval

    def data(self, params: Optional[dict] = None) -> Optional[dict]:
        try:
            data = json.loads(self.static_data)
            if not isinstance(data, dict):
                logger.warning("%s.data: static_data is not a dict, returning None.", self.formatted_class_name)
                return None
            return data
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("%s.data: Failed to decode static_data JSON: %s", self.formatted_class_name, e)
            return None

    def __str__(self) -> str:
        return str(self.plugin.name)

    class Meta:
        verbose_name = "Plugin Static Data"
        verbose_name_plural = "Plugin Static Data"


class ConnectionBase(TimestampedModel, SmarterHelperMixin):
    """
    Base class for connection models.
    """

    class Meta:
        abstract = True

    CONNECTION_KIND_CHOICES = [
        (SAMKinds.SQL_CONNECTION.value, SAMKinds.SQL_CONNECTION.value),
        (SAMKinds.API_CONNECTION.value, SAMKinds.API_CONNECTION.value),
    ]

    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    name = models.CharField(
        help_text="The name of the connection, without spaces. Example: 'hr_database', 'sales_db', 'inventory_api'.",
        max_length=255,
        validators=[SmarterValidator.validate_snake_case, validate_no_spaces],
    )
    kind = models.CharField(
        help_text="The kind of connection. Example: 'SQL', 'API'.",
        max_length=50,
        choices=CONNECTION_KIND_CHOICES,
    )
    description = models.TextField(
        help_text="A brief description of the connection. Be verbose, but not too verbose.", blank=True, null=True
    )
    version = models.CharField(
        help_text="The version of the connection. Example: '1.0.0'.",
        max_length=255,
        default="1.0.0",
        blank=True,
        null=True,
    )

    @property
    @abstractmethod
    def connection_string(self) -> str:
        """Return the connection string."""
        raise NotImplementedError

    @classmethod
    def get_cached_connections_for_user(cls, user: User) -> list["ConnectionBase"]:
        """
        Return a list of all instances of all concrete subclasses of ConnectionBase.
        """
        if user is None:
            logger.warning("%s.get_cached_connections_for_user: user is None", cls.formatted_class_name)
            return []
        account = get_cached_account_for_user(user)
        instances = []
        for subclass in ConnectionBase.__subclasses__():
            instances.extend(subclass.objects.filter(account=account).order_by("name"))
        return instances or []

    @classmethod
    @cache_results()
    def get_cached_connection_by_name_and_kind(
        cls, user: User, kind: SAMKinds, name: str
    ) -> Union["ConnectionBase", None]:
        """
        Return a single instance of a concrete subclass of ConnectionBase by name.
        """
        account = get_cached_account_for_user(user)
        if not kind or not kind in [SAMKinds.SQL_CONNECTION, SAMKinds.API_CONNECTION]:
            raise SmarterValueError(f"Unsupported connection kind: {kind}")
        if kind == SAMKinds.SQL_CONNECTION:
            try:
                return SqlConnection.objects.get(account=account, name=name)
            except SqlConnection.DoesNotExist:
                pass

        elif kind == SAMKinds.API_CONNECTION:
            try:
                return ApiConnection.objects.get(account=account, name=name)
            except ApiConnection.DoesNotExist:
                pass


class SqlConnection(ConnectionBase):
    """
    Stores SQL connection configuration for a Smarter plugin.

    This model defines the connection details for a SQL database used by a plugin,
    including database engine, authentication method, host, port, credentials, SSL/TLS,
    and proxy settings. It provides methods for establishing connections using various
    authentication methods (TCP/IP, SSH, LDAP), executing queries, and validating the connection.
    """

    _connection: Optional[BaseDatabaseWrapper] = None

    def __del__(self):
        """Close the database connection when the object instance is destroyed."""
        self.close()

    class ParamikoUpdateKnownHostsPolicy(paramiko.MissingHostKeyPolicy):
        def __init__(self, sql_connection: "SqlConnection"):
            self.sql_connection = sql_connection

        # pylint: disable=W0613
        def missing_host_key(self, client, hostname, key):
            # Add the new host key to the known_hosts field
            new_entry = f"{hostname} {key.get_name()} {key.get_base64()}\n"
            if self.sql_connection.ssh_known_hosts:
                self.sql_connection.ssh_known_hosts += new_entry
            else:
                self.sql_connection.ssh_known_hosts = new_entry
            self.sql_connection.save()
            logger.warning(
                "%s. Unknown host key for %s. Key added to known_hosts.",
                self.sql_connection.formatted_class_name,
                hostname,
            )

    DBMS_DEFAULT_TIMEOUT = 30
    DBMS_CHOICES = [
        (DbEngines.MYSQL.value, DbEngines.MYSQL.value),
        (DbEngines.POSTGRES.value, DbEngines.POSTGRES.value),
        (DbEngines.SQLITE.value, DbEngines.SQLITE.value),
        (DbEngines.ORACLE.value, DbEngines.ORACLE.value),
        (DbEngines.MSSQL.value, DbEngines.MSSQL.value),
        (DbEngines.SYBASE.value, DbEngines.SYBASE.value),
    ]
    DBMS_AUTHENITCATION_METHODS = [
        (DBMSAuthenticationMethods.NONE.value, "None"),
        (DBMSAuthenticationMethods.TCPIP.value, "Standard TCP/IP"),
        (DBMSAuthenticationMethods.TCPIP_SSH.value, "Standard TCP/IP over SSH"),
        (DBMSAuthenticationMethods.LDAP_USER_PWD.value, "LDAP User/Password"),
    ]
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="sql_connections")
    db_engine = models.CharField(
        help_text="The type of database management system. Example: 'MySQL', 'PostgreSQL', 'MS SQL Server', 'Oracle'.",
        default=DbEngines.MYSQL.value,
        max_length=255,
        choices=DBMS_CHOICES,
        blank=True,
        null=True,
    )
    authentication_method = models.CharField(
        help_text="The authentication method to use for the connection. Example: 'Standard TCP/IP', 'Standard TCP/IP over SSH', 'LDAP User/Password'.",
        max_length=255,
        choices=DBMSAuthenticationMethods.choices(),
        default=DBMSAuthenticationMethods.TCPIP.value,
    )
    timeout = models.IntegerField(
        help_text="The timeout for the database connection in seconds. Default is 30 seconds.",
        default=DBMS_DEFAULT_TIMEOUT,
        validators=[MinValueValidator(1)],
        blank=True,
    )

    # SSL/TLS fields
    use_ssl = models.BooleanField(
        default=False, help_text="Whether to use SSL/TLS for the connection.", blank=True, null=True
    )
    ssl_cert = models.TextField(blank=True, null=True, help_text="The SSL certificate for the connection, if required.")
    ssl_key = models.TextField(blank=True, null=True, help_text="The SSL key for the connection, if required.")
    ssl_ca = models.TextField(
        blank=True, null=True, help_text="The Certificate Authority (CA) certificate for verifying the server."
    )

    # connection fields
    hostname = models.CharField(
        max_length=255, help_text="The remote host of the SQL connection. Should be a valid internet domain name."
    )
    port = models.IntegerField(
        default=3306, help_text="The port of the SQL connection. example: 3306 for MySQL.", blank=True, null=True
    )
    database = models.CharField(max_length=255, help_text="The name of the database to connect to.")
    username = models.CharField(max_length=255, blank=True, null=True, help_text="The database username.")
    password = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="sql_connections_password",
        help_text="The password for authentication, if required.",
        blank=True,
        null=True,
    )
    pool_size = models.IntegerField(default=5, help_text="The size of the connection pool.", blank=True, null=True)
    max_overflow = models.IntegerField(
        default=10,
        help_text="The maximum number of connections to allow beyond the pool size.",
        validators=[MinValueValidator(1)],
        blank=True,
        null=True,
    )

    # Proxy fields
    proxy_protocol = models.CharField(
        max_length=10,
        choices=[("http", "HTTP"), ("https", "HTTPS"), ("socks", "SOCKS")],
        default="http",
        help_text="The protocol to use for the proxy connection.",
        blank=True,
        null=True,
    )
    proxy_host = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The remote host of the SQL proxy connection. Should be a valid internet domain name.",
    )
    proxy_port = models.IntegerField(blank=True, null=True, help_text="The port of the SQL proxy connection.")
    proxy_username = models.CharField(
        max_length=255, blank=True, null=True, help_text="The username for the proxy connection."
    )
    proxy_password = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="sql_connections_proxy_password",
        help_text="The API key for authentication, if required.",
        blank=True,
        null=True,
    )
    ssh_known_hosts = models.TextField(
        blank=True,
        null=True,
        help_text="The known_hosts file content for verifying SSH connections. Usually comes from ~/.ssh/known_hosts.",
    )

    @property
    def connection(self) -> Optional[BaseDatabaseWrapper]:
        """
        Return the database connection if it exists, otherwise create a new one.
        """
        if self._connection:
            return self._connection
        self._connection = self.get_connection()
        return self._connection

    @property
    def db_options(self) -> dict:
        """Return the database connection options."""
        retval = {}
        if self.use_ssl:
            retval["ssl"] = {
                "ca": self.ssl_ca,
                "cert": self.ssl_cert,
                "key": self.ssl_key,
            }
        if self.authentication_method == "ldap_user_pwd":
            retval["authentication"] = "LDAP"
        return retval

    @property
    def django_db_connection(self) -> dict:
        """Return the database connection settings for Django."""
        retval = {
            "ENGINE": self.db_engine,
            "NAME": self.database,
            "USER": self.username,
            "PASSWORD": self.password.get_secret() if self.password else None,
            "HOST": self.hostname,
            "PORT": str(self.port),
            "OPTIONS": self.db_options,
        }
        return retval

    @property
    def connection_string(self) -> str:
        return self.get_connection_string()

    def connect_tcpip(self) -> Optional[BaseDatabaseWrapper]:
        """
        Establish a test database connection using Standard TCP/IP.
        """
        plugin_sql_connection_attempted.send(sender=self.__class__, connection=self)
        try:
            connection_handler = ConnectionHandler({"default": self.django_db_connection})
            db_wrapper = connection_handler["default"]
            db_wrapper.ensure_connection()
            if db_wrapper.is_usable():
                plugin_sql_connection_success.send(sender=self.__class__, connection=self)
                return db_wrapper  # type: ignore[return-value]
            else:
                msg = "Failed to establish TCP/IP connection: No connection object found."
                plugin_sql_connection_failed.send(sender=self.__class__, connection=self, error=msg)
                return None
        except (DatabaseError, ImproperlyConfigured) as e:
            plugin_sql_connection_failed.send(sender=self.__class__, connection=self, error=str(e))
            return None

    def transport_handler(self, channel, src_addr, dest_addr):
        logger.info(
            "%s.transport_handler() Transport handler called with channel: %s, src_addr: %s, dest_addr: %s",
            self.formatted_class_name,
            channel,
            src_addr,
            dest_addr,
        )

    def connect_tcpip_ssh(self) -> Optional[BaseDatabaseWrapper]:
        """
        Establish a database connection using Standard TCP/IP over SSH with Paramiko.
        """

        try:
            plugin_sql_connection_attempted.send(sender=self.__class__, connection=self)
            ssh_client = paramiko.SSHClient()
            if self.ssh_known_hosts:
                known_hosts_file = io.StringIO(self.ssh_known_hosts)
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    temp_file.write(self.ssh_known_hosts.encode())
                    known_hosts_file = temp_file.name
                ssh_client.load_host_keys(known_hosts_file)
            else:
                ssh_client.load_system_host_keys()

            ssh_client.load_system_host_keys()
            ssh_client.set_missing_host_key_policy(SqlConnection.ParamikoUpdateKnownHostsPolicy(self))

            ssh_client.connect(
                hostname=self.hostname,
                port=self.port if self.port else 22,  # Default SSH port is 22
                username=self.proxy_username,
                password=self.proxy_password.get_secret(update_last_accessed=False) if self.proxy_password else None,
                timeout=self.timeout,
            )

            # Open a local port forwarding channel
            transport = ssh_client.get_transport()
            local_socket = socket()
            local_socket.bind(("127.0.0.1", 0))  # Bind to an available local port
            local_socket.listen(1)
            local_port = local_socket.getsockname()[1]

            # Forward the remote database port to the local port
            if isinstance(transport, paramiko.Transport):
                transport.request_port_forward(address="127.0.0.1", port=local_port, handler=self.transport_handler)

            connection_handler = ConnectionHandler(self.django_db_connection)
            tcpip_ssh_connection: BaseDatabaseWrapper = connection_handler["default"].connection
            tcpip_ssh_connection.ensure_connection()

            # Close the SSH connection after ensuring the database connection
            plugin_sql_connection_success.send(sender=self.__class__, connection=self)
            return connection_handler

        except (paramiko.SSHException, DatabaseError, ImproperlyConfigured) as e:
            logger.error("%s.connect_tcpip_ssh() SSH connection failed: %s", self.formatted_class_name, e)
            plugin_sql_connection_failed.send(sender=self.__class__, connection=self, error=str(e))
            return None
        # pylint: disable=W0718
        except Exception as e:
            plugin_sql_connection_failed.send(sender=self.__class__, connection=self, error=str(e))
            logger.error("%s.connect_tcpip_ssh() An unexpected error occurred: %s", self.formatted_class_name, e)
            return None

    def connect_ldap_user_pwd(self) -> Optional[BaseDatabaseWrapper]:
        """
        Establish a database connection using LDAP User/Password authentication.
        """
        try:
            # Example: Customize the connection string for LDAP authentication
            plugin_sql_connection_attempted.send(sender=self.__class__, connection=self)
            databases = self.django_db_connection
            connection_handler = ConnectionHandler(databases)
            ldap_user_pwd_connection: BaseDatabaseWrapper = connection_handler["default"].connection
            ldap_user_pwd_connection.ensure_connection()
            plugin_sql_connection_success.send(sender=self.__class__, connection=self)
            return ldap_user_pwd_connection
        # pylint: disable=W0718
        except Exception as e:
            plugin_sql_connection_failed.send(sender=self.__class__, connection=self, error=str(e))
            logger.error(
                "%s.connect_ldap_user_pwd() LDAP User/Password connection failed: %s", self.formatted_class_name, e
            )
            return None

    def test_connection(self) -> bool:
        """
        Establish a database connection based on the authentication method.
        """
        connection = self.get_connection()
        return connection is not None

    def get_connection(self) -> Optional[BaseDatabaseWrapper]:
        """
        Establish a database connection based on the authentication method.
        """
        if self.authentication_method == DBMSAuthenticationMethods.NONE.value:
            retval = self.connect_tcpip()
        elif self.authentication_method == DBMSAuthenticationMethods.TCPIP.value:
            retval = self.connect_tcpip()
        elif self.authentication_method == DBMSAuthenticationMethods.TCPIP_SSH.value:
            retval = self.connect_tcpip_ssh()
        elif self.authentication_method == DBMSAuthenticationMethods.LDAP_USER_PWD.value:
            retval = self.connect_ldap_user_pwd()
        else:
            raise SmarterValueError(f"Unsupported authentication method: {self.authentication_method}")

        if isinstance(retval, BaseDatabaseWrapper):
            return retval
        else:
            logger.error(
                "%s.get_connection() Failed to establish a database connection using method: %s. Got return type of %s",
                self.formatted_class_name,
                self.authentication_method,
                type(retval),
            )
            return None

    def close(self):
        """Close the database connection."""
        if self._connection:
            try:
                self._connection.close()
            # pylint: disable=W0718
            except Exception as e:
                logger.error("%s.close() Failed to close the database connection: %s", self.formatted_class_name, e)
            self._connection = None

    def execute_query(self, sql: str, limit: Optional[int] = None) -> Union[str, bool]:
        def query_result_to_json(cursor) -> str:
            # Get column names from cursor description
            columns = [col[0] for col in cursor.description]
            # Fetch all rows
            rows = cursor.fetchall()
            # Convert each row to a dict
            result = [dict(zip(columns, row)) for row in rows]
            # Convert to JSON string (optional)
            return json.dumps(result)

        if not isinstance(self.connection, BaseDatabaseWrapper):
            return False
        query_connection = self.connection
        plugin_sql_connection_query_attempted.send(sender=self.__class__, connection=self, sql=sql, limit=limit)
        try:
            if limit is not None:
                sql = sql.rstrip(";")  # Remove any trailing semicolon
                sql += f" LIMIT {limit};"
            with query_connection.cursor() as cursor:
                cursor.execute(sql)
                json_str = query_result_to_json(cursor)
                plugin_sql_connection_query_success.send(sender=self.__class__, connection=self, sql=sql, limit=limit)
                return json_str
        except (DatabaseError, ImproperlyConfigured) as e:
            plugin_sql_connection_query_failed.send(
                sender=self.__class__, connection=self, sql=sql, limit=limit, error=str(e)
            )
            logger.error("%s.execute_query() SQL query execution failed: %s", self.formatted_class_name, e)
            return False
        finally:
            self.close()

    def test_proxy(self) -> bool:
        proxy_dict: Optional[dict] = (
            {
                self.proxy_protocol: f"{self.proxy_protocol}://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}",
            }
            if self.proxy_protocol is not None and self.proxy_host is not None
            else None
        )
        try:
            response = requests.get("https://www.google.com", proxies=proxy_dict, timeout=self.timeout)
            return response.status_code in [HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT]
        except requests.exceptions.RequestException as e:
            logger.error("%s.test_proxy() proxy test connection failed: %s", self.formatted_class_name, e)
            return False

    def get_connection_string(self, masked: bool = True) -> str:
        """Return the connection string."""
        if masked:
            password = "******"
        else:
            password = self.password.get_secret() if self.password else None
        userinfo = f"{self.username}:{password}" if password else self.username
        return f"{self.db_engine}://{userinfo}@{self.hostname}:{self.port}/{self.database}"

    def validate(self) -> bool:
        super().validate()
        retval = self.test_connection()
        plugin_sql_connection_validated.send(sender=self.__class__, connection=self)
        return retval

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        if not SmarterValidator.is_valid_snake_case(self.name):
            snake_case_name = camel_to_snake(self.name)
            logger.warning(
                "%s.save(): name %s was not in snake_case. Converted to snake_case: %s",
                self.formatted_class_name,
                self.name,
                snake_case_name,
            )
            self.name = snake_case_name
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name + " - " + self.get_connection_string() if isinstance(self.name, str) else "unassigned"


class PluginDataSql(PluginDataBase):
    """
    Stores SQL-based data configuration for a Smarter plugin.

    This model is used for plugins that return data by executing SQL queries.
    It defines the SQL connection, query, parameters, test values, and result limits.
    The model provides methods for validating parameter and test value structures,
    preparing SQL queries with parameters, and executing queries.
    """

    class DataTypes:
        STR = "string"
        NUMBER = "number"
        INT = "integer"
        BOOL = "bool"
        OBJECT = "object"
        ARRAY = "array"
        NULL = "null"

        @classmethod
        def all(cls) -> list[str]:
            return [cls.STR, cls.NUMBER, cls.INT, cls.BOOL, cls.OBJECT, cls.ARRAY, cls.NULL]

    connection = models.ForeignKey(SqlConnection, on_delete=models.CASCADE, related_name="plugin_data_sql_connection")
    sql_query = models.TextField(
        help_text="The SQL query that this plugin will execute when invoked by the user prompt.",
    )
    limit = models.IntegerField(
        help_text="The maximum number of rows to return from the query.",
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )

    def data(self, params: Optional[dict] = None) -> dict:
        return {
            "parameters": self.parameters,
            "sql_query": self.prepare_sql(params=params),
        }

    def are_test_values_pydantic(self) -> bool:
        if not isinstance(self.test_values, list):
            return False
        return all(isinstance(tv, dict) and "name" in tv and "value" in tv for tv in self.test_values)  # type: ignore  # pylint: disable=not-an-iterable

    def validate_test_values(self) -> None:
        """
        Validate if the structure of self.test_values matches the expected Json representation
        by attempting to instantiate each item in the list as a Pydantic TestValue model.

            "test_values": [
                {
                "name": "username",
                "value": "admin"
                },
                {
                "name": "unit",
                "value": "Celsius"
                }
            ]
        """
        if self.test_values is None:
            return None
        if not isinstance(self.test_values, list):
            raise SmarterValueError(f"test_values must be a list of dictionaries but got: {type(self.test_values)}")

        # pylint: disable=E1133
        for test_value in self.test_values:
            try:
                TestValue(**test_value)
            except (ValidationError, SmarterValueError) as e:
                raise SmarterValueError(f"Invalid test value structure: {e}") from e

    def validate_all_placeholders_in_parameters(self) -> None:
        """
        Validate that all placeholders in the SQL query string are present in the parameters.

        example plugin:
            {
            'plugin': <PluginMeta: sql_test>,
            'description': 'test plugin',
            'sql_query': "SELECT * FROM auth_user WHERE username = '{username}';",

            'parameters': {
                'type': 'object',
                'properties': {
                    'username': {
                        'type': 'string',
                        'description': 'The username of the user.'
                    }
                },
                'required': ['username'],
                'additionalProperties': False
                },
            'test_values': 'admin',
            'limit': 1,
            'connection': <SqlConnection: test_sql_connection - django.db.backends.mysql://smarter:******@smarter-mysql:3306/smarter>
            }

        """
        placeholders = re.findall(r"{(.*?)}", self.sql_query) or []
        parameters = self.parameters or {}
        properties = parameters.get("properties", {})
        logger.info(
            "%s.validate_all_placeholders_in_parameters() Validating all placeholders in SQL query parameters: %s\n properties: %s, placeholders: %s",
            self.formatted_class_name,
            self.sql_query,
            properties,
            placeholders,
        )
        for placeholder in placeholders:
            if self.parameters is None or placeholder not in properties:
                raise SmarterValueError(f"Placeholder '{placeholder}' is not defined in parameters.")

    def validate(self) -> bool:
        super().validate()
        self.validate_test_values()
        self.validate_all_parameters_in_test_values()
        self.validate_all_placeholders_in_parameters()

        return True

    def prepare_sql(self, params: Optional[dict]) -> str:
        """Prepare the SQL query by replacing placeholders with values."""
        params = params or {}
        sql = self.sql_query
        for key, value in params.items():
            placeholder = "{" + key + "}"
            opening_tag = "<" + key + ">"
            closing_tag = "</" + key + ">"
            sql = sql.replace(placeholder, str(value)).replace(opening_tag, "").replace(closing_tag, "")
        if self.limit:
            sql += f" LIMIT {self.limit}"
        sql += ";"

        # Remove remaining tag pairs and any text between them
        sql = re.sub("<[^>]+>.*?</[^>]+>", "", sql)

        # Remove extra blank spaces
        sql = re.sub("\\s+", " ", sql)

        return sql

    def execute_query(self, params: Optional[dict]) -> Union[str, bool]:
        """Execute the SQL query and return the results."""
        sql = self.prepare_sql(params)
        return self.connection.execute_query(sql, self.limit)

    def test(self) -> Union[str, bool]:
        """Test the SQL query using the test_values in the record."""
        return self.execute_query(self.test_values)

    def sanitized_return_data(self, params: Optional[dict] = None) -> Union[str, bool]:
        """Return a dict by executing the query with the provided params."""
        logger.info("%s.sanitized_return_data called. - %s", self.formatted_class_name, params)
        return self.execute_query(params)

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        self.validate()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        account_number: Optional[str] = (
            self.plugin.account.account_number if self.plugin and self.plugin.account else "No Account"
        )
        account_number = cast(str, account_number)
        return str(account_number + " - " + self.plugin.name)


class ApiConnection(ConnectionBase):
    """
    Stores API connection configuration for a Smarter plugin.

    This model defines the connection details for a remote API used by a plugin,
    including authentication method, base URL, credentials, timeout, and proxy settings.
    It provides methods for testing the API and proxy connections, and for validating
    the configuration.
    """

    AUTH_METHOD_CHOICES = [
        ("none", "None"),
        ("basic", "Basic Auth"),
        ("token", "Token Auth"),
        ("oauth", "OAuth"),
    ]
    PROXY_PROTOCOL_CHOICES = [("http", "HTTP"), ("https", "HTTPS"), ("socks", "SOCKS")]

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="api_connections")
    base_url = models.URLField(
        help_text="The root domain of the API. Example: 'https://api.example.com'.",
    )
    api_key = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="api_connections_api_key",
        help_text="The API key for authentication, if required.",
        blank=True,
        null=True,
    )
    auth_method = models.CharField(
        help_text="The authentication method to use. Example: 'Basic Auth', 'Token Auth'.",
        max_length=50,
        choices=AUTH_METHOD_CHOICES,
        default="none",
        blank=True,
        null=True,
    )
    timeout = models.IntegerField(
        help_text="The timeout for the API request in seconds. Default is 30 seconds.",
        default=30,
        validators=[MinValueValidator(1)],
        blank=True,
        null=True,
    )
    # Proxy fields
    proxy_protocol = models.CharField(
        max_length=10,
        choices=PROXY_PROTOCOL_CHOICES,
        default="http",
        help_text="The protocol to use for the proxy connection.",
        blank=True,
        null=True,
    )
    proxy_host = models.CharField(max_length=255, blank=True, null=True)
    proxy_port = models.IntegerField(blank=True, null=True)
    proxy_username = models.CharField(max_length=255, blank=True, null=True)
    proxy_password = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="api_connections_proxy_password",
        help_text="The proxy password for authentication, if required.",
        blank=True,
        null=True,
    )

    @property
    def connection_string(self) -> str:
        return self.get_connection_string()

    def test_proxy(self) -> bool:
        proxy_dict = {
            self.proxy_protocol: f"{self.proxy_protocol}://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}",
        }
        try:
            response = requests.get("https://www.google.com", proxies=proxy_dict, timeout=self.timeout)
            return response.status_code in [HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT]
        except requests.exceptions.RequestException as e:
            logger.error("%s.test_proxy() proxy test connection failed: %s", self.formatted_class_name, e)
            return False

    def test_connection(self) -> bool:
        """Test the API connection by making a simple GET request to the root domain."""
        try:
            logger.warning(
                "%s.test_connection() called for %s with auth method %s but we didn't actually test it.",
                self.formatted_class_name,
                self.name,
                self.auth_method,
            )
            # result = self.execute_query(endpoint="/", params=None, limit=1)
            # return bool(result)
            return True
        # pylint: disable=W0718
        except Exception:
            return False

    def get_connection_string(self, masked: bool = True) -> str:
        """Return the connection string."""
        if masked:
            return f"{self.base_url} (Auth: ******)"
        return f"{self.base_url} (Auth: {self.auth_method})"

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        if isinstance(self.name, str) and not SmarterValidator.is_valid_snake_case(self.name):
            snake_case_name = camel_to_snake(self.name)
            logger.warning(
                "%s.save(): name %s was not in snake_case. Converted to snake_case: %s",
                self.formatted_class_name,
                self.name,
                snake_case_name,
            )
            self.name = snake_case_name
        self.validate()
        super().save(*args, **kwargs)

    def validate(self) -> bool:
        """Validate the API connection."""
        super().validate()
        return self.test_connection()

    def execute_query(
        self, endpoint: str, params: Optional[dict] = None, limit: Optional[int] = None
    ) -> Union[dict[str, Any], list[Any], bool]:
        """
        Execute the API query and return the results.
        This method constructs the full URL by combining the base URL and the endpoint,
        and sends a GET request to the API with the provided parameters.

        :param endpoint: The API endpoint to query.
        :param params: A dictionary of parameters to include in the API request.
        :param limit: The maximum number of rows to return from the API response.
        :return: The API response as a JSON object or False if the request fails.
        """
        params = params or {}
        url = urljoin(self.base_url, endpoint)
        headers = {}
        if self.auth_method == "basic" and self.api_key:
            headers["Authorization"] = f"Basic {self.api_key}"
        elif self.auth_method == "token" and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            plugin_api_connection_attempted.send(sender=self.__class__, connection=self)
            plugin_api_connection_query_attempted.send(sender=self.__class__, connection=self)
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            if response.status_code in [HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT]:
                plugin_api_connection_success.send(sender=self.__class__, connection=self)
                plugin_api_connection_query_success.send(sender=self.__class__, connection=self, response=response)
                if limit:
                    response_data = response.json()
                    if isinstance(response_data, list):
                        response_data = response_data[:limit]
                    elif isinstance(response_data, dict):
                        response_data = {k: v[:limit] for k, v in response_data.items() if isinstance(v, list)}
                    return response_data
                return response.json()
            else:
                # we connected, but the query failed.
                plugin_api_connection_query_success.send(sender=self.__class__, connection=self, response=response)
                plugin_api_connection_failed.send(sender=self.__class__, connection=self, response=response, error=None)
                return False
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # connection failed, and so by extension, so did the query
            plugin_api_connection_query_failed.send(sender=self.__class__, connection=self, response=response, error=e)
            plugin_api_connection_failed.send(sender=self.__class__, connection=self, response=response, error=e)
            return False
        except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as e:
            # query failed, but connection was successful
            plugin_api_connection_success.send(sender=self.__class__, connection=self, response=response, error=e)
            plugin_api_connection_query_failed.send(sender=self.__class__, connection=self, response=response, error=e)
            return False

    def __str__(self) -> str:
        return self.name + " - " + self.get_connection_string() if isinstance(self.name, str) else "unassigned"


class PluginDataApi(PluginDataBase):
    """
    Stores API-based data configuration for a Smarter plugin.

    This model is used to store the connection endpoint details for a REST API remote data source.
    It defines the API connection, endpoint, parameters, headers, body, test values, and result limits.
    The model provides methods for preparing and executing API requests, as well as validating
    the structure of parameters, headers, and test values.
    """

    class DataTypes:
        INT = "int"
        FLOAT = "float"
        STR = "str"
        BOOL = "bool"
        LIST = "list"
        DICT = "dict"
        NULL = "null"

        @classmethod
        def all(cls) -> list:
            return [cls.INT, cls.FLOAT, cls.STR, cls.BOOL, cls.LIST, cls.DICT, cls.NULL]

    connection = models.ForeignKey(
        ApiConnection,
        on_delete=models.CASCADE,
        related_name="plugin_data_api_connection",
        help_text="The API connection associated with this plugin.",
    )
    method = models.CharField(
        max_length=10,
        choices=[("GET", "GET"), ("POST", "POST"), ("PUT", "PUT"), ("DELETE", "DELETE")],
        default="GET",
        help_text="The HTTP method to use for the API request. Example: 'GET', 'POST'.",
        blank=True,
        null=True,
    )
    endpoint = models.CharField(
        max_length=255,
        help_text="The endpoint path for the API. Example: '/v1/weather'.",
    )
    url_params = models.JSONField(
        help_text="A JSON dict containing URL parameters. Example: {'city': 'San Francisco', 'state': 'CA'}",
        blank=True,
        null=True,
    )
    headers = models.JSONField(
        help_text="A JSON dict containing headers to be sent with the API request. Example: {'Authorization': 'Bearer <token>'}",
        blank=True,
        null=True,
    )
    body = models.JSONField(
        help_text="A JSON dict containing the body of the API request, if applicable.",
        blank=True,
        null=True,
    )
    limit = models.IntegerField(
        help_text="The maximum number of rows to return from the API response.",
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )

    @property
    def url(self) -> str:
        """Return the full URL for the API endpoint."""
        return urljoin(self.connection.base_url, self.endpoint)

    def data(self, params: Optional[dict] = None) -> dict:
        return {
            "parameters": self.parameters,
            "endpoint": self.endpoint,
            "headers": self.headers,
            "body": self.body,
        }

    def prepare_request(self, params: Optional[dict]) -> dict:
        """Prepare the API request by merging parameters, headers, and body."""
        params = params or {}
        self.validate_url_params()

        request_data = {
            "url": f"{self.connection.base_url}{self.endpoint}",
            "headers": self.headers or {},
            "params": params,
            "json": self.body or {},
        }
        return request_data

    def execute_request(self, params: Optional[dict]) -> Union[dict, bool]:
        """Execute the API request and return the results."""
        request_data = self.prepare_request(params)
        try:
            response = requests.get(**request_data, timeout=self.connection.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("%s.execute_request() API request failed: %s", self.formatted_class_name, e)
            return False

    def test(self) -> Union[dict, bool]:
        """Test the API request using the test_values in the record."""
        return self.execute_request(self.test_values)

    def sanitized_return_data(self, params: Optional[dict] = None) -> Union[dict, bool]:
        """Return a dict by executing the API request with the provided params."""
        logger.info("%s.sanitized_return_data called. - %s", self.formatted_class_name, params)
        return self.execute_request(params)

    def validate_endpoint(self) -> None:
        """Validate the endpoint format."""
        if not SmarterValidator.is_valid_url_endpoint(self.endpoint):
            raise SmarterValueError("Endpoint must be a valid cleanstring.")

    def validate_url_params(self) -> None:
        """Validate the URL parameters format."""
        if self.url_params is None:
            return None
        if not isinstance(self.url_params, list):
            raise SmarterValueError(f"url_params must be a list of dictionaries but got: {type(self.url_params)}")

        for url_param in self.url_params:  # type: ignore  # pylint: disable=not-an-iterable
            try:
                # pylint: disable=E1134
                UrlParam(**url_param)
            except (ValidationError, SmarterValueError) as e:
                raise SmarterValueError(
                    f"Invalid url_param structure. Should match the Pydantic model structure, UrlParam: {e}"
                ) from e

    def validate_headers(self) -> None:
        """Validate the headers format."""
        if self.headers is None:
            return None
        if not isinstance(self.headers, list):
            raise SmarterValueError(f"headers must be a list of dictionaries but got: {type(self.headers)}")

        # pylint: disable=E1133
        for header_dict in self.headers:  # type: ignore  # pylint: disable=not-an-iterable
            try:
                # pylint: disable=E1134
                RequestHeader(**header_dict)
            except (ValidationError, SmarterValueError) as e:
                raise SmarterValueError(
                    f"Invalid header structure. Should match the Pydantic model structure, RequestHeader {e}"
                ) from e

    def validate_body(self) -> None:
        """
        Validate the body format. Currently nothing to do here.
        """
        if self.body is None:
            return None
        if not isinstance(self.body, dict) and not isinstance(self.body, list):
            raise SmarterValueError(f"body must be a dict or a list but got: {type(self.body)}")

    def validate_test_values(self) -> None:
        """Validate the test values format."""
        if self.test_values is None:
            return None
        if not isinstance(self.test_values, list):
            raise SmarterValueError(f"test_values must be a list of dictionaries but got: {type(self.test_values)}")

        # pylint: disable=E1133
        for test_value in self.test_values:
            try:
                # pylint: disable=E1134
                TestValue(**test_value)
            except (ValidationError, SmarterValueError) as e:
                raise SmarterValueError(
                    f"Invalid test value structure. Should match the Pydantic model structure, TestValue {e}"
                ) from e

    def validate_all_placeholders_in_parameters(self) -> None:
        """
        Validate that all placeholders in the SQL query string are present in the parameters.
        """
        placeholders = re.findall(r"{(.*?)}", self.endpoint) or []
        parameters = self.parameters or {}
        properties = parameters.get("properties", {})
        logger.info(
            "%s.validate_all_placeholders_in_parameters() Validating all placeholders in SQL query parameters: %s\n properties: %s, placeholders: %s",
            self.formatted_class_name,
            self.endpoint,
            properties,
            placeholders,
        )
        for placeholder in placeholders:
            if self.parameters is None or placeholder not in properties:
                raise SmarterValueError(f"Placeholder '{placeholder}' is not defined in parameters.")

    def validate(self) -> bool:
        super().validate()
        self.validate_test_values()
        self.validate_all_parameters_in_test_values()
        self.validate_all_placeholders_in_parameters()
        self.validate_endpoint()
        self.validate_url_params()
        self.validate_headers()
        self.validate_body()
        return True

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        self.validate()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        account_number: Optional[str] = (
            self.connection.account.account_number if self.connection and self.connection.account else "No Account"
        )
        account_number = cast(str, account_number)
        return str(account_number + " - " + self.plugin.name)


PluginDataType = type[PluginDataStatic] | type[PluginDataApi] | type[PluginDataSql]
PLUGIN_DATA_MAP: dict[str, PluginDataType] = {
    SAMKinds.API_PLUGIN.value: PluginDataApi,
    SAMKinds.SQL_PLUGIN.value: PluginDataSql,
    SAMKinds.STATIC_PLUGIN.value: PluginDataStatic,
}
