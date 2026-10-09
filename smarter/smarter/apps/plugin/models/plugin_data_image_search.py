"""
PluginDataImageSearch model for storing the configuration of an ImageSearchPlugin.

.. note::

    **Experimental.** The ImageSearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental.
"""

from typing import Any, Optional, Union

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from smarter.apps.plugin.manifest.models.image_search_plugin.const import (
    DEFAULT_API_KEY_SECRET_NAME,
    DEFAULT_CACHE_TTL,
    DEFAULT_COUNT,
    DEFAULT_TIMEOUT,
    MAX_CACHE_TTL,
    MAX_COUNT,
    MAX_DIMENSION,
    MAX_QUERY_LENGTH,
    MAX_TIMEOUT,
)
from smarter.apps.plugin.manifest.models.image_search_plugin.enum import (
    ImageSearchSafeSearch,
)
from smarter.apps.plugin.manifest.models.image_search_plugin.spec import (
    normalize_country,
    normalize_file_types,
    normalize_search_lang,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.policy import (
    DomainPolicy,
    WebsearchPolicyError,
    normalize_domains,
)
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .plugin_data_base import PluginDataBase
from .plugin_meta import PluginMeta

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])


def valid_or_default(normalize, value: Any, default: Optional[str]) -> Optional[str]:
    """
    Return a search parameter that the LLM set, normalized, or the default if it is empty or invalid.

    :param normalize: The parameter's normalizer, e.g. :func:`normalize_country`.
    :param value: The LLM's value.
    :param default: The plugin's own value.
    """
    try:
        return normalize(value) or default
    except ValueError:
        logger.debug("valid_or_default() ignored an invalid search parameter from the LLM: %s", value)
        return default


