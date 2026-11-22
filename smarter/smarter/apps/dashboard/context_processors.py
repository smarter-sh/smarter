# pylint: disable=W0613
"""
Custom Django context processors for the Smarter dashboard application.

These processors inject template context variables into every view that renders
a template inheriting from ``base.html``. Each processor is registered in
``TEMPLATES['OPTIONS']['context_processors']`` in Django settings.

Context processors
------------------

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

Sidebar links
-------------

:func:`sidebar_context`
    The urls of the web console sidebar's links, which the console's session api returns. The console
    renders the sidebar.

Cache utilities
---------------

:func:`cache_invalidations`
    Invalidates all per-user caches (account, profile, plugins, llmclients, and
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
                    "smarter.apps.dashboard.context_processors.base",
                    "smarter.apps.dashboard.context_processors.branding",
                    "smarter.apps.dashboard.context_processors.footer",
                    "smarter.apps.dashboard.context_processors.cache_buster",
                ],
            },
        }
    ]
"""

import sys
import time
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union
from urllib.parse import urljoin

from cache_results import cache_results
from django.conf import settings
from django.templatetags.static import static
from pydantic import HttpUrl

from smarter.apps.account.models import (
    Account,
    UserProfile,
    get_resolved_user,
)
from smarter.apps.account.models.user_profile import DEFAULT_PROFILE_IMAGE
from smarter.apps.account.utils import get_cached_avatar_url
from smarter.apps.account.views.budget.urls import BudgetReverseNames
from smarter.apps.connection.urls import ConnectionReverseNames
from smarter.apps.dashboard.views.dropzone.urls import DropzoneReverseNames
from smarter.apps.dashboard.views.passthrough.urls import PassthroughReverseNames
from smarter.apps.dashboard.views.terminal_emulator.names import (
    DashboardTerminalReverseNames,
)
from smarter.apps.dashboard.views.views.urls import DashboardReverseNames
from smarter.apps.docs.urls import DocsReverseNames
from smarter.apps.guardrail.urls import GuardrailReverseNames
from smarter.apps.infrastructure.urls import InfrastructureReverseNames
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.urls import LLMClientReverseNames
from smarter.apps.llmhost.urls import LLMHostReverseNames
from smarter.apps.llmtool.extension.urls import ExtensionReverseNames
from smarter.apps.llmtool.models import (
    PluginMeta,
)
from smarter.apps.llmtool.urls import PluginReverseNames
from smarter.apps.mcpclient.urls import MCPClientReverseNames
from smarter.apps.orchestrator.urls import OrchestratorReverseNames
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.apps.provider.urls import ProviderReverseNames
from smarter.apps.proxy.urls import ProxyReverseNames
from smarter.apps.secret.urls import SecretReverseNames
from smarter.apps.vectorsearch.urls import VectorsearchReverseNames
from smarter.apps.vectorstore.urls import VectorstoreReverseNames
from smarter.common.conf import smarter_settings
from smarter.common.utils import snake_case
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.drf.urls import AuthTokenReverseNames
from smarter.lib.manifest.sam_apps import get_sam_app
from smarter.lib.typing import SmarterDictType

if TYPE_CHECKING:
    from django.http import HttpRequest


def is_sphinx_build():
    """Determine if the current execution context is a Sphinx documentation build."""

    return "sphinx" in sys.modules


logger = logging.getSmarterLogger(__name__)


def static_version(request):
    """
    Add the platform's version to the template context, to version static file urls.

    :param request: The request.
    :returns: ``{"STATIC_VERSION": <version>}``.
    """
    return {
        "STATIC_VERSION": smarter_settings.version,
    }


def console_reverse(*args: str) -> str:
    """
    Reverse a web console url name against ``settings.ROOT_URLCONF``.

    The console's session api, which returns the sidebar's links, may be called on any host, including a
    deployed LLMClient's host, which django-hosts serves with :mod:`smarter.urls.llmclients`. That urlconf has
    none of the console's names, so reversing against the active urlconf raises ``NoReverseMatch`` there.

    :param args: The namespaces and the view name, as for :func:`smarter.lib.django.shortcuts.reverse`.
    :type args: str
    :returns: The url path of the console view.
    :rtype: str
    """
    return reverse(*args, urlconf=settings.ROOT_URLCONF)


