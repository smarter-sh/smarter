# pylint: disable=W0613
"""
smarter.apps.dashboard.context_processors
=========================================

This module provides custom Django context processors for the Smarter dashboard
application. These context processors are designed to inject additional context
variables into templates that inherit from ``base.html``, supporting the dynamic
rendering of dashboard and branding information throughout the application.

Overview
--------

The context processors in this module serve the following purposes:

- **Dashboard Context**: Supplies user-specific and application-wide metadata,
such as the current user's email, username, role flags, product version, and
resource counts (e.g., chatbots, plugins, API keys, custom domains, connections,
and secrets). This enables the dashboard to display personalized and up-to-date
information for each authenticated user.

- **Branding Context**: Provides organization-specific branding details, including
support contact information, corporate name, address, social media links, and
copyright notices. This ensures consistent branding and support information
across all dashboard templates.

- **Cache Busting**: Adds a cache-busting query parameter to static asset URLs
during local development, preventing browsers from serving outdated static
files.

Caching
-------

Many of the resource-counting functions in this module are decorated with a
caching mechanism to reduce database load and improve performance. The cache
timeout is configurable and set to 60 seconds by default.

Usage
-----

To use these context processors, add their import paths to the
``TEMPLATES['OPTIONS']['context_processors']`` list in your Django settings.
This will make the provided context variables available in all templates
rendered by Django that inherit from ``base.html``.

Note
----

This module does not document individual function signatures or arguments, as
these are automatically included by Sphinx's ``automodule`` directive. For
detailed API documentation, refer to the generated documentation for each function.
"""

import logging
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
from smarter.apps.plugin.models import (
    ConnectionBase,
    PluginMeta,
)
from smarter.apps.provider.models import Provider
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_PRODUCT_DESCRIPTION, SMARTER_PRODUCT_NAME
from smarter.common.helpers.console_helpers import formatted_text, formatted_text_blue
from smarter.lib.cache import cache_results

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)
logger_prefix = formatted_text(__name__)
logger_prefix_cache_invalidations = formatted_text_blue(f"{__name__}.cache_invalidations()")


