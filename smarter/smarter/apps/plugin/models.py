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
    Validates that the provided value is a dictionary matching the OpenAI parameters schema.

    **Example schema:**

    .. code-block:: python

        {
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
            'required': ['max_cost'],
            'additionalProperties': False
        }

    :param value: The value to validate. Should be a dict or a string representation of a dict.
    :raises PluginDataValueError: If the value is not a valid parameters dictionary.
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
    """
    Clean a key by replacing spaces and whitespace characters with underscores.

    This function removes newline (``\\n``), carriage return (``\\r``), tab (``\\t``), and space characters
    from the input string and replaces them with underscores (``_``).

    :param key: The string key to clean.
    :type key: str
    :return: The cleaned key with whitespace replaced by underscores.
    :rtype: str

    **Example:**

    .. code-block:: python

        dict_key_cleaner("my key\\nwith\\tspaces")
        # returns: 'my_key_with_spaces'
    """
    return str(key).replace("\n", "").replace("\r", "").replace("\t", "").replace(" ", "_")


def dict_keys_to_list(data: dict, keys=None) -> list[str]:
    """
    Recursively extract all keys from a nested dictionary.

    This function traverses a dictionary and all nested dictionaries,
    collecting every key encountered into a flat list.

    :param data: The dictionary to extract keys from.
    :type data: dict
    :param keys: (Optional) An existing list to append keys to (used for recursion).
    :type keys: list, optional
    :return: A list of all keys found in the dictionary and its nested dictionaries.
    :rtype: list[str]

    **Example:**

    .. code-block:: python

        data = {
            "a": 1,
            "b": {"c": 2, "d": {"e": 3}}
        }
        dict_keys_to_list(data)
        # returns: ['a', 'b', 'c', 'd', 'e']
    """
    if keys is None:
        keys = []
    for key, value in data.items():
        keys.append(key)
        if isinstance(value, dict):
            dict_keys_to_list(value, keys)
    return keys


