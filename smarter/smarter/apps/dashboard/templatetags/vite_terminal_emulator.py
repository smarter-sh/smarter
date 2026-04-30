"""
Vite manifest loader for Django templates.

A typical vite manifest.json looks like this:

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

from django import template
from django.conf import settings

from smarter.lib import logging
from smarter.lib.cache import cache_results

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(f"{__name__}")

register = template.Library()


@cache_results()
def load_manifest():
    manifest_path = os.path.join(settings.STATIC_ROOT, "react/terminal_emulator/manifest.json")
    with open(manifest_path, encoding="utf-8") as f:
        retval = json.load(f)
        logger.debug("%s.load_manifest() Loaded Vite manifest: %s", logger_prefix, logging.formatted_json(retval))
        return retval


@cache_results()
def collect_css(manifest, key, seen=None):
    """Recursively collect CSS from a manifest entry and its imports."""
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
def terminal_emulator_vite_assets(entry="index.html"):
    """Load CSS and JS files for a Vite entry point from the manifest."""
    manifest = load_manifest()
    entry_data = manifest.get(entry, {})

    # De-duplicate while preserving order, prefix paths for Django static
    prefix = "react/terminal_emulator/"
    seen_css = set()
    css_files = []
    for path in collect_css(manifest, entry):
        prefixed = prefix + path
        if prefixed not in seen_css:
            seen_css.add(prefixed)
            css_files.append(prefixed)

    assets = {
        "js": entry_data.get("file", ""),
        "css": css_files,
    }

    logger.debug(
        "%s.terminal_emulator_vite_assets() entry=%s assets=%s", logger_prefix, entry, logging.formatted_json(assets)
    )
    return assets
