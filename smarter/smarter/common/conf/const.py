"""
This module contains constants used for Pydantic Settings.
"""

import os

from dotenv import load_dotenv

from smarter.common.const import SmarterEnvironments
from smarter.common.helpers.console_helpers import formatted_text_red

from .env import get_env

THE_EMPTY_SET = [None, "", "NULL", "None", "none", "null"]
DEFAULT_ROOT_DOMAIN = "example.com"
DOT_ENV_LOADED = load_dotenv()
"""
True if .env file was loaded successfully.
"""

SERVICE_TYPE = str(os.environ.get("SERVICE_TYPE")).lower() if os.environ.get("SERVICE_TYPE") else None
"""
Describes the type of service this instance is running as. valid values are: app, worker, beat.
This value can be set in .env or docker-compose.yml or set as an environment variable.
"""

__all__ = [
    "DEFAULT_ROOT_DOMAIN",
    "DOT_ENV_LOADED",
    "SERVICE_TYPE",
    "THE_EMPTY_SET",
]

DOT_ENV_LOADED = DOT_ENV_LOADED or get_env("ENV_LOADED", False)
if not DOT_ENV_LOADED and get_env("ENVIRONMENT", SmarterEnvironments.LOCAL) == SmarterEnvironments.LOCAL:
    print(
        formatted_text_red(
            "\n"
            + "=" * 80
            + "\n[WARNING] .env file was NOT loaded! Environment variables may be missing.\n"
            + "Look for .env.example in the project root and follow the instructions that begin at the top of the file.\n"
            + "Settings values that are required (there are many) will be noted in this file.\n"
            + "=" * 80
            + "\n"
        )
    )
