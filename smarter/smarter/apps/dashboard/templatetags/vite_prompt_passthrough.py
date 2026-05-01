"""
Vite manifest loader and asset collector for Django templates.

This module provides template tags and utility functions to load and process
the Vite manifest.json for the prompt passthrough frontend, enabling Django
templates to include the correct JavaScript and CSS assets built by Vite.

Features
--------
- Loads the Vite manifest.json from the static files directory.
- Recursively collects CSS dependencies for a given entry point, including imports.
- Provides a Django template tag to retrieve the JS and CSS assets for a Vite entry.

Functions
---------
- load_manifest(): Loads and caches the Vite manifest as a dictionary.
- collect_css(manifest, key, seen=None): Recursively collects CSS files for a manifest entry and its imports.
- prompt_passthrough_vite_assets(entry="index.html"): Django template tag that returns the JS and CSS assets for a given Vite entry.

Example
-------
In a Django template, use the provided tag to get asset paths::

    {% load vite_prompt_passthrough %}
    {% prompt_passthrough_vite_assets "index.html" as assets %}
    {% for css_file in assets.css %}
        <link class="smarter" rel="stylesheet" href="{% static css_file %}">
    {% endfor %}

Example Vite Manifest
---------------------
A typical vite manifest.json looks like this::

    {
        "_rolldown-runtime.js": {
            "file": "assets/rolldown-runtime.js",
            "name": "rolldown-runtime"
        },
        "_xterm-TdnZ7DQy.css": {
            "file": "assets/xterm-TdnZ7DQy.css",
            "src": "_xterm-TdnZ7DQy.css"
        },
        "_xterm.js": {
            "file": "assets/xterm.js",
            "name": "xterm",
            "imports": [
                "_rolldown-runtime.js"
            ],
            "css": [
                "assets/xterm-TdnZ7DQy.css"
            ]
        },
        "index.html": {
            "file": "assets/index.js",
            "name": "index",
            "src": "index.html",
            "isEntry": true,
            "imports": [
                "_rolldown-runtime.js",
                "_xterm.js"
            ],
            "css": [
                "assets/index-DvLY75bJ.css"
            ]
        }
    }
"""

import json
import os
from typing import Any

from django import template
from django.conf import settings

from smarter.lib import logging
from smarter.lib.cache import cache_results

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(f"{__name__}")

register = template.Library()


@cache_results()
def load_manifest() -> dict[str, Any]:
    """
    Load and cache the Vite manifest as a dictionary.

    :return: The Vite manifest loaded from the static files directory.
    :rtype: dict[str, Any]
    """
    manifest_path = os.path.join(settings.STATIC_ROOT, "react/prompt_passthrough/manifest.json")
    with open(manifest_path, encoding="utf-8") as f:
        retval = json.load(f)
        logger.debug("%s.load_manifest() Loaded Vite manifest: %s", logger_prefix, logging.formatted_json(retval))
        return retval


@cache_results()
def collect_css(manifest: dict[str, Any], key: str, seen: set[str] | None = None) -> list[str]:
    """
    Recursively collect CSS from a manifest entry and its imports.

    :param manifest: The Vite manifest dictionary.
    :param key: The key of the manifest entry to collect CSS for.
    :param seen: A set of already seen keys to avoid circular dependencies.
    :return: A list of CSS file paths.
    :rtype: list[str]
    """
    if seen is None:
        seen = set()
    if key in seen:
        return []
    seen.add(key)

    entry = manifest.get(key, {})
    css = list(entry.get("css", []))

    for imported_key in entry.get("imports", []):
        css.extend(collect_css(manifest, imported_key, seen))

    return css


@register.simple_tag
@cache_results()
def prompt_passthrough_vite_assets(entry: str = "index.html") -> dict[str, Any]:
    """
    Load CSS and JS files for a Vite entry point from the manifest.

    This function retrieves the JavaScript and CSS assets for a given Vite entry
    point (defaulting to "index.html") by loading the manifest and collecting
    all CSS dependencies recursively. It returns a dictionary with the main JS file
    and a list of CSS files, all prefixed for Django static file usage.

    :param entry: The Vite entry point to retrieve assets for (default: "index.html").
    :return: A dictionary containing the JS file and a list of CSS files.
    :rtype: dict[str, Any]

    Example output::

        {
            "js": "assets/index.js",
            "css": [
                "assets/index-DvLY75bJ.css",
                "assets/xterm-TdnZ7DQy.css"
            ]
        }
    """
    manifest = load_manifest()
    entry_data = manifest.get(entry, {})

    css_files = collect_css(manifest, entry)
    entry_point = entry_data.get("file")
    if not entry_point:
        raise ValueError(f"Entry point '{entry}' not found in Vite manifest")

    assets = {
        "js": entry_point,
        "css": css_files,
    }

    logger.debug(
        "%s.prompt_passthrough_vite_assets() entry=%s assets=%s", logger_prefix, entry, logging.formatted_json(assets)
    )
    return assets
