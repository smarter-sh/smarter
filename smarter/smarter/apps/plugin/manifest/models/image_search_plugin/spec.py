"""
Smarter API Manifest - ImageSearchPlugin.spec.

An ImageSearchPlugin gives the LLM an image search, powered by the
`Brave Image Search API <https://api-dashboard.search.brave.com/app/documentation/image-search/get-started>`__.
Its tool returns a JSON list of strings: the https urls of the images that it found.

The LLM supplies the search query, e.g. ``formula 1 race cars``, in each tool call.
``spec.imageSearchData.queryTerms``, if set, are appended to it, e.g. ``black and white
photograph``, so that Brave searches for ``formula 1 race cars black and white photograph``.
``spec.imageSearchData.searchParams`` map 1:1 to the Brave Image Search API's other query
parameters. ``spec.imageSearchData.filters`` are applied by Smarter to Brave's results, for
what the API itself cannot filter: file type, minimum size, and the websites that images
come from.

.. code-block:: yaml

    imageSearchData:
      apiKey: brave_search_api_key   # the name of a Smarter Secret
      queryTerms: null               # terms appended to every query that the LLM sends
      llmSearchParams: false         # whether the LLM may set every search parameter in each call
      searchParams:
        count: 10                    # 1 to 20
        country: us                  # a two letter country code, or all
        searchLang: en               # a language code, e.g. en, pt-br
        safesearch: strict           # strict or off
        spellcheck: true
      filters:
        fileType: jpg|png            # any of jpg, png, gif, svg, webp, avif, bmp, ico
        minWidth: 800                # pixels. Images of unknown width are skipped
        minHeight: null
        allowedDomains: []           # if not empty, only images from web pages on these domains
        blockedDomains: []           # never images on, or from web pages on, these domains
      validateUrls: true             # only return urls that respond with HTTP 200
      timeout: 10
      cacheTtl: 900

.. note::

    **Experimental.** The ImageSearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental.
"""

import os
import re
from typing import Any, ClassVar, Optional

from pydantic import Field, field_validator

from smarter.apps.plugin.manifest.models.common.plugin.spec import SAMPluginCommonSpec
from smarter.apps.plugin.manifest.models.websearch_plugin.policy import (
    WebsearchPolicyError,
    normalize_domains,
)
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import SmarterBasePydanticModel

from .const import (
    DEFAULT_API_KEY_SECRET_NAME,
    DEFAULT_CACHE_TTL,
    DEFAULT_COUNT,
    DEFAULT_TIMEOUT,
    MANIFEST_KIND,
    MAX_CACHE_TTL,
    MAX_COUNT,
    MAX_DIMENSION,
    MAX_QUERY_LENGTH,
    MAX_TIMEOUT,
)
from .enum import ImageSearchFileType, ImageSearchSafeSearch

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"

COUNTRY_PATTERN = re.compile(r"^([a-z]{2}|all)$")
SEARCH_LANG_PATTERN = re.compile(r"^[a-z]{2}(-[a-z]{2,4})?$")


