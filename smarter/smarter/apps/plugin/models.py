# pylint: disable=C0114,C0115,C0302,W0613
"""PluginMeta app models."""

# python stuff
import ast
import logging
import re
from abc import abstractmethod
from functools import lru_cache
from typing import Any, Optional, Union
from urllib.parse import urljoin

import requests
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

# django stuff
from django.db.models import QuerySet

# 3rd party stuff
from pydantic import ValidationError
from rest_framework import serializers

from smarter.apps.account.models import (
    Account,
    MetaDataWithOwnershipModel,
    User,
    UserProfile,
)
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    smarter_cached_objects,
)

# smarter stuff
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.connection.models import ApiConnection, SqlConnection
from smarter.common.conf import settings_defaults, smarter_settings
from smarter.common.const import SmarterHttpMethods
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.logger_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin
from smarter.common.utils import camel_to_snake, rfc1034_compliant_str
from smarter.lib import json
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.models import (
    TimestampedModel,
    dict_keys_to_list,
    list_of_dicts_to_dict,
    list_of_dicts_to_list,
)
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .manifest.enum import (
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
)

# plugin stuff
from .manifest.models.common import RequestHeader, TestValue, UrlParam


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_prefix = formatted_text(f"{__name__}")


class PluginDataValueError(SmarterValueError):
    """Custom exception for PluginData SQL errors."""


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


