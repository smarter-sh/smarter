"""
A Plugin that searches for images with the Brave Image Search API, and returns a JSON list of image urls.

.. note::

    This is a complex AI resource that exists within the following class hierarchy

    1. Smarter Secret: a Brave Search API key.
    2. Smarter ImageSearch Plugin: The plugin that configures the image search parameters and filters.
    3. Smarter LLMClient: The prompting resource (LLMClient, Agent, Workflow unit, etcetera) that includes the ImageSearch Plugin.

.. note::

    The ImageSearchPlugin is powered by the
    `Brave Image Search API <https://api-dashboard.search.brave.com/app/documentation/image-search/get-started>`__.
    Its manifest's ``spec.imageSearchData.searchParams`` map 1:1 to the API's query parameters,
    and its ``spec.imageSearchData.filters`` are applied by Smarter to the API's results. The
    LLM supplies the query, and optionally a smaller number of images. The tool returns a JSON
    list of strings, e.g. ``["https://example.com/cat.png"]``:

    - Only the https urls of the original images are returned, never Brave's thumbnails.
    - Images are filtered by file type, minimum size, and the domain of the web page that
      they come from.
    - Unless ``validateUrls`` is false, only urls that respond to a HEAD request with HTTP
      200, and not with a web page, are returned. Requests are made with
      :py:func:`smarter.apps.plugin.plugin.safe_http.fetch`, so only public hosts are contacted.
    - If the Brave Search API key is unavailable, or the search fails, the tool returns an
      empty list, and logs a warning. When the api key is missing, the warning explains how
      to create it.

.. sphinx note: these are relative to the rst doc that calls automodule on this file.

.. literalinclude:: ../../../../../smarter/smarter/apps/plugin/data/sample-plugins/image-search-safe.yaml
    :language: yaml
    :caption: Example ImageSearch Plugin Manifest

.. note::

    **Experimental.** The ImageSearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental.
"""

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Type, Union
from urllib.parse import unquote, urlparse

