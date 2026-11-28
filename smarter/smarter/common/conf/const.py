"""This module contains constants used for Pydantic Settings."""

import os
import re

from dotenv import load_dotenv

from smarter.common.const import SMARTER_LOCAL_PORT, SmarterEnvironments
from smarter.common.helpers.console_helpers import SmarterFormattedText

THE_EMPTY_SET = [None, "", "NULL", "None", "none", "null"]

DEFAULT_MISSING_VALUE = "SET-ME-PLEASE"
"""The placeholder of a setting that is not set, e.g. in ``.env.example``."""

LOCAL_HOSTS = [
    "localhost",
    "127.0.0.1",
    f"localhost:{SMARTER_LOCAL_PORT}",
    f"127.0.0.1:{SMARTER_LOCAL_PORT}",
    # the React dev server of smarter-console.
    "localhost:5173",
    # the host of Django's test client.
    "testserver",
]
"""The hosts of a developer's own machine, which are always local: the dev server, the React dev server, Django's test client."""

SENSITIVE_FILES_AMNESTY_PATTERNS = (
    re.compile(r"^/$", re.IGNORECASE),
    re.compile(r"^/static(/.*)?$", re.IGNORECASE),
    re.compile(r"^/api/v\d+(\.\d+)?/.+", re.IGNORECASE),
    re.compile(r"^/api/web/.+", re.IGNORECASE),
    re.compile(r"^/dashboard(/.*)?$", re.IGNORECASE),
    re.compile(r"^/docs/manifest(/.*)?$", re.IGNORECASE),
    re.compile(r"^/docs/json-schema(/.*)?$", re.IGNORECASE),
    re.compile(r"^/config/?$", re.IGNORECASE),
    re.compile(r"^/login/?$", re.IGNORECASE),
    re.compile(r"^/admin/?$", re.IGNORECASE),
)
"""
The paths that the sensitive files middleware never blocks, even when they end like a sensitive file, a.

static set that no setting changes: the home page, static files,.

the apis, the dashboard, the manifest and JSON Schema docs, an LLMClient's ``/config/``, the sign-in page
and the admin.
"""
DOT_ENV_LOADED = load_dotenv()
"""True if .env file was loaded successfully."""

SERVICE_TYPE = str(os.environ.get("SERVICE_TYPE")).lower() if os.environ.get("SERVICE_TYPE") else None
"""
The kind of pod this process runs in, unvalidated, from the ``SERVICE_TYPE`` environment variable.

Read the validated value, ``smarter_settings.service_type``, instead: its docstring, and
:data:`smarter.common.conf.settings.platform.POD_KINDS`, list the kinds that the Helm chart and docker-compose set.
"""

__all__ = [
    "DEFAULT_MISSING_VALUE",
    "DOT_ENV_LOADED",
    "LOCAL_HOSTS",
    "SENSITIVE_FILES_AMNESTY_PATTERNS",
    "SERVICE_TYPE",
    "THE_EMPTY_SET",
]

_ENVIRONMENT = os.environ.get("SMARTER_ENVIRONMENT") or SmarterEnvironments.LOCAL
if not DOT_ENV_LOADED and _ENVIRONMENT == SmarterEnvironments.LOCAL:
    print(
        SmarterFormattedText.text(
            "\n"
            + "=" * 80
            + "\n[WARNING] .env file was NOT loaded! Environment variables may be missing.\n"
            + "Look for .env.example in the project root and follow the instructions that begin at the top of the file.\n"
            + "Settings values that are required (there are many) will be noted in this file.\n"
            + "=" * 80
            + "\n",
            SmarterFormattedText.DARK_RED,
        )
    )
