# pylint: disable=W0613
"""
Custom Django context processors for the Smarter dashboard application.

These processors inject template context variables into every view that renders
a template inheriting from ``base.html``. Each processor is registered in
``TEMPLATES['OPTIONS']['context_processors']`` in Django settings.

Context processors
------------------

:func:`sidebar`
    Resolves and caches the href targets for every sidebar navigation link.
    Returns a ``sidebar`` dict keyed by destination name.

:func:`file_drop_zone`
    Injects drop-zone feature flags and relevant API/list URLs into a
    ``drop_zone`` dict.  Enabled via ``ENABLE_DASHBOARD_APPLY``.

:func:`base`
    Assembles the primary ``dashboard`` context dict: user identity, role
    flags (``is_superuser``, ``is_staff``), feature toggles, resource counts,
    and platform version metadata.  The inner result is cached per user.

:func:`branding`
    Provides a ``branding`` dict containing corporate identity, support
    contact details, social-media URLs, CDN paths, and a dynamic copyright
    notice.  Values are sourced from ``smarter_settings``.

:func:`footer`
    Provides a ``footer`` dict with links to legal, plans, support, and
    contact pages.

:func:`cache_buster`
    Injects a ``cache_buster`` string (``v=<timestamp>``) for appending to
    static asset URLs in local development.

:func:`prompt_list_context`
    **Deprecated.** Provides a placeholder ``prompt_list`` dict to prevent
    template errors from Wagtail admin interactions.  Slated for removal.

Cache utilities
---------------

:func:`cache_invalidations`
    Invalidates all per-user caches (account, profile, plugins, chatbots, and
    page-level caches for the dashboard and workbench) after user data changes.
    Called by signal handlers in the account app.

    .. seealso::

        - :class:`smarter.lib.manifest.broker.AbstractBroker`
        - ``smarter.apps.account.signals.cache_invalidate``

Usage
-----

Add the processors to your Django settings::

    TEMPLATES = [
        {
            "OPTIONS": {
                "context_processors": [
                    ...
                    "smarter.apps.dashboard.context_processors.sidebar",
                    "smarter.apps.dashboard.context_processors.base",
                    "smarter.apps.dashboard.context_processors.branding",
                    "smarter.apps.dashboard.context_processors.footer",
                    "smarter.apps.dashboard.context_processors.file_drop_zone",
                    "smarter.apps.dashboard.context_processors.cache_buster",
                ],
            },
        }
    ]
"""

import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import urljoin

from django.test import RequestFactory

from smarter.__version__ import __version__
from smarter.apps.account.models import (
    Account,
    UserProfile,
    get_resolved_user,
)
from smarter.apps.account.urls import AccountReverseNames
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.chatbot.utils import get_cached_chatbots_for_user_profile
from smarter.apps.connection.urls import ConnectionReverseNames
from smarter.apps.dashboard.views.apply_manifest.urls import ApplyManifestReverseNames
from smarter.apps.dashboard.views.logs.names import DashboardLogsReverseNames
from smarter.apps.dashboard.views.passthrough.urls import PassthroughReverseNames
from smarter.apps.dashboard.views.views.urls import DashboardReverseNames
from smarter.apps.docs.urls import DocsReverseNames
from smarter.apps.plugin.models import (
    PluginMeta,
)
from smarter.apps.plugin.urls import PluginReverseNames
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.apps.provider.urls import ProviderReverseNames
from smarter.apps.secret.urls import SecretReverseNames
from smarter.apps.vectorstore.urls import VectorstoreReverseNames
from smarter.common.conf import smarter_settings
from smarter.common.const import SMARTER_PRODUCT_DESCRIPTION, SMARTER_PRODUCT_NAME
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.shortcuts import reverse

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)
logger_prefix_cache_invalidations = logging.formatted_text_blue(f"{__name__}.cache_invalidations()")