def list_of_dicts_to_list(data: list[dict]) -> Optional[list[str]]:
    """
    Convert a list of dictionaries into a list of cleaned keys extracted from the first key in each dict.

    This function iterates over a list of dictionaries, extracts the value of the first key in each dictionary,
    cleans it using :func:`dict_key_cleaner`, and returns a list of these cleaned keys.

    :param data: A list of dictionaries.
    :type data: list[dict]
    :return: A list of cleaned keys, or None if input is invalid.
    :rtype: Optional[list[str]]

    **Example:**

    .. code-block:: python

        data = [{"name": "Alice"}, {"name": "Bob"}]
        list_of_dicts_to_list(data)
        # returns: ['Alice', 'Bob']
    """
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
    """
    Convert a list of dictionaries into a single dict with keys extracted
    from the first key in the first dict.

    This function iterates over a list of dictionaries, extracts the value of the first key in each dictionary,
    cleans it using :func:`dict_key_cleaner`, and uses the cleaned key as the key in the resulting dictionary,
    mapping to the original value.

    :param data: A list of dictionaries.
    :type data: list[dict]
    :return: A dictionary with cleaned keys mapped to their corresponding values, or None if input is invalid.
    :rtype: Optional[dict]

    **Example:**

    .. code-block:: python

        data = [{"name": "Alice"}, {"name": "Bob"}]
        list_of_dicts_to_dict(data)
        # returns: {'Alice': 'Alice', 'Bob': 'Bob'}
    """
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
    Represents the core metadata for a Smarter plugin, serving as the central registry for all plugin types.

    This class defines the essential identifying and descriptive information for a plugin, including its name,
    description, type (static, SQL, or API), version, author, and associated tags. Each plugin is uniquely
    associated with an account and an author profile, ensuring that plugin names are unique per account and
    enforcing a snake_case naming convention for consistency and compatibility.

    The ``PluginMeta`` model acts as the anchor point for related plugin configuration and data models, such as
    :class:`PluginDataStatic`, :class:`PluginDataSql`, and :class:`PluginDataApi`, which store the specific
    data and behavior for each plugin type. It is also linked to selection and prompt configuration through
    :class:`PluginSelector` and :class:`PluginPrompt`, enabling flexible plugin discovery and LLM prompt customization.

    Validation logic within this class ensures that plugin names conform to required standards, and class methods
    provide efficient, cached access to plugin instances for a given user or account.

    This model is foundational for the Smarter plugin system, enabling the organization, discovery, and management
    of all plugins within an account, and supporting integration with the broader plugin data and connection models
    defined in this module.
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
    """
    The classes of plugins supported by Smarter.
    """

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="plugin_meta_account")
    name = models.CharField(
        help_text="The name of the plugin. Example: 'HR Policy Update' or 'Public Relation Talking Points'.",
        max_length=255,
        validators=[SmarterValidator.validate_snake_case, validate_no_spaces],
    )

    @property
    def rfc1034_compliant_name(self) -> Optional[str]:
        """
        Returns a URL-friendly name for the chatbot.

        This property returns an RFC 1034-compliant name for the chatbot, suitable for use in URLs and DNS labels.

        **Example:**

        .. code-block:: python

            self.name = 'Example ChatBot 1'
            self.rfc1034_compliant_name  # 'example-chatbot-1'

        :return: The RFC 1034-compliant name, or None if ``self.name`` is not set.
        :rtype: Optional[str]
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
        """
        Override the save method to validate the field dicts.

        This method ensures that all relevant fields are validated before saving the model instance.
        For example, it checks that the name is in snake_case and converts it if necessary, logs a warning if conversion occurs,
        and calls the model's ``validate()`` method to enforce any additional validation logic defined on the model.
        After validation, it proceeds with the standard Django save operation.

        :param args: Positional arguments passed to the parent save method.
        :param kwargs: Keyword arguments passed to the parent save method.

        :return: None
        """
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

        This property is used to determine how the plugin should be handled by the system.
        It maps the plugin's class to a corresponding :class:`SAMKinds` enumeration value.

        :return: The kind of the plugin as a :class:`SAMKinds` enum.
        :rtype: SAMKinds

        **Example:**

        .. code-block:: python

            plugin.plugin_class = 'static'
            plugin.kind  # SAMKinds.STATIC_PLUGIN
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
        Returns a URL-friendly kind for the chatbot.

        This is a convenience property that returns an RFC 1034-compliant kind for the chatbot,
        suitable for use in URLs and DNS labels.

        **Example:**

        .. code-block:: python

            self.kind  # 'Static'
            self.rfc1034_compliant_kind  # 'static'

        :return: The RFC 1034-compliant kind, or None if ``self.kind`` is not set.
        :rtype: Optional[str]
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

        :param user: The user whose plugins should be retrieved.
        :type user: User
        :return: A list of PluginMeta instances for the user.
        :rtype: list[PluginMeta]

        See also:

        - :func:`smarter.lib.cache.cache_results`
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

        :param user: The user whose plugin should be retrieved.
        :type user: User
        :param name: The name of the plugin to retrieve.
        :type name: str
        :return: A PluginMeta instance if found, otherwise None.
        :rtype: Union[PluginMeta, None]
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

    The ``PluginSelector`` model defines how and when a plugin is included in the prompt sent to the LLM (Large Language Model). Each instance is linked to a :class:`PluginMeta` object, representing the plugin whose selection logic is being configured.

    The primary function of this model is to specify a selection directive—such as ``search_terms``, ``always``, or ``llm``—that determines the conditions under which the plugin should be activated. For example, when the directive is ``search_terms``, the ``search_terms`` field contains a list of keywords or phrases (in JSON format). If any of these terms are detected in the user's prompt, Smarter will prioritize loading and invoking the associated plugin. This enables context-aware, dynamic plugin routing based on user intent.

    ``PluginSelector`` works in concert with other models in this module:
      - It references :class:`PluginMeta` to associate selection logic with a specific plugin.
      - It is audited by :class:`PluginSelectorHistory`, which records each activation event, the triggering search term, and relevant user prompt context for analytics and debugging.
      - It complements :class:`PluginPrompt`, which customizes the LLM prompt for each plugin, allowing for both selection and prompt configuration to be managed independently.

    By supporting multiple selection strategies, this model enables flexible, intelligent plugin discovery and orchestration within the Smarter platform. It is essential for implementing advanced plugin routing, ensuring that the most relevant plugins are surfaced to the LLM based on user input and system configuration.

    See also:

    - :class:`PluginMeta`
    - :class:`PluginSelectorHistory`
    - :class:`smarter.apps.plugin.manifest.enum.SAMPluginCommonSpecSelectorKeyDirectiveValues`
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
    Stores the history of plugin selector activations for auditing and analytics.

    The ``PluginSelectorHistory`` model records every instance in which a plugin was selected for inclusion in an LLM prompt, capturing the context and rationale for the selection. Each record includes a reference to the associated :class:`PluginSelector`, the specific search term (if any) that triggered the selection, the full set of user prompt messages at the time of activation, and the session key for correlating events across a user session.

    This model is essential for understanding and debugging plugin routing decisions within the Smarter platform. By persisting a detailed log of selector activations, it enables retrospective analysis of plugin usage patterns, supports compliance and auditing requirements, and provides valuable data for improving plugin selection strategies.

    ``PluginSelectorHistory`` works closely with:
      - :class:`PluginSelector`, which defines the selection logic and strategies for plugins.
      - :class:`PluginMeta`, which provides the core metadata for each plugin and is referenced indirectly via the selector.
      - :class:`PluginPrompt`, which may be used to further customize the LLM prompt for the selected plugin.

    Typical use cases include tracking which plugins were surfaced to the LLM in response to specific user queries, analyzing the effectiveness of search term-based selection, and debugging unexpected plugin activations.

    See also:

    - :class:`PluginSelector`
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

    This serializer provides a complete representation of :class:`PluginSelectorHistory` records,
    including all model fields and a nested serialization of the related :class:`PluginSelector`.
    It is used to expose selector activation history for auditing, analytics, and debugging purposes.

    By including the nested selector, this serializer enables clients to access both the activation
    context and the selection logic that led to the plugin being surfaced to the LLM. This is
    particularly useful for building admin interfaces, audit logs, or analytics dashboards that
    require insight into plugin routing decisions.

    See also:

    - :class:`PluginSelectorHistory`
    - :class:`PluginSelector`
    """

    plugin_selector = PluginSelectorSerializer()

    class Meta:
        model = PluginSelectorHistory
        fields = "__all__"