def normalize_file_types(value: Any) -> Optional[str]:
    """
    Validate and normalize a ``fileType`` filter.

    :param value: File types separated by ``|``, e.g. ``jpg|png``. ``jpeg`` is read as ``jpg``.
    :return: The normalized value, e.g. ``jpg|png``, or None if the value is empty.
    :raises ValueError: If a file type is not permitted.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise ValueError(f"fileType must be a string: {value}")
    permitted = ImageSearchFileType.all()
    values = [item.strip().lower() for item in value.split("|") if item.strip()]
    values = ["jpg" if item == "jpeg" else item for item in values]
    for item in values:
        if item not in permitted:
            raise ValueError(f"fileType must be any of {permitted}, separated by '|': {item}")
    return "|".join(dict.fromkeys(values)) or None


def normalize_country(value: Any) -> Optional[str]:
    """
    Validate and normalize a ``country`` search parameter.

    :param value: A two letter country code, or ``all`` for worldwide results.
    :return: The lower case value, or None if the value is empty.
    :raises ValueError: If the value is not a two letter country code, nor ``all``.
    """
    if value is None or not str(value).strip():
        return None
    value = str(value).strip().lower()
    if not COUNTRY_PATTERN.match(value):
        raise ValueError(f"country must be a two letter country code, or all: {value}")
    return value


def normalize_search_lang(value: Any) -> Optional[str]:
    """
    Validate and normalize a ``searchLang`` search parameter.

    :param value: A language code, e.g. ``en`` or ``pt-br``.
    :return: The lower case value, or None if the value is empty.
    :raises ValueError: If the value is not a language code.
    """
    if value is None or not str(value).strip():
        return None
    value = str(value).strip().lower()
    if not SEARCH_LANG_PATTERN.match(value):
        raise ValueError(f"searchLang must be a language code, e.g. en or pt-br: {value}")
    return value


class ImageSearchParams(SmarterBasePydanticModel):
    """
    Smarter API - ImageSearchPlugin.spec.imageSearchData.searchParams.

    These map 1:1 to the query parameters of the Brave Image Search API, except for ``q``, the
    query itself, which the LLM supplies. See ``imageSearchData.queryTerms``.
    """

    class_identifier: ClassVar[str] = f"{MODULE_IDENTIFIER}.searchParams"

    count: int = Field(
        default=DEFAULT_COUNT,
        ge=1,
        le=MAX_COUNT,
        description=f"{class_identifier}.count[int]: the maximum number of images per search, 1 to {MAX_COUNT}.",
    )
    country: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.country[str]: a two letter country code, e.g. us, or all for worldwide results.",
    )
    searchLang: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.searchLang[str]: prefer images from content in this language, e.g. en or pt-br.",
    )
    safesearch: str = Field(
        default=ImageSearchSafeSearch.STRICT.value,
        description=f"{class_identifier}.safesearch[str]: adult content filtering. One of: {ImageSearchSafeSearch.all()}",
    )
    spellcheck: bool = Field(
        default=True,
        description=f"{class_identifier}.spellcheck[bool]: whether Brave may correct the spelling of the query.",
    )

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        """Validate the country code."""
        try:
            return normalize_country(v)
        except ValueError as e:
            raise SAMValidationError(f"{cls.class_identifier}: {e}") from e

    @field_validator("searchLang")
    @classmethod
    def validate_search_lang(cls, v: Optional[str]) -> Optional[str]:
        """Validate the language code."""
        try:
            return normalize_search_lang(v)
        except ValueError as e:
            raise SAMValidationError(f"{cls.class_identifier}: {e}") from e

    @field_validator("safesearch")
    @classmethod
    def validate_safesearch(cls, v: str) -> str:
        """Validate the safe search level."""
        v = str(v).strip().lower()
        if v not in ImageSearchSafeSearch.all():
            raise SAMValidationError(
                f"{cls.class_identifier}.safesearch must be one of {ImageSearchSafeSearch.all()}: {v}"
            )
        return v


class ImageSearchFilters(SmarterBasePydanticModel):
    """
    Smarter API - ImageSearchPlugin.spec.imageSearchData.filters.

    Smarter applies these to the Brave Image Search API's results.
    """

    class_identifier: ClassVar[str] = f"{MODULE_IDENTIFIER}.filters"

    fileType: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.fileType[str]: only images of these file types, separated by '|', e.g. jpg|png. "
            f"Any of: {ImageSearchFileType.all()}"
        ),
    )
    minWidth: Optional[int] = Field(
        default=None,
        ge=1,
        le=MAX_DIMENSION,
        description=(
            f"{class_identifier}.minWidth[int]: only images at least this many pixels wide. Images whose width "
            "Brave does not report are skipped."
        ),
    )
    minHeight: Optional[int] = Field(
        default=None,
        ge=1,
        le=MAX_DIMENSION,
        description=(
            f"{class_identifier}.minHeight[int]: only images at least this many pixels high. Images whose height "
            "Brave does not report are skipped."
        ),
    )
    allowedDomains: Optional[list[str]] = Field(
        default=None,
        description=(
            f"{class_identifier}.allowedDomains[list]: if not empty, only images from web pages on these domains, "
            "and their subdomains."
        ),
    )
    blockedDomains: Optional[list[str]] = Field(
        default=None,
        description=(
            f"{class_identifier}.blockedDomains[list]: never images on these domains, nor from web pages on them, "
            "including their subdomains."
        ),
    )

    @field_validator("fileType")
    @classmethod
    def validate_file_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate the file types."""
        try:
            return normalize_file_types(v)
        except ValueError as e:
            raise SAMValidationError(f"{cls.class_identifier}: {e}") from e

    @field_validator("allowedDomains", "blockedDomains")
    @classmethod
    def validate_domains(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate and normalize domain names."""
        if v is None:
            return None
        try:
            return list(normalize_domains(v))
        except WebsearchPolicyError as e:
            raise SAMValidationError(f"{cls.class_identifier}: {e}") from e


class ImageSearchData(SmarterBasePydanticModel):
    """Smarter API - ImageSearchPlugin.spec.imageSearchData."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    apiKey: str = Field(
        default=DEFAULT_API_KEY_SECRET_NAME,
        description=(
            f"{class_identifier}.apiKey[str]: the name of the Smarter Secret that contains a Brave Search API key. "
            "The api key itself is never included in the manifest."
        ),
    )
    queryTerms: Optional[str] = Field(
        default=None,
        max_length=MAX_QUERY_LENGTH,
        description=(
            f"{class_identifier}.queryTerms[str]: optional search terms appended to every query that the LLM "
            "sends, e.g. 'black and white photograph'. The LLM always supplies the query itself, e.g. 'formula 1 "
            "race cars', so that Brave searches for 'formula 1 race cars black and white photograph'."
        ),
    )
    llmSearchParams: bool = Field(
        default=False,
        description=(
            f"{class_identifier}.llmSearchParams[bool]: whether the LLM may set every Brave Image Search API "
            f"parameter in each tool call: count (up to {MAX_COUNT}), country, search_lang, safesearch and "
            "spellcheck. searchParams are then the defaults. If false, the LLM may only lower the count."
        ),
    )
    searchParams: ImageSearchParams = Field(
        default_factory=ImageSearchParams,
        description=f"{class_identifier}.searchParams[obj]: the Brave Image Search API query parameters.",
    )
    filters: ImageSearchFilters = Field(
        default_factory=ImageSearchFilters,
        description=f"{class_identifier}.filters[obj]: the filters that Smarter applies to the search results.",
    )
    validateUrls: bool = Field(
        default=True,
        description=(
            f"{class_identifier}.validateUrls[bool]: only return image urls that respond to a request with "
            "HTTP 200, and not with a web page. Urls are always https."
        ),
    )
    timeout: int = Field(
        default=DEFAULT_TIMEOUT,
        ge=1,
        le=MAX_TIMEOUT,
        description=f"{class_identifier}.timeout[int]: seconds to wait for each web request, 1 to {MAX_TIMEOUT}.",
    )
    cacheTtl: int = Field(
        default=DEFAULT_CACHE_TTL,
        ge=0,
        le=MAX_CACHE_TTL,
        description=f"{class_identifier}.cacheTtl[int]: seconds to cache search results. 0 disables caching.",
    )

    @field_validator("queryTerms")
    @classmethod
    def validate_query_terms(cls, v: Optional[str]) -> Optional[str]:
        """Normalize the query terms."""
        if v is None:
            return None
        v = " ".join(str(v).split())
        return v or None

    @field_validator("apiKey")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that the api key is the name of a Secret, not empty."""
        if not isinstance(v, str) or not v.strip():
            raise SAMValidationError(f"{cls.class_identifier}.apiKey must be the name of a Smarter Secret.")
        return v.strip()


class SAMImageSearchPluginSpec(SAMPluginCommonSpec):
    """Smarter API Manifest - ImageSearchPlugin.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    imageSearchData: ImageSearchData = Field(
        default_factory=ImageSearchData,
        description=f"{class_identifier}.imageSearchData[obj]: the image search configuration of the {MANIFEST_KIND}.",
    )