@cache_results()
def sidebar_context() -> SmarterDictType:
    """
    The urls of the web console sidebar's links, reversed against ``settings.ROOT_URLCONF``.

    The SAM resource apps' lists, the manifest drop zone and the terminal are included only when their
    settings enable them. The result is cached.

    :returns: ``{"sidebar": {<link name>: <url>, ...}}``.
    """
    context = {
        "sidebar": {
            "dashboard": console_reverse(DashboardReverseNames.namespace, DashboardReverseNames.dashboard),
            "workbench": console_reverse(PromptReverseNames.namespace, PromptReverseNames.listview),
            "prompt_passthrough": console_reverse(
                DashboardReverseNames.namespace, PassthroughReverseNames.namespace, PassthroughReverseNames.view
            ),
            "budgets": console_reverse(BudgetReverseNames.namespace, BudgetReverseNames.listview),
            "infrastructure_resources": console_reverse(
                InfrastructureReverseNames.namespace, InfrastructureReverseNames.listview
            ),
            "api_keys": console_reverse(AuthTokenReverseNames.namespace, AuthTokenReverseNames.listview),
            "example_manifests": console_reverse(DocsReverseNames.namespace, DocsReverseNames.example_manifests),
            "openapi": console_reverse(DocsReverseNames.namespace, DocsReverseNames.openapi),
            "json_schemas": console_reverse(DocsReverseNames.namespace, DocsReverseNames.json_schemas),
            "admin": "/admin/",  # FIX ME
        }
    }
    # the SAM resource apps' lists, each only while its app is enabled. See smarter.lib.manifest.sam_apps.
    sam_app_links = [
        ("llmhost", "app_llmhost_enable", (LLMHostReverseNames.namespace, LLMHostReverseNames.listview)),
        ("llmhostcompute", "app_llmhost_enable", (LLMHostReverseNames.namespace, LLMHostReverseNames.compute_listview)),
        ("mcpclients", "app_mcpclient_enable", (MCPClientReverseNames.namespace, MCPClientReverseNames.listview)),
        (
            "orchestrators",
            "app_orchestrator_enable",
            (OrchestratorReverseNames.namespace, OrchestratorReverseNames.listview),
        ),
        ("providers", "app_provider_enable", (ProviderReverseNames.namespace, ProviderReverseNames.listview)),
        ("plugins", "app_llmtool_enable", (PluginReverseNames.namespace, PluginReverseNames.listview)),
        ("extensions", "app_llmtool_enable", (ExtensionReverseNames.namespace, ExtensionReverseNames.listview)),
        ("connections", "app_connection_enable", (ConnectionReverseNames.namespace, ConnectionReverseNames.listview)),
        ("guardrails", "app_guardrail_enable", (GuardrailReverseNames.namespace, GuardrailReverseNames.listview)),
        ("secrets", "app_secret_enable", (SecretReverseNames.namespace, SecretReverseNames.listview)),
        (
            "vectorsearches",
            "app_vectorsearch_enable",
            (VectorsearchReverseNames.namespace, VectorsearchReverseNames.listview),
        ),
        (
            "custom_domains",
            "app_llmclient_enable",
            (LLMClientReverseNames.namespace, LLMClientReverseNames.custom_domain_listview),
        ),
        ("proxies", "app_proxy_enable", (ProxyReverseNames.namespace, ProxyReverseNames.listview)),
        (
            "vectorstores",
            "app_vectorstore_enable",
            (VectorstoreReverseNames.namespace, VectorstoreReverseNames.listview),
        ),
    ]
    for link_name, setting, url_name in sam_app_links:
        sam_app = get_sam_app(setting)
        if not sam_app.is_enabled(smarter_settings):
            continue
        context["sidebar"][link_name] = console_reverse(*url_name)
    if smarter_settings.app_dashboard_manifest_dropzone_enable:
        context["sidebar"]["manifest_drop_zone"] = console_reverse(
            DashboardReverseNames.namespace,
            DropzoneReverseNames.namespace,
            DropzoneReverseNames.dropzone,
        )
    if smarter_settings.app_dashboard_web_console_terminal_enable:
        # the session api gives it to superusers only. See smarter.apps.api.web.session.views.sidebar().
        context["sidebar"]["terminal"] = console_reverse(
            DashboardReverseNames.namespace,
            DashboardTerminalReverseNames.namespace,
            DashboardTerminalReverseNames.terminal_emulator_view,
        )
    return context


