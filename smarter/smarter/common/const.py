# pylint: disable=E1101
"""
Constants of the platform's code.

This is for constants that are highly unlikely to change.
Anything else belongs in ``smarter_settings`` and/or Django settings, who's values are
substantially derived from the Helm chart and environment variables.
"""

import importlib.util
import os
from pathlib import Path
from typing import Dict

SMARTER_LOCAL_PORT = 9357
SMARTER_ACCOUNT_NUMBER = "3141-5926-5359"
SMARTER_API_SUBDOMAIN = "api"


# This is a custom attribute that can be added to the request
# to indicate that the request is an internal API request. This
# is used to bypass DRF authentication and permission checks in the API views.
SMARTER_IS_INTERNAL_API_REQUEST = "smarter_is_internal_api_request"


HERE = os.path.abspath(os.path.dirname(__file__))  # smarter/smarter/common
PROJECT_ROOT = str(Path(HERE).parent)  # smarter/smarter
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)  # smarter
REPO_ROOT = str(Path(PYTHON_ROOT).parent)  # ./


def load_version() -> Dict[str, str]:
    """Stringify the __version__ module."""
    version_file_path = os.path.join(PROJECT_ROOT, "__version__.py")
    spec = importlib.util.spec_from_file_location("__version__", version_file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load version file: {version_file_path}")
    version_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(version_module)
    return version_module.__dict__


VERSION = load_version()
AUTHOR = "Lawrence P. McDaniel - https://lawrencemcdaniel.com"


# pylint: disable=too-few-public-methods
class SmarterEnvironments:
    """A class representing the fixed set environments for the Smarter API."""

    LOCAL = "local"
    ALPHA = "alpha"
    BETA = "beta"
    NEXT = "next"
    PROD = "prod"
    all = [LOCAL, ALPHA, BETA, NEXT, PROD]
    aws_environments = [ALPHA, BETA, NEXT, PROD]


class SmarterHttpMethods:
    """A class representing the fixed set of HTTP methods used in the Smarter API."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
    all = [GET, POST, PUT, PATCH, DELETE]
