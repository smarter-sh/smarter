"""
PluginDataWebsearch model for storing the configuration of a WebsearchPlugin.

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from typing import Any, Optional, Union

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from smarter.apps.account.models.budget import charge_authorization
from smarter.apps.plugin.manifest.models.websearch_plugin.const import (
    DEFAULT_CACHE_TTL,
    DEFAULT_FETCH_CHARACTERS,
    DEFAULT_MAX_RESULTS,
    DEFAULT_TIMEOUT,
    MAX_CACHE_TTL,
    MAX_FETCH_CHARACTERS,
    MAX_RESULTS,
    MAX_TIMEOUT,
    MIN_FETCH_CHARACTERS,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.enum import (
    WebsearchFreshness,
    WebsearchOperation,
    WebsearchProvider,
    WebsearchSafeSearch,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.policy import (
    DomainPolicy,
    WebsearchPolicyError,
    normalize_domains,
)
from smarter.apps.secret.models import Secret
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .plugin_data_base import PluginDataBase
from .plugin_meta import PluginMeta

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])


def choices(enum) -> list[tuple[str, str]]:
    """Return Django model field choices for a SmarterEnumAbstract."""
    return [(value, value) for value in enum.all()]


class PluginDataWebsearch(PluginDataBase):
    """
    Stores the configuration of a WebsearchPlugin, which searches the open web and reads web pages.

    A WebsearchPlugin performs two operations, each of which is optional:

    - **search**, via a web search API (``search_provider``), authenticated with an api key
      stored in a Smarter Secret (``search_api_key``).
    - **fetch**, reading a web page by URL (``fetch_enabled``).

    Both operations are subject to the plugin's domain policy (``allowed_domains`` and
    ``blocked_domains``), its request ``timeout``, and its ``cache_ttl``.

    .. seealso::

        - :class:`PluginDataBase`
        - :py:class:`smarter.apps.plugin.plugin.websearch.WebsearchPlugin`
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Plugin Websearch Data"
        verbose_name_plural = "Plugin Websearch Data"

    search_provider = models.CharField(
        max_length=16,
        choices=choices(WebsearchProvider),
        blank=True,
        null=True,
        help_text="The web search API. Null if web search is disabled.",
    )
    search_api_key = models.ForeignKey(
        Secret,
        on_delete=models.SET_NULL,
        related_name="plugin_data_websearch_api_key",
        blank=True,
        null=True,
        help_text="The Secret that contains the web search API's api key.",
    )
    search_max_results = models.PositiveSmallIntegerField(
        default=DEFAULT_MAX_RESULTS,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_RESULTS)],
        help_text="The maximum number of results per search.",
    )
    search_safe_search = models.CharField(
        max_length=16,
        choices=choices(WebsearchSafeSearch),
        default=WebsearchSafeSearch.MODERATE.value,
        help_text="Adult content filtering of search results.",
    )
    search_country = models.CharField(
        max_length=2, blank=True, null=True, help_text="An ISO 3166-1 alpha-2 country code, to localize results."
    )
    search_language = models.CharField(
        max_length=2, blank=True, null=True, help_text="An ISO 639-1 language code, to localize results."
    )
    search_freshness = models.CharField(
        max_length=16,
        choices=choices(WebsearchFreshness),
        blank=True,
        null=True,
        help_text="By default, restrict results to those published within the last day, week, month or year.",
    )
    fetch_enabled = models.BooleanField(default=False, help_text="Whether the plugin can read web pages by URL.")
    fetch_max_characters = models.PositiveIntegerField(
        default=DEFAULT_FETCH_CHARACTERS,
        validators=[MinValueValidator(MIN_FETCH_CHARACTERS), MaxValueValidator(MAX_FETCH_CHARACTERS)],
        help_text="The maximum number of characters of a web page to return.",
    )
    fetch_respect_robots_txt = models.BooleanField(
        default=True, help_text="Whether to obey websites' robots.txt files."
    )
    allowed_domains = models.JSONField(
        default=list,
        blank=True,
        encoder=json.SmarterJSONEncoder,
        help_text="If not empty, only these domains, and their subdomains, may be searched and read.",
    )
    blocked_domains = models.JSONField(
        default=list,
        blank=True,
        encoder=json.SmarterJSONEncoder,
        help_text="These domains, and their subdomains, are never searched nor read.",
    )
    timeout = models.PositiveSmallIntegerField(
        default=DEFAULT_TIMEOUT,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_TIMEOUT)],
        help_text="Seconds to wait for each web request.",
    )
    cache_ttl = models.PositiveIntegerField(
        default=DEFAULT_CACHE_TTL,
        validators=[MaxValueValidator(MAX_CACHE_TTL)],
        help_text="Seconds to cache search results and web pages. 0 disables caching.",
    )

    @property
    def search_enabled(self) -> bool:
        """Whether the plugin can search the web."""
        return bool(self.search_provider)

    @property
    def operations(self) -> list[str]:
        """The operations that the plugin performs."""
        retval = []
        if self.search_enabled:
            retval.append(WebsearchOperation.SEARCH.value)
        if self.fetch_enabled:
            retval.append(WebsearchOperation.FETCH.value)
        return retval

    @property
    def domain_policy(self) -> DomainPolicy:
        """The plugin's domain policy."""
        return DomainPolicy.create(allowed=self.allowed_domains, blocked=self.blocked_domains)

    @property
    def return_data_keys(self) -> list[str]:
        """The operations that the plugin performs."""
        return self.operations

    def api_key(self) -> Optional[str]:
        """
        Return the web search API's api key.

        :return: The api key, or None if web search is disabled or the Secret is unavailable.
        """
        if not self.search_enabled or not self.search_api_key:
            return None
        return self.search_api_key.get_secret()

    # pylint: disable=too-many-branches
    def validate(self) -> bool:
        """
        Validate the configuration.

        :raises SmarterValueError: If neither operation is enabled, a value is out of range,
            web search is enabled without an api key, or a domain is invalid.
        """
        super().validate()
        if not self.search_enabled and not self.fetch_enabled:
            raise SmarterValueError("a websearch plugin must enable web search, reading web pages, or both.")
        if self.search_provider and self.search_provider not in WebsearchProvider.all():
            raise SmarterValueError(f"search_provider must be one of {WebsearchProvider.all()}: {self.search_provider}")
        if self.search_enabled and not self.search_api_key_id:  # type: ignore[attr-defined]
            raise SmarterValueError("web search requires an api key Secret.")
        if self.search_safe_search not in WebsearchSafeSearch.all():
            raise SmarterValueError(f"search_safe_search must be one of {WebsearchSafeSearch.all()}")
        if self.search_freshness and self.search_freshness not in WebsearchFreshness.all():
            raise SmarterValueError(f"search_freshness must be one of {WebsearchFreshness.all()}")
        for name, value, low, high in (
            ("search_max_results", self.search_max_results, 1, MAX_RESULTS),
            ("fetch_max_characters", self.fetch_max_characters, MIN_FETCH_CHARACTERS, MAX_FETCH_CHARACTERS),
            ("timeout", self.timeout, 1, MAX_TIMEOUT),
            ("cache_ttl", self.cache_ttl, 0, MAX_CACHE_TTL),
        ):
            if not isinstance(value, int) or not low <= value <= high:
                raise SmarterValueError(f"{name} must be an integer from {low} to {high}: {value}")
        try:
            normalize_domains(self.allowed_domains)
            normalize_domains(self.blocked_domains)
        except WebsearchPolicyError as e:
            raise SmarterValueError(str(e)) from e
        return True

    def save(self, *args, **kwargs):
        """Normalize the domain lists, validate, and save."""
        try:
            self.allowed_domains = list(normalize_domains(self.allowed_domains))
            self.blocked_domains = list(normalize_domains(self.blocked_domains))
        except WebsearchPolicyError as e:
            raise SmarterValueError(str(e)) from e
        if not self.search_enabled:
            self.search_api_key = None
        super().save(*args, **kwargs)

    def data(self, params: Optional[dict] = None) -> dict[str, Any]:
        """
        Return the configuration of the plugin, without the api key.

        :param params: Optional parameters for future extensibility (currently unused).
        :return: The configuration.
        """
        return {
            "operations": self.operations,
            "search_provider": self.search_provider,
            "allowed_domains": self.allowed_domains,
            "blocked_domains": self.blocked_domains,
        }

    def sanitized_return_data(self, params: Optional[dict] = None) -> dict[str, Any]:
        """
        Return the configuration of the plugin, without the api key.

        The results of web searches and web page fetches are returned by
        :py:meth:`smarter.apps.plugin.plugin.websearch.WebsearchPlugin.tool_call_fetch_plugin_response`.
        """
        return self.data(params)

    def manifest_data(self) -> dict[str, Any]:
        """
        Return the ``spec.websearchData`` section of the plugin manifest.

        The api key is rendered as the name of its Secret, never its value.

        :return: The manifest section, in camelCase.
        """
        retval: dict[str, Any] = {
            "allowedDomains": self.allowed_domains or None,
            "blockedDomains": self.blocked_domains or None,
            "timeout": self.timeout,
            "cacheTtl": self.cache_ttl,
        }
        if self.search_enabled:
            retval["search"] = {
                "provider": self.search_provider,
                "apiKey": self.search_api_key.name if self.search_api_key else None,
                "maxResults": self.search_max_results,
                "safeSearch": self.search_safe_search,
                "country": self.search_country,
                "language": self.search_language,
                "freshness": self.search_freshness,
            }
        if self.fetch_enabled:
            retval["fetch"] = {
                "maxCharacters": self.fetch_max_characters,
                "respectRobotsTxt": self.fetch_respect_robots_txt,
            }
        return retval

    @classmethod
    def get_cached_data_by_plugin(
        cls, plugin: PluginMeta, invalidate: bool = False
    ) -> Union["PluginDataWebsearch", None]:
        """
        Return a single instance of PluginDataWebsearch by plugin, with caching.

        :param plugin: The plugin whose data should be retrieved.
        :param invalidate: If True, invalidate the cache before retrieving.
        :return: The PluginDataWebsearch instance.
        :raises PluginDataWebsearch.DoesNotExist: If the plugin has no websearch data.
        """

        @cache_results()
        def data_by_plugin_id(plugin_id: int) -> Union["PluginDataWebsearch", None]:
            try:
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                raise cls.DoesNotExist(f"PluginDataWebsearch with plugin_id {plugin_id} does not exist.") from e

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
        Retrieve a model instance by primary key or by plugin, with caching.

        :param invalidate: If True, invalidate the cache for this query before retrieving the object.
        :param pk: The primary key of the model instance to retrieve.
        :param plugin: The PluginMeta instance associated with the data to retrieve.
        :returns: The model instance.
        :raises PluginDataWebsearch.DoesNotExist: If the plugin has no websearch data.
        """

        @cache_results()
        def _get_model_by_plugin_meta(plugin_id: int) -> Optional["PluginDataBase"]:
            try:
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                raise cls.DoesNotExist(f"PluginDataWebsearch with plugin_id {plugin_id} does not exist.") from e

        if invalidate and plugin:
            _get_model_by_plugin_meta.invalidate(plugin.id)  # type: ignore[union-attr]

        retval: Optional[PluginDataBase] = None
        if pk:
            retval = super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[assignment]
            charge_authorization(retval.record_locator, cls.__name__)  # type: ignore[union-attr]
        if plugin:
            retval = _get_model_by_plugin_meta(plugin.id)
            charge_authorization(retval.record_locator, cls.__name__)  # type: ignore[union-attr]
        return retval
