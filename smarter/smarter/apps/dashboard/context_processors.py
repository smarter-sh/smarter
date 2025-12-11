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
from typing import Optional

from django.conf import settings
from django.http import HttpRequest

from smarter.__version__ import __version__
from smarter.apps.account.models import (
    Account,
    Secret,
    User,
    UserProfile,
    get_resolved_user,
)
from smarter.apps.account.utils import get_cached_account_for_user
from smarter.apps.chatbot.models import ChatBot, ChatBotAPIKey, ChatBotCustomDomain
from smarter.apps.plugin.models import ApiConnection, PluginMeta, SqlConnection
from smarter.lib.cache import cache_results


CACHE_TIMEOUT = 60  # 1 minute


@cache_results(timeout=CACHE_TIMEOUT)
def get_pending_deployments(account: Account) -> int:
    """
    Returns the number of chatbot deployments that are pending for the specified user.

    This function queries the database for all chatbot instances associated with the user's account that have not yet been deployed. The result is used to inform users of outstanding deployment actions required on their dashboard.

    The result is cached for a short duration to minimize database load and improve dashboard responsiveness.

    :param user: The user whose pending deployments are to be counted.
    :type user: User
    :return: The number of pending chatbot deployments for the user.
    :rtype: int
    """
    return ChatBot.objects.filter(account=account, deployed=False).count() or 0


@cache_results(timeout=CACHE_TIMEOUT)
def get_chatbots(account: Account) -> int:
    """
    Returns the total number of chatbots associated with the specified user.

    This function queries the database for all chatbot instances linked to the user's account, regardless of deployment status. The resulting count is used to display the user's available chatbots on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user: The user whose chatbots are to be counted.
    :type user: User
    :return: The number of chatbots belonging to the user.
    :rtype: int
    """
    return ChatBot.objects.filter(account=account).count() or 0


@cache_results(timeout=CACHE_TIMEOUT)
def get_plugins(account: Account) -> int:
    """
    Returns the total number of plugins associated with the specified user.

    This function queries the database for all plugin metadata records linked to the user's account. The resulting count is used to display the user's available plugins on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user: The user whose plugins are to be counted.
    :type user: User
    :return: The number of plugins belonging to the user.
    :rtype: int
    """
    return PluginMeta.objects.filter(account=account).count() or 0


@cache_results(timeout=CACHE_TIMEOUT)
def get_api_keys(account: Account) -> int:
    """
    Returns the total number of API keys associated with the specified user.

    This function queries the database for all API key records linked to chatbots owned by the user's account. The resulting count is used to display the user's available API keys on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user: The user whose API keys are to be counted.
    :type user: User
    :return: The number of API keys belonging to the user.
    :rtype: int
    """
    return ChatBotAPIKey.objects.filter(chatbot__account=account).count() or 0


@cache_results(timeout=CACHE_TIMEOUT)
def get_custom_domains(account: Account) -> int:
    """
    Returns the total number of custom domains associated with the specified user.

    This function queries the database for all custom domain records linked to chatbots owned by the user's account. The resulting count is used to display the user's available custom domains on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user: The user whose custom domains are to be counted.
    :type user: User
    :return: The number of custom domains belonging to the user.
    :rtype: int
    """
    return ChatBotCustomDomain.objects.filter(chatbot__account=account).count() or 0


@cache_results(timeout=CACHE_TIMEOUT)
def get_connections(account: Account) -> int:
    """
    Returns the total number of API and SQL connections associated with the specified user.

    This function queries the database for all API and SQL connection records linked to the user's account. The resulting count is used to display the user's available connections on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user: The user whose connections are to be counted.
    :type user: User
    :return: The number of API and SQL connections belonging to the user.
    :rtype: int
    """
    retval = ApiConnection.objects.filter(account=account).count() or 0
    retval += SqlConnection.objects.filter(account=account).count() or 0
    return retval


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


def base(request: HttpRequest) -> dict:
    """
    Provides the base context for all templates inheriting from ``base.html`` in the Smarter dashboard.

    This context processor injects a comprehensive set of user-specific and application-wide variables into the template context. These variables include user identity, role flags, product metadata, and resource counts (such as chatbots, plugins, API keys, custom domains, connections, and secrets). The context is used to render the dashboard layout and personalize the user experience.

    The resource counts are cached for performance, and the context is dynamically constructed based on the authenticated user's account and profile.

    :param request: The HTTP request object.
    :type request: HttpRequest
    :return: A dictionary containing the dashboard context variables.
    :rtype: dict
    """
    user = request.user
    resolved_user = get_resolved_user(user)
    user_profile: Optional[UserProfile] = None
    account: Optional[Account] = None
    if resolved_user and getattr(resolved_user, "is_authenticated", False):
        user_profile = UserProfile.objects.filter(user=resolved_user).first()
        account = get_cached_account_for_user(user)

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
                "product_name": "Smarter",
                "company_name": "smarter.sh",
                "smarter_version": "v" + __version__,
                "current_year": current_year,
                "product_description": "Smarter is an enterprise class plugin-based chat solution.",
                "my_resources_pending_deployments": get_pending_deployments(account=account) if account else 0,
                "my_resources_chatbots": get_chatbots(account=account) if account else 0,
                "my_resources_plugins": get_plugins(account=account) if account else 0,
                "my_resources_api_keys": get_api_keys(account=account) if account else 0,
                "my_resources_custom_domains": get_custom_domains(account=account) if account else 0,
                "my_resources_connections": get_connections(account=account) if account else 0,
                "my_resources_secrets": get_secrets(user_profile=user_profile) if user_profile else 0,
            }
        }
        return cached_context

    context = get_cached_context(user=resolved_user)  # type: ignore[assignment]
    return context


def branding(request: HttpRequest) -> dict:
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
        {{ branding.copy_right }}

    This processor is intended to be added to the ``TEMPLATES['OPTIONS']['context_processors']`` list in your Django settings, making the ``branding`` context variable available in all templates rendered by Django that inherit from ``base.html``.
    """
    current_year = datetime.now().year
    root_url = request.build_absolute_uri("/").rstrip("/")
    context = {
        "branding": {
            "root_url": root_url,
            "support_phone_number": settings.SMARTER_BRANDING_SUPPORT_PHONE_NUMBER,
            "corporate_name": settings.SMARTER_BRANDING_CORPORATE_NAME,
            "support_email": settings.SMARTER_BRANDING_SUPPORT_EMAIL,
            "corp_address": settings.SMARTER_BRANDING_ADDRESS,
            "contact": settings.SMARTER_BRANDING_CONTACT,
            "support_hours": settings.SMARTER_BRANDING_SUPPORT_HOURS,
            "copy_right": f"© {current_year} {settings.SMARTER_BRANDING_CORPORATE_NAME}. All rights reserved.",
            "url_facebook": settings.SMARTER_BRANDING_URL_FACEBOOK,
            "url_twitter": settings.SMARTER_BRANDING_URL_TWITTER,
            "url_linkedin": settings.SMARTER_BRANDING_URL_LINKEDIN,
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