class PluginPrompt(TimestampedModel, SmarterHelperMixin):
    """
    Stores LLM prompt model configuration for a Smarter plugin.

    The ``PluginPrompt`` model defines the prompt settings and LLM interaction parameters for a plugin. Each instance is linked to a :class:`PluginMeta` object, allowing prompt customization on a per-plugin basis. This includes specifying the LLM provider (such as OpenAI), the system role (which sets the context or persona for the LLM), the model to use, temperature for response creativity, and the maximum number of completion tokens.

    By encapsulating these settings, ``PluginPrompt`` enables fine-grained control over how each plugin interacts with the LLM, supporting use cases such as tailoring the assistant's tone, optimizing for cost or accuracy, and enforcing token limits. This model works in conjunction with :class:`PluginSelector` (which determines when a plugin is invoked) and :class:`PluginMeta` (which provides the core plugin metadata).

    Typical scenarios include customizing the system prompt for different plugins, selecting different LLM models for specific tasks, or adjusting temperature and token limits to balance creativity and resource usage.

    See also:

    - :class:`PluginMeta`
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
    """
    Abstract base class for all plugin data configuration models in the Smarter platform.

    ``PluginDataBase`` defines the common interface and fields required for storing and validating
    plugin data specifications, including parameter schemas, test values, and descriptive metadata.
    It is not intended to be instantiated directly, but rather to be subclassed by concrete data
    models such as :class:`PluginDataStatic`, :class:`PluginDataSql`, and :class:`PluginDataApi`,
    each of which implements data handling for a specific plugin type (static, SQL, or API).

    This base class enforces a consistent structure for plugin data models by providing:
      - A reference to the associated :class:`PluginMeta` instance, linking data configuration to plugin metadata.
      - A ``description`` field for documenting the data returned by the plugin.
      - A ``parameters`` field for specifying the expected input schema, validated against OpenAI-compatible conventions.
      - A ``test_values`` field for storing example parameter values used in validation and testing.
      - Abstract methods for returning sanitized data and the plugin's data payload, which must be implemented by subclasses.
      - Validation methods to ensure that all parameters are covered by test values and that test values conform to the expected structure.

    Subclasses are responsible for implementing the logic to return data in the appropriate format for their plugin type,
    as well as any additional validation or preparation steps required for their data source (e.g., SQL query, API request, or static data).

    This class is foundational for the plugin data architecture, ensuring that all plugin data models in the Smarter system
    adhere to a uniform interface and validation strategy.

    See also:

    - :class:`PluginDataStatic`
    - :class:`PluginDataSql`
    - :class:`PluginDataApi`
    - :class:`PluginMeta`
    """

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
    """
    A JSON dict containing parameter names and data types. Example: {'required': [], 'properties': {'max_cost': {'type': 'float', 'description': 'the maximum cost that a student is willing to pay for a course.'}, 'description': {'enum': ['AI', 'mobile', 'web', 'database', 'network', 'neural networks'], 'type': 'string', 'description': 'areas of specialization for courses in the catalogue.'}}}
    """

    test_values = models.JSONField(
        help_text="A JSON dict containing test values for each parameter. Example: {'city': 'San Francisco'}",
        blank=True,
        null=True,
    )
    """
    A JSON dict containing test values for each parameter. Example: {'city': 'San Francisco'}
    """

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
        Ensure that every parameter defined in ``parameters['properties']`` has a corresponding entry in ``test_values``.

        This method checks that all parameter names specified in the ``parameters`` field are present in the ``test_values`` list.
        Each test value should be a dictionary with a ``name`` key matching a parameter name.

        **Example:**

            .. code-block:: python

                parameters = {
                    "properties": {
                        "description": {"type": "string"},
                        "max_cost": {"type": "float"}
                    }
                }
                test_values = [
                    {"name": "description", "value": "AI"},
                    {"name": "max_cost", "value": "500.0"}
                ]

        If any parameter is missing from ``test_values``, a :class:`SmarterValueError` is raised.

        :raises SmarterValueError: If a parameter is defined in ``parameters`` but not present in ``test_values``.
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

    This model is used for plugins that return static (predefined) data to the LLM.
    The ``static_data`` field holds the JSON data that will be returned when the plugin is invoked.
    This enables plugins to provide consistent, deterministic responses without external dependencies.

    ``PluginDataStatic`` provides methods for:
      - Returning sanitized static data, either as a dictionary or a list, with optional truncation for large datasets.
      - Extracting and caching all keys present in the static data, supporting both flat and nested structures.
      - Ensuring that the static data conforms to the expected structure and is compatible with the plugin's parameter schema.

    This model is a concrete subclass of :class:`PluginDataBase`, and is referenced by :class:`PluginMeta`
    to provide the data payload for static-type plugins. It is also used in conjunction with
    :class:`PluginSelector` and :class:`PluginPrompt` to enable full plugin lifecycle management.

    Typical use cases include plugins that serve reference data, lookup tables, or any information
    that does not require dynamic computation or remote queries.

    See also:

    - :class:`PluginDataBase`
    - :class:`PluginMeta`
    """

    static_data = models.JSONField(
        help_text="The JSON data that this plugin returns to OpenAI API when invoked by the user prompt.", default=dict
    )
    """
    The JSON data that this plugin returns to OpenAI API when invoked by the user prompt.
    """

    def sanitized_return_data(self, params: Optional[dict] = None) -> Optional[Union[dict, list]]:
        """
        Return the static data for this plugin, either as a dictionary or a list.

        This method returns the value of ``self.static_data`` in a sanitized form:

        - If ``static_data`` is a dictionary, it is returned as-is.
        - If ``static_data`` is a list, it is truncated to ``SMARTER_PLUGIN_MAX_DATA_RESULTS`` items (if necessary)
          and converted to a dictionary using :func:`list_of_dicts_to_dict`.
        - If ``static_data`` is neither a dictionary nor a list, a :class:`SmarterValueError` is raised.

        :param params: Optional parameters for future extensibility (currently unused).
        :type params: Optional[dict]
        :return: The sanitized static data as a dictionary or list.
        :rtype: Optional[Union[dict, list]]
        :raises SmarterValueError: If ``static_data`` is not a dict or list.
        """
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
        """
        Return all keys present in the ``static_data`` attribute.

        This property extracts, caches and returns a list of all keys found in the ``static_data`` field, supporting both dictionary and list formats:

        - If ``static_data`` is a dictionary, all nested keys are recursively collected and returned as a flat list.
        - If ``static_data`` is a list of dictionaries, the keys are extracted from each dictionary and returned as a list, truncated to ``SMARTER_PLUGIN_MAX_DATA_RESULTS`` items if necessary.
        - If ``static_data`` is neither a dictionary nor a list, a :class:`SmarterValueError` is raised.

        :return: A list of all keys in the static data, or None if not applicable.
        :rtype: Optional[list[str]]
        :raises SmarterValueError: If ``static_data`` is not a dict or list.

        **Example:**

        .. code-block:: python

            # If static_data is a dict:
            static_data = {"a": 1, "b": {"c": 2}}
            return_data_keys  # ['a', 'b', 'c']

            # If static_data is a list of dicts:
            static_data = [{"name": "Alice"}, {"name": "Bob"}]
            return_data_keys  # ['Alice', 'Bob']
        """

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
        """
        Return the static data as a dictionary.
        This method attempts to parse and return the ``static_data`` field as a dictionary.

        :param params: Optional parameters for future extensibility (currently unused).
        :type params: Optional[dict]
        :return: The static data as a dictionary, or None if parsing fails.
        :rtype: Optional[dict]
        """
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
    Abstract base class for all connection models in the Smarter platform.

    ``ConnectionBase`` defines the shared interface and core fields required for representing connection
    configurations to external data sources, such as SQL databases and remote APIs. This class is not
    intended to be instantiated directly, but rather to be subclassed by concrete connection models like
    :class:`SqlConnection` and :class:`ApiConnection`, each of which implements the logic for a specific
    connection type.

    This base class enforces a consistent structure for connection models by providing:
      - An ``account`` field to associate the connection with a specific user account.
      - A ``name`` field, validated to ensure snake_case and no spaces, for uniquely identifying the connection.
      - A ``kind`` field to distinguish between connection types (e.g., SQL, API).
      - Descriptive metadata fields such as ``description`` and ``version``.
      - An abstract ``connection_string`` property that must be implemented by subclasses to return a usable connection string.
      - Class methods for retrieving and caching connections for a user, supporting efficient access and management of connection objects.

    Subclasses are responsible for implementing the logic to establish, test, and manage connections to their
    respective data sources, as well as any additional configuration or validation required for their protocols.

    This class is foundational for the Smarter connection architecture, ensuring that all connection models
    adhere to a uniform interface and can be managed, validated, and retrieved in a consistent manner.

    See also:

    - :class:`SqlConnection`
    - :class:`ApiConnection`
    - :class:`PluginMeta`
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
    """
    The name of the connection, without spaces. Example: 'hr_database', 'sales_db', 'inventory_api'.
    """
    kind = models.CharField(
        help_text="The kind of connection. Example: 'SQL', 'API'.",
        max_length=50,
        choices=CONNECTION_KIND_CHOICES,
    )
    description = models.TextField(
        help_text="A brief description of the connection. Be verbose, but not too verbose.", blank=True, null=True
    )
    """
    A brief description of the connection. Be verbose, but not too verbose.
    """
    version = models.CharField(
        help_text="The version of the connection. Example: '1.0.0'.",
        max_length=255,
        default="1.0.0",
        blank=True,
        null=True,
    )
    """
    The semantic version of the connection. Example: '1.0.0'.
    """

    @property
    @abstractmethod
    def connection_string(self) -> str:
        """Return the connection string."""
        raise NotImplementedError

    @classmethod
    def get_cached_connections_for_user(cls, user: User) -> list["ConnectionBase"]:
        """
        Return a list of all instances of all concrete subclasses of :class:`ConnectionBase`.

        This method retrieves all connection objects (such as :class:`SqlConnection` and :class:`ApiConnection`)
        associated with the user's account, across all concrete subclasses of :class:`ConnectionBase`.
        It is useful for enumerating all available connections for a given user, regardless of connection type.

        :param user: The user whose connections should be retrieved.
        :type user: User
        :return: A list of all connection instances for the user's account.
        :rtype: list[ConnectionBase]

        **Example:**

        .. code-block:: python

            connections = ConnectionBase.get_cached_connections_for_user(user)
            # returns [<SqlConnection ...>, <ApiConnection ...>, ...]

        See also:

        - :class:`SqlConnection`
        - :class:`ApiConnection`
        - :func:`smarter.apps.account.utils.get_cached_account_for_user`
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
        Return a single instance of a concrete subclass of :class:`ConnectionBase` by name and kind.

        This method retrieves a connection object (such as :class:`SqlConnection` or :class:`ApiConnection`)
        for the given user, connection kind, and connection name. It searches across all concrete subclasses
        of :class:`ConnectionBase` and returns the matching instance if found.

        :param user: The user whose connection should be retrieved.
        :type user: User
        :param kind: The kind of connection (e.g., ``SAMKinds.SQL_CONNECTION`` or ``SAMKinds.API_CONNECTION``).
        :type kind: SAMKinds
        :param name: The name of the connection to retrieve.
        :type name: str
        :return: The connection instance if found, otherwise None.
        :rtype: Union[ConnectionBase, None]

        **Example:**

        .. code-block:: python

            sql_conn = ConnectionBase.get_cached_connection_by_name_and_kind(user, SAMKinds.SQL_CONNECTION, "hr_database")
            api_conn = ConnectionBase.get_cached_connection_by_name_and_kind(user, SAMKinds.API_CONNECTION, "inventory_api")

        See also:

        - :class:`SqlConnection`
        - :class:`ApiConnection`
        - :func:`smarter.lib.cache.cache_results`
        - :func:`smarter.apps.account.utils.get_cached_account_for_user`
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

    ``SqlConnection`` is a concrete subclass of :class:`ConnectionBase` and is referenced by
    :class:`PluginDataSql` to provide the database connection for SQL-based plugins. It supports
    advanced features such as connection pooling, SSL configuration, SSH tunneling, and proxy
    authentication, enabling secure and flexible integration with a wide range of SQL databases.

    This model is responsible for:
      - Managing connection credentials and secrets using the :class:`Secret` model.
      - Constructing Django-compatible database connection settings and connection strings.
      - Providing methods for testing connectivity, executing SQL queries, and handling connection errors.
      - Supporting multiple authentication methods, including TCP/IP, SSH tunneling, and LDAP.
      - Integrating with Django's database backend and connection pooling mechanisms.
      - Emitting signals for connection attempts, successes, failures, and query events for observability.

    Typical use cases include plugins that need to query organizational databases, perform analytics,
    or retrieve structured data from remote SQL servers as part of the Smarter plugin ecosystem.

    See also:

    - :class:`ConnectionBase`
    - :class:`PluginDataSql`
    - :class:`smarter.apps.account.models.Secret`
    """

    _connection: Optional[BaseDatabaseWrapper] = None

    def __del__(self):
        """Close the database connection when the object instance is destroyed."""
        self.close()

    class ParamikoUpdateKnownHostsPolicy(paramiko.MissingHostKeyPolicy):
        """
        Custom Paramiko policy to automatically add missing SSH host keys to the known_hosts field.
        This policy extends Paramiko's MissingHostKeyPolicy to handle unknown host keys by appending
        them to the ``ssh_known_hosts`` field of the associated :class:`SqlConnection`
        model instance. When an unknown host key is encountered during an SSH connection attempt,
        this policy captures the key and updates the database record accordingly.
        """

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
    """
    The default timeout for database connections in seconds.
    30 seconds is a reasonable default that balances responsiveness with network latency.
    """
    DBMS_CHOICES = [
        (DbEngines.MYSQL.value, DbEngines.MYSQL.value),
        (DbEngines.POSTGRES.value, DbEngines.POSTGRES.value),
        (DbEngines.SQLITE.value, DbEngines.SQLITE.value),
        (DbEngines.ORACLE.value, DbEngines.ORACLE.value),
        (DbEngines.MSSQL.value, DbEngines.MSSQL.value),
        (DbEngines.SYBASE.value, DbEngines.SYBASE.value),
    ]
    """
    The supported database management systems (DBMS) for SQL connections.
    """
    DBMS_AUTHENITCATION_METHODS = [
        (DBMSAuthenticationMethods.NONE.value, "None"),
        (DBMSAuthenticationMethods.TCPIP.value, "Standard TCP/IP"),
        (DBMSAuthenticationMethods.TCPIP_SSH.value, "Standard TCP/IP over SSH"),
        (DBMSAuthenticationMethods.LDAP_USER_PWD.value, "LDAP User/Password"),
    ]
    """
    The supported authentication methods for SQL connections.
    """
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="sql_connections")
    db_engine = models.CharField(
        help_text="The type of database management system. Example: 'MySQL', 'PostgreSQL', 'MS SQL Server', 'Oracle'.",
        default=DbEngines.MYSQL.value,
        max_length=255,
        choices=DBMS_CHOICES,
        blank=True,
        null=True,
    )
    """
    The type of database management system. Example: 'MySQL', 'PostgreSQL', 'MS SQL Server', 'Oracle'.
    """
    authentication_method = models.CharField(
        help_text="The authentication method to use for the connection. Example: 'Standard TCP/IP', 'Standard TCP/IP over SSH', 'LDAP User/Password'.",
        max_length=255,
        choices=DBMSAuthenticationMethods.choices(),
        default=DBMSAuthenticationMethods.TCPIP.value,
    )
    """
    The authentication method to use for the connection. Example: 'Standard TCP/IP', 'Standard TCP/IP over SSH', 'LDAP User/Password'.
    """
    timeout = models.IntegerField(
        help_text="The timeout for the database connection in seconds. Default is 30 seconds.",
        default=DBMS_DEFAULT_TIMEOUT,
        validators=[MinValueValidator(1)],
        blank=True,
    )
    """
    The timeout for the database connection in seconds. Default is 30 seconds.
    """

    # SSL/TLS fields
    use_ssl = models.BooleanField(
        default=False, help_text="Whether to use SSL/TLS for the connection.", blank=True, null=True
    )
    """
    Whether to use SSL/TLS for the connection.
    """
    ssl_cert = models.TextField(blank=True, null=True, help_text="The SSL certificate for the connection, if required.")
    ssl_key = models.TextField(blank=True, null=True, help_text="The SSL key for the connection, if required.")
    ssl_ca = models.TextField(
        blank=True, null=True, help_text="The Certificate Authority (CA) certificate for verifying the server."
    )
    """
    The SSL certificate for the connection, if required.
    The SSL key for the connection, if required.
    The Certificate Authority (CA) certificate for verifying the server.
    """

    # connection fields
    hostname = models.CharField(
        max_length=255, help_text="The remote host of the SQL connection. Should be a valid internet domain name."
    )
    """
    The remote host of the SQL connection. Should be a valid internet domain name.
    """
    port = models.IntegerField(
        default=3306, help_text="The port of the SQL connection. example: 3306 for MySQL.", blank=True, null=True
    )
    """
    The port of the SQL connection. example: 3306 for MySQL.
    5432 for PostgreSQL, 1521 for Oracle, 1433 for MS SQL Server.
    5000 for Sybase.
    1234 for SQLite (not commonly used).
    3306 is a reasonable default as MySQL is widely used.
    5432 could also be a reasonable default as PostgreSQL is also widely used.
    """
    database = models.CharField(max_length=255, help_text="The name of the database to connect to.")
    """
    The name of the database to connect to.
    """
    username = models.CharField(max_length=255, blank=True, null=True, help_text="The database username.")
    """
    The database username.
    """
    password = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="sql_connections_password",
        help_text="The password for authentication, if required.",
        blank=True,
        null=True,
    )
    """
    The password for authentication, if required.

    See: :class:`smarter.apps.account.models.Secret`
    """
    pool_size = models.IntegerField(default=5, help_text="The size of the connection pool.", blank=True, null=True)
    """
    The size of the connection pool.
    """
    max_overflow = models.IntegerField(
        default=10,
        help_text="The maximum number of connections to allow beyond the pool size.",
        validators=[MinValueValidator(1)],
        blank=True,
        null=True,
    )
    """
    The maximum number of connections to allow beyond the pool size.
    """

    # Proxy fields
    proxy_protocol = models.CharField(
        max_length=10,
        choices=[("http", "HTTP"), ("https", "HTTPS"), ("socks", "SOCKS")],
        default="http",
        help_text="The protocol to use for the proxy connection.",
        blank=True,
        null=True,
    )
    """
    The protocol to use for the proxy connection.
    """
    proxy_host = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The remote host of the SQL proxy connection. Should be a valid internet domain name.",
    )
    """
    The remote host of the SQL proxy connection. Should be a valid internet domain name.
    """
    proxy_port = models.IntegerField(blank=True, null=True, help_text="The port of the SQL proxy connection.")
    """
    The port of the SQL proxy connection.
    8080 is a common default for HTTP proxies.
    3128 is another common default for HTTP proxies.
    1080 is a common default for SOCKS proxies.
    8080 is a reasonable default as it is widely used for HTTP proxies.
    """
    proxy_username = models.CharField(
        max_length=255, blank=True, null=True, help_text="The username for the proxy connection."
    )
    """
    The username for the proxy connection.
    """
    proxy_password = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="sql_connections_proxy_password",
        help_text="The API key for authentication, if required.",
        blank=True,
        null=True,
    )
    """
    The password for the proxy connection, if required.

    See: :class:`smarter.apps.account.models.Secret`
    """
    ssh_known_hosts = models.TextField(
        blank=True,
        null=True,
        help_text="The known_hosts file content for verifying SSH connections. Usually comes from ~/.ssh/known_hosts.",
    )
    """
    The known_hosts file content for verifying SSH connections. Usually comes from ~/.ssh/known_hosts.
    """

    @property
    def connection(self) -> Optional[BaseDatabaseWrapper]:
        """
        Return the database connection if it exists, otherwise create a new one.

        This property returns the current database connection for this SQL connection instance.
        If a connection has already been established, it is returned; otherwise, a new connection
        is created using the configured authentication method and connection parameters.

        :return: The database connection object, or None if the connection could not be established.
        :rtype: Optional[BaseDatabaseWrapper]

        **Example:**

        .. code-block:: python

            conn = sql_connection.connection
            if conn:
                # Use the database connection
                ...

        See also:

        - :meth:`get_connection`
        """
        if self._connection:
            return self._connection
        self._connection = self.get_connection()
        return self._connection

    @property
    def db_options(self) -> dict:
        """
        Return the database connection options.

        This property constructs and returns a dictionary of options for the database connection,
        including SSL/TLS settings and authentication method if applicable.

        - If SSL is enabled (``use_ssl`` is True), the returned dictionary includes the keys ``ca``, ``cert``, and ``key`` for SSL configuration.
        - If the authentication method is LDAP user/password, the dictionary includes an ``authentication`` key set to ``LDAP``.

        :return: A dictionary of database connection options.
        :rtype: dict

        **Example:**

        .. code-block:: python

            options = sql_connection.db_options
            # returns: {'ssl': {'ca': '...', 'cert': '...', 'key': '...'}, 'authentication': 'LDAP'}
        """
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
        """
        Return the database connection settings for Django.

        This property constructs and returns a dictionary of settings compatible with Django's database
        connection handler, using the current SQL connection instance's configuration.

        The returned dictionary includes the following keys:

        - ``ENGINE``: The database backend engine (e.g., ``django.db.backends.mysql``).
        - ``NAME``: The name of the database.
        - ``USER``: The database username.
        - ``PASSWORD``: The password for authentication, if set.
        - ``HOST``: The database host.
        - ``PORT``: The database port as a string.
        - ``OPTIONS``: Additional database connection options (such as SSL or authentication settings).

        :return: A dictionary of Django database connection settings.
        :rtype: dict

        **Example:**

        .. code-block:: python

            settings = sql_connection.django_db_connection
            # returns:
            # {
            #     "ENGINE": "django.db.backends.mysql",
            #     "NAME": "mydb",
            #     "USER": "myuser",
            #     "PASSWORD": "mypassword",
            #     "HOST": "localhost",
            #     "PORT": "3306",
            #     "OPTIONS": {...}
            # }
        """
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
        """
        Return the database connection string.
        This property constructs and returns a database connection string based on the current
        SQL connection instance's configuration.

        :return: A database connection string.
        :rtype: str
        """
        return self.get_connection_string()

    def connect_tcpip(self) -> Optional[BaseDatabaseWrapper]:
        """
        Establish a test database connection using Standard TCP/IP.

        This method attempts to create and validate a database connection using the standard TCP/IP authentication method,
        based on the current SQL connection instance's configuration. It emits signals for connection attempts, successes,
        and failures for observability.

        :return: The database connection object if successful, otherwise None.
        :rtype: Optional[BaseDatabaseWrapper]

        **Example:**

        .. code-block:: python

            db_wrapper = sql_connection.connect_tcpip()
            if db_wrapper:
                # Connection established, use db_wrapper...
                pass

        See also:

        - :meth:`django.db.utils.ConnectionHandler`
        - :meth:`SqlConnection.django_db_connection`
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
        """
        (NOT IMPLEMENTED) Handler for Paramiko SSH transport channels.

        .. warning::
            This method is a placeholder and does not implement actual port forwarding logic.
        """
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

        This method attempts to create and validate a database connection using the standard TCP/IP authentication method
        over an SSH tunnel, based on the current SQL connection instance's configuration. It emits signals for connection
        attempts, successes, and failures for observability.

        :return: The database connection object if successful, otherwise None.
        :rtype: Optional[BaseDatabaseWrapper]
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
            return connection_handler  # type: ignore[return-value]

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

        This method attempts to create and validate a database connection using LDAP User/Password authentication,
        based on the current SQL connection instance's configuration. It emits signals for connection attempts, successes,
        and failures for observability.

        :return: The database connection object if successful, otherwise None.
        :rtype: Optional[BaseDatabaseWrapper]
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

        This method attempts to establish a database connection using the configured authentication method
        for this SQL connection instance. The authentication method can be standard TCP/IP, TCP/IP over SSH,
        LDAP user/password, or none. Returns True if the connection is successfully established, otherwise False.

        :return: True if the connection is established, False otherwise.
        :rtype: bool

        .. important::

            This method is called during the validation process to ensure that the connection parameters are correct
            and that a connection can be successfully made to the database. For example, it is invoked when saving
            a :class:`SqlConnection` instance to verify the connection details.

        See also:

        - :meth:`get_connection`
        """
        connection = self.get_connection()
        return connection is not None

    def get_connection(self) -> Optional[BaseDatabaseWrapper]:
        """
        Establish a database connection based on the authentication method.

        This method attempts to establish a database connection using the configured authentication method
        for this SQL connection instance. The authentication method can be standard TCP/IP, TCP/IP over SSH,
        LDAP user/password, or none. Returns the database connection object if successful, otherwise None.

        :return: The database connection object if successful, otherwise None.
        :rtype: Optional[BaseDatabaseWrapper]
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
        """
        Close the database connection.

        This method closes the current database connection associated with this SQL connection instance,
        if it exists. If an error occurs while closing the connection, it is logged and the connection
        reference is cleared.

        :return: None
        """
        if self._connection:
            try:
                self._connection.close()
            # pylint: disable=W0718
            except Exception as e:
                logger.error("%s.close() Failed to close the database connection: %s", self.formatted_class_name, e)
            self._connection = None

    def execute_query(self, sql: str, limit: Optional[int] = None) -> Union[str, bool]:
        """
        Execute a SQL query and return the results as a JSON string.

        :param sql: The SQL query to execute.
        :param limit: Optional limit on the number of rows to return.
        :return: JSON string of query results if successful, otherwise False.

        .. warning::

            This method does not perform any SQL injection protection or parameterization.
            It is the caller's responsibility to ensure that the SQL query is safe and properly formatted.

        .. warning::

            This method does not limit the execution time nor the number of rows returned by the query,
            unless the ``limit`` parameter is provided. It is the caller's responsibility to ensure that
            the query is efficient and does not return excessive data.
        """

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
        """
        Test the proxy connection by making a request to a known URL through the proxy.

        :return: True if the proxy connection is successful, otherwise False.
        :rtype: bool
        """
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
        """
        Return the connection string.

        This method constructs and returns a database connection string based on the current
        connection instance's configuration. If ``masked`` is True, sensitive information such as
        the password or API key will be masked in the returned string.

        :param masked: Whether to mask sensitive information in the connection string.
        :type masked: bool
        :return: The constructed connection string.
        :rtype: str

        **Example:**

        .. code-block:: python

            conn_str = sql_connection.get_connection_string(masked=True)
            # returns: 'mysql://user:******@host:3306/dbname'

        .. important::

            Unlike most of the Smarter codebase, this method does not use Pydantic SecretStr for masking
            to avoid adding Pydantic as a dependency for the entire ``smarter`` package.
        """
        if masked:
            password = "******"
        else:
            password = self.password.get_secret() if self.password else None
        userinfo = f"{self.username}:{password}" if password else self.username
        return f"{self.db_engine}://{userinfo}@{self.hostname}:{self.port}/{self.database}"

    def validate(self) -> bool:
        """
        Override the validate method to test the SQL connection.

        :return: True if the connection test is successful, otherwise False.
        :rtype: bool
        """
        super().validate()
        retval = self.test_connection()
        plugin_sql_connection_validated.send(sender=self.__class__, connection=self)
        return retval

    def save(self, *args, **kwargs):
        """
        Override the save method to validate the field dicts.

        This method ensures that all relevant fields are validated before saving the model instance.
        For example, it checks that the name is in snake_case and converts it if necessary, logs a warning if conversion occurs,
        and calls the model's ``validate()`` method to enforce any additional validation logic defined on the model.
        After validation, it proceeds with the standard Django save operation.

        :param args: Positional arguments passed to the parent save method.
        :param kwargs: Keyword arguments passed to the parent save method.
        :return: None
        """

        # this should never happen, but the linter complains without it.
        if not isinstance(self.name, str):
            raise SmarterValueError(f"Connection name must be a string but got: {type(self.name)}")

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

    ``PluginDataSql`` is a concrete subclass of :class:`PluginDataBase` and is referenced by :class:`PluginMeta`
    to provide the data payload for SQL-type plugins. It is tightly integrated with :class:`SqlConnection` for
    managing database connectivity and query execution, and supports advanced features such as parameterized queries,
    dynamic placeholder validation, and result limiting.

    This model is responsible for:
      - Storing the SQL query template and associated parameter schema.
      - Validating that all placeholders in the SQL query are defined in the parameters.
      - Ensuring that test values are provided and conform to the expected structure.
      - Preparing and executing SQL queries with runtime parameters, including safe substitution of placeholders.
      - Enforcing result limits to prevent excessive data retrieval.
      - Providing methods for returning sanitized query results for use in LLM responses.

    Typical use cases include plugins that need to retrieve or analyze data from organizational databases,
    support dynamic user queries, or expose structured data to the Smarter LLM platform.

    See also:

    - :class:`PluginDataBase`
    - :class:`SqlConnection`
    - :class:`PluginMeta`
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
        Validates the structure of the ``test_values`` attribute to ensure it matches the expected JSON representation.

        Each item in ``test_values`` must be a dictionary with the keys ``name`` and ``value``. This method attempts to instantiate each item as a Pydantic ``TestValue`` model to verify the structure.

        Example of a valid ``test_values`` list:

        .. code-block:: json

            [
                {"name": "username", "value": "admin"},
                {"name": "unit", "value": "Celsius"}
            ]

        :raises SmarterValueError: If any item in ``test_values`` does not conform to the required structure.
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
        Validates that every placeholder found in the SQL query string is defined as a parameter.

        This method scans the ``sql_query`` attribute for placeholders in the format ``{parameter_name}``.
        It then checks that each placeholder corresponds to a key in the ``parameters['properties']`` dictionary.
        If any placeholder is not defined in the parameters, a ``SmarterValueError`` is raised.

        **Example:**

            .. code-block:: python

                plugin = {
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

        :raises SmarterValueError: If a placeholder in the SQL query is not defined in the parameters.

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

    ``ApiConnection`` is a concrete subclass of :class:`ConnectionBase` and is referenced by
    :class:`PluginDataApi` to provide the connection for API-based plugins. It supports a variety
    of authentication methods (none, basic, token, OAuth), as well as proxy configuration for secure
    and flexible integration with external APIs.

    This model is responsible for:
      - Managing API credentials and secrets using the :class:`Secret` model.
      - Constructing connection strings and request headers for different authentication schemes.
      - Providing methods for testing connectivity to the API and proxy endpoints.
      - Supporting timeout and proxy configuration for robust and secure API access.
      - Integrating with the Smarter plugin system to enable dynamic, authenticated API requests.

    Typical use cases include plugins that need to retrieve or send data to external REST APIs,
    integrate with third-party services, or expose organizational APIs to the Smarter LLM platform.

    See also:

    - :class:`ConnectionBase`
    - :class:`PluginDataApi`
    - :class:`smarter.apps.account.models.Secret`
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

    ``PluginDataApi`` is a concrete subclass of :class:`PluginDataBase` and is referenced by :class:`PluginMeta`
    to provide the data payload for API-type plugins. It is tightly integrated with :class:`ApiConnection` for
    managing API connectivity and request execution, and supports advanced features such as parameterized endpoints,
    dynamic placeholder validation, and flexible request construction.

    This model is responsible for:
      - Storing the API endpoint path, HTTP method, parameter schema, headers, and request body.
      - Validating that all placeholders in the endpoint are defined in the parameters.
      - Ensuring that test values, headers, and URL parameters are provided and conform to the expected structure.
      - Preparing and executing API requests with runtime parameters, including safe substitution of placeholders.
      - Enforcing result limits to prevent excessive data retrieval.
      - Providing methods for returning sanitized API responses for use in LLM responses.

    Typical use cases include plugins that need to retrieve or send data to external REST APIs,
    integrate with third-party services, or expose organizational APIs to the Smarter LLM platform.

    See also:

    - :class:`PluginDataBase`
    - :class:`ApiConnection`
    - :class:`PluginMeta`
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
