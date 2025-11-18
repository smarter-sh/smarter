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
from smarter.urls import api as smarter_api_urls
from smarter.urls import chatbots as smarter_chatbots_urls
from smarter.urls import console as smarter_console_urls


host_patterns = patterns(
    "",
    # -------------------------------------------------------------------------
    # web console
    # -------------------------------------------------------------------------
    host(r"localhost:8000", smarter_console_urls, name="localhost"),  # for http://localhost:8000/
    host(r"127.0.0.1:8000", smarter_console_urls, name="127001"),  # for http://127.0.0.1:8000/
    host(
        rf"{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
        smarter_console_urls,
        name=SMARTER_PLATFORM_SUBDOMAIN,
    ),  # for https://platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.ALPHA}.{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
        smarter_console_urls,
        name=f"{SmarterEnvironments.ALPHA}_{SMARTER_PLATFORM_SUBDOMAIN}",
    ),  # for https://alpha.platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.BETA}.{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
        smarter_console_urls,
        name=f"{SmarterEnvironments.BETA}_{SMARTER_PLATFORM_SUBDOMAIN}",
    ),  # for https://beta.platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.NEXT}.{SMARTER_PLATFORM_SUBDOMAIN}.{smarter_settings.root_domain}",
        smarter_console_urls,
        name=f"{SmarterEnvironments.NEXT}_{SMARTER_PLATFORM_SUBDOMAIN}",
    ),  # for https://next.platform.smarter.sh/
    # -------------------------------------------------------------------------
    # API subdomains
    # -------------------------------------------------------------------------
    host(r"api.localhost:8000", smarter_api_urls, name="api_localhost"),  # for http://api.localhost:8000/
    host(r"api.127.0.0.1:8000", smarter_api_urls, name="api_127001"),  # for http://api.127.0.0.1:8000/
    host(
        rf"{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}", smarter_api_urls, name=SMARTER_API_SUBDOMAIN
    ),  # for https://api.platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.ALPHA}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        smarter_api_urls,
        name=f"{SmarterEnvironments.ALPHA}_{SMARTER_API_SUBDOMAIN}",
    ),  # for https://alpha.api.platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.BETA}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        smarter_api_urls,
        name=f"{SmarterEnvironments.BETA}_{SMARTER_API_SUBDOMAIN}",
    ),  # for https://beta.api.platform.smarter.sh/
    host(
        rf"{SmarterEnvironments.NEXT}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        smarter_api_urls,
        name=f"{SmarterEnvironments.NEXT}_{SMARTER_API_SUBDOMAIN}",
    ),  # for https://next.api.platform.smarter.sh/
    # -------------------------------------------------------------------------
    # Deployed named ChatBots
    # eg https://education.3141-5926-5359.alpha.api.smarter.sh/
    # -------------------------------------------------------------------------
    host(
        rf"(?P<chatbot_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        smarter_chatbots_urls,
        name="chatbot_named_api",
    ),  # for https://<chatbot_name>.<account_number>.api.platform.smarter.sh/
    host(
        rf"(?P<chatbot_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{SmarterEnvironments.ALPHA}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        smarter_chatbots_urls,
        name=f"chatbot_named_{SmarterEnvironments.ALPHA}_api",
    ),  # for https://<chatbot_name>.<account_number>.alpha.api.platform.smarter.sh/
    host(
        rf"(?P<chatbot_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{SmarterEnvironments.BETA}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        smarter_chatbots_urls,
        name=f"chatbot_named_{SmarterEnvironments.BETA}_api",
    ),  # for https://<chatbot_name>.<account_number>.beta.api.platform.smarter.sh/
    host(
        rf"(?P<chatbot_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{SmarterEnvironments.NEXT}.{SMARTER_API_SUBDOMAIN}.{smarter_settings.root_domain}",
        smarter_chatbots_urls,
        name=f"chatbot_named_{SmarterEnvironments.NEXT}_api",
    ),  # for https://<chatbot_name>.<account_number>.next.api.platform.smarter.sh/
)

__all__ = ["host_patterns"]
