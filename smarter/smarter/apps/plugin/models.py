# pylint: disable=C0114,C0115
"""PluginMeta app models."""
import json
import logging
from functools import lru_cache

import yaml
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from taggit.managers import TaggableManager

from smarter.apps.account.models import Account, UserProfile
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.model_helpers import TimestampedModel


logger = logging.getLogger(__name__)


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


def list_of_dicts_to_list(data: list[dict]) -> list[str]:
    """Convert a list of dictionaries into a single dict with keys extracted
    from the first key in the first dict."""
    if not data or not isinstance(data[0], dict):
        return None
    logger.warning("converting list of dicts to a single dict")
    retval = []
    key = next(iter(data[0]))
    for d in data:
        if key in d:
            cleaned_key = dict_key_cleaner(d[key])
            retval.append(cleaned_key)
    return retval


def list_of_dicts_to_dict(data: list[dict]) -> dict:
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


class PluginMeta(TimestampedModel):
    """PluginMeta model."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="plugins")
    name = models.CharField(
        help_text="The name of the plugin. Example: 'HR Policy Update' or 'Public Relation Talking Points'.",
        max_length=255,
        default="PluginMeta",
    )
    description = models.TextField(
        help_text="A brief description of the plugin. Be verbose, but not too verbose.",
    )
    plugin_class = models.CharField(help_text="The class name of the plugin", max_length=255, default="PluginMeta")
    version = models.CharField(max_length=255, default="1.0.0")
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="plugins")
    tags = TaggableManager(blank=True)

    def __str__(self):
        return str(self.name) or ""

    # pylint: disable=missing-class-docstring
    class Meta:
        unique_together = (
            "account",
            "name",
        )
        verbose_name = "Plugin"
        verbose_name_plural = "Plugins"


class PluginSelector(TimestampedModel):
    """PluginSelector model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="selector")
    directive = models.CharField(
        help_text="The selection strategy to use for this plugin.", max_length=255, default="search_terms"
    )
    search_terms = models.JSONField(
        help_text="search terms in JSON format that, if detected in the user prompt, will incentivize Smarter to load this plugin.",
        default=list,
    )

    def __str__(self) -> str:
        search_terms = json.dumps(self.search_terms)[:50]
        return f"{str(self.directive)} - {search_terms}"


class PluginSelectorHistory(TimestampedModel):
    """PluginSelectorHistory model."""

    plugin_selector = models.ForeignKey(PluginSelector, on_delete=models.CASCADE, related_name="history")
    search_term = models.CharField(max_length=255, blank=True, null=True, default="")
    messages = models.JSONField(help_text="The user prompt messages.", default=list, blank=True, null=True)

    def __str__(self) -> str:
        return f"{str(self.plugin_selector.plugin.name)} - {self.search_term}"

    class Meta:
        verbose_name_plural = "Plugin Selector History"


class PluginPrompt(TimestampedModel):
    """PluginPrompt model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="prompt")
    system_role = models.TextField(
        help_text="The role of the system in the conversation.",
        null=True,
        blank=True,
        default="You are a helful assistant.",
    )
    model = models.CharField(help_text="The model to use for the completion.", max_length=255, default="gpt-3.5-turbo")
    temperature = models.FloatField(
        help_text="The higher the temperature, the more creative the result.",
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    max_tokens = models.IntegerField(
        help_text="The maximum number of tokens for both input and output.",
        default=256,
        validators=[MinValueValidator(0), MaxValueValidator(4096)],
    )

    def __str__(self) -> str:
        return str(self.plugin.name)


class PluginDataStatic(TimestampedModel):
    """PluginDataStatic model."""

    plugin = models.OneToOneField(PluginMeta, on_delete=models.CASCADE, related_name="plugin_data")
    description = models.TextField(
        help_text="A brief description of what this plugin returns. Be verbose, but not too verbose.",
    )
    return_data = models.JSONField(
        help_text="The JSON data that this plugin returns to OpenAI API when invoked by the user prompt.", default=dict
    )

    @property
    def sanitized_return_data(self) -> dict:
        """Returns a dict of self.return_data."""
        retval: dict = {}
        if isinstance(self.return_data, dict):
            return self.return_data
        if isinstance(self.return_data, list):
            retval = self.return_data
            if isinstance(retval, list) and len(retval) > 0:
                if len(retval) > settings.SMARTER_PLUGIN_MAX_DATA_RESULTS:
                    logger.warning(
                        "PluginDataStatic.sanitized_return_data: Truncating return_data to %s items.",
                        {settings.SMARTER_PLUGIN_MAX_DATA_RESULTS},
                    )
                retval = retval[: settings.SMARTER_PLUGIN_MAX_DATA_RESULTS]  # pylint: disable=E1136
                retval = list_of_dicts_to_dict(data=retval)
        else:
            raise SmarterValueError("return_data must be a dict or a list or None")

        return retval

    @property
    @lru_cache(maxsize=128)
    def return_data_keys(self) -> list:
        """Return all keys in the return_data."""

        retval: list = []
        if isinstance(self.return_data, dict):
            retval = dict_keys_to_list(data=self.return_data)
            retval = list(retval)
        elif isinstance(self.return_data, list):
            retval = self.return_data
            if isinstance(retval, list) and len(retval) > 0:
                if len(retval) > settings.SMARTER_PLUGIN_MAX_DATA_RESULTS:
                    logger.warning(
                        "PluginDataStatic.return_data_keys: Truncating return_data to %s items.",
                        {settings.SMARTER_PLUGIN_MAX_DATA_RESULTS},
                    )
                retval = retval[: settings.SMARTER_PLUGIN_MAX_DATA_RESULTS]  # pylint: disable=E1136
                retval = list_of_dicts_to_list(data=retval)
        else:
            raise SmarterValueError("return_data must be a dict or a list or None")

        return retval[: settings.SMARTER_PLUGIN_MAX_DATA_RESULTS]  # pylint: disable=E1136

    @property
    def data(self) -> dict:
        return yaml.dump(self.return_data)

    def __str__(self) -> str:
        return str(self.plugin.name)

    class Meta:
        verbose_name = "Plugin Data"
        verbose_name_plural = "Plugin Data"
