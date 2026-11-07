"""
The static files' storage on the environment's S3 bucket, behind its CDN, while ``SMARTER_STATIC_FILES_ON_CDN`` is on.

``collectstatic``, which ``initialize_platform`` runs on each deployment, uploads the files under ``static/``, and
pages load them from the CDN, e.g. ``https://cdn.platform.example.com/static/``. A React app's build output under
``assets/`` has content-hashed names, so a browser may keep it for a year; every other file, e.g. a Keen theme
asset that templates version with a query string, may be kept for an hour. ``collectstatic`` adds and replaces
files, and deletes none, so a page that a browser opened before a deployment keeps loading its scripts.

See :doc:`ADR-035 </adr/035-single-page-app>` and :mod:`smarter.apps.dashboard.views.console_app`.
"""

import re

from storages.backends.s3 import S3Storage

from smarter.lib.typing import SmarterDictType

STATIC_LOCATION = "static"
"""The folder of the bucket that holds the static files."""

HASHED_CACHE_CONTROL = "public, max-age=31536000, immutable"
"""Cache-Control of a file whose name changes with its content."""

DEFAULT_CACHE_CONTROL = "public, max-age=3600"
"""Cache-Control of any other static file."""

HASHED_ASSET = re.compile(r"^react/.+/assets/[^/]+-[A-Za-z0-9_-]{8,}\.[a-z0-9]+$")
"""A React app's build output, e.g. ``react/@smarter/console/assets/index-DlE53XQD.js``, whose name has its hash."""


def cache_control(name: str) -> str:
    """
    The Cache-Control header of a static file.

    :param name: The file's name, relative to the static files' root, e.g. ``react/@smarter/console/index.html``.
    :returns: A year, immutable, for a file whose name has its content's hash, and an hour otherwise.
    """
    if HASHED_ASSET.match(name):
        return HASHED_CACHE_CONTROL
    return DEFAULT_CACHE_CONTROL


class SmarterStaticFilesStorage(S3Storage):
    """The static files on the environment's S3 bucket, under ``static/``, each with its own Cache-Control."""

    def get_object_parameters(self, name: str) -> SmarterDictType:
        """
        The S3 object's parameters: the storage's own, plus the file's Cache-Control.

        :param name: The file's name, relative to the static files' root.
        :returns: The parameters.
        """
        parameters = super().get_object_parameters(name)
        parameters["CacheControl"] = cache_control(name)
        return parameters


__all__ = [
    "DEFAULT_CACHE_CONTROL",
    "HASHED_CACHE_CONTROL",
    "STATIC_LOCATION",
    "SmarterStaticFilesStorage",
    "cache_control",
]
