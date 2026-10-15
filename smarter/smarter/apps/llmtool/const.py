"""Constants for the plugin app."""

import os
from enum import IntEnum

namespace = "llmtool"
presentation_app_name = "LLMTool"
HERE = os.path.abspath(os.path.dirname(__file__))
DATA_PATH = HERE

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

    DEFAULT = 10 * ONE_MINUTE
    """The default TTL for a plugin's remote calls to safe_http.py, if the plugin does not specify a cacheTtl in its manifest."""

    API = 10 * ONE_MINUTE
    """An ApiPlugin's GET responses."""

    SQL = 10 * ONE_MINUTE
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
"""The slugs of the official Smarter Extensions, which ``manage.py add_builtin_extensions`` installs from the registry."""
