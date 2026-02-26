# pylint: disable=W0613
"""
smarter.apps.dashboard.context_processors
=========================================

This module provides custom Django context processors for the Smarter dashboard application. These context processors are designed to inject additional context variables into templates that inherit from ``base.html``, supporting the dynamic rendering of dashboard and branding information throughout the application.

Overview
--------

The context processors in this module serve the following purposes:

- **Dashboard Context**: Supplies user-specific and application-wide metadata, such as the current user's email, username, role flags, product version, and resource counts (e.g., chatbots, plugins, API keys, custom domains, connections, and secrets). This enables the dashboard to display personalized and up-to-date information for each authenticated user.

- **Branding Context**: Provides organization-specific branding details, including support contact information, corporate name, address, social media links, and copyright notices. This ensures consistent branding and support information across all dashboard templates.

- **Cache Busting**: Adds a cache-busting query parameter to static asset URLs during local development, preventing browsers from serving outdated static files.

Caching
-------

Many of the resource-counting functions in this module are decorated with a caching mechanism to reduce database load and improve performance. The cache timeout is configurable and set to 60 seconds by default.

Usage
-----

To use these context processors, add their import paths to the ``TEMPLATES['OPTIONS']['context_processors']`` list in your Django settings. This will make the provided context variables available in all templates rendered by Django that inherit from ``base.html``.

Note
----

This module does not document individual function signatures or arguments, as these are automatically included by Sphinx's ``automodule`` directive. For detailed API documentation, refer to the generated documentation for each function.
"""

import time
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from urllib.parse import urljoin

from django.urls import reverse

from smarter.__version__ import __version__
from smarter.apps.account.models import (
    Secret,
    User,
    UserProfile,
    get_resolved_user,
)
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.chatbot.models import ChatBot, ChatBotAPIKey, ChatBotCustomDomain
from smarter.apps.chatbot.utils import get_cached_chatbots_for_user_profile
from smarter.apps.plugin.models import (
    ConnectionBase,
    PluginMeta,
)
from smarter.apps.provider.models import Provider
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_PRODUCT_DESCRIPTION, SMARTER_PRODUCT_NAME
from smarter.common.utils import smarter_build_absolute_uri
from smarter.lib.cache import cache_results

if TYPE_CHECKING:
    from django.http import HttpRequest


CACHE_TIMEOUT = 60  # 1 minute


def get_pending_deployments(user_profile: UserProfile) -> int:
    """
    Returns the number of chatbot deployments that are pending for the specified user.

    This function queries the database for all chatbot instances associated with the user's account that have not yet been deployed. The result is used to inform users of outstanding deployment actions required on their dashboard.

    The result is cached for a short duration to minimize database load and improve dashboard responsiveness.

    :param user: The user whose pending deployments are to be counted.
    :type user: User
    :return: The number of pending chatbot deployments for the user.
    :rtype: int
    """

    @cache_results(timeout=CACHE_TIMEOUT)
    def _get_pending_deployments(user_profile_id: int) -> int:
        return ChatBot.objects.filter(user_profile__id=user_profile_id, deployed=False).count() or 0

    return _get_pending_deployments(user_profile.id)


def get_chatbots(user_profile: UserProfile) -> int:
    """
    Returns the total number of chatbots associated with the specified user.

    This function queries the database for all chatbot instances linked to the user's account, regardless of deployment status. The resulting count is used to display the user's available chatbots on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user: The user whose chatbots are to be counted.
    :type user: User
    :return: The number of chatbots belonging to the user.
    :rtype: int
    """

    chatbots = get_cached_chatbots_for_user_profile(user_profile_id=user_profile.id)
    return len(chatbots)


def get_plugins(user_profile: UserProfile) -> int:
    """
    Returns the total number of plugins associated with the specified user.

    This function queries the database for all plugin metadata records linked to the user's account. The resulting count is used to display the user's available plugins on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user: The user whose plugins are to be counted.
    :type user: User
    :return: The number of plugins belonging to the user.
    :rtype: int
    """

    retval = PluginMeta.get_cached_plugins_for_user_profile_id(user_profile_id=user_profile.id)
    return len(retval)


def get_api_keys(user_profile: UserProfile) -> int:
    """
    Returns the total number of API keys associated with the specified user.

    This function queries the database for all API key records linked to chatbots owned by the user's account. The resulting count is used to display the user's available API keys on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user: The user whose API keys are to be counted.
    :type user: User
    :return: The number of API keys belonging to the user.
    :rtype: int
    """

    @cache_results(timeout=CACHE_TIMEOUT)
    def _get_api_keys(user_profile_id: int) -> int:
        return ChatBotAPIKey.objects.filter(chatbot__user_profile__id=user_profile_id).count() or 0

    return _get_api_keys(user_profile.id)