class PluginMeta(MetaDataWithOwnershipModel, SmarterHelperMixin):
    """
    Represents the core metadata for a Smarter plugin, serving as the central registry for all plugin types.

    This class defines the essential identifying and descriptive information for a plugin, including its name,
    description, type (static, SQL, or API), version, user_profile, and associated tags. Each plugin is uniquely
    associated with an account and a user_profile, ensuring that plugin names are unique per account and
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
        verbose_name = "Plugin"
        verbose_name_plural = "Plugins"
        unique_together = ("user_profile", "name")

    PLUGIN_CLASSES = [
        (SAMPluginCommonMetadataClassValues.STATIC.value, SAMPluginCommonMetadataClassValues.STATIC.value),
        (SAMPluginCommonMetadataClassValues.SQL.value, SAMPluginCommonMetadataClassValues.SQL.value),
        (SAMPluginCommonMetadataClassValues.API.value, SAMPluginCommonMetadataClassValues.API.value),
    ]
    """
    The classes of plugins supported by Smarter.
    """

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

    plugin_class = models.CharField(
        choices=PLUGIN_CLASSES, help_text="The class name of the plugin", max_length=255, default="PluginMeta"
    )

    def __str__(self):
        return str(self.user_profile) + " " + str(self.name) or ""

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
        if not isinstance(self.name, str) or not self.name:
            raise SmarterValueError("PluginMeta.save(): name is required after save.")

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

    # pylint: disable=W0221
    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        name: Optional[str] = None,
        user: Optional[User] = None,
        user_profile: Optional[UserProfile] = None,
        username: Optional[str] = None,
        account: Optional[Account] = None,
        plugin_class: Optional[str] = None,
        **kwargs,
    ) -> Optional["PluginMeta"]:
        """
        Return a single instance of PluginMeta by primary key or by name and user.

        This method caches the results to improve performance.

        :param name: The name of the plugin to retrieve.
        :type name: str
        :param user: The user who owns the plugin.
        :type user: User
        :param account: The account associated with the plugin.
        :type account: Account
        :param username: The username of the user who owns the plugin.
        :type username: str
        :param invalidate: If True, invalidate the cache for this query.
        :type invalidate: bool
        :return: A PluginMeta instance if found, otherwise None.
        :rtype: Optional[PluginMeta]
        """
        # pylint: disable=W0621
        logger_prefix = formatted_text(f"{__name__}.{PluginMeta.__name__}.get_cached_object()")
        logger.debug(
            "%s called with pk: %s, name: %s, user: %s, user_profile: %s, account: %s, plugin_class: %s",
            logger_prefix,
            pk,
            name,
            user.username if user else None,
            user_profile.id if user_profile else None,  # type: ignore[attr-defined]
            account.id if account else None,  # type: ignore[attr-defined]
            plugin_class,
        )

        @cache_results(cls.cache_expiration)
        def _get_model_by_name_and_userprofile_and_plugin_class(
            name: str, user_profile_id: int, plugin_class: str
        ) -> Optional["PluginMeta"]:
            try:
                logger.debug(
                    "%s._get_model_by_name_and_userprofile_and_plugin_class() cache miss for name: %s, user_profile_id: %s, plugin_class: %s",
                    logger_prefix,
                    name,
                    user_profile_id,
                    plugin_class,
                )
                return (
                    cls.objects.prefetch_related("tags")
                    .select_related("user_profile", "user_profile__account", "user_profile__user")
                    .get(name=name, user_profile_id=user_profile_id, plugin_class=plugin_class)
                )
            except cls.DoesNotExist as e:
                logger.debug(
                    "%s._get_model_by_name_and_userprofile_and_plugin_class() no PluginMeta found for name: %s, user_profile_id: %s, plugin_class: %s",
                    logger_prefix,
                    name,
                    user_profile_id,
                    plugin_class,
                )
                raise cls.DoesNotExist(
                    f"No PluginMeta found for name: {name}, user_profile_id: {user_profile_id}, plugin_class: {plugin_class}"
                ) from e

        if username and not user:
            user_profile = UserProfile.get_cached_object(invalidate=invalidate, username=username, account=account)  # type: ignore[arg-type]
            user = user_profile.user if user_profile else None
            account = account or (user_profile.account if user_profile else None)

        user_profile = user_profile or UserProfile.get_cached_object(invalidate=invalidate, user=user, account=account)  # type: ignore[arg-type]
        if not user_profile and not pk:
            raise SmarterValueError("either a pk or UserProfile + name is required to get a PluginMeta object.")

        if invalidate and user_profile and name:
            _get_model_by_name_and_userprofile_and_plugin_class.invalidate(name, user_profile.id, plugin_class)  # type: ignore[union-attr]

        if pk:
            return super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return-value]

        if not plugin_class:
            retval = super().get_cached_object(
                *args,
                invalidate=invalidate,
                pk=pk,
                name=name,
                user=user,
                user_profile=user_profile,
                account=account,
                **kwargs,
            )
            if isinstance(retval, PluginMeta):
                return retval
            return None

        if plugin_class:
            return _get_model_by_name_and_userprofile_and_plugin_class(name, user_profile.id, plugin_class)  # type: ignore[return-value]
        retval = super().get_cached_object(*args, invalidate=invalidate, name=name, user_profile=user_profile, **kwargs)
        if isinstance(retval, PluginMeta):
            return retval

    # pylint: disable=W0222
    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, user_profile: Optional[UserProfile] = None
    ) -> QuerySet["PluginMeta"]:
        """
        Return a QuerySet of all PluginMeta instances for the given user profile.
        This method caches the results to improve performance.

        :param invalidate: If True, invalidate the cache for this query.
        :type invalidate: bool
        :param user_profile: The user profile whose plugins should be retrieved.
        :type user_profile: UserProfile
        :return: A QuerySet of PluginMeta instances for the user profile.
        :rtype: QuerySet[PluginMeta]
        """

        # pylint: disable=W0621
        logger_prefix = formatted_text(f"{__name__}.{PluginMeta.__name__}.get_cached_objects()")
        logger.debug("%s called with user_profile=%s, invalidate=%s", logger_prefix, user_profile, invalidate)

        return super().get_cached_objects(invalidate=invalidate, user_profile=user_profile)  # type: ignore[return-value]

    @classmethod
    def get_cached_plugins_for_user_profile_id(
        cls, invalidate: Optional[bool] = False, user_profile_id: Optional[int] = None
    ) -> list["PluginMeta"]:
        """
        Return a list of all instances of PluginMeta for the given user.

        This method caches the results to improve performance.

        :param user_profile_id: The ID of the user profile whose plugins should be retrieved.
        :type user_profile_id: int
        :param invalidate: Whether to invalidate the cache before retrieving the plugins.
        :type invalidate: bool
        :return: A list of PluginMeta instances for the user profile.
        :rtype: list[PluginMeta]

        See also:

        - :func:`smarter.lib.cache.cache_results`
        """

        try:
            retval = []
            user_profile = UserProfile.get_cached_object(invalidate=invalidate, pk=user_profile_id)
            if not user_profile:
                raise SmarterValueError(f"UserProfile with id {user_profile_id} not found.")
            admin_user = get_cached_admin_user_for_account(invalidate=invalidate, account=user_profile.cached_account)  # type: ignore[arg-type]
            admin_user_profile = UserProfile.get_cached_object(invalidate=invalidate, user=admin_user, account=user_profile.cached_account)  # type: ignore[arg-type]

            def was_already_added(plugin_meta: PluginMeta) -> bool:
                if not plugin_meta:
                    logger.error("%s.dispatch() - plugin_meta is None. This is a bug.", logger_prefix)
                    return False
                for b in retval:
                    if b.id == plugin_meta.id:  # type: ignore[union-attr]
                        return True
                return False

            def get_plugins_for_account() -> QuerySet:
                user_plugins = PluginMeta.get_cached_objects(user_profile=user_profile, invalidate=invalidate)
                logger.debug(
                    "%s.get_cached_plugins_for_user_profile_id() - Retrieved %d user plugins for %s",
                    logger_prefix,
                    len(user_plugins),
                    user_profile,
                )

                admin_plugins = PluginMeta.get_cached_objects(user_profile=admin_user_profile, invalidate=invalidate)  # type: ignore[assignment]
                logger.debug(
                    "%s.get_cached_plugins_for_user_profile_id() - Retrieved %d admin plugins for %s",
                    logger_prefix,
                    len(admin_plugins),
                    admin_user_profile,
                )

                smarter_plugins = PluginMeta.get_cached_objects(
                    user_profile=smarter_cached_objects.smarter_admin_user_profile, invalidate=invalidate
                )
                logger.debug(
                    "%s.get_cached_plugins_for_user_profile_id() - Retrieved %d smarter plugins for %s",
                    logger_prefix,
                    len(smarter_plugins),
                    smarter_cached_objects.smarter_admin_user_profile,
                )

                @cache_results(15)
                def _combined_plugins_list(use_profile_id: int, class_name: str = PluginMeta.__name__) -> QuerySet:
                    """
                    Short-lived cache for combined plugins list.
                    Combines user, admin, and smarter plugins into a single queryset
                    and caches the result for 15 seconds to improve performance.
                    """

                    combined_plugins = user_plugins | admin_plugins | smarter_plugins
                    combined_plugins = (
                        combined_plugins.distinct()
                        .select_related("user_profile", "user_profile__account", "user_profile__user")
                        .order_by("name")
                    )
                    return combined_plugins

                return _combined_plugins_list(user_profile.id, class_name=PluginMeta.__name__)  # type: ignore[return-value]

            plugins = get_plugins_for_account()

            for plugin_meta in plugins:
                if not was_already_added(plugin_meta):
                    retval.append(plugin_meta)

            return retval

        # pylint: disable=broad-except
        except Exception:
            logger.error(
                "%s.dispatch() - Exception occurred while getting plugins for user_profile %s.",
                logger_prefix,
                user_profile,
            )
            return []


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
        encoder=json.SmarterJSONEncoder,
    )

    def __str__(self) -> str:
        search_terms = json.dumps(self.search_terms)[:50]
        return f"{str(self.directive)} - {search_terms}"

    @classmethod
    def get_cached_selector_by_plugin(
        cls, plugin: PluginMeta, invalidate: bool = False
    ) -> Union["PluginSelector", None]:
        """
        Return a single instance of PluginSelector by plugin.

        This method caches the results to improve performance.

        :param plugin: The plugin whose selector should be retrieved.
        :type plugin: PluginMeta
        :return: A PluginSelector instance if found, otherwise None.
        :rtype: Union[PluginSelector, None]
        """

        @cache_results()
        def selector_by_plugin_id(plugin_id: int) -> Union["PluginSelector", None]:
            try:
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_selector_by_plugin: Selector not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginSelector with plugin_id {plugin_id} does not exist.") from e

        if invalidate:
            selector_by_plugin_id.invalidate(plugin.id)  # type: ignore[union-attr]

        return selector_by_plugin_id(plugin.id)  # type: ignore[return-value]


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
    messages = models.JSONField(
        help_text="The user prompt messages.", default=list, blank=True, null=True, encoder=json.SmarterJSONEncoder
    )
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
        default=settings_defaults.LLM_DEFAULT_PROVIDER,
    )
    system_role = models.TextField(
        help_text="The role of the system in the conversation.",
        null=True,
        blank=True,
        default="You are a helful assistant.",
    )
    model = models.CharField(
        help_text="The model to use for the completion.", max_length=255, default=settings_defaults.LLM_DEFAULT_MODEL
    )
    temperature = models.FloatField(
        help_text="The higher the temperature, the more creative the result.",
        default=settings_defaults.LLM_DEFAULT_TEMPERATURE,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    max_completion_tokens = models.IntegerField(
        help_text="The maximum number of tokens for both input and output.",
        default=settings_defaults.LLM_DEFAULT_MAX_TOKENS,
        validators=[MinValueValidator(0), MaxValueValidator(8192)],
    )

    def __str__(self) -> str:
        return str(self.plugin.name)

    @classmethod
    def get_cached_prompt_by_plugin(cls, plugin: PluginMeta, invalidate: bool = False) -> Union["PluginPrompt", None]:
        """
        Return a single instance of PluginPrompt by plugin.

        This method caches the results to improve performance.

        :param plugin: The plugin whose prompt should be retrieved.
        :type plugin: PluginMeta
        :return: A PluginPrompt instance if found, otherwise None.
        :rtype: Union[PluginPrompt, None]
        """

        @cache_results()
        def prompt_by_plugin_id(plugin_id: int) -> Union["PluginPrompt", None]:
            try:
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_prompt_by_plugin: Prompt not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginPrompt not found for plugin_id: {plugin_id}") from e

        if invalidate:
            prompt_by_plugin_id.invalidate(plugin.id)  # type: ignore[union-attr]

        return prompt_by_plugin_id(plugin.id)  # type: ignore[return-value]


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

    def __str__(self) -> str:
        plugin: PluginMeta = self.plugin
        user_profile = plugin.user_profile if self.plugin else "No User Profile"
        user_profile = str(user_profile)
        name = str(plugin.name) if plugin else "No Plugin Name"
        return str("<" + user_profile + " - " + name + ">")

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
        encoder=json.SmarterJSONEncoder,
    )
    """
    A JSON dict containing parameter names and data types. Example: {'required': [], 'properties': {'max_cost': {'type': 'float', 'description': 'the maximum cost that a student is willing to pay for a course.'}, 'description': {'enum': ['AI', 'mobile', 'web', 'database', 'network', 'neural networks'], 'type': 'string', 'description': 'areas of specialization for courses in the catalogue.'}}}
    """

    test_values = models.JSONField(
        help_text="A JSON dict containing test values for each parameter. Example: {'city': 'San Francisco'}",
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
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

    @classmethod
    def get_cached_data_by_plugin(cls, plugin: PluginMeta, invalidate: bool = False) -> Union["PluginDataBase", None]:

        raise NotImplementedError("Subclasses must implement get_cached_data_by_plugin method.")

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        self.validate()
        super().save(*args, **kwargs)
        self.get_cached_data_by_plugin(self.plugin, invalidate=True)


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

    class Meta:
        verbose_name = "Plugin Static Data"
        verbose_name_plural = "Plugin Static Data"

    static_data = models.JSONField(
        help_text="The JSON data that this plugin returns to OpenAI API when invoked by the user prompt.",
        default=dict,
        encoder=json.SmarterJSONEncoder,
    )
    """
    The JSON data that this plugin returns to OpenAI API when invoked by the user prompt.
    """

    def sanitized_return_data(self, params: Optional[dict] = None) -> Optional[Union[dict, list]]:
        """
        Return the static data for this plugin, either as a dictionary or a list.

        This method returns the value of ``self.static_data`` in a sanitized form:

        - If ``static_data`` is a dictionary, it is returned as-is.
        - If ``static_data`` is a list, it is truncated to ``smarter_settings.plugin_max_data_results`` items (if necessary)
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
                if len(retval) > smarter_settings.plugin_max_data_results:
                    logger.warning(
                        "%s.sanitized_return_data: Truncating static_data to %s items.",
                        self.formatted_class_name,
                        {smarter_settings.plugin_max_data_results},
                    )
                retval = retval[: smarter_settings.plugin_max_data_results]  # pylint: disable=E1136
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
        - If ``static_data`` is a list of dictionaries, the keys are extracted from each dictionary and returned as a list, truncated to ``smarter_settings.plugin_max_data_results`` items if necessary.
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
                if len(retval) > smarter_settings.plugin_max_data_results:
                    logger.warning(
                        "%s.return_data_keys: Truncating static_data to %s items.",
                        self.formatted_class_name,
                        {smarter_settings.plugin_max_data_results},
                    )
                retval = retval[: smarter_settings.plugin_max_data_results]  # pylint: disable=E1136
                retval = list_of_dicts_to_list(data=retval)
        else:
            raise SmarterValueError("static_data must be a dict or a list or None")

        return retval[: smarter_settings.plugin_max_data_results] if isinstance(retval, list) else retval

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

    @classmethod
    def get_cached_data_by_plugin(cls, plugin: PluginMeta, invalidate: bool = False) -> Union["PluginDataStatic", None]:
        """
        Return a single instance of PluginDataStatic by plugin.

        This method caches the results to improve performance.

        :param plugin: The plugin whose data should be retrieved.
        :type plugin: PluginMeta
        :return: A PluginDataStatic instance if found, otherwise None.
        :rtype: Union[PluginDataStatic, None]
        """

        @cache_results()
        def data_by_plugin_id(plugin_id: int) -> Union["PluginDataStatic", None]:
            try:
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    formatted_text(cls.__name__),
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginDataStatic with plugin_id {plugin_id} does not exist.") from e

        if invalidate:
            data_by_plugin_id.invalidate(plugin.id)  # type: ignore[union-attr]

        return data_by_plugin_id(plugin.id)  # type: ignore[return-value]

    # pylint: disable=W0221
    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        plugin: Optional[PluginMeta] = None,
        **kwargs,
    ) -> Optional["PluginDataBase"]:
        """
        Retrieve a model instance by primary key, using caching to
        optimize performance. This method is selectively overridden in
        models that inherit from MetaDataModel to provide class-specific
        function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)

        :param invalidate: If True, invalidate the cache for this query before retrieving the object.
        :type invalidate: bool
        :param pk: The primary key of the model instance to retrieve.
        :type pk: int
        :param plugin: The PluginMeta instance associated with the data to retrieve.
        :type plugin: PluginMeta

        :returns: The model instance if found, otherwise None.
        :rtype: Optional["PluginDataBase"]
        """
        # pylint: disable=W0621
        logger_prefix = formatted_text(f"{__name__}.{PluginDataStatic.__name__}.get_cached_object()")
        logger.debug(
            "%s called with pk: %s, plugin: %s",
            logger_prefix,
            pk,
            plugin,
        )

        @cache_results()
        def _get_model_by_plugin_meta(plugin_id: int) -> Optional["PluginDataBase"]:
            try:
                logger.debug(
                    "%s._get_model_by_plugin_meta() cache miss for plugin_id: %s",
                    logger_prefix,
                    plugin_id,
                )
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginDataStatic with plugin_id {plugin_id} does not exist.") from e

        if invalidate and plugin:
            _get_model_by_plugin_meta.invalidate(plugin.id)  # type: ignore[union-attr]

        if pk:
            return super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return-value]

        if plugin:
            return _get_model_by_plugin_meta(plugin.id)  # type: ignore[return-value]


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
        self.get_cached_data_by_plugin(self.plugin, invalidate=True)

    # pylint: disable=W0221
    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        plugin: Optional[PluginMeta] = None,
        **kwargs,
    ) -> Optional["PluginDataBase"]:
        """
        Retrieve a model instance by primary key, using caching to
        optimize performance. This method is selectively overridden in
        models that inherit from MetaDataModel to provide class-specific
        function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)

        :param invalidate: If True, invalidate the cache for this query before retrieving the object.
        :type invalidate: bool
        :param pk: The primary key of the model instance to retrieve.
        :type pk: int
        :param plugin: The PluginMeta instance associated with the data to retrieve.
        :type plugin: PluginMeta

        :returns: The model instance if found, otherwise None.
        :rtype: Optional["PluginDataBase"]
        """
        # pylint: disable=W0621
        logger_prefix = formatted_text(f"{__name__}.{PluginDataSql.__name__}.get_cached_object()")
        logger.debug(
            "%s called with pk: %s, plugin: %s",
            logger_prefix,
            pk,
            plugin,
        )

        @cache_results()
        def _get_model_by_plugin_meta(plugin_id: int) -> Optional["PluginDataBase"]:
            try:
                logger.debug(
                    "%s._get_model_by_plugin_meta() cache miss for plugin_id: %s",
                    logger_prefix,
                    plugin_id,
                )
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"No {cls.formatted_class_name} found for plugin_id: {plugin_id}") from e

        if invalidate and plugin:
            _get_model_by_plugin_meta.invalidate(plugin.id)  # type: ignore[union-attr]

        if pk:
            return super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return-value]

        if plugin:
            return _get_model_by_plugin_meta(plugin.id)  # type: ignore[return-value]

    @classmethod
    def get_cached_data_by_plugin(cls, plugin: PluginMeta, invalidate: bool = False) -> Union["PluginDataSql", None]:
        """
        Return a single instance of PluginDataSql by plugin.

        This method caches the results to improve performance.

        :param plugin: The plugin whose data should be retrieved.
        :type plugin: PluginMeta
        :return: A PluginDataSql instance if found, otherwise None.
        :rtype: Union[PluginDataSql, None]
        """

        @cache_results()
        def data_by_plugin_id(plugin_id: int) -> Union["PluginDataSql", None]:
            try:
                return cls.objects.select_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"No {cls.formatted_class_name} found for plugin_id: {plugin_id}") from e

        if invalidate:
            data_by_plugin_id.invalidate(plugin.id)  # type: ignore[union-attr]

        return data_by_plugin_id(plugin.id)  # type: ignore[return-value]


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
        choices=[
            (SmarterHttpMethods.GET, SmarterHttpMethods.GET),
            (SmarterHttpMethods.POST, SmarterHttpMethods.POST),
            (SmarterHttpMethods.PUT, SmarterHttpMethods.PUT),
            (SmarterHttpMethods.DELETE, SmarterHttpMethods.DELETE),
        ],
        default=SmarterHttpMethods.GET,
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
        encoder=json.SmarterJSONEncoder,
    )
    headers = models.JSONField(
        help_text="A JSON dict containing headers to be sent with the API request. Example: {'Authorization': 'Bearer <token>'}",
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )
    body = models.JSONField(
        help_text="A JSON dict containing the body of the API request, if applicable.",
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
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
        self.get_cached_data_by_plugin(self.plugin, invalidate=True)

    @classmethod
    def get_cached_data_by_plugin(cls, plugin: PluginMeta, invalidate: bool = False) -> Union["PluginDataApi", None]:
        """
        Return a single instance of PluginDataApi by plugin.

        This method caches the results to improve performance.

        :param plugin: The plugin whose data should be retrieved.
        :type plugin: PluginMeta
        :return: A PluginDataApi instance if found, otherwise None.
        :rtype: Union[PluginDataApi, None]
        """

        @cache_results()
        def data_by_plugin_id(plugin_id: int) -> Union["PluginDataApi", None]:
            try:
                return cls.objects.select_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginDataApi not found for plugin_id: {plugin_id}") from e

        if invalidate:
            data_by_plugin_id.invalidate(plugin.id)  # type: ignore[union-attr]

        return data_by_plugin_id(plugin.id)  # type: ignore[return-value]

    # pylint: disable=W0221
    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        plugin: Optional[PluginMeta] = None,
        **kwargs,
    ) -> Optional["PluginDataBase"]:
        """
        Retrieve a model instance by primary key, using caching to
        optimize performance. This method is selectively overridden in
        models that inherit from MetaDataModel to provide class-specific
        function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)

        :param invalidate: If True, invalidate the cache for this query before retrieving the object.
        :type invalidate: bool
        :param pk: The primary key of the model instance to retrieve.
        :type pk: int
        :param plugin: The PluginMeta instance associated with the data to retrieve.
        :type plugin: PluginMeta

        :returns: The model instance if found, otherwise None.
        :rtype: Optional["PluginDataBase"]
        """
        # pylint: disable=W0621
        logger_prefix = formatted_text(f"{__name__}.{PluginDataApi.__name__}.get_cached_object()")
        logger.debug(
            "%s called with pk: %s, plugin: %s",
            logger_prefix,
            pk,
            plugin,
        )

        @cache_results()
        def _get_model_by_plugin_meta(plugin_id: int) -> Optional["PluginDataBase"]:
            try:
                logger.debug(
                    "%s._get_model_by_plugin_meta() cache miss for plugin_id: %s",
                    logger_prefix,
                    plugin_id,
                )
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginDataApi not found for plugin_id: {plugin_id}") from e

        if invalidate and plugin:
            _get_model_by_plugin_meta.invalidate(plugin.id)  # type: ignore[union-attr]

        if pk:
            return super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return-value]

        if plugin:
            return _get_model_by_plugin_meta(plugin.id)  # type: ignore[return-value]


PluginDataType = type[PluginDataStatic] | type[PluginDataApi] | type[PluginDataSql]
PLUGIN_DATA_MAP: dict[str, PluginDataType] = {
    SAMKinds.API_PLUGIN.value: PluginDataApi,
    SAMKinds.SQL_PLUGIN.value: PluginDataSql,
    SAMKinds.STATIC_PLUGIN.value: PluginDataStatic,
}

__all__ = [
    "PluginMeta",
    "PluginSelector",
    "PluginPrompt",
    "PluginSelectorHistory",
    "PluginDataBase",
    "PluginDataStatic",
    "PluginDataSql",
    "PluginDataApi",
    "PluginDataType",
    "PLUGIN_DATA_MAP",
]
