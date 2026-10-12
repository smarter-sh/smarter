"""
Vite-generated React manifest.json loader and asset collector base class for Django templatetags.

This module provides a reusable base class and supporting types for
managing Vite-generated React manifest.json files and collecting
frontend assets for React apps in Django projects. It is designed
to be instantiated as a singleton representing a specific React app,
enabling Django templates to include the correctly-sequenced JavaScript
and CSS assets built by Vite for each app.

Key Features
-------------
- Loads and caches the manifest.json for each React app from the static files directory,
  validated against the Pydantic model :class:`~smarter.lib.django.templatetags.smarter_react_contract.ViteManifest`.
- Recursively collects CSS and JS dependencies for the entry point, including all imports.
- Returns the JS and CSS assets for the entry point as a
  :class:`~smarter.lib.django.templatetags.smarter_react_contract.ReactAppAssets`, for use in Django template tags.
- Designed as a base class to be instantiated for each React app; singletons are used to register template tags per app.

Main Classes and Functions
---------------------------
- SmarterReactTemplateTagManager: Base class for managing Vite-generated React manifest loading and asset collection for a React app.
- reactapp_build_assets: The JS and CSS assets for the configured entry point.
- :mod:`smarter.lib.django.templatetags.smarter_react_contract`: the Pydantic models of the manifest and of the assets.

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
from typing import Optional

from django import template
from django.conf import settings
from pydantic import ValidationError

from smarter.common.exceptions import SmarterValueError
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging

from .smarter_react_contract import ReactAppAssets, ViteManifest

logger = logging.getLogger(__name__)

register = template.Library()


class SmarterReactTemplateTagManager(SmarterHelperMixin):
    """
    Base class for per-React-app singleton managers that load and analyze Vite-generated React manifest.json files in order to generate ordered lists of JS and CSS assets.

    This class is intended to be instantiated once per React app, providing a
    long-lived singleton that manages loading and caching the React manifest.json
    and collecting all required JS and CSS assets for the app's entry point.

    After instantiation, the only public attribute used is reactapp_build_assets,
    which returns ordered lists of the JS and CSS assets for the configured
    entry point. Its value is cached for the effective lifetime
    of the object instance (until server reboot).

    This design ensures that asset collection is efficient and consistent, and that
    Django templates can reliably include the dependency-ordered asset files for each
    React app.
    """

    app_name: str
    templatetag_name: str
    entry_key: Optional[str]

    def __init__(self, app_name: str, templatetag_name: str):
        """
        Initialize the SmarterReactTemplateTagManager.

        :param app_name: The name of the app to manage template tags for.
        :param templatetag_name: The name of the template tag to register.
        :raises SmarterValueError: If the app's manifest.json has no entry point.
        """
        super().__init__()
        self.app_name = app_name
        self.templatetag_name = templatetag_name
        self.entry_key = self.find_entry_key()
        logger.info(
            "%s[%s] %s is registered to React app '%s'",
            self.formatted_class_name,
            id(self),
            self.templatetag_name,
            self.app_name,
        )

    @property
    def manifest_path(self) -> str:
        """
        The path of the app's Vite-generated manifest.json in the static files directory.

        :returns: The manifest.json's path.
        :rtype: str
        """
        return os.path.join(settings.STATIC_ROOT, f"react/{self.app_name}/manifest.json")

    @cached_property
    def manifest(self) -> Optional[ViteManifest]:
        """
        Load, validate and cache the app's manifest.json.

        A manifest.json that is missing, isn't JSON, or doesn't match
        :class:`~smarter.lib.django.templatetags.smarter_react_contract.ViteManifest`
        is logged, and is cached as None, until the server restarts.

        :returns: The manifest, or None if it couldn't be loaded.
        :rtype: Optional[ViteManifest]
        """
        try:
            with open(self.manifest_path, encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            logger.error(
                "%s.manifest manifest.json not found at expected path: %s. Ensure Vite build has been run and static files are collected.",
                self.formatted_class_name,
                self.manifest_path,
            )
            return None
        try:
            manifest = ViteManifest.model_validate_json(content)
        except ValidationError as e:
            logger.error(
                "%s.manifest failed to parse manifest.json at %s: %s. content: %s",
                self.formatted_class_name,
                self.manifest_path,
                e,
                content,
            )
            return None
        logger.debug(
            "%s.manifest loaded and cached manifest.json for %s: %s",
            self.formatted_class_name,
            self.app_name,
            logging.formatted_json(manifest.model_dump(mode="json", by_alias=True, exclude_defaults=True)),
        )
        return manifest

    def find_entry_key(self) -> Optional[str]:
        """
        Locate the key of the manifest's entry point, the chunk with ``"isEntry": true``.

        Example entry:

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

        :returns: The entry point's key, or None if there is no manifest.
        :rtype: Optional[str]
        :raises SmarterValueError: If the manifest has no entry point.
        """
        if not self.manifest:
            return None
        entry_key = self.manifest.entry_key()
        if entry_key is None:
            raise SmarterValueError(f"No entry with 'isEntry' found in manifest.json for app '{self.app_name}'")
        return entry_key

    @cached_property
    def reactapp_build_assets(self) -> ReactAppAssets:
        """
        The JS and CSS files of the app's entry point, including all of its imports, in load order.

        The entry point's own files come first, followed by those of its
        imports, depth first. The result is cached for the lifetime of the
        manager.

        :returns: The entry point's JS and CSS files. Both lists are empty if there is no manifest.
        :rtype: ReactAppAssets

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
        if not self.manifest or not self.entry_key:
            logger.error(
                "%s.reactapp_build_assets() No manifest.json found for app '%s'. Cannot collect assets.",
                self.formatted_class_name,
                self.app_name,
            )
            return ReactAppAssets()

        assets = ReactAppAssets(
            js=self.manifest.collect_assets(key=self.entry_key, asset_type="js"),
            css=self.manifest.collect_assets(key=self.entry_key, asset_type="css"),
        )
        logger.debug(
            "%s[%s].reactapp_build_assets() caching build assets for React app %s: %s",
            self.formatted_class_name,
            id(self),
            self.app_name,
            logging.formatted_json(assets.model_dump(mode="json")),
        )
        return assets