def get_custom_domains(user_profile: UserProfile) -> int:
    """
    Returns the total number of custom domains associated with the specified user.

    This function queries the database for all custom domain records linked to chatbots owned by the user's account. The resulting count is used to display the user's available custom domains on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user: The user whose custom domains are to be counted.
    :type user: User
    :return: The number of custom domains belonging to the user.
    :rtype: int
    """

    @cache_results(timeout=CACHE_TIMEOUT)
    def _get_custom_domains(user_profile_id: int) -> int:
        return ChatBotCustomDomain.objects.filter(chatbot__user_profile__id=user_profile_id).count() or 0

    return _get_custom_domains(user_profile.id)


def get_connections(user_profile: UserProfile) -> int:
    """
    Returns the total number of API and SQL connections associated with the specified user.

    This function queries the database for all API and SQL connection records linked to the user's account. The resulting count is used to display the user's available connections on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user: The user whose connections are to be counted.
    :type user: User
    :return: The number of API and SQL connections belonging to the user.
    :rtype: int
    """
    retval = ConnectionBase.get_cached_connections_for_user(user_profile.user)
    return len(retval)


@cache_results(timeout=CACHE_TIMEOUT)
def get_secrets(user_profile: UserProfile) -> int:
    """
    Returns the total number of secrets associated with the specified user's profile.

    This function queries the database for all secret records linked to the user's profile. The resulting count is used to display the user's available secrets on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user_profile: The user profile whose secrets are to be counted.
    :type user_profile: UserProfile
    :return: The number of secrets belonging to the user profile.
    :rtype: int
    """
    return Secret.objects.filter(user_profile=user_profile).count() if user_profile else 0


@cache_results(timeout=CACHE_TIMEOUT)
def get_providers(user_profile: UserProfile) -> int:
    """
    Returns the total number of providers associated with the specified user's account.

    This function queries the database for all provider records linked to the user's account. The resulting count is used to display the user's available providers on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user_profile: The user profile whose providers are to be counted.
    :type user_profile: UserProfile
    :return: The number of providers belonging to the user account + those belonging to the official smarter admin.
    :rtype: int
    """
    retval = Provider.get_cached_providers_for_user(user_profile.user)
    return len(retval)


def file_drop_zone(request: "HttpRequest") -> dict:
    """
    Provides context for enabling file drop zone functionality in the dashboard.

    This context processor injects a variable into the template context that can be used to enable or disable file drop zone features in the dashboard interface. This is useful for enhancing user experience by allowing drag-and-drop file uploads.

    :param request: The HTTP request object.
    :type request: "HttpRequest"
    :return: A dictionary containing the file drop zone context variable.
    :rtype: dict
    """
    return {
        "drop_zone": {
            "file_drop_zone_enabled": smarter_settings.file_drop_zone_enabled,
            "api_apply_path": reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.apply),
            "workbench_list_path": reverse("prompt_workbench:listview"),
            "plugin_list_path": reverse("plugin:plugin_listview"),
            "connection_list_path": reverse("plugin:connection_listview"),
            "provider_list_path": reverse("provider:provider_listview"),
        }
    }


