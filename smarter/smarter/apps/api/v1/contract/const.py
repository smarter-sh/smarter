"""Constants of the Smarter api contract: the SAM JSON Schemas, and the OpenAPI document of the Smarter api."""

import os

from smarter.common.const import (
    SMARTER_PLATFORM_DEFAULT_SUBDOMAIN,
    SMARTER_PROJECT_ROOT_DOMAIN,
)

HERE = os.path.abspath(os.path.dirname(__file__))

SAM_SCHEMA_DIR = os.path.join(HERE, "sam")
"""The folder of the SAM JSON Schemas, one ``<Kind>.schema.json`` per kind."""

SAM_SCHEMA_SUFFIX = ".schema.json"
"""The suffix of a SAM JSON Schema's file name, after its kind."""

SAM_EXAMPLE_SUFFIX = ".example.json"
"""The suffix of a SAM example manifest's file name, after its kind."""

SAM_EXAMPLE_HOST = "localhost"
"""The host of the in-process request that renders an example manifest.

Every environment allows it.
"""

OPENAPI_PATH = os.path.join(HERE, "openapi.json")
"""The OpenAPI document of the Smarter api, generated from :mod:`smarter.apps.api.v1.contract.openapi`."""

OPENAPI_VERSION = "3.1.0"
"""The version of the OpenAPI Specification that the document follows.

3.1 schemas are JSON Schema 2020-12.
"""

JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
"""The dialect of the document's schemas, and of the SAM JSON Schemas."""

API_VERSION = "v1"
"""
The document's ``info.version``: the version of the api, not of the platform.

The platform's version changes with every release, which would make the committed document stale.
"""

DEFAULT_PLATFORM_URL = f"https://{SMARTER_PLATFORM_DEFAULT_SUBDOMAIN}.{SMARTER_PROJECT_ROOT_DOMAIN}"
"""The default of the document's ``platform`` server variable.

Each Smarter installation has its own.
"""

LOCAL_PLATFORM_URL = "http://localhost:9357"
"""The platform of a local development environment."""
