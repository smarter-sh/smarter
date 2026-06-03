"""
Vite-generated React manifest.json loader and asset collector base class for Django
templatetags.

This module provides a reusable base class and supporting types for
managing Vite-generated React manifest.json files and collecting
frontend assets for React apps in Django projects. It is designed
to be instantiated as a singleton representing a specific React app,
enabling Django templates to include the correctly-sequenced JavaScript
and CSS assets built by Vite for each app.

Key Features
-------------
- Loads and caches the manifest.json for each React app from the static files directory.
- Recursively collects CSS and JS dependencies for a given entry point, including all imports, preserving dependency order.
- Provides a method to retrieve the JS and CSS assets for a manifest entry, suitable for use in Django template tags.
- Designed as a base class to be instantiated for each React app; singletons are used to register template tags per app.

Main Classes and Functions
---------------------------
- SmarterReactTemplateTagManager: Base class for managing Vite-generated React manifest loading and asset collection for a React app.
- collect_assets(): Recursively collects asset files (CSS or JS) for a manifest entry and its imports.
- reactapp_build_assets(): Returns the JS and CSS assets for the configured entry point.

Usage Example
-------------
In a Django template, use the registered template tag for your app to get asset paths::

    {% load react_dashboard %}
    {% dashboard_react_assets as assets %}
    {% for css_file in assets.css %}
        <link class="smarter" rel="stylesheet" href="{% static 'react/smarter-dashboard/' %}{{ css_file }}">
    {% endfor %}

Example React manifest.json
---------------------------
A typical React manifest.json looks like this::

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
from typing import Any, List, Optional, TypedDict

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
    TypedDict representing the structure of assets returned for a
    manifest.json entry point.

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
    Base class for per-React-app singleton managers that load
    and analyze Vite-generated React manifest.json files in order
    to generate ordered lists of JS and CSS assets.

    This class is intended to be instantiated once per React app, providing a
    long-lived singleton that manages loading and caching the React manifest.json
    and collecting all required JS and CSS assets for the app's entry point.

    After instantiation, the only public method called is reactapp_build_assets(),
    which returns ordered lists of the JS and CSS assets for the configured
    entry point. The results of this method are cached for the effective lifetime
    of the object instance (until server reboot).

    This design ensures that asset collection is efficient and consistent, and that
    Django templates can reliably include the dependency-ordered asset files for each
    React app.
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
            retval: ManifestType = {}
            try:
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
                        logger.error(
                            "%s.load_manifest() failed to parse manifest.json at %s: content: %s. This error was raised %s",
                            self.formatted_class_name,
                            manifest_path,
                            f.read(),
                            e,
                        )
            except FileNotFoundError:
                logger.error(
                    "%s.load_manifest() manifest.json not found at expected path: %s. Ensure Vite build has been run and static files are collected.",
                    self.formatted_class_name,
                    manifest_path,
                )
            logger.debug(
                "%s.load_manifest() loaded and cached manifest.json for %s: %s",
                self.formatted_class_name,
                self.app_name,
                logging.formatted_json(retval) if retval else "None",
            )
            if not isinstance(retval, dict):
                logger.error(
                    "%s.load_manifest() manifest.json is not a dictionary: %s", self.formatted_class_name, type(retval)
                )
                return {}
            return retval

        manifest_data = _load_manifest()
        if manifest_data:
            self._manifest = manifest_data
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

        :param manifest: The React manifest.json dictionary.
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
        if not self.manifest:
            return None  # type: ignore[return-value]
        REACT_ENTRY_KEY = "isEntry"
        for key, value in self.manifest.items():
            if isinstance(value, dict) and REACT_ENTRY_KEY in value:
                return key
        raise SmarterValueError(f"No entry with '{REACT_ENTRY_KEY}' found in manifest.json for app '{self.app_name}'")

    def reactapp_build_assets(self) -> AssetDict:
        """
        Load CSS and JS files for a Vite-generated React manifest.json entry
        point from the manifest, including all dependencies, cache and return
        them as an ordered dictionary.

        This function retrieves the JavaScript and CSS assets for a given manifest.json
        entry point (defaulting to "index.html") by loading the manifest and collecting
        all CSS dependencies recursively. It returns a dictionary with the main JS file
        and a list of CSS files, all prefixed for Django static file usage.

        :param entry: The manifest.json entry point to retrieve assets for (default: "index.html").
        :return: A dictionary containing the JS file and a list of CSS files.
        :rtype: AssetDict

        Example output::

            {
                "js": [
                    "assets/index-CZK_Bxxh.js",
                    "assets/rolldown-runtime-B3igc2qu.js",
                    "assets/xterm-D5XSfLrr.js"
                ],
                "css": [
                    "assets/index-58MXwt-L.css",
                    "assets/xterm-kHJ-D0s7.css"
                ]
            }
        """
        if not self.manifest:
            logger.error(
                "%s.reactapp_build_assets() No manifest.json found for app '%s'. Cannot collect assets.",
                self.formatted_class_name,
                self.app_name,
            )
            return {"js": [], "css": []}

        # pylint: disable=W0613
        @cache_results(timeout=CACHE_TIMEOUT)
        def _collect_reactapp_assets(cache_key: int) -> AssetDict:
            css_files = self.collect_assets(manifest=self.manifest, key=self.entry_key, asset_type="css")  # type: ignore[assignment]
            js_files = self.collect_assets(manifest=self.manifest, key=self.entry_key, asset_type="file")  # type: ignore[assignment]

            assets: AssetDict = {
                "js": js_files,
                "css": css_files,
            }
            serialized_assets = json.dumps(assets)

            logger.debug(
                "%s[%s].reactapp_build_assets() caching build assets for React app %s: %s",
                self.formatted_class_name,
                id(self),
                self.app_name,
                logging.formatted_json(json.loads(serialized_assets)),
            )
            return assets

        return _collect_reactapp_assets(cache_key=id(self))
