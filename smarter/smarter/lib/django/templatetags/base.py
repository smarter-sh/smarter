"""
Vite manifest loader and asset collector for Django templates.

This module provides template tags and utility functions to load and process
the Vite manifest.json for the terminal emulator frontend, enabling Django
templates to include the correct JavaScript and CSS assets built by Vite.

Features
--------
- Loads the manifest.json from the static files directory.
- Recursively collects CSS dependencies for a given entry point, including imports.
- Provides a Django template tag to retrieve the JS and CSS assets for a manifest entry.

Functions
---------
- load_manifest(): Loads and caches the manifest.json as a dictionary.
- collect_assets(manifest, key, seen=None): Recursively collects CSS files for a manifest entry and its imports.
- reactapp_build_assets(entry="index.html"): Django template tag that returns the JS and CSS assets for a given manifest entry.

Example
-------
In a Django template, use the provided tag to get asset paths::

    {% load vite_reactapp %}
    {% reactapp_build_assets "index.html" as assets %}
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

import os
from functools import cached_property
from typing import Any, List, TypedDict

from django import template
from django.conf import settings

from smarter.common.exceptions import SmarterValueError
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import json, logging
from smarter.lib.cache import cache_results

logger = logging.getLogger(__name__)

register = template.Library()

CACHE_TIMEOUT = 60 * 60 * 24 * 365  # 1 year in seconds. basically 'forever' for static assets.
ManifestValues = dict[str, Any]
ManifestType = dict[str, ManifestValues]


class AssetDict(TypedDict):
    """
    TypedDict representing the structure of assets returned for a Vite entry point.

    Attributes
    ----------
    js: List[str]
        A list of JavaScript file paths required for the entry point, including dependencies.
    css: List[str]
        A list of CSS file paths required for the entry point, including dependencies.
    """

    js: List[str]
    css: List[str]


class SmarterReactTemplateTagManager(SmarterHelperMixin):
    """
    Manager for smarter template tags, providing utilities for loading Vite manifests
    and collecting assets for Django templates.

    This class encapsulates the logic for loading the Vite manifest, collecting CSS
    dependencies, and providing a template tag to retrieve assets for a given entry point.
    """

    _manifest: ManifestType
    app_name: str
    templatetag_name: str
    entry_key: str

    def __init__(self, app_name: str, templatetag_name: str):
        """
        Initialize the SmarterReactTemplateTagManager.

        :param app_name: The name of the app to manage template tags for.
        :param templatetag_name: The name of the template tag to register.
        """
        super().__init__()
        self._manifest: ManifestType = None  # type: ignore[assignment]
        self.app_name = app_name
        self.templatetag_name = templatetag_name
        self.entry_key = self.find_entry_key()
        logger.debug(
            "%s[%s] registered %s Template Tag for React app '%s'",
            self.formatted_class_name,
            id(self),
            self.templatetag_name,
            self.app_name,
        )

    @cached_property
    def manifest(self) -> ManifestType:
        """
        Load and cache the manifest.json as a dictionary.

        :return: The manifest.json loaded from the static files directory.
        :rtype: dict[str, Any]
        """
        if self._manifest:
            return self._manifest

        def _load_manifest() -> ManifestType:
            """
            Load the manifest.json from the static files directory and
            cache the result.
            """
            manifest_path = os.path.join(settings.STATIC_ROOT, f"react/{self.app_name}/manifest.json")
            retval: ManifestType
            with open(manifest_path, encoding="utf-8") as f:
                try:
                    retval = json.load(f)
                except json.JSONDecodeError as e:
                    logger.error(
                        "%s.load_manifest() Failed to parse manifest.json at %s: %s",
                        self.formatted_class_name,
                        manifest_path,
                        e,
                    )
                    raise SmarterValueError(f"Failed to parse manifest.json at {manifest_path}: {e}") from e
            logger.debug(
                "%s.load_manifest() loaded and cached manifest.json for %s: %s",
                self.formatted_class_name,
                self.app_name,
                logging.formatted_json(retval),
            )
            if not isinstance(retval, dict):
                logger.error(
                    "%s.load_manifest() manifest.json is not a dictionary: %s", self.formatted_class_name, type(retval)
                )
                raise SmarterValueError(f"manifest.json is not a dictionary: {type(retval)}")
            return retval

        self._manifest = _load_manifest()
        return self._manifest

    def collect_assets(
        self, manifest: ManifestType, key: str, asset_type: str, seen: set[str] | None = None
    ) -> list[str]:
        """
        Recursively collect assets from a manifest entry and its imports,
        preserving dependency order.

        Assets are collected in the order required for correct script or style
        loading in the DOM: dependencies (as listed in the "imports" array) are
        always collected before the assets of the entry itself. This ensures
        that, for example, JavaScript files are loaded in the correct order so
        that dependencies are available before their dependents execute.

        :param manifest: The Vite manifest dictionary.
        :param key: The key of the manifest entry to collect assets for.
        :param asset_type: The type of asset to collect (e.g., "css" or "js").
        :param seen: A set of already seen keys to avoid circular dependencies.
        :return: A list of asset file paths, ordered so that dependencies appear before dependents.
        :rtype: list[str]
        """
        if seen is None:
            seen = set()
        if key in seen:
            return []
        seen.add(key)

        entry = manifest.get(key, {})
        assets = []

        # For JS, the 'file' field is a string, not a list
        if asset_type == "file":
            file_val = entry.get(asset_type, None)
            if file_val:
                assets.append(file_val)
        else:
            assets = list(entry.get(asset_type, []))

        for imported_key in entry.get("imports", []):
            assets.extend(self.collect_assets(manifest=manifest, key=imported_key, asset_type=asset_type, seen=seen))

        if not seen:
            # Only log the collected assets for the top-level entry to avoid
            # cluttering logs with recursive calls.
            logger.debug(
                "%s.collect_assets() collected and cached %s for key=%s: %s",
                self.formatted_class_name,
                asset_type,
                key,
                assets,
            )
        return assets

    def find_entry_key(self) -> str:
        """
        Locate the top-level key and dict in the manifest where the dict contains the key 'isEntry'.
        Returns the key if found, else raises an error.

        Example entry dict:

            .. code-block:: json

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
        """
        REACT_ENTRY_KEY = "isEntry"
        for key, value in self.manifest.items():
            if isinstance(value, dict) and REACT_ENTRY_KEY in value:
                return key
        raise SmarterValueError(f"No entry with '{REACT_ENTRY_KEY}' found in Vite manifest")

    def reactapp_build_assets(self) -> AssetDict:
        """
        Load CSS and JS files for a Vite entry point from the manifest.

        This function retrieves the JavaScript and CSS assets for a given Vite entry
        point (defaulting to "index.html") by loading the manifest and collecting
        all CSS dependencies recursively. It returns a dictionary with the main JS file
        and a list of CSS files, all prefixed for Django static file usage.

        :param entry: The Vite entry point to retrieve assets for (default: "index.html").
        :return: A dictionary containing the JS file and a list of CSS files.
        :rtype: AssetDict

        Example output::

            {
                "js": ["assets/index.js"],
                "css": [
                    "assets/index-DvLY75bJ.css",
                    "assets/xterm-TdnZ7DQy.css"
                ]
            }
        """

        # pylint: disable=W0613
        @cache_results(timeout=CACHE_TIMEOUT)
        def _collect_reactapp_assets(cache_key: int) -> AssetDict:

            css_files = self.collect_assets(manifest=self.manifest, key=self.entry_key, asset_type="css")
            js_files = self.collect_assets(manifest=self.manifest, key=self.entry_key, asset_type="file")

            assets: AssetDict = {
                "js": js_files,
                "css": css_files,
            }
            serialized_assets = json.dumps(assets)

            logger.debug(
                "%s.reactapp_build_assets() caching build assets for React entry_key=%s assets=%s",
                self.formatted_class_name,
                self.entry_key,
                logging.formatted_json(json.loads(serialized_assets)),
            )
            return assets

        return _collect_reactapp_assets(cache_key=id(self))
