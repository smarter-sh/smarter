"""
Smarter API Manifest - WebsearchPlugin.spec.

A WebsearchPlugin gives the LLM access to the open web, through one tool that performs two
operations, like the web search and web fetch tools of Claude itself:

- **search** the web for a query, via a web search API, and return ranked results, each
  with a title, URL and snippet, for the LLM to cite.
- **fetch** a web page by URL, and return its main content as Markdown.

``spec.websearchData`` configures each operation. Include a ``search`` section to enable
search, and a ``fetch`` section to enable fetch. At least one is required.

.. code-block:: yaml

    websearchData:
      search:
        provider: brave            # brave or tavily
        apiKey: brave_search_key   # the name of a Smarter Secret containing the api key
        maxResults: 5
        safeSearch: moderate
        country: us
        language: en
        freshness: null            # day, week, month or year
      fetch:
        maxCharacters: 20000
        respectRobotsTxt: true
      allowedDomains: []           # if not empty, only these domains may be searched and read
      blockedDomains: []           # these domains are never searched nor read
      timeout: 15
      cacheTtl: 900

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import os
import re
from typing import ClassVar, Optional

from pydantic import Field, field_validator, model_validator

from smarter.apps.plugin.manifest.models.common.plugin.spec import SAMPluginCommonSpec
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.models import SmarterBasePydanticModel

from .const import (
    DEFAULT_CACHE_TTL,
    DEFAULT_FETCH_CHARACTERS,
    DEFAULT_MAX_RESULTS,
    DEFAULT_TIMEOUT,
    MANIFEST_KIND,
    MAX_CACHE_TTL,
    MAX_FETCH_CHARACTERS,
    MAX_RESULTS,
    MAX_TIMEOUT,
    MIN_FETCH_CHARACTERS,
)
from .enum import WebsearchFreshness, WebsearchProvider, WebsearchSafeSearch
from .policy import DomainPolicy, WebsearchPolicyError, normalize_domains

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"

COUNTRY_PATTERN = re.compile(r"^[a-z]{2}$")
LANGUAGE_PATTERN = re.compile(r"^[a-z]{2}$")


class WebsearchSearch(SmarterBasePydanticModel):
    """Smarter API - WebsearchPlugin.spec.websearchData.search: web search, via a web search API."""

    class_identifier: ClassVar[str] = f"{MODULE_IDENTIFIER}.search"

    provider: str = Field(
        ...,
        description=f"{class_identifier}.provider[str]: the web search API. One of: {WebsearchProvider.all()}",
    )
    apiKey: str = Field(
        ...,
        description=(
            f"{class_identifier}.apiKey[str]: the name of the Smarter Secret that contains the web search API's "
            "api key. The api key itself is never included in the manifest."
        ),
    )
    maxResults: int = Field(
        default=DEFAULT_MAX_RESULTS,
        ge=1,
        le=MAX_RESULTS,
        description=f"{class_identifier}.maxResults[int]: the maximum number of results per search, 1 to {MAX_RESULTS}.",
    )
    safeSearch: str = Field(
        default=WebsearchSafeSearch.MODERATE.value,
        description=f"{class_identifier}.safeSearch[str]: adult content filtering. One of: {WebsearchSafeSearch.all()}",
    )
    country: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.country[str]: an ISO 3166-1 alpha-2 country code, e.g. us, to localize results.",
    )
    language: Optional[str] = Field(
        default=None,
        description=f"{class_identifier}.language[str]: an ISO 639-1 language code, e.g. en, to localize results.",
    )
    freshness: Optional[str] = Field(
        default=None,
        description=(
            f"{class_identifier}.freshness[str]: by default, restrict results to those published within the last "
            f"{WebsearchFreshness.all()}. The LLM can override this per search."
        ),
    )

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate the provider."""
        v = str(v).strip().lower()
        if v not in WebsearchProvider.all():
            raise SAMValidationError(f"{cls.class_identifier}.provider must be one of {WebsearchProvider.all()}: {v}")
        return v

    @field_validator("apiKey")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that the api key is the name of a Secret, not empty."""
        if not isinstance(v, str) or not v.strip():
            raise SAMValidationError(f"{cls.class_identifier}.apiKey must be the name of a Smarter Secret.")
        return v.strip()

    @field_validator("safeSearch")
    @classmethod
    def validate_safe_search(cls, v: str) -> str:
        """Validate the safe search level."""
        v = str(v).strip().lower()
        if v not in WebsearchSafeSearch.all():
            raise SAMValidationError(
                f"{cls.class_identifier}.safeSearch must be one of {WebsearchSafeSearch.all()}: {v}"
            )
        return v

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        """Validate the country code."""
        if v is None:
            return None
        v = str(v).strip().lower()
        if not COUNTRY_PATTERN.match(v):
            raise SAMValidationError(f"{cls.class_identifier}.country must be a two letter country code: {v}")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        """Validate the language code."""
        if v is None:
            return None
        v = str(v).strip().lower()
        if not LANGUAGE_PATTERN.match(v):
            raise SAMValidationError(f"{cls.class_identifier}.language must be a two letter language code: {v}")
        return v

    @field_validator("freshness")
    @classmethod
    def validate_freshness(cls, v: Optional[str]) -> Optional[str]:
        """Validate the default freshness."""
        if v is None:
            return None
        v = str(v).strip().lower()
        if v not in WebsearchFreshness.all():
            raise SAMValidationError(f"{cls.class_identifier}.freshness must be one of {WebsearchFreshness.all()}: {v}")
        return v


class WebsearchFetch(SmarterBasePydanticModel):
    """Smarter API - WebsearchPlugin.spec.websearchData.fetch: reading web pages by URL."""

    class_identifier: ClassVar[str] = f"{MODULE_IDENTIFIER}.fetch"

    maxCharacters: int = Field(
        default=DEFAULT_FETCH_CHARACTERS,
        ge=MIN_FETCH_CHARACTERS,
        le=MAX_FETCH_CHARACTERS,
        description=(
            f"{class_identifier}.maxCharacters[int]: the maximum number of characters of a web page to return, "
            f"{MIN_FETCH_CHARACTERS} to {MAX_FETCH_CHARACTERS}. Longer pages are truncated."
        ),
    )
    respectRobotsTxt: bool = Field(
        default=True,
        description=f"{class_identifier}.respectRobotsTxt[bool]: whether to obey websites' robots.txt files.",
    )


class WebsearchData(SmarterBasePydanticModel):
    """Smarter API - WebsearchPlugin.spec.websearchData."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    search: Optional[WebsearchSearch] = Field(
        default=None,
        description=f"{class_identifier}.search[obj]: enables web search. Requires a web search API key.",
    )
    fetch: Optional[WebsearchFetch] = Field(
        default=None,
        description=f"{class_identifier}.fetch[obj]: enables reading web pages by URL.",
    )
    allowedDomains: Optional[list[str]] = Field(
        default=None,
        description=(
            f"{class_identifier}.allowedDomains[list]: if not empty, only these domains, and their subdomains, may "
            "be searched and read."
        ),
    )
    blockedDomains: Optional[list[str]] = Field(
        default=None,
        description=f"{class_identifier}.blockedDomains[list]: these domains, and their subdomains, are never searched nor read.",
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
        description=f"{class_identifier}.cacheTtl[int]: seconds to cache search results and web pages. 0 disables caching.",
    )

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

    @model_validator(mode="after")
    def validate_websearch_data(self) -> "WebsearchData":
        """Validate that at least one operation is enabled."""
        if not self.search and not self.fetch:
            raise SAMValidationError(
                f"{self.class_identifier}: at least one of 'search' or 'fetch' is required, to enable web search or "
                "reading web pages."
            )
        return self

    @property
    def domain_policy(self) -> DomainPolicy:
        """The domain policy."""
        return DomainPolicy.create(allowed=self.allowedDomains, blocked=self.blockedDomains)


class SAMWebsearchPluginSpec(SAMPluginCommonSpec):
    """Smarter API Manifest - WebsearchPlugin.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    websearchData: WebsearchData = Field(
        ...,
        description=f"{class_identifier}.websearchData[obj]: the web search and web fetch configuration of the {MANIFEST_KIND}.",
    )