def base(request: "HttpRequest") -> dict:
    """
    Provides the base context for all templates inheriting from ``base.html`` in the Smarter dashboard.

    This context processor injects a comprehensive set of user-specific and application-wide variables into the template context. These variables include user identity, role flags, product metadata, and resource counts (such as chatbots, plugins, API keys, custom domains, connections, and secrets). The context is used to render the dashboard layout and personalize the user experience.

    The resource counts are cached for performance, and the context is dynamically constructed based on the authenticated user's account and profile.

    :param request: The HTTP request object.
    :type request: "HttpRequest"
    :return: A dictionary containing the dashboard context variables.
    :rtype: dict
    """
    user = request.user
    resolved_user = get_resolved_user(user)
    user_profile: Optional[UserProfile] = None
    if resolved_user and getattr(resolved_user, "is_authenticated", False):
        user_profile = UserProfile.objects.filter(user=resolved_user).first()

    @cache_results(timeout=CACHE_TIMEOUT)
    def get_cached_context(user: Optional[User]) -> dict:
        """
        Constructs and returns the cached dashboard context for the specified user.

        This helper function assembles a dictionary of dashboard context variables, including user identity, role flags, product metadata, and resource counts. It is decorated with a cache to optimize performance and minimize redundant database queries.

        The context is tailored to the authenticated user and is used by the main ``base`` context processor to populate the dashboard template.

        :param user: The user for whom the dashboard context is being constructed.
        :type user: Optional[User]
        :return: A dictionary containing the dashboard context variables for the user.
        :rtype: dict
        """
        current_year = datetime.now().year
        user_email = "anonymous@mail.edu"
        username = "anonymous"
        is_superuser = False
        is_staff = False
        if user_profile and user_profile.user.is_authenticated:
            try:
                user_email = user_profile.user.email
                username = user_profile.user.username
                is_superuser = user_profile.user.is_superuser
                is_staff = user_profile.user.is_staff
            except AttributeError:
                # technically, this is supposed to be impossible due to the is_authenticated check
                pass

        cached_context = {
            "dashboard": {
                "user_email": user_email,
                "username": username,
                "is_superuser": is_superuser,
                "is_staff": is_staff,
                "profile_image_url": user_profile.profile_image_url if user_profile else "",
                "first_name": user_profile.user.first_name if user_profile else "",
                "last_name": user_profile.user.last_name if user_profile else "",
                "product_name": SMARTER_PRODUCT_NAME,
                "company_name": smarter_settings.root_domain,
                "smarter_version": "v" + __version__,
                "current_year": current_year,
                "my_resources_pending_deployments": (
                    get_pending_deployments(user_profile=user_profile) if user_profile else 0
                ),
                "my_resources_chatbots": get_chatbots(user_profile=user_profile) if user_profile else 0,
                "my_resources_plugins": get_plugins(user_profile=user_profile) if user_profile else 0,
                "my_resources_api_keys": get_api_keys(user_profile=user_profile) if user_profile else 0,
                "my_resources_custom_domains": get_custom_domains(user_profile=user_profile) if user_profile else 0,
                "my_resources_connections": get_connections(user_profile=user_profile) if user_profile else 0,
                "my_resources_secrets": get_secrets(user_profile=user_profile) if user_profile else 0,
                "my_resources_providers": get_providers(user_profile=user_profile) if user_profile else 0,
            }
        }
        return cached_context

    context = get_cached_context(user=resolved_user)  # type: ignore[assignment]
    return context


def branding(request: "HttpRequest") -> dict:
    """
    Provides organization-specific branding context for dashboard templates.

    This context processor injects a comprehensive set of branding and support variables into the template context for all pages inheriting from ``base.html``. These variables ensure that consistent corporate identity, contact, and support information are available throughout the dashboard user interface.

    The context includes:

    - The root URL of the application, suitable for constructing absolute links.
    - Support contact details, such as phone number and email address, for user assistance.
    - Corporate name and physical address, for legal and informational display.
    - General contact information and published support hours.
    - A copyright notice, dynamically including the current year and corporate name.
    - Social media profile URLs (Facebook, Twitter, LinkedIn) for brand presence and outreach.

    All values are sourced from Django settings, allowing for easy customization and environment-specific overrides.

    Example usage in a Django template::

        {{ branding.corporate_name }}
        {{ branding.support_email }}
        {{ branding.copyright }}

    This processor is intended to be added to the ``TEMPLATES['OPTIONS']['context_processors']`` list in your Django settings, making the ``branding`` context variable available in all templates rendered by Django that inherit from ``base.html``.
    """
    current_year = datetime.now().year
    root_url = request.build_absolute_uri("/").rstrip("/")
    context = {
        "branding": {
            "canonical": request.path,
            "root_url": root_url,
            "corporate_name": smarter_settings.branding_corporate_name,
            "corporate_address": smarter_settings.branding_address,
            "support_email": smarter_settings.branding_support_email,
            "contact_url": smarter_settings.branding_contact_url,
            "support_hours": smarter_settings.branding_support_hours,
            "support_phone_number": smarter_settings.branding_support_phone_number,
            "copyright": f"© {current_year} {smarter_settings.branding_corporate_name}. All rights reserved.",
            "og_url": smarter_build_absolute_uri(request),
            "og_image": "https://cdn.smarter.sh/cms/img/smarter_og_image.png",
            "url_facebook": smarter_settings.branding_url_facebook,
            "url_twitter": smarter_settings.branding_url_twitter,
            "url_linkedin": smarter_settings.branding_url_linkedin,
            "smarter_logo": smarter_settings.logo,
            "smarter_product_name": SMARTER_PRODUCT_NAME,
            "smarter_product_description": SMARTER_PRODUCT_DESCRIPTION,
            "smarter_marketing_site_url": smarter_settings.marketing_site_url,
            "smarter_home_url": "/",
            "smarter_project_website_url": smarter_settings.smarter_project_website_url,
            "smarter_project_cdn_url": smarter_settings.smarter_project_cdn_url,
            "smarter_project_docs_url": smarter_settings.smarter_project_docs_url,
            "cdn_logo_url": urljoin(smarter_settings.smarter_project_cdn_url, "images/logo/smarter-crop.png"),
            "login_url": urljoin(smarter_settings.environment_url, "/login/"),
            "learn_url": smarter_settings.smarter_project_docs_url,
            "workbench_exmample_url": urljoin(smarter_settings.environment_url, "/workbench/smarter/chat/"),
        }
    }
    return context