def base(request: "HttpRequest") -> SmarterDictType:
    """
    Provides the base context for all templates inheriting from ``base.html`` in the Smarter dashboard.

    This context processor injects a comprehensive set of user-specific and
    application-wide variables into the template context. These variables
    include user identity, role flags, product metadata, and resource counts
    (such as llmclients, plugins, API keys, custom domains, connections, and
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
    user_profile: Optional[UserProfile] = None
    resolved_user = None
    if hasattr(request, "user"):
        user = request.user
        resolved_user = get_resolved_user(user)
        if resolved_user and getattr(resolved_user, "is_authenticated", False):
            user_profile = UserProfile.get_cached_object(user=resolved_user)  # type: ignore
        else:
            user = None

    @cache_results()
    @snake_case()
    def get_cached_context(username: Optional[str]) -> SmarterDictType:
        """
        Constructs and returns the cached dashboard context for the specified user.

        This helper function assembles a dictionary of dashboard context variables,
        including user identity, role flags, product metadata, and resource counts.
        It is decorated with a cache to optimize performance and minimize redundant
        database queries.

        The context is tailored to the authenticated user and is used by the main
        ``base`` context processor to populate the dashboard template.

        :param username: The username for whom the dashboard context is being constructed.
        :type username: Optional[str]
        :return: A dictionary containing the dashboard context variables for the user.
        :rtype: dict
        """
        user_email = "anonymous@mail.edu"
        username = "anonymous"
        if user_profile and user_profile.user.is_authenticated:
            try:
                user_email = user_profile.user.email
                username = user_profile.user.username
            except AttributeError:
                # technically, this is supposed to be impossible due to the is_authenticated check
                pass

        cached_context = {
            "dashboard": {
                "user_email": user_email,
                "username": username,
                "is_proxy_enabled": smarter_settings.app_proxy_enable,
                "is_vectorstore_enabled": smarter_settings.app_vectorstore_enable,
                "is_file_drop_zone_enabled": smarter_settings.app_dashboard_manifest_dropzone_enable,
                "first_name": (user_profile.user.first_name if user_profile and user_profile.user.first_name else ""),
                "last_name": (user_profile.user.last_name if user_profile and user_profile.user.last_name else ""),
                "product_name": smarter_settings.platform_branding_product_name,
            }
        }
        logger.debug(
            "cached dashboard context for user %s: %s",
            username,
            logging.SmarterFormattedText.json(cached_context),
        )
        return cached_context

    context = get_cached_context(username=resolved_user.username if resolved_user else "missing")  # type: ignore[assignment]
    # not cached with the rest, so that a newly uploaded profile image shows at once. get_cached_avatar_url() has its own cache.
    profile_image_url = (
        get_cached_avatar_url(user_id=user_profile.user_id) if user_profile else static(DEFAULT_PROFILE_IMAGE)
    )
    context = {
        **context,
        "dashboard": {
            **context["dashboard"],
            "profile_image_url": profile_image_url,
        },
    }
    return context


def branding(request: "HttpRequest") -> SmarterDictType:
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
    @snake_case()
    def get_cached_context() -> SmarterDictType:
        current_year = datetime.now().year
        root_url = request.build_absolute_uri("/").rstrip("/")
        context = {
            "branding": {
                "canonical": request.path,
                "root_url": root_url,
                "corporate_name": smarter_settings.platform_branding_corporate_name,
                "corporate_address": ", ".join(
                    filter(
                        None,
                        [
                            smarter_settings.platform_branding_address1,
                            smarter_settings.platform_branding_address2,
                            smarter_settings.platform_branding_city,
                            smarter_settings.platform_branding_state,
                            smarter_settings.platform_branding_postal_code,
                            smarter_settings.platform_branding_country,
                        ],
                    )
                ),
                "corporate_currency": smarter_settings.platform_branding_currency,
                "corporate_timezone": smarter_settings.platform_branding_timezone,
                "support_email": smarter_settings.platform_branding_support_email,
                "contact_url": smarter_settings.platform_branding_contact_url,
                "primary_contact": smarter_settings.platform_branding_primary_contact,
                "support_hours": smarter_settings.platform_branding_support_hours,
                "support_phone_number": smarter_settings.platform_branding_support_phone_number,
                "copyright": f"© 2023-{current_year} {smarter_settings.platform_branding_corporate_name}. All rights reserved.",
                "og_url": smarter_settings.platform_branding_marketing_site_url,
                "canonical_url": smarter_settings.environment_url,
                "og_image": urljoin(str(smarter_settings.platform_branding_cdn_url), "cms/img/smarter_og_image.png"),
                "url_facebook": smarter_settings.platform_branding_url_facebook,
                "url_twitter": smarter_settings.platform_branding_url_twitter,
                "url_linkedin": smarter_settings.platform_branding_url_linkedin,
                "url_slack": smarter_settings.platform_branding_url_slack,
                "smarter_logo": smarter_settings.platform_branding_logo,
                "smarter_app_name": smarter_settings.platform_branding_app_name,
                "smarter_product_name": smarter_settings.platform_branding_product_name,
                "smarter_product_description": smarter_settings.platform_branding_product_description,
                "smarter_marketing_site_url": smarter_settings.platform_branding_marketing_site_url,
                "smarter_home_url": "/",
                "smarter_project_website_url": str(smarter_settings.platform_branding_marketing_site_url).rstrip("/"),
                "smarter_project_cdn_url": str(smarter_settings.platform_branding_cdn_url).rstrip("/"),
                "smarter_project_docs_url": str(smarter_settings.platform_branding_docs_url).rstrip("/"),
                "smarter_project_blog_url": str(smarter_settings.platform_branding_blog_url).rstrip("/"),
                "logo_url": "images/logo/smarter-crop.png",
                "cdn_logo_url": urljoin(
                    str(smarter_settings.platform_branding_cdn_url).rstrip("/"), "images/logo/smarter-crop.png"
                ),
                "login_url": urljoin(smarter_settings.environment_url, "/login/"),
                "learn_url": str(smarter_settings.platform_branding_docs_url).rstrip("/"),
                "workbench_exmample_url": urljoin(smarter_settings.environment_url, "/workbench/"),
            }
        }
        logger.debug("cached branding context: %s", logging.SmarterFormattedText.json(context))
        return context

    return get_cached_context()


@snake_case()
def footer(request: "HttpRequest") -> dict[str, dict[str, Optional[Union[str, HttpUrl]]]]:
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
            "about_url": smarter_settings.platform_branding_marketing_site_url,
            "support_url": smarter_settings.platform_branding_marketing_site_url,
            "legal_url": urljoin(str(smarter_settings.platform_branding_marketing_site_url), "legal"),
            "plans_url": smarter_settings.platform_branding_marketing_site_url,
            "contact_url": "https://lawrencemcdaniel.com/contact/",
        }
    }
    return context


@snake_case()
def cache_buster(request) -> SmarterDictType:
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


def cache_invalidations(user_profile: Optional[UserProfile]) -> None:
    """
    Invalidates caches for all resource-counting context processors.

    This function is
    intended to be called after any operation that modifies the underlying user data.

    .. note::

        This is called by signal handlers in the account app, tied to the AbstractBroker.

    .. seealso::

        - :class:`smarter.lib.manifest.broker.AbstractBroker`
        - ``smarter.apps.account.signals.cache_invalidate``
    """
    if not user_profile:
        logger.warning(
            "called without user_profile. No caches will be invalidated.",
            prefix_format=logging.SmarterFormattedText.BOLD_DARK_BLUE,
        )
        return

    logger.debug("called for %s", user_profile, prefix_format=logging.SmarterFormattedText.BOLD_DARK_BLUE)

    ###########################################################################
    # resource invalidations
    ###########################################################################
    if user_profile:
        Account.get_cached_object(invalidate=True, pk=user_profile.account.id)
        UserProfile.get_cached_object(invalidate=True, pk=user_profile.id)  # type: ignore
        PluginMeta.get_cached_plugins_for_user_profile_id(invalidate=True, user_profile_id=user_profile.id)  # type: ignore
        LLMClient.get_cached_objects(invalidate=True, user_profile=user_profile)  # type: ignore