class PluginDataImageSearch(PluginDataBase):
    """
    Stores the configuration of an ImageSearchPlugin, which searches the Brave Image Search API and returns image urls.

    ``query_terms`` are appended to every query that the LLM sends. The search parameters
    (``count``, ``country``, ``search_lang``, ``safesearch`` and ``spellcheck``) map 1:1 to the
    Brave Image Search API's other query parameters. The filters
    (``file_type``, ``min_width``, ``min_height``, ``allowed_domains`` and ``blocked_domains``)
    are applied by Smarter to Brave's results. The Brave Search API key is stored in a Smarter
    Secret, which is referred to by name, and read when the plugin is called. If it is
    unavailable then the plugin returns no images, and logs a warning that explains how to
    create it.

    .. seealso::

        - :class:`PluginDataBase`
        - :py:class:`smarter.apps.plugin.plugin.image_search.ImageSearchPlugin`
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Plugin Image Search Data"
        verbose_name_plural = "Plugin Image Search Data"

    api_key_secret_name = models.CharField(
        max_length=255,
        default=DEFAULT_API_KEY_SECRET_NAME,
        help_text="The name of the Secret that contains the Brave Search API key.",
    )
    query_terms = models.CharField(
        max_length=MAX_QUERY_LENGTH,
        blank=True,
        null=True,
        help_text="Search terms appended to every query that the LLM sends.",
    )
    llm_search_params = models.BooleanField(
        default=False,
        help_text="Whether the LLM may set every search parameter in each tool call. The others are then defaults.",
    )
    count = models.PositiveSmallIntegerField(
        default=DEFAULT_COUNT,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_COUNT)],
        help_text="The maximum number of images per search.",
    )
    country = models.CharField(
        max_length=3, blank=True, null=True, help_text="A two letter country code, or all for worldwide results."
    )
    search_lang = models.CharField(
        max_length=8, blank=True, null=True, help_text="Prefer images from content in this language, e.g. en."
    )
    safesearch = models.CharField(
        max_length=8,
        choices=[(value, value) for value in ImageSearchSafeSearch.all()],
        default=ImageSearchSafeSearch.STRICT.value,
        help_text="Adult content filtering: strict or off.",
    )
    spellcheck = models.BooleanField(default=True, help_text="Whether Brave may correct the spelling of the query.")
    file_type = models.CharField(
        max_length=64, blank=True, null=True, help_text="Only images of these file types, e.g. jpg|png."
    )
    min_width = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_DIMENSION)],
        help_text="Only images at least this many pixels wide. Images of unknown width are skipped.",
    )
    min_height = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_DIMENSION)],
        help_text="Only images at least this many pixels high. Images of unknown height are skipped.",
    )
    allowed_domains = models.JSONField(
        default=list,
        blank=True,
        encoder=json.SmarterJSONEncoder,
        help_text="If not empty, only images from web pages on these domains, and their subdomains.",
    )
    blocked_domains = models.JSONField(
        default=list,
        blank=True,
        encoder=json.SmarterJSONEncoder,
        help_text="Never images on these domains, nor from web pages on them, including their subdomains.",
    )
    validate_urls = models.BooleanField(
        default=True, help_text="Only return image urls that respond to a request with HTTP 200."
    )
    timeout = models.PositiveSmallIntegerField(
        default=DEFAULT_TIMEOUT,
        validators=[MinValueValidator(1), MaxValueValidator(MAX_TIMEOUT)],
        help_text="Seconds to wait for each web request.",
    )
    cache_ttl = models.PositiveIntegerField(
        default=DEFAULT_CACHE_TTL,
        validators=[MaxValueValidator(MAX_CACHE_TTL)],
        help_text="Seconds to cache search results. 0 disables caching.",
    )

    @property
    def return_data_keys(self) -> list[str]:
        """The plugin returns a list of image urls."""
        return []

    @property
    def domain_policy(self) -> DomainPolicy:
        """The plugin's domain policy, which applies to the web pages that images come from."""
        return DomainPolicy.create(allowed=self.allowed_domains, blocked=self.blocked_domains)

    @property
    def file_types(self) -> list[str]:
        """The permitted file types, e.g. ``['jpg', 'png']``.

        Empty if any file type is permitted.
        """
        return [item for item in (self.file_type or "").split("|") if item]

    def search_params(
        self, query: Optional[str] = None, count: Optional[int] = None, llm_params: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Return the Brave Image Search API query parameters.

        :param query: The LLM's search query, to which ``query_terms`` are appended.
        :param count: The number of images, which defaults to ``count``. It may not exceed
            ``count``, or, if ``llm_search_params``, :data:`MAX_COUNT`.
        :param llm_params: The search parameters that the LLM set in its tool call: ``country``,
            ``search_lang``, ``safesearch`` and ``spellcheck``. They are used only if
            ``llm_search_params``, and invalid values are ignored, in favor of the plugin's own.
        :return: The query parameters, without empty values.
        """
        terms = " ".join(term for term in (query, self.query_terms) if term)
        country, search_lang, safesearch, spellcheck = self.country, self.search_lang, self.safesearch, self.spellcheck
        if self.llm_search_params and llm_params:
            country = valid_or_default(normalize_country, llm_params.get("country"), country)
            search_lang = valid_or_default(normalize_search_lang, llm_params.get("search_lang"), search_lang)
            if llm_params.get("safesearch") in ImageSearchSafeSearch.all():
                safesearch = llm_params["safesearch"]
            if isinstance(llm_params.get("spellcheck"), bool):
                spellcheck = llm_params["spellcheck"]
        max_count = MAX_COUNT if self.llm_search_params else self.count
        retval: dict[str, Any] = {
            "q": terms[:MAX_QUERY_LENGTH] or None,
            "count": max(1, min(count or self.count, max_count)),
            "country": country.upper() if country else None,
            "search_lang": search_lang,
            "safesearch": safesearch,
            "spellcheck": "true" if spellcheck else "false",
        }
        return {key: value for key, value in retval.items() if value}

    # pylint: disable=too-many-branches
    def validate(self) -> bool:
        """
        Validate the configuration.

        :raises SmarterValueError: If a value is out of range, or a search parameter or filter is not permitted.
        """
        super().validate()
        if not isinstance(self.api_key_secret_name, str) or not self.api_key_secret_name.strip():
            raise SmarterValueError("api_key_secret_name must be the name of a Secret.")
        if self.safesearch not in ImageSearchSafeSearch.all():
            raise SmarterValueError(f"safesearch must be one of {ImageSearchSafeSearch.all()}: {self.safesearch}")
        for name, value, low, high, optional in (
            ("count", self.count, 1, MAX_COUNT, False),
            ("min_width", self.min_width, 1, MAX_DIMENSION, True),
            ("min_height", self.min_height, 1, MAX_DIMENSION, True),
            ("timeout", self.timeout, 1, MAX_TIMEOUT, False),
            ("cache_ttl", self.cache_ttl, 0, MAX_CACHE_TTL, False),
        ):
            if optional and value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise SmarterValueError(f"{name} must be an integer from {low} to {high}: {value}")
        try:
            normalize_country(self.country)
            normalize_search_lang(self.search_lang)
            normalize_file_types(self.file_type)
            normalize_domains(self.allowed_domains)
            normalize_domains(self.blocked_domains)
        except (ValueError, WebsearchPolicyError) as e:
            raise SmarterValueError(str(e)) from e
        return True

    def save(self, *args, **kwargs):
        """Normalize the domain lists, validate, and save."""
        try:
            self.allowed_domains = list(normalize_domains(self.allowed_domains))
            self.blocked_domains = list(normalize_domains(self.blocked_domains))
        except WebsearchPolicyError as e:
            raise SmarterValueError(str(e)) from e
        super().save(*args, **kwargs)

    def data(self, params: Optional[dict] = None) -> dict[str, Any]:
        """
        Return the configuration of the plugin, without its api key.

        :param params: Optional parameters for future extensibility (currently unused).
        :return: The configuration.
        """
        return {
            "llm_search_params": self.llm_search_params,
            "search_params": self.search_params(),
            "file_types": self.file_types,
            "allowed_domains": self.allowed_domains,
            "blocked_domains": self.blocked_domains,
            "validate_urls": self.validate_urls,
        }

    def sanitized_return_data(self, params: Optional[dict] = None) -> dict[str, Any]:
        """
        Return the configuration of the plugin, without its api key.

        The image urls are returned by
        :py:meth:`smarter.apps.plugin.plugin.image_search.ImageSearchPlugin.tool_call_fetch_plugin_response`.
        """
        return self.data(params)

    def manifest_data(self) -> dict[str, Any]:
        """
        Return the ``spec.imageSearchData`` section of the plugin manifest.

        :return: The manifest section, in camelCase.
        """
        return {
            "apiKey": self.api_key_secret_name,
            "queryTerms": self.query_terms or None,
            "llmSearchParams": self.llm_search_params,
            "searchParams": {
                "count": self.count,
                "country": self.country or None,
                "searchLang": self.search_lang or None,
                "safesearch": self.safesearch,
                "spellcheck": self.spellcheck,
            },
            "filters": {
                "fileType": self.file_type or None,
                "minWidth": self.min_width,
                "minHeight": self.min_height,
                "allowedDomains": self.allowed_domains or None,
                "blockedDomains": self.blocked_domains or None,
            },
            "validateUrls": self.validate_urls,
            "timeout": self.timeout,
            "cacheTtl": self.cache_ttl,
        }

    @classmethod
    def get_cached_data_by_plugin(
        cls, plugin: PluginMeta, invalidate: bool = False
    ) -> Union["PluginDataImageSearch", None]:
        """
        Return a single instance of PluginDataImageSearch by plugin, with caching.

        :param plugin: The plugin whose data should be retrieved.
        :param invalidate: If True, invalidate the cache before retrieving.
        :return: The PluginDataImageSearch instance.
        :raises PluginDataImageSearch.DoesNotExist: If the plugin has no image search data.
        """

        @cache_results()
        def data_by_plugin_id(plugin_id: int) -> Union["PluginDataImageSearch", None]:
            try:
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                raise cls.DoesNotExist(f"PluginDataImageSearch with plugin_id {plugin_id} does not exist.") from e

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
        :raises PluginDataImageSearch.DoesNotExist: If the plugin has no image search data.
        """

        @cache_results()
        def _get_model_by_plugin_meta(plugin_id: int) -> Optional["PluginDataBase"]:
            try:
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                raise cls.DoesNotExist(f"PluginDataImageSearch with plugin_id {plugin_id} does not exist.") from e

        if invalidate and plugin:
            _get_model_by_plugin_meta.invalidate(plugin.id)  # type: ignore[union-attr]

        retval: Optional[PluginDataBase] = None
        if pk:
            retval = super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[assignment]
        if plugin:
            retval = _get_model_by_plugin_meta(plugin.id)  # type: ignore[reportAttributeAccessIssue]
        return retval