def get_pending_deployments(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the number of chatbot deployments that are pending for the specified user.

    This function queries the database for all chatbot instances associated with the
    user's account that have not yet been deployed. The result is used to inform users
    of outstanding deployment actions required on their dashboard.

    The result is cached for a short duration to minimize database load and
    improve dashboard responsiveness.

    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :param user_profile: UserProfile instance. The user profile whose pending deployments are to be counted.
    :type user_profile: UserProfile
    :return: The number of pending chatbot deployments for the user.
    :rtype: int
    """
    logger.debug(
        "%s.get_pending_deployments() called with invalidate=%s for user_profile_id=%s",
        logger_prefix,
        invalidate,
        user_profile,
    )

    @cache_results()
    def _get_pending_deployments(user_profile_id: int) -> int:
        return ChatBot.objects.filter(user_profile__id=user_profile_id, deployed=False).count() or 0

    if invalidate and user_profile:
        _get_pending_deployments.invalidate(user_profile.id)  # type: ignore

    return _get_pending_deployments(user_profile.id)


def get_chatbots(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of chatbots associated with the specified user.

    This function queries the database for all chatbot instances linked to
    the user's account, regardless of deployment status. The resulting count
    is used to display the user's available chatbots on the dashboard.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: UserProfile instance. The user profile whose chatbots are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.

    :return: The number of chatbots belonging to the user.
    :rtype: int
    """
    logger.debug(
        "%s.get_chatbots() called with invalidate=%s for user_profile_id=%s",
        logger_prefix,
        invalidate,
        user_profile,
    )
    chatbots = ChatBot.get_cached_objects(invalidate=invalidate, user_profile=user_profile)
    return len(chatbots)


def get_plugins(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of plugins associated with the specified user.

    This function queries the database for all plugin metadata records linked
    to the user's account. The resulting count is used to display the user's
    available plugins on the dashboard.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: UserProfile instance. The user profile whose plugins are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :return: The number of plugins belonging to the user.
    :rtype: int
    """
    logger.debug(
        "%s.get_plugins() called with invalidate=%s for user_profile_id=%s",
        logger_prefix,
        invalidate,
        user_profile,
    )
    retval = PluginMeta.get_cached_plugins_for_user_profile_id(invalidate=invalidate, user_profile_id=user_profile.id)
    return len(retval)


def get_api_keys(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of API keys associated with the specified user.

    This function queries the database for all API key records linked to
    chatbots owned by the user's account. The resulting count is used to
    display the user's available API keys on the dashboard.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: UserProfile instance. The user profile whose API keys are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :return: The number of API keys belonging to the user.
    :rtype: int
    """
    logger.debug(
        "%s.get_api_keys() called with invalidate=%s for user_profile_id=%s",
        logger_prefix,
        invalidate,
        user_profile,
    )

    @cache_results()
    def _get_api_keys(user_profile_id: int) -> int:
        return ChatBotAPIKey.objects.filter(chatbot__user_profile__id=user_profile_id).count() or 0

    if invalidate and user_profile:
        _get_api_keys.invalidate(user_profile.id)  # type: ignore

    return _get_api_keys(user_profile.id)


def get_custom_domains(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of custom domains associated with the specified user.

    This function queries the database for all custom domain records linked
    to chatbots owned by the user's account. The resulting count is used to
    display the user's available custom domains on the dashboard.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: UserProfile instance. The user profile whose custom domains are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :return: The number of custom domains belonging to the user.
    :rtype: int
    """
    logger.debug(
        "%s.get_custom_domains() called with invalidate=%s for user_profile_id=%s",
        logger_prefix,
        invalidate,
        user_profile,
    )

    @cache_results()
    def _get_custom_domains(user_profile_id: int) -> int:
        return ChatBotCustomDomain.objects.filter(chatbot__user_profile__id=user_profile_id).count() or 0

    if invalidate and user_profile:
        _get_custom_domains.invalidate(user_profile.id)  # type: ignore

    return _get_custom_domains(user_profile.id)


def get_connections(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of API and SQL connections associated with the specified user.

    This function queries the database for all API and SQL connection records linked to the user's account. The resulting count is used to display the user's available connections on the dashboard.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: UserProfile instance. The user profile whose connections are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :return: The number of API and SQL connections belonging to the user.
    :rtype: int
    """
    logger.debug(
        "%s.get_connections() called with invalidate=%s for user_profile_id=%s",
        logger_prefix,
        invalidate,
        user_profile,
    )
    retval = ConnectionBase.get_cached_connections_for_user(invalidate=invalidate, user=user_profile.cached_user) or []
    return len(retval)


@cache_results()
def get_secrets(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of secrets associated with the specified user's profile.

    This function queries the database for all secret records linked to the user's profile.
    The resulting count is used to display the user's available secrets on the dashboard.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: The user profile whose secrets are to be counted.
    :type user_profile: UserProfile
    :return: The number of secrets belonging to the user profile.
    :rtype: int
    """
    logger.debug(
        "%s.get_secrets() called with invalidate=%s for user_profile_id=%s", logger_prefix, invalidate, user_profile.id
    )
    return Secret.get_cached_objects(invalidate=invalidate, user_profile=user_profile).count()


def get_providers(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of providers associated with the specified user's account.

    This function queries the database for all provider records linked to the user's account.
    The resulting count is used to display the user's available providers on the dashboard.

    The result is cached for a short duration to reduce database queries and improve dashboard performance.

    :param user_profile: The user profile whose providers are to be counted.
    :type user_profile: UserProfile
    :return: The number of providers belonging to the user account + those belonging to the official smarter admin.
    :rtype: int
    """
    logger.debug(
        "%s.get_providers() called with invalidate=%s for user_profile_id=%s",
        logger_prefix,
        invalidate,
        user_profile.id,
    )
    retval = Provider.get_cached_providers_for_user(invalidate=invalidate, user=user_profile.cached_user) or []
    return len(retval)


def file_drop_zone(request: "HttpRequest") -> dict:
    """
    Provides context for enabling file drop zone functionality in the dashboard.

    This context processor injects a variable into the template context that can
    be used to enable or disable file drop zone features in the dashboard interface.
    This is useful for enhancing user experience by allowing drag-and-drop file uploads.

    :param request: The HTTP request object.
    :type request: "HttpRequest"
    :return: A dictionary containing the file drop zone context variable.
    :rtype: dict
    """
    logger.debug("%s.file_drop_zone() called.", logger_prefix)

    @cache_results()
    def get_cached_file_drop_zone_context() -> dict:
        retval = {
            "drop_zone": {
                "file_drop_zone_enabled": smarter_settings.file_drop_zone_enabled,
                "api_apply_path": reverse(ApiV1CliReverseViews.namespace + ApiV1CliReverseViews.apply),
                "workbench_list_path": reverse("prompt_workbench:listview"),
                "plugin_list_path": reverse("plugin:plugin_listview"),
                "connection_list_path": reverse("plugin:connection_listview"),
                "provider_list_path": reverse("provider:provider_listview"),
            }
        }
        return retval

    return get_cached_file_drop_zone_context()


def base(request: "HttpRequest") -> dict:
    """
    Provides the base context for all templates inheriting from ``base.html``
    in the Smarter dashboard.

    This context processor injects a comprehensive set of user-specific and
    application-wide variables into the template context. These variables
    include user identity, role flags, product metadata, and resource counts
    (such as chatbots, plugins, API keys, custom domains, connections, and
    secrets). The context is used to render the dashboard layout and
    personalize the user experience.

    The resource counts are cached for performance, and the context is dynamically
    constructed based on the authenticated user's account and profile.

    :param request: The HTTP request object.
    :type request: "HttpRequest"
    :return: A dictionary containing the dashboard context variables.
    :rtype: dict
    """
    logger.debug("%s.base() called.", logger_prefix)
    user = request.user
    resolved_user = get_resolved_user(user)
    user_profile: Optional[UserProfile] = None
    if resolved_user and getattr(resolved_user, "is_authenticated", False):
        user_profile = UserProfile.objects.filter(user=resolved_user).first()

    @cache_results()
    def get_cached_context(user: Optional[User]) -> dict:
        """
        Constructs and returns the cached dashboard context for the specified user.

        This helper function assembles a dictionary of dashboard context variables,
        including user identity, role flags, product metadata, and resource counts.
        It is decorated with a cache to optimize performance and minimize redundant
        database queries.

        The context is tailored to the authenticated user and is used by the main
        ``base`` context processor to populate the dashboard template.

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
        if user_profile and user_profile.cached_user.is_authenticated:
            try:
                user_email = user_profile.cached_user.email
                username = user_profile.cached_user.username
                is_superuser = user_profile.cached_user.is_superuser
                is_staff = user_profile.cached_user.is_staff
            except AttributeError:
                # technically, this is supposed to be impossible due to the is_authenticated check
                pass

        cached_context = {
            "dashboard": {
                "debug_mode": smarter_settings.debug_mode,
                "user_email": user_email,
                "username": username,
                "is_superuser": is_superuser,
                "is_staff": is_staff,
                "profile_image_url": (
                    user_profile.profile_image_url if user_profile and user_profile.profile_image_url else "#"
                ),
                "first_name": (
                    user_profile.cached_user.first_name if user_profile and user_profile.cached_user.first_name else ""
                ),
                "last_name": (
                    user_profile.cached_user.last_name if user_profile and user_profile.cached_user.last_name else ""
                ),
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
    logger.debug("%s.branding() called.", logger_prefix)

    @cache_results()
    def get_cached_context() -> dict:
        current_year = datetime.now().year
        root_url = request.build_absolute_uri("/").rstrip("/")
        context = {
            "branding": {
                "canonical": request.path,
                "root_url": root_url,
                "corporate_name": smarter_settings.branding_corporate_name,
                "corporate_address": ", ".join(
                    filter(
                        None,
                        [
                            smarter_settings.branding_address1,
                            smarter_settings.branding_address2,
                            smarter_settings.branding_city,
                            smarter_settings.branding_state,
                            smarter_settings.branding_postal_code,
                            smarter_settings.branding_country,
                        ],
                    )
                ),
                "corporate_currency": smarter_settings.branding_currency,
                "corporate_timezone": smarter_settings.branding_timezone,
                "support_email": smarter_settings.branding_support_email,
                "contact_url": smarter_settings.branding_contact_url,
                "support_hours": smarter_settings.branding_support_hours,
                "support_phone_number": smarter_settings.branding_support_phone_number,
                "copyright": f"© {current_year} {smarter_settings.branding_corporate_name}. All rights reserved.",
                "og_url": smarter_settings.marketing_site_url,
                "canonical_url": smarter_settings.environment_url,
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
                "logo_url": "images/logo/smarter-crop.png",
                "cdn_logo_url": urljoin(smarter_settings.smarter_project_cdn_url, "images/logo/smarter-crop.png"),
                "login_url": urljoin(smarter_settings.environment_url, "/login/"),
                "learn_url": smarter_settings.smarter_project_docs_url,
                "workbench_exmample_url": urljoin(smarter_settings.environment_url, "/workbench/smarter/chat/"),
            }
        }
        return context

    return get_cached_context()


def footer(request: "HttpRequest") -> dict[str, dict[str, str]]:
    """
    Provides organization-specific legal context for dashboard templates.

    This context processor injects legal and compliance-related variables into
    the template context for all pages inheriting from ``base.html``. These
    variables ensure that consistent legal information, such as terms of service,
    privacy policy, and cookie policy URLs, are available throughout the dashboard user interface.

    The context includes:

    - URLs for the terms of service, privacy policy, and cookie policy documents.
    - A dynamically generated copyright notice that includes the current year
    and corporate name.

    All values are sourced from Django settings, allowing for easy
    customization and environment-specific overrides.

    Example usage in a Django template::

        {{ footer.legal_url }}
        {{ footer.plans_url }}
        {{ footer.contact_url }}
    """
    logger.debug("%s.footer() called.", logger_prefix)
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

    This context processor is intended for use in local development environments
    to ensure that browsers do not serve outdated versions of static files
    (such as JavaScript, CSS, or images) from cache. It injects a ``cache_buster``
    variable into the template context, which can be appended as a query parameter
    to static asset URLs. The value is a version string based on the current
    timestamp, guaranteeing uniqueness on each page load.

    Example usage in a Django template::

        <script src="{{ STATIC_URL }}main.js?{{ cache_buster }}"></script>

    This approach is especially useful when making frequent changes to static
    assets during development, as it forces the browser to fetch the latest
    version every time the page is reloaded. In production, this processor is
    typically disabled or omitted to allow for proper static file caching and
    performance optimization.

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
    logger.debug("%s.prompt_list_context() called.", logger_prefix)
    return {"prompt_list": {"smarter_admin": smarter_cached_objects.smarter_admin, "chatbot_helpers": []}}


def cache_invalidations(user_profile: Optional[UserProfile]) -> None:
    """
    Invalidates caches for all resource-counting context processors. This function is
    intended to be called after any operation that modifies the underlying user data.

    .. note::

        This is called by signal handlers in the account app, tied to the AbstractBroker.

    .. seealso::

        - :class:`smarter.lib.manifest.broker.AbstractBroker`
        - :signal:`smarter.apps.account.signals.cache_invalidate`
    """
    logger.debug("%s called for %s", logger_prefix_cache_invalidations, user_profile)

    get_pending_deployments(invalidate=True, user_profile=user_profile)
    get_chatbots(invalidate=True, user_profile=user_profile)
    get_plugins(invalidate=True, user_profile=user_profile)
    get_api_keys(invalidate=True, user_profile=user_profile)
    get_custom_domains(invalidate=True, user_profile=user_profile)
    get_connections(invalidate=True, user_profile=user_profile)
    get_secrets(invalidate=True, user_profile=user_profile)
    get_providers(invalidate=True, user_profile=user_profile)

    # page cache invalidations
    # dashboard:dashboard
    #
    # resolve the reverse url, create an authenticated request
    # and call the invalidate_view method with the request and user_profile
    from django.test import RequestFactory
    from django.urls import reverse

    from smarter.apps.dashboard.views.dashboard import DashboardView
    from smarter.lib.django.views import SmarterAuthenticatedWebView

    factory = RequestFactory()
    url = reverse("dashboard:dashboard")
    request = factory.get(url)

    logger.debug(
        "%s.cache_invalidations() Created invalidation request for URL %s: %s",
        logger_prefix_cache_invalidations,
        url,
        request,
    )
    request.user = user_profile.user
    DashboardView.dispatch.invalidate(request)