def sidebar(request: "HttpRequest") -> dict[str, Any]:
    """
    Resolve and cache the href targets for every dashboard sidebar navigation link.

    The inner result is cached so that URL reversals are only performed once
    per process lifetime (the URLs are static). The resolved URLs are returned
    under a ``sidebar`` key whose sub-keys correspond to each navigation
    destination:

    ``dashboard``, ``workbench``, ``apply_manifest``, ``prompt_passthrough``,
    ``server_logs``, ``providers``, ``plugins``, ``connections``, ``secrets``,
    ``vectorstores``, ``api_keys``, ``custom_domains``, ``example_manifests``,
    ``swagger_docs``, ``redoc``, ``json_schemas``, ``account``, ``admin``.

    :param request: The incoming HTTP request (not used directly; required by
        the Django context-processor protocol).
    :type request: HttpRequest
    :returns: A dict with a single ``"sidebar"`` key mapping destination names
        to their resolved URL strings.
    :rtype: dict[str, Any]
    """

    @cache_results()
    def cached_sidebar_context() -> dict[str, Any]:
        retval = {
            "sidebar": {
                "dashboard": reverse(DashboardReverseNames.namespace, DashboardReverseNames.dashboard),
                "workbench": reverse(PromptReverseNames.namespace, PromptReverseNames.listview),
                "apply_manifest": reverse(
                    DashboardReverseNames.namespace,
                    ApplyManifestReverseNames.namespace,
                    ApplyManifestReverseNames.manifest_drop_zone,
                ),
                "prompt_passthrough": reverse(
                    DashboardReverseNames.namespace, PassthroughReverseNames.namespace, PassthroughReverseNames.view
                ),
                "server_logs": reverse(
                    DashboardReverseNames.namespace,
                    DashboardLogsReverseNames.namespace,
                    DashboardLogsReverseNames.terminal_emulator_view,
                ),
                "providers": reverse(ProviderReverseNames.namespace, ProviderReverseNames.listview),
                "plugins": reverse(PluginReverseNames.namespace, PluginReverseNames.listview),
                "connections": reverse(ConnectionReverseNames.namespace, ConnectionReverseNames.listview),
                "secrets": reverse(SecretReverseNames.namespace, SecretReverseNames.SECRETS),
                "vectorstores": reverse(VectorstoreReverseNames.namespace, VectorstoreReverseNames.list_view),
                "api_keys": reverse(AccountReverseNames.namespace, AccountReverseNames.API_KEYS_LIST),
                "custom_domains": reverse(ConnectionReverseNames.namespace, ConnectionReverseNames.listview),  # FIX ME
                "example_manifests": reverse(DocsReverseNames.namespace, DocsReverseNames.example_manifests),
                "swagger_docs": reverse(DocsReverseNames.namespace, DocsReverseNames.swagger_docs),
                "redoc": reverse(DocsReverseNames.namespace, DocsReverseNames.redoc),
                "json_schemas": reverse(DocsReverseNames.namespace, DocsReverseNames.json_schemas),
                "account": "/dashboard/account/dashboard/overview/",  # FIX ME
                "admin": "/admin/",  # FIX ME
            }
        }
        logger.debug("%s.sidebar() cached sidebar context: %s", logger_prefix, logging.formatted_json(retval))
        return retval

    return cached_sidebar_context()


def file_drop_zone(request: "HttpRequest") -> dict[str, Any]:
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

    @cache_results()
    def get_cached_file_drop_zone_context() -> dict[str, Any]:

        retval = {
            "drop_zone": {
                "file_drop_zone_enabled": smarter_settings.file_drop_zone_enabled,
                "api_apply_path": reverse(
                    DashboardReverseNames.namespace,
                    ApplyManifestReverseNames.namespace,
                    ApplyManifestReverseNames.manifest_drop_zone,
                ),
                "workbench_list_path": reverse(PromptReverseNames.namespace, PromptReverseNames.listview),
                "plugin_list_path": reverse(PluginReverseNames.namespace, PluginReverseNames.listview),
                "connection_list_path": reverse(ConnectionReverseNames.namespace, ConnectionReverseNames.listview),
                "provider_list_path": reverse(ProviderReverseNames.namespace, ProviderReverseNames.listview),
            }
        }
        logger.debug(
            "%s.file_drop_zone() cached file drop zone context: %s", logger_prefix, logging.formatted_json(retval)
        )
        return retval

    return get_cached_file_drop_zone_context()


