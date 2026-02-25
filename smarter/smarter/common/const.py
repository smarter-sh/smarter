# pylint: disable=E1101
"""A module containing constants for the OpenAI API."""

import importlib.util
import logging
import os
from pathlib import Path
from typing import Dict

import hcl2

logger = logging.getLogger(__name__)

SMARTER_LOCAL_PORT = 9357
SMARTER_ADMIN_USERNAME = "admin"
SMARTER_ACCOUNT_NUMBER = "3141-5926-5359"
SMARTER_BETA_ACCOUNT_NUMBER = "4386-2072-3294"
SMARTER_UBC_ACCOUNT_NUMBER = "5680-6558-6577"
SMARTER_API_SUBDOMAIN = "api"
SMARTER_PLATFORM_DEFAULT_SUBDOMAIN = "platform"
SMARTER_COMPANY_NAME = "Lawrence P. McDaniel"
SMARTER_PRODUCT_NAME = "The Smarter Project"
SMARTER_PRODUCT_DESCRIPTION = "An open source, no-code AI authoring platform designed for instructional use."
SMARTER_EXAMPLE_CHATBOT_NAME = "example"
SMARTER_CUSTOMER_SUPPORT_EMAIL = "lpm0073@gmail.com"
SMARTER_CONTACT_EMAIL = "lpm0073@gmail.com"
SMARTER_CUSTOMER_SUPPORT_PHONE = "+1 (617) 834-6172"
SMARTER_PROJECT_ROOT_DOMAIN = "smarter.sh"
SMARTER_PROJECT_WEBSITE_URL = f"https://{SMARTER_PROJECT_ROOT_DOMAIN}"
SMARTER_PROJECT_CDN_URL = f"https://cdn.{SMARTER_PROJECT_ROOT_DOMAIN}"
SMARTER_PROJECT_DOCS_URL = f"https://docs.{SMARTER_PROJECT_ROOT_DOMAIN}"
SMARTER_BUG_REPORT_URL = "https://github.com/smarter-sh/smarter/issues."
SMARTER_DEFAULT_REACTJS_APP_LOADER_URL = "https://cdn.smarter.sh/ui-chat/app-loader.js"

# The following are used in the React app
# to store the chatbot chat session key and debug mode settings
# as browser cookies. The React app has constants
# for these values as well which should be kept in sync.
SMARTER_CHAT_SESSION_KEY_NAME = "session_key"

# This is a custom attribute that can be added to the request
# to indicate that the request is an internal API request. This
# is used to bypass DRF authentication and permission checks in the API views.
SMARTER_IS_INTERNAL_API_REQUEST = "smarter_is_internal_api_request"

# Default maximum lifetime for Smarter API keys in days.
SMARTER_API_KEY_MAX_LIFETIME_DAYS = 365 * 3  # 3 years

# Default path to the Smarter Chat Component app-loader.js script
# used to load the React chat component into a web page.
SMARTER_DEFAULT_APP_LOADER_PATH = "/ui-chat/app-loader.js"


HERE = os.path.abspath(os.path.dirname(__file__))  # smarter/smarter/common
PROJECT_ROOT = str(Path(HERE).parent)  # smarter/smarter
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)  # smarter
REPO_ROOT = str(Path(PYTHON_ROOT).parent)  # ./
TERRAFORM_ROOT = str(Path(PROJECT_ROOT).parent.parent)  # ./

TERRAFORM_TFVARS = os.path.join(TERRAFORM_ROOT, "terraform.tfvars")
if not os.path.exists(TERRAFORM_TFVARS):
    TERRAFORM_TFVARS = os.path.join(PROJECT_ROOT, "terraform.tfvars")

IS_USING_TFVARS = False

try:
    with open(TERRAFORM_TFVARS, encoding="utf-8") as f:
        TFVARS = hcl2.load(f)
    IS_USING_TFVARS = True
except FileNotFoundError:
    logger.debug("No terraform.tfvars file found. Using default values.")


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


LANGCHAIN_MESSAGE_HISTORY_ROLES = ["user", "assistant"]
