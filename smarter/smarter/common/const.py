# pylint: disable=E1101
"""A module containing constants for the OpenAI API."""
import importlib.util
import logging
import os
from pathlib import Path
from typing import Dict

import hcl2


logger = logging.getLogger(__name__)

SMARTER_ACCOUNT_NUMBER = "3141-5926-5359"
SMARTER_BETA_ACCOUNT_NUMBER = "4386-2072-3294"
SMARTER_UBC_ACCOUNT_NUMBER = "5680-6558-6577"
SMARTER_API_SUBDOMAIN = "api"
SMARTER_PLATFORM_SUBDOMAIN = "platform"
SMARTER_COMPANY_NAME = "Smarter"
SMARTER_EXAMPLE_CHATBOT_NAME = "example"
SMARTER_CUSTOMER_SUPPORT = "support@smarter.sh"

# The following are used in the React app
# to store the chatbot chat session key and debug mode settings
# as browser cookies. The React app has constants
# for these values as well which should be kept in sync.
SMARTER_CHAT_SESSION_KEY_NAME = "session_key"

SMARTER_DEFAULT_CACHE_TIMEOUT = 60 * 10  # 10 minutes


# Smarter Waffle Switches and Flags
class SmarterWaffleSwitches:
    """A class representing the fixed set of Waffle switches for the Smarter API."""

    SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING = "chatbot_api_view_logging"
    SMARTER_WAFFLE_SWITCH_CHATBOT_HELPER_LOGGING = "chatbothelper_logging"
    SMARTER_WAFFLE_SWITCH_REQUEST_MIXIN_LOGGING = "request_mixin_logging"
    SMARTER_WAFFLE_SWITCH_CHAT_LOGGING = "chat_logging"
    SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING = "csrf_middleware_logging"
    SMARTER_WAFFLE_SWITCH_JOURNAL = "journal"
    SMARTER_WAFFLE_SWITCH_SUPPRESS_FOR_CHATBOTS = "csrf_middleware_suppress_for_chatbots"
    SMARTER_WAFFLE_SWITCH_CHATAPP_VIEW_LOGGING = "chatapp_view_logging"
    SMARTER_WAFFLE_MANIFEST_LOGGING = "manifest_logging"
    SMARTER_WAFFLE_REACTAPP_DEBUG_MODE = "reactapp_debug_mode"

    @property
    def all(self):
        """Return all switches."""
        return [
            self.SMARTER_WAFFLE_SWITCH_CHATBOT_API_VIEW_LOGGING,
            self.SMARTER_WAFFLE_SWITCH_CHATBOT_HELPER_LOGGING,
            self.SMARTER_WAFFLE_SWITCH_CHAT_LOGGING,
            self.SMARTER_WAFFLE_SWITCH_MIDDLEWARE_LOGGING,
            self.SMARTER_WAFFLE_SWITCH_JOURNAL,
            self.SMARTER_WAFFLE_SWITCH_SUPPRESS_FOR_CHATBOTS,
            self.SMARTER_WAFFLE_SWITCH_CHATAPP_VIEW_LOGGING,
            self.SMARTER_WAFFLE_MANIFEST_LOGGING,
            self.SMARTER_WAFFLE_REACTAPP_DEBUG_MODE,
        ]


HERE = os.path.abspath(os.path.dirname(__file__))  # smarter/smarter/common
PROJECT_ROOT = str(Path(HERE).parent)  # smarter/smarter
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)  # smarter
TERRAFORM_ROOT = str(Path(PROJECT_ROOT).parent.parent)  # ./
REPO_ROOT = str(Path(PYTHON_ROOT).parent.parent)  # ./

TERRAFORM_TFVARS = os.path.join(TERRAFORM_ROOT, "terraform.tfvars")
if not os.path.exists(TERRAFORM_TFVARS):
    TERRAFORM_TFVARS = os.path.join(PROJECT_ROOT, "terraform.tfvars")

TFVARS = {}
IS_USING_TFVARS = False

try:
    with open(TERRAFORM_TFVARS, encoding="utf-8") as f:
        TFVARS = hcl2.load(f)
    IS_USING_TFVARS = True
except FileNotFoundError:
    logger.info("No terraform.tfvars file found. Using default values.")


def load_version() -> Dict[str, str]:
    """Stringify the __version__ module."""
    version_file_path = os.path.join(PROJECT_ROOT, "__version__.py")
    spec = importlib.util.spec_from_file_location("__version__", version_file_path)
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