from django.core.cache import cache

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClass,
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
    SAMPluginSpecKeys,
)
from smarter.apps.plugin.manifest.models.common.plugin.metadata import (
    SAMPluginCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.plugin.spec import (
    SAMPluginCommonSpecPrompt,
    SAMPluginCommonSpecSelector,
)
from smarter.apps.plugin.manifest.models.common.plugin.status import (
    SAMPluginCommonStatus,
)
from smarter.apps.plugin.manifest.models.image_search_plugin.const import (
    BRAVE_IMAGE_SEARCH_URL,
    CREDENTIALS_HELP,
    MANIFEST_KIND,
    MAX_COUNT,
    MAX_QUERY_LENGTH,
)
from smarter.apps.plugin.manifest.models.image_search_plugin.enum import (
    FILE_TYPE_CONTENT_TYPES,
    FILE_TYPE_EXTENSIONS,
    ImageSearchSafeSearch,
)
from smarter.apps.plugin.manifest.models.image_search_plugin.model import (
    SAMImageSearchPlugin,
)
from smarter.apps.plugin.manifest.models.image_search_plugin.spec import (
    ImageSearchData,
    ImageSearchFilters,
    ImageSearchParams,
    SAMImageSearchPluginSpec,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.policy import DomainPolicy
from smarter.apps.plugin.models import PluginDataImageSearch
from smarter.apps.plugin.serializers import PluginImageSearchSerializer
from smarter.apps.plugin.signals import plugin_called, plugin_responded
from smarter.apps.secret.models import Secret
from smarter.common.api import SmarterApiVersions
from smarter.common.conf import settings_defaults
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json, logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys

from .base import PluginBase, SmarterPluginError
from .safe_http import SafeHttpError, fetch
from .websearch_providers import SearchProvider


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

CACHE_KEY_PREFIX = "smarter.image_search"
MAX_VALIDATION_WORKERS = 10
MAX_RESPONSE_BYTES = 5_000_000
BRAVE_MAX_COUNT = 200
"""The most images that one Brave Image Search API request returns."""
BRAVE_MIN_COUNT = 50
"""The fewest images to request from Brave, since many may be filtered out.

Brave bills per request, not per image.
"""
OVERFETCH_FACTOR = 5
"""Request at least this many times the number of images wanted from Brave, since many may be filtered out."""
LLM_SEARCH_PARAMS = ("country", "search_lang", "safesearch", "spellcheck")
"""The search parameters, besides query and count, that the LLM may set if the plugin's llmSearchParams is true."""
REJECTED_CONTENT_TYPE_PREFIXES = ("text/", "application/json", "application/xml", "application/xhtml")
"""Content-Types of responses that are not images, e.g. the html page of a hotlink protected image."""


class SmarterImageSearchPluginError(SmarterPluginError):
    """Base class for all ImageSearch plugin errors."""


@dataclass(frozen=True)
class ImageResult:
    """
    An image found by the Brave Image Search API.

    :ivar url: The url of the original image.
    :ivar page_url: The url of the web page on which the image appears, if known.
    :ivar width: The image width in pixels, if known.
    :ivar height: The image height in pixels, if known.
    """

    url: str
    page_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


def is_https_url(url: Any) -> bool:
    """
    Return True if the url is an https url with a host.

    :param url: The url.
    """
    if not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.hostname)


def file_type_of_url(url: str) -> Optional[str]:
    """
    Return the file type of an image url, from its file extension.

    :param url: The image url.
    :return: The file type, e.g. ``jpg``, or None if the url has no known image file extension.
    """
    extension = os.path.splitext(unquote(urlparse(url).path))[1].lstrip(".").lower()
    return FILE_TYPE_EXTENSIONS.get(extension)


def file_type_of_content_type(content_type: Optional[str]) -> Optional[str]:
    """
    Return the file type of a response, from its Content-Type.

    :param content_type: The media type, e.g. ``image/png``.
    :return: The file type, e.g. ``png``, or None if the Content-Type is not a known image type.
    """
    return FILE_TYPE_CONTENT_TYPES.get((content_type or "").split(";", 1)[0].strip().lower())


def as_dimension(value: Any) -> Optional[int]:
    """Return an image width or height reported by the API as a positive int, or None."""
    if isinstance(value, bool):
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def parse_brave_images(data: Any) -> list[ImageResult]:
    """
    Parse a Brave Image Search API response.

    :param data: The response, e.g. ``{"results": [{"url": "https://page", "properties": {"url": "https://image.png"}}]}``.
    :return: The images, in Brave's order. Results without an original image url are skipped.
    """
    results = data.get("results") if isinstance(data, dict) else None
    retval: list[ImageResult] = []
    for item in results if isinstance(results, list) else []:
        if not isinstance(item, dict):
            continue
        properties = item.get("properties") if isinstance(item.get("properties"), dict) else {}
        url = properties.get("url")
        if not isinstance(url, str) or not url.strip():
            continue
        page_url = item.get("url")
        retval.append(
            ImageResult(
                url=url.strip(),
                page_url=page_url if isinstance(page_url, str) and page_url.strip() else None,
                width=as_dimension(properties.get("width")),
                height=as_dimension(properties.get("height")),
            )
        )
    return retval


def describe_brave_error(error: SafeHttpError) -> str:
    """Describe a failed Brave Image Search API request, without disclosing the api key."""
    if error.status_code in (401, 403):
        return "the Brave Search API rejected the api key, or the api key's plan does not include image search."
    if error.status_code == 422:
        return "the Brave Search API rejected the search parameters."
    if error.status_code == 429:
        return "the Brave Search API rate limit, or the plan's monthly quota, was exceeded."
    if error.status_code:
        return f"the Brave Search API responded with HTTP {error.status_code}."
    return "the Brave Search API could not be reached."


def image_content_type(url: str, timeout: float) -> Optional[str]:
    """
    Return the Content-Type of an image url, if a HEAD request to it responds with HTTP 200 and not with a web page.

    This runs in worker threads, so it neither logs nor touches the database: the waffle
    switched logger reads its switch from the database, which would open a connection per thread.

    :param url: The https url of an image.
    :param timeout: Seconds to wait for each request.
    :return: The Content-Type, which is empty if the server did not send one, or None if the url is not available.
    """
    try:
        response = fetch(url, method="HEAD", timeout=timeout)
    except SafeHttpError:
        return None
    content_type = response.content_type
    if content_type.startswith(REJECTED_CONTENT_TYPE_PREFIXES):
        return None
    return content_type


class ImageSearchPlugin(PluginBase):
    """
    Implements a plugin that searches for images with the Brave Image Search API, and returns a list of image urls.

    **Key Features:**

        - Image search via the Brave Image Search API, whose query parameters (count, country,
          language, safe search and spellcheck) are set by the manifest.
        - Filters for file type, minimum size, and the websites that images come from.
        - Returns only https urls, which, by default, are validated to respond with HTTP 200.
        - Returns an empty list, and logs how to create it, when its api key is missing.
        - Caching of search results.

    **Example Use Cases:**

        - Kid-friendly image search, with strict safe search, from Wikimedia Commons.
        - Technical diagrams, or SVG images, to illustrate documentation.
        - High resolution black and white photographs.

    .. seealso::

        :class:`PluginBase`
        :class:`PluginDataImageSearch`
    """

    SAMPluginType = SAMImageSearchPlugin

    _manifest: Optional[SAMImageSearchPlugin] = None
    _metadata_class: str = SAMPluginCommonMetadataClass.IMAGE_SEARCH.value
    _plugin_data: Optional[PluginDataImageSearch] = None
    _plugin_data_serializer: Optional[PluginImageSearchSerializer] = None

    def __init__(
        self,
        *args,
        manifest: Optional[SAMImageSearchPlugin] = None,
        **kwargs,
    ):
        super().__init__(*args, manifest=manifest, **kwargs)

    @property
    def kind(self) -> str:
        """
        Returns the kind identifier for this plugin.

        :returns: ``ImageSearchPlugin``
        :rtype: str
        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMImageSearchPlugin]:
        """
        Return the Pydantic model representation of the plugin manifest.

        If the manifest has not been set but the plugin is in a ready state, it is
        reconstructed from the Django ORM data, using :meth:`to_json`.

        :return: The manifest, or ``None`` if unavailable.
        :rtype: Optional[SAMImageSearchPlugin]
        """
        if not self._manifest and self.ready:
            self._manifest = SAMImageSearchPlugin(**self.to_json())  # type: ignore[call-arg]
        return self._manifest

    @property
    def plugin_data(self) -> Optional[PluginDataImageSearch]:
        """
        Return the plugin data as a Django ORM instance.

        :return: The image search configuration, or ``None`` if unavailable.
        :rtype: Optional[PluginDataImageSearch]
        """
        if self._plugin_data:
            return self._plugin_data
        if not self.plugin_meta:
            return None
        try:
            self._plugin_data = PluginDataImageSearch.get_cached_object(plugin=self.plugin_meta)  # type: ignore[assignment]
            return self._plugin_data
        except PluginDataImageSearch.DoesNotExist:
            logger.debug(
                "%s.plugin_data() no existing PluginDataImageSearch found in database for plugin_meta: %s",
                self.formatted_class_name,
                self.plugin_meta,
            )
        if self._manifest:
            # the Plugin exists in the database, AND we've received manifest data from the cli.
            self._plugin_data = PluginDataImageSearch(**self.plugin_data_django_model)  # type: ignore[arg-type]
            self._plugin_data.save()
        return self._plugin_data

    @property
    def plugin_data_class(self) -> Type[PluginDataImageSearch]:
        """Return the Django ORM class used for image search plugin data."""
        return PluginDataImageSearch

    @property
    def plugin_data_serializer(self) -> Optional[PluginImageSearchSerializer]:
        """Return the serializer instance for the plugin's image search data."""
        if not self._plugin_data_serializer:
            self._plugin_data_serializer = PluginImageSearchSerializer(self.plugin_data)
        return self._plugin_data_serializer

    @property
    def plugin_data_serializer_class(self) -> Type[PluginImageSearchSerializer]:
        """Return the plugin data serializer class."""
        return PluginImageSearchSerializer

    @property
    def plugin_data_django_model(self) -> Optional[dict[str, Any]]:
        """
        Transform the Pydantic manifest into a Django ORM-compatible dictionary.

        :return: A dictionary of :class:`PluginDataImageSearch` fields, or ``None`` if the manifest is not available.
        """
        if not self._manifest:
            return None
        data: ImageSearchData = self._manifest.spec.imageSearchData
        params: ImageSearchParams = data.searchParams
        filters: ImageSearchFilters = data.filters
        return {
            "plugin": self.plugin_meta,
            "description": self._manifest.metadata.description,
            "api_key_secret_name": data.apiKey,
            "query_terms": data.queryTerms,
            "llm_search_params": data.llmSearchParams,
            "count": params.count,
            "country": params.country,
            "search_lang": params.searchLang,
            "safesearch": params.safesearch,
            "spellcheck": params.spellcheck,
            "file_type": filters.fileType,
            "min_width": filters.minWidth,
            "min_height": filters.minHeight,
            "allowed_domains": list(filters.allowedDomains or []),
            "blocked_domains": list(filters.blockedDomains or []),
            "validate_urls": data.validateUrls,
            "timeout": data.timeout,
            "cache_ttl": data.cacheTtl,
        }

    @property
    def tool_description(self) -> str:
        """The tool description presented to the LLM: what the plugin does, and how to use it."""
        plugin_data = self.plugin_data
        if not plugin_data:
            return ""
        sentences = [plugin_data.description.strip()] if plugin_data.description else []
        sentences.append(
            "Set query to search for images. Returns a JSON list of image urls, which is empty if no images were found."
        )
        if plugin_data.llm_search_params:
            sentences.append(
                "Optionally, set count, country, search_lang, safesearch and spellcheck to tailor the search."
            )
        return " ".join(sentences)

    @property
    def custom_tool(self) -> Optional[dict[str, Any]]:  # type: ignore[override]
        """
        Return the plugin tool definition for OpenAI function calling.

        :return: The tool definition, or ``None`` if the plugin is not ready.

        **Example:**

        .. code-block:: python

            tool = {
                "type": "function",
                "function": {
                    "name": "smarter_plugin_0000000042",
                    "description": "Kid-friendly image search. Set query to search for images ...",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "maxLength": 400, "description": "..."},
                            "count": {"type": "integer", "minimum": 1, "maximum": 10, "description": "..."},
                        },
                        "required": ["query"],
                    },
                },
            }
        """
        if not self.ready or not self.plugin_data:
            return None
        plugin_data = self.plugin_data
        properties: dict[str, Any] = {
            "query": {
                "type": "string",
                "maxLength": MAX_QUERY_LENGTH,
                "description": "The image search query, e.g. 'golden retriever puppy'.",
            },
            "count": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_COUNT if plugin_data.llm_search_params else plugin_data.count,
                "description": f"Optional. The maximum number of images. Defaults to {plugin_data.count}.",
            },
        }
        if plugin_data.llm_search_params:
            properties.update(
                {
                    "country": {
                        "type": "string",
                        "description": (
                            "Optional. Prefer images from this country, a two letter country code, e.g. us, or all. "
                            f"Defaults to {plugin_data.country or 'us'}."
                        ),
                    },
                    "search_lang": {
                        "type": "string",
                        "description": (
                            "Optional. Prefer images from content in this language, e.g. en or pt-br. "
                            f"Defaults to {plugin_data.search_lang or 'en'}."
                        ),
                    },
                    "safesearch": {
                        "type": "string",
                        "enum": ImageSearchSafeSearch.all(),
                        "description": f"Optional. Adult content filtering. Defaults to {plugin_data.safesearch}.",
                    },
                    "spellcheck": {
                        "type": "boolean",
                        "description": (
                            "Optional. Whether the search engine may correct the spelling of the query. "
                            f"Defaults to {'true' if plugin_data.spellcheck else 'false'}."
                        ),
                    },
                }
            )
        return {
            "type": "function",
            "function": {
                "name": self.function_calling_identifier,
                "description": self.tool_description,
                "parameters": {"type": "object", "properties": properties, "required": ["query"]},
            },
        }

    @classmethod
    def example_manifest(cls, kwargs: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        """
        Use Pydantic models to generate an example manifest for an ImageSearchPlugin.

        :param kwargs: Optional keyword arguments to customize the example manifest.
        :return: An example manifest as a dictionary.

        See Also:

        - :class:`SAMImageSearchPlugin`
        - ``smarter/apps/plugin/data/sample-plugins/image-search-*.yaml`` for more examples.
        """
        metadata = SAMPluginCommonMetadata(
            name="safe_image_search",
            description="Finds kid-friendly, freely licensed images from Wikimedia Commons.",
            version="0.1.0",
            tags=["imagesearch", "kid-friendly"],
            annotations=[
                {"smarter.sh/created_by": "smarter_image_search_plugin_broker"},
                {"smarter.sh/plugin": "safe_image_search"},
            ],
            pluginClass=SAMPluginCommonMetadataClassValues.IMAGE_SEARCH.value,
        )
        selector = SAMPluginCommonSpecSelector(
            directive=SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value,
            searchTerms=["image", "picture", "photo", "show me"],
        )
        prompt = SAMPluginCommonSpecPrompt(
            provider=settings_defaults.LLM_DEFAULT_PROVIDER,
            systemRole="You are a friendly assistant for children. Show images that help to explain your answers.",
            model=settings_defaults.LLM_DEFAULT_MODEL,
            temperature=settings_defaults.LLM_DEFAULT_TEMPERATURE,
            maxTokens=settings_defaults.LLM_DEFAULT_MAX_TOKENS,
        )
        spec = SAMImageSearchPluginSpec(
            selector=selector,
            prompt=prompt,
            imageSearchData=ImageSearchData(
                searchParams=ImageSearchParams(count=5, safesearch="strict"),
                filters=ImageSearchFilters(minWidth=400, allowedDomains=["wikimedia.org"]),
            ),
        )
        status = SAMPluginCommonStatus(
            accountNumber="1234567890",
            username="example_user",
            recordLocator="abc123def456",
            created=datetime(2024, 1, 1, 0, 0, 0),
            modified=datetime(2024, 1, 1, 0, 0, 0),
        )
        sam_image_search_plugin = SAMImageSearchPlugin(
            apiVersion=SmarterApiVersions.V1,
            kind=MANIFEST_KIND,
            metadata=metadata,
            spec=spec,
            status=status,
        )
        return json.loads(sam_image_search_plugin.model_dump_json())

    # -------------------------------------------------------------------------
    # tool calls
    # -------------------------------------------------------------------------
    def api_key(self) -> Optional[str]:
        """
        Return the Brave Search API key, from a Secret that the plugin's user may read.

        If it is unavailable, a warning explains how to create it.

        :return: The api key, or None if there is no such Secret that the user may read.
        """
        plugin_data: PluginDataImageSearch = self.plugin_data  # type: ignore[assignment]
        name = plugin_data.api_key_secret_name
        user = self.user or (self.user_profile.user if self.user_profile else None)
        secret = Secret.objects.filter(name=name).with_read_permission_for(user).first() if user else None  # type: ignore[attr-defined]
        value = None
        if isinstance(secret, Secret):
            try:
                value = secret.get_secret() or None
            except SmarterValueError as e:
                base_logger.error(
                    "%s.api_key() the Secret %s could not be read: %s", self.formatted_class_name, name, e
                )
        if not value:
            base_logger.warning(
                "%s plugin %s cannot search for images, and returns an empty list: the Brave Search API key Secret "
                "%s is missing or not readable. %s",
                self.formatted_class_name,
                self.name,
                name,
                CREDENTIALS_HELP,
            )
        return value

    def cache_key(self, search_params: dict[str, Any]) -> str:
        """Return a cache key that is unique to the plugin, and the search parameters."""
        plugin_data = self.plugin_data
        payload = json.dumps(
            {"plugin_data": plugin_data.pk if plugin_data else None, **search_params}, sort_keys=True, default=str
        )
        return f"{CACHE_KEY_PREFIX}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"

    def brave_images(self, api_key: str, search_params: dict[str, Any]) -> list[ImageResult]:
        """
        Search the Brave Image Search API.

        More images than wanted are requested, since many may be filtered out. The allowed
        domains are added to the query as ``site:`` operators, so that Brave searches them. The
        blocked domains are not, since Brave returns no results for some queries with several
        ``-site:`` operators: :py:meth:`filtered_images` removes their images instead.

        :param api_key: The Brave Search API key.
        :param search_params: The query parameters, from :py:meth:`PluginDataImageSearch.search_params`.
        :return: The images found, or an empty list if the search fails.
        """
        plugin_data: PluginDataImageSearch = self.plugin_data  # type: ignore[assignment]
        params = dict(search_params)
        operators = SearchProvider.site_operators(DomainPolicy.create(allowed=plugin_data.allowed_domains))
        if operators:
            params["q"] = f"{params['q']} {operators}"
        params["count"] = min(BRAVE_MAX_COUNT, max(BRAVE_MIN_COUNT, params["count"] * OVERFETCH_FACTOR))
        try:
            response = fetch(
                BRAVE_IMAGE_SEARCH_URL,
                headers={"Accept": "application/json", "X-Subscription-Token": api_key},
                params=params,
                timeout=plugin_data.timeout,
                max_bytes=MAX_RESPONSE_BYTES,
            )
        except SafeHttpError as e:
            base_logger.warning(
                "%s plugin %s image search failed: %s", self.formatted_class_name, self.name, describe_brave_error(e)
            )
            return []
        try:
            return parse_brave_images(json.loads(response.content))
        except (ValueError, UnicodeDecodeError):
            base_logger.warning(
                "%s plugin %s image search failed: the Brave Search API returned an invalid response.",
                self.formatted_class_name,
                self.name,
            )
            return []

    def filtered_images(self, images: list[ImageResult]) -> list[ImageResult]:
        """
        Apply the plugin's filters to the images, except for file types that only a request can determine.

        Images are removed if their url is not https or is a duplicate, their web page is not
        permitted by the domain policy, the image itself is on a blocked domain, they are smaller
        than the minimum size, or of unknown size when a minimum is set, or their url's file
        extension is not a permitted file type. Blocked domains apply to the image too, since a
        website's localized pages, e.g. on example.fr, often serve images from its main domain. Images without a file extension are kept
        for :py:meth:`validated_urls`, if url validation is enabled.

        :param images: The images found.
        :return: The images that pass the filters, in order.
        """
        plugin_data: PluginDataImageSearch = self.plugin_data  # type: ignore[assignment]
        policy = plugin_data.domain_policy
        blocked = DomainPolicy.create(blocked=plugin_data.blocked_domains)
        file_types = plugin_data.file_types
        retval: list[ImageResult] = []
        seen: set[str] = set()
        for image in images:
            if not is_https_url(image.url) or image.url in seen:
                continue
            if (policy.allowed or policy.blocked) and not (image.page_url and policy.permits_url(image.page_url)):
                continue
            if not blocked.permits_url(image.url):
                continue
            if plugin_data.min_width and (image.width or 0) < plugin_data.min_width:
                continue
            if plugin_data.min_height and (image.height or 0) < plugin_data.min_height:
                continue
            if file_types:
                file_type = file_type_of_url(image.url)
                if file_type not in file_types and not (file_type is None and plugin_data.validate_urls):
                    continue
            seen.add(image.url)
            retval.append(image)
        return retval

    def validated_urls(self, images: list[ImageResult], count: int) -> list[str]:
        """
        Return the urls of up to ``count`` images, in order, that respond with HTTP 200, if validation is enabled.

        Images whose file type could not be determined from their url are checked against the
        permitted file types by the Content-Type of their response.

        :param images: The filtered images.
        :param count: The maximum number of urls to return.
        """
        plugin_data: PluginDataImageSearch = self.plugin_data  # type: ignore[assignment]
        if not plugin_data.validate_urls:
            return [image.url for image in images[:count]]
        file_types = plugin_data.file_types
        retval: list[str] = []
        # validate in batches, so that no more requests are made than needed.
        for start in range(0, len(images), MAX_VALIDATION_WORKERS):
            batch = images[start : start + MAX_VALIDATION_WORKERS]
            with ThreadPoolExecutor(max_workers=len(batch)) as executor:
                content_types = list(
                    executor.map(lambda image: image_content_type(image.url, plugin_data.timeout), batch)
                )
            for image, content_type in zip(batch, content_types):
                if content_type is None:
                    logger.debug(
                        "%s.validated_urls() %s is not available, or is not an image.",
                        self.formatted_class_name,
                        image.url,
                    )
                    continue
                if file_types and file_type_of_url(image.url) is None:
                    if file_type_of_content_type(content_type) not in file_types:
                        continue
                retval.append(image.url)
                if len(retval) >= count:
                    return retval
        return retval

    def search(self, query: str, count: Any = None, llm_params: Optional[dict[str, Any]] = None) -> list[str]:
        """
        Search for images.

        :param query: The search query.
        :param count: The maximum number of images, up to the plugin's ``count``, or, if the
            LLM may set every search parameter, up to :data:`MAX_COUNT`.
        :param llm_params: The other search parameters that the LLM set, which are used only
            if the plugin's ``llmSearchParams`` is true. See
            :py:meth:`PluginDataImageSearch.search_params`.
        :return: The https urls of the images found. Empty if none were found, the api key is
            missing, or the search failed.
        """
        plugin_data: PluginDataImageSearch = self.plugin_data  # type: ignore[assignment]
        query = " ".join(query.split())[:MAX_QUERY_LENGTH]
        if isinstance(count, bool) or not isinstance(count, int):
            count = None
        search_params = plugin_data.search_params(query=query, count=count, llm_params=llm_params)
        key = self.cache_key(search_params)
        urls = cache.get(key) if plugin_data.cache_ttl else None
        if urls is not None:
            return urls
        api_key = self.api_key()
        if not api_key:
            return []
        images = self.filtered_images(self.brave_images(api_key, search_params))
        urls = self.validated_urls(images, search_params["count"])
        if urls and plugin_data.cache_ttl:
            cache.set(key, urls, plugin_data.cache_ttl)
        return urls

    def tool_call_fetch_plugin_response(
        self, function_args: Union[dict[str, Any], str, None]
    ) -> Union[dict, list, str]:
        """
        Search for images in response to a tool call.

        **Example tool call payload:**

        .. code-block:: python

            "arguments": "{\\"query\\": \\"bald eagle\\", \\"count\\": 3}"
            "arguments": "{\\"query\\": \\"tour de france\\", \\"country\\": \\"fr\\", \\"search_lang\\": \\"fr\\"}"

        **Example response:**

        .. code-block:: python

            ["https://upload.wikimedia.org/wikipedia/commons/1/1a/bald-eagle.jpg", "https://..."]

        :param function_args: The function arguments, as a dict or as the JSON string sent by OpenAI.
        :return: A list of https image urls. Empty if the arguments are invalid, no images were
            found, the api key is missing, or the search failed.
        :raises SmarterImageSearchPluginError: If the plugin is not ready, or has no data.
        """
        if not self.ready:
            raise SmarterImageSearchPluginError(f"Plugin {self.name} is not in a ready state.")
        if not self.plugin_data:
            raise SmarterImageSearchPluginError(f"Plugin {self.name} is not ready. Plugin data is not available.")

        if isinstance(function_args, str):
            try:
                function_args = json.loads(function_args) if function_args.strip() else {}
            except json.JSONDecodeError:
                function_args = {}
        if not isinstance(function_args, dict):
            function_args = {}
        query = function_args.get("query")
        if not isinstance(query, str) or not query.strip():
            logger.warning("%s.tool_call_fetch_plugin_response() query is missing.", self.formatted_class_name)
            return []

        plugin_called.send(sender=self.tool_call_fetch_plugin_response, plugin=self, inquiry_type="search")
        llm_params = {key: function_args.get(key) for key in LLM_SEARCH_PARAMS if key in function_args}
        retval = self.search(query, count=function_args.get("count"), llm_params=llm_params)
        plugin_responded.send(
            sender=self.tool_call_fetch_plugin_response, plugin=self, inquiry_type="search", response=retval
        )
        return retval

    def to_json(self, version: str = "v1") -> Optional[dict[str, Any]]:
        """
        Serialize the ImageSearchPlugin to a JSON-compatible dictionary suitable for Pydantic import.

        :param version: The API version to use for serialization. Only "v1" is supported.
        :returns: A dictionary representing the plugin in JSON format, or ``None`` if the plugin is not ready.
        :raises SmarterPluginError: If an unsupported version is specified.
        """
        if not self.ready:
            return None
        if version != "v1":
            raise SmarterPluginError(f"Invalid version: {version}")
        retval = super().to_json(version=version)
        if not isinstance(retval, dict) or not self.plugin_data:
            raise SmarterPluginError(
                f"{self.formatted_class_name}.to_json() error: {self.name} plugin data is not a valid JSON object."
            )
        spec = retval[SAMKeys.SPEC.value]
        spec.pop(SAMPluginSpecKeys.DATA.value, None)
        spec[SAMPluginSpecKeys.IMAGE_SEARCH_DATA.value] = self.plugin_data.manifest_data()
        return json.loads(json.dumps(retval))