def footer(request: "HttpRequest") -> dict[str, dict[str, str]]:
    """
    Provides organization-specific legal context for dashboard templates.

    This context processor injects legal and compliance-related variables into the template context for all pages inheriting from ``base.html``. These variables ensure that consistent legal information, such as terms of service, privacy policy, and cookie policy URLs, are available throughout the dashboard user interface.

    The context includes:

    - URLs for the terms of service, privacy policy, and cookie policy documents.
    - A dynamically generated copyright notice that includes the current year and corporate name.

    All values are sourced from Django settings, allowing for easy customization and environment-specific overrides.

    Example usage in a Django template::

        {{ footer.legal_url }}
        {{ footer.plans_url }}
        {{ footer.contact_url }}
    """

    context = {
        "footer": {
            "about_url": smarter_settings.marketing_site_url,
            "support_url": smarter_settings.marketing_site_url,
            "legal_url": urljoin(str(smarter_settings.marketing_site_url), "legal"),
            "plans_url": smarter_settings.marketing_site_url,
            "contact_url": "https://lawrencemcdaniel.com/contact/",
        }
    }
    return context


def cache_buster(request) -> dict:
    """
    Adds a cache-busting query parameter to static asset URLs during development.

    This context processor is intended for use in local development environments to ensure that browsers do not serve outdated versions of static files (such as JavaScript, CSS, or images) from cache. It injects a ``cache_buster`` variable into the template context, which can be appended as a query parameter to static asset URLs. The value is a version string based on the current timestamp, guaranteeing uniqueness on each page load.

    Example usage in a Django template::

        <script src="{{ STATIC_URL }}main.js?{{ cache_buster }}"></script>

    This approach is especially useful when making frequent changes to static assets during development, as it forces the browser to fetch the latest version every time the page is reloaded. In production, this processor is typically disabled or omitted to allow for proper static file caching and performance optimization.

    The ``cache_buster`` variable is a string in the format ``v=<timestamp>``.
    """
    return {"cache_buster": "v=" + str(time.time())}


def prompt_list_context(request: "HttpRequest") -> dict:
    """
    Provides default placeholder context for prompt list views in the dashboard.
    This mitigates Django template rendering errors presumably caused by Wagtail
    admin interface interactions.

    Example usage in a Django template::

        {% for prompt in prompt_list.prompts %}
            {{ prompt.title }}
        {% endfor %}

    DEPRECATED: This context processor is slated for removal in future releases as
    the underlying issues with Wagtail integration are resolved.
    """
    return {"prompt_list": {"smarter_admin": smarter_cached_objects.smarter_admin, "chatbot_helpers": []}}


def prompt_chatapp_workbench_context(request: "HttpRequest") -> dict:
    """
    Provides default placeholder context for chat application workbench views in the dashboard.
    This mitigates Django template rendering errors presumably caused by Wagtail
    admin interface interactions.

    Example usage in a Django template::

        <script class="smarter-chat" async="" src="{{ chatapp_workbench.app_loader_url }}"></script>

    DEPRECATED: This context processor is slated for removal in future releases as
    the underlying issues with Wagtail integration are resolved.
    """
    return {
        "chatapp_workbench": {
            "div_id": smarter_settings.smarter_reactjs_root_div_id,
            "app_loader_url": "",
            "chatbot_api_url": "",
            "toggle_metadata": True,
            "csrf_cookie_name": "csrftoken",
            "smarter_session_cookie_name": "",
            "django_session_cookie_name": "",
            "cookie_domain": "",
            "debug_mode": False,
        }
    }