def base(request: "HttpRequest") -> dict[str, Any]:
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
    user = None
    user_profile = None
    resolved_user = None
    if hasattr(request, "user"):
        user = request.user
        resolved_user = get_resolved_user(user)
        user_profile: Optional[UserProfile] = None
        if resolved_user and getattr(resolved_user, "is_authenticated", False):
            user_profile = UserProfile.get_cached_object(user=resolved_user)  # type: ignore
        else:
            user = None

    @cache_results()
    def get_cached_context(username: Optional[str]) -> dict[str, Any]:
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
        logger.debug("%s.base() called.", logger_prefix)
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
                "debug_mode": smarter_settings.debug_mode,
                "user_email": user_email,
                "username": username,
                "is_superuser": is_superuser,
                "is_staff": is_staff,
                "is_vectorstore_enabled": smarter_settings.enable_vectorstore,
                "is_file_drop_zone_enabled": smarter_settings.enable_dashboard_apply,
                "is_enabled_server_logs": smarter_settings.enable_dashboard_server_logs,
                "profile_image_url": (
                    user_profile.profile_image_url if user_profile and user_profile.profile_image_url else "#"
                ),
                "first_name": (user_profile.user.first_name if user_profile and user_profile.user.first_name else ""),
                "last_name": (user_profile.user.last_name if user_profile and user_profile.user.last_name else ""),
                "product_name": SMARTER_PRODUCT_NAME,
                "company_name": smarter_settings.root_domain,
                "smarter_version": "v" + __version__,
                "python_version": smarter_settings.python_version,
                "django_version": smarter_settings.django_version,
                "current_year": current_year,
            }
        }
        logger.debug(
            "%s.base() cached dashboard context for user %s: %s",
            logger_prefix,
            username,
            logging.formatted_json(cached_context),
        )
        return cached_context

    context = get_cached_context(username=resolved_user.username if resolved_user else "missing")  # type: ignore[assignment]
    return context


def branding(request: "HttpRequest") -> dict[str, Any]:
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

    @cache_results()
    def get_cached_context() -> dict[str, Any]:
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
        logger.debug("%s.branding() cached branding context: %s", logger_prefix, logging.formatted_json(context))
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
    - A dynamically generated copyright notice that includes the current year and corporate name.

    All values are sourced from Django settings, allowing for easy
    customization and environment-specific overrides.

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


def cache_buster(request) -> dict[str, Any]:
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


def prompt_list_context(request: "HttpRequest") -> dict[str, Any]:
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


def cache_invalidations(user_profile: Optional[UserProfile]) -> None:
    """
    Invalidates caches for all resource-counting context processors. This function is
    intended to be called after any operation that modifies the underlying user data.

    .. note::

        This is called by signal handlers in the account app, tied to the AbstractBroker.

    .. seealso::

        - :class:`smarter.lib.manifest.broker.AbstractBroker`
        - ``smarter.apps.account.signals.cache_invalidate``
    """
    if not user_profile:
        logger.warning(
            "%s.cache_invalidations() called without user_profile. No caches will be invalidated.",
            logger_prefix_cache_invalidations,
        )
        return

    logger.debug("%s called for %s", logger_prefix_cache_invalidations, user_profile)

    ###########################################################################
    # resource invalidations
    ###########################################################################
    if user_profile:
        Account.get_cached_object(invalidate=True, pk=user_profile.account.id)
        UserProfile.get_cached_object(invalidate=True, pk=user_profile.id)  # type: ignore
        PluginMeta.get_cached_plugins_for_user_profile_id(invalidate=True, user_profile_id=user_profile.id)  # type: ignore
        get_cached_chatbots_for_user_profile(user_profile_id=user_profile.id, invalidate=True)  # type: ignore

    ###########################################################################
    # page cache invalidations
    ###########################################################################
    factory = RequestFactory()
    url = reverse(DashboardReverseNames.namespace, DashboardReverseNames.dashboard)
    request = factory.get(url)

    logger.debug(
        "%s.cache_invalidations() Created invalidation request for URL %s: %s",
        logger_prefix_cache_invalidations,
        url,
        request,
    )
    request.user = user_profile.user
    # pylint: disable=C0415
    from smarter.apps.dashboard.views.views import DashboardView

    DashboardView.dispatch.invalidate(request)

    url = reverse(PromptReverseNames.namespace, PromptReverseNames.listview)
    request = factory.get(url)
    logger.debug(
        "%s.cache_invalidations() Created invalidation request for URL %s: %s",
        logger_prefix_cache_invalidations,
        url,
        request,
    )
    request.user = user_profile.user
