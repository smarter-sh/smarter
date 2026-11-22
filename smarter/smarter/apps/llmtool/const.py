"""Constants for the plugin app."""

import os
from enum import IntEnum

from django.utils.translation import gettext_noop

namespace = "llmtool"
presentation_app_name = gettext_noop("LLMTool")
HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = HERE

LLMTOOL_ENV_PREFIX = "APP_LLMTOOL_"
"""
The prefix of the llmtool app's environment variables, after the optional ``SMARTER_``.

E.g. ``SMARTER_APP_LLMTOOL_TAVILY_API_KEY``. ``manage.py initialize_llmtool_api_keys`` stores each key as
a Secret named without it, e.g. ``tavily_api_key``, which the plugins' manifests name.
"""

TAVILY_API_KEY_SECRET_NAME = "tavily_api_key"
"""The Secret of the Tavily web search api key, which WebsearchPlugins such as smarter_project_websearch use."""

BRAVE_SEARCH_API_KEY_SECRET_NAME = "brave_search_api_key"
"""
The Secret of the Brave Search api key.

ImageSearchPlugins such as safe_image_search use it, and so do the Brave WebsearchPlugin samples
such as research_assistant.
"""

ONE_MINUTE = 60
ONE_HOUR = 60 * ONE_MINUTE
ONE_DAY = 24 * ONE_HOUR
ONE_WEEK = 7 * ONE_DAY


class PluginCacheTtl(IntEnum):
    """
    Seconds to cache the results of each kind of plugin's remote calls, with ``@cache_results``.

    Each TTL reflects how quickly the remote data is expected to change. The ImageSearch and
    Websearch values are the defaults of the manifest's ``cacheTtl``, which a plugin may override.
    """

    DEFAULT = ONE_HOUR
    """The default TTL for a plugin's remote calls to safe_http.py, if the plugin does not specify a cacheTtl in its manifest."""

    API = ONE_HOUR
    """An ApiPlugin's GET responses.

    Other methods may change something, so they are never cached.
    """

    SQL = ONE_HOUR
    """A SqlPlugin's query results."""

    SKILL = 3 * ONE_DAY
    """A SkillPlugin's remote skill, retrieved from GitHub or another https host."""

    IMAGE_SEARCH = ONE_WEEK
    """An ImageSearchPlugin's Brave Image Search API responses."""

    WEBSEARCH = ONE_HOUR
    """A WebsearchPlugin's search results and web pages."""

    WEBSEARCH_ROBOTS_TXT = ONE_HOUR
    """The robots.txt files that a WebsearchPlugin obeys."""


OFFICIAL_EXTENSIONS = ("calculator", "date-calculator", "weather")
"""The slugs of the official Smarter Extensions, which ``manage.py install_official_extensions`` installs from the registry."""
