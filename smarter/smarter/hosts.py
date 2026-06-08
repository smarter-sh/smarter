"""
This module defines the complete set of host patterns for the Smarter Framework,.

organized by logical group.

Web Console Hosts
-----------------
.. list-table:: Web Console Hosts
   :header-rows: 1

   * - Host
     - Description
   * - localhost:9357
     - For local development via http://localhost:9357/
   * - 127.0.0.1:9357
     - For local development via http://127.0.0.1:9357/
   * - platform.example.com
     - Main production platform console.
   * - alpha.platform.example.com
     - Alpha environment for the platform console.
   * - beta.platform.example.com
     - Beta environment for the platform console.
   * - next.platform.example.com
     - Next environment for the platform console.

API Subdomain Hosts
-------------------
.. list-table:: API Subdomain Hosts
   :header-rows: 1

   * - Host
     - Description
   * - api.localhost:9357
     - Local API endpoint for http://api.localhost:9357/
   * - api.127.0.0.1:9357
     - Local API endpoint for http://api.127.0.0.1:9357/
   * - api.example.com
     - Main production API endpoint.
   * - alpha.api.example.com
     - Alpha environment for the API.
   * - beta.api.example.com
     - Beta environment for the API.
   * - next.api.example.com
     - Next environment for the API.

Named LLMClient Hosts
-------------------
.. list-table:: Named LLMClient Hosts
   :header-rows: 1

   * - Host
     - Description
   * - <llm_client_name>.<account_number>.api.example.com
     - Deployed named llm_client on production API.
   * - <llm_client_name>.<account_number>.alpha.api.example.com
     - Deployed named llm_client on alpha API.
   * - <llm_client_name>.<account_number>.beta.api.example.com
     - Deployed named llm_client on beta API.
   * - <llm_client_name>.<account_number>.next.api.example.com
     - Deployed named llm_client on next API.

Each host pattern is mapped to the appropriate Django URL configuration for the
console, API, or llm_client endpoints, and supports multiple environments for
development, staging, and production.
"""

from django_hosts import host, patterns

from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.urls import api as smarter_api_urls
from smarter.urls import console as smarter_console_urls
from smarter.urls import llm_clients as smarter_llm_clients_urls

host_patterns = patterns(
    "",
    # -------------------------------------------------------------------------
    # web console
    # -------------------------------------------------------------------------
    host(r"localhost:9357", smarter_console_urls, name="localhost"),  # for http://localhost:9357/
    host(r"127.0.0.1:9357", smarter_console_urls, name="127001"),  # for http://127.0.0.1:9357/
    host(
        rf"{smarter_settings.platform_subdomain}.{smarter_settings.root_domain}",
        smarter_console_urls,
        name=smarter_settings.platform_subdomain,
    ),  # for https://platform.example.com/
    host(
        rf"{SmarterEnvironments.ALPHA}.{smarter_settings.platform_subdomain}.{smarter_settings.root_domain}",
        smarter_console_urls,
        name=f"{SmarterEnvironments.ALPHA}_{smarter_settings.platform_subdomain}",
    ),  # for https://alpha.platform.example.com/
    host(
        rf"{SmarterEnvironments.BETA}.{smarter_settings.platform_subdomain}.{smarter_settings.root_domain}",
        smarter_console_urls,
        name=f"{SmarterEnvironments.BETA}_{smarter_settings.platform_subdomain}",
    ),  # for https://beta.platform.example.com/
    host(
        rf"{SmarterEnvironments.NEXT}.{smarter_settings.platform_subdomain}.{smarter_settings.root_domain}",
        smarter_console_urls,
        name=f"{SmarterEnvironments.NEXT}_{smarter_settings.platform_subdomain}",
    ),  # for https://next.platform.example.com/
    # -------------------------------------------------------------------------
    # API subdomains
    # -------------------------------------------------------------------------
    host(r"api.localhost:9357", smarter_api_urls, name="api_localhost"),  # for http://api.localhost:9357/
    host(r"api.127.0.0.1:9357", smarter_api_urls, name="api_127001"),  # for http://api.127.0.0.1:9357/
    host(
        rf"{smarter_settings.api_subdomain}.{smarter_settings.root_domain}",
        smarter_api_urls,
        name=smarter_settings.api_subdomain,
    ),  # for https://api.platform.example.com/
    host(
        rf"{SmarterEnvironments.ALPHA}.{smarter_settings.api_subdomain}.{smarter_settings.root_domain}",
        smarter_api_urls,
        name=f"{SmarterEnvironments.ALPHA}_{smarter_settings.api_subdomain}",
    ),  # for https://alpha.api.platform.example.com/
    host(
        rf"{SmarterEnvironments.BETA}.{smarter_settings.api_subdomain}.{smarter_settings.root_domain}",
        smarter_api_urls,
        name=f"{SmarterEnvironments.BETA}_{smarter_settings.api_subdomain}",
    ),  # for https://beta.api.platform.example.com/
    host(
        rf"{SmarterEnvironments.NEXT}.{smarter_settings.api_subdomain}.{smarter_settings.root_domain}",
        smarter_api_urls,
        name=f"{SmarterEnvironments.NEXT}_{smarter_settings.api_subdomain}",
    ),  # for https://next.api.platform.example.com/
    # -------------------------------------------------------------------------
    # Deployed named LLMClients
    # eg https://education.3141-5926-5359.alpha.api.example.com/
    # -------------------------------------------------------------------------
    host(
        rf"(?P<llm_client_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{smarter_settings.api_subdomain}.{smarter_settings.root_domain}",
        smarter_llm_clients_urls,
        name="llm_client_named_api",
    ),  # for https://<llm_client_name>.<account_number>.api.platform.example.com/
    host(
        rf"(?P<llm_client_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{SmarterEnvironments.ALPHA}.{smarter_settings.api_subdomain}.{smarter_settings.root_domain}",
        smarter_llm_clients_urls,
        name=f"llm_client_named_{SmarterEnvironments.ALPHA}_api",
    ),  # for https://<llm_client_name>.<account_number>.alpha.api.platform.example.com/
    host(
        rf"(?P<llm_client_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{SmarterEnvironments.BETA}.{smarter_settings.api_subdomain}.{smarter_settings.root_domain}",
        smarter_llm_clients_urls,
        name=f"llm_client_named_{SmarterEnvironments.BETA}_api",
    ),  # for https://<llm_client_name>.<account_number>.beta.api.platform.example.com/
    host(
        rf"(?P<llm_client_name>[\w\-]+)\.(?P<account_number>\d{{4}}-\d{{4}})\.{SmarterEnvironments.NEXT}.{smarter_settings.api_subdomain}.{smarter_settings.root_domain}",
        smarter_llm_clients_urls,
        name=f"llm_client_named_{SmarterEnvironments.NEXT}_api",
    ),  # for https://<llm_client_name>.<account_number>.next.api.platform.example.com/
)

__all__ = ["host_patterns"]
