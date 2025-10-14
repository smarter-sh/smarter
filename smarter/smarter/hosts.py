"""
Django Hosts configuration.
"""

from django_hosts import host, patterns

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import (
    SMARTER_API_SUBDOMAIN,
    SMARTER_PLATFORM_SUBDOMAIN,
    SmarterEnvironments,
)


SMARTER_URLS = "smarter.urls"
SMARTER_URLS_API_MODULE = f"{SMARTER_URLS}.api"
SMARTER_URLS_NAMED_CHATBOTS_MODULE = f"{SMARTER_URLS}.chatbots"
SMARTER_URLS_MODULE = f"{SMARTER_URLS}.console"

host_patterns = patterns(
    "",
    # -------------------------------------------------------------------------
    # web console
    # -------------------------------------------------------------------------
    host(
        rf"{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
        SMARTER_URLS_MODULE,
        name=SMARTER_PLATFORM_SUBDOMAIN,
    ),  # for https://platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.ALPHA}.{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
        SMARTER_URLS_MODULE,
        name=f"{SmarterEnvironments.ALPHA}_{SMARTER_PLATFORM_SUBDOMAIN}",
    ),  # for https://alpha.platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.BETA}.{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
        SMARTER_URLS_MODULE,
        name=f"{SmarterEnvironments.BETA}_{SMARTER_PLATFORM_SUBDOMAIN}",
    ),  # for https://beta.platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.NEXT}.{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
        SMARTER_URLS_MODULE,
        name=f"{SmarterEnvironments.NEXT}_{SMARTER_PLATFORM_SUBDOMAIN}",
    ),  # for https://next.platform.smarter.sh/
    # -------------------------------------------------------------------------
    # API subdomains
    # -------------------------------------------------------------------------
    host(
        rf"{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}", SMARTER_URLS_API_MODULE, name=SMARTER_API_SUBDOMAIN
    ),  # for https://api.platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.ALPHA}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        SMARTER_URLS_API_MODULE,
        name=f"{SmarterEnvironments.ALPHA}_{SMARTER_API_SUBDOMAIN}",
    ),  # for https://alpha.api.platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.BETA}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        SMARTER_URLS_API_MODULE,
        name=f"{SmarterEnvironments.BETA}_{SMARTER_API_SUBDOMAIN}",
    ),  # for https://beta.api.platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.NEXT}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        SMARTER_URLS_API_MODULE,
        name=f"{SmarterEnvironments.NEXT}_{SMARTER_API_SUBDOMAIN}",
    ),  # for https://next.api.platform.smarter.sh/
    # -------------------------------------------------------------------------
    # Deployed named ChatBots
    # eg https://education.3141-5926-5359.alpha.api.smarter.sh/
    # -------------------------------------------------------------------------
    host(
        rf"(?P<chatbot_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        SMARTER_URLS_NAMED_CHATBOTS_MODULE,
        name="chatbot_named_api",
    ),  # for https://<chatbot_name>.<account_number>.api.platform.smarter.sh/
    host(
        rf"(?P<chatbot_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{SmarterEnvironments.ALPHA}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        SMARTER_URLS_NAMED_CHATBOTS_MODULE,
        name=f"chatbot_named_{SmarterEnvironments.ALPHA}_api",
    ),  # for https://<chatbot_name>.<account_number>.alpha.api.platform.smarter.sh/
    host(
        rf"(?P<chatbot_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{SmarterEnvironments.BETA}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        SMARTER_URLS_NAMED_CHATBOTS_MODULE,
        name=f"chatbot_named_{SmarterEnvironments.BETA}_api",
    ),  # for https://<chatbot_name>.<account_number>.beta.api.platform.smarter.sh/
    host(
        rf"(?P<chatbot_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{SmarterEnvironments.NEXT}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        SMARTER_URLS_NAMED_CHATBOTS_MODULE,
        name=f"chatbot_named_{SmarterEnvironments.NEXT}_api",
    ),  # for https://<chatbot_name>.<account_number>.next.api.platform.smarter.sh/
)

__all__ = ["host_patterns"]
