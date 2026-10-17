# pylint: disable=W0613
"""
Smarter.apps.dashboard.views.dashboard.api.my_resources
=========================================================

This module provides custom Django context processors for the Smarter dashboard
application. These context processors are designed to inject additional context
variables into templates that inherit from ``base.html``, supporting the dynamic
rendering of dashboard and branding information throughout the application.

Overview
--------

The context processors in this module serve the following purposes:

- **Dashboard Context**: Supplies user-specific and application-wide metadata,
    such as the current user's email, username, role flags, product version, and
    resource counts (e.g., llmclients, plugins, API keys, custom domains, MCPClients,
    secrets, guardrails, vectorstores, LLMHosts and extensions). This enables the dashboard to display personalized and up-to-date
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

cache_invalidations(user_profile) is a utility function provided to invalidate
all relevant caches when user data changes, ensuring that the dashboard
reflects the most current information.

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

from http import HTTPStatus
from typing import Optional

from django.db.models import Q
from django.http import HttpRequest, JsonResponse

from smarter.__version__ import __version__
from smarter.apps.account.models import (
    UserProfile,
    get_resolved_user,
)
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.urls import GuardrailReverseNames
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
)
from smarter.apps.llmclient.urls import LLMClientReverseNames
from smarter.apps.llmhost.models import LLMHost
from smarter.apps.llmhost.urls import LLMHostReverseNames
from smarter.apps.llmtool.extension.urls import ExtensionReverseNames
from smarter.apps.llmtool.models import (
    Extension,
    PluginMeta,
)
from smarter.apps.llmtool.urls import PluginReverseNames
from smarter.apps.mcpclient.caching import (
    get_cached_mcpclients_available_to_user_profile,
    invalidate_cached_mcpclients_available_to_user_profile,
)
from smarter.apps.mcpclient.urls import MCPClientReverseNames
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.apps.prompt.views.listview.api import PENDING_FILTER
from smarter.apps.provider.models import Provider
from smarter.apps.provider.urls import ProviderReverseNames
from smarter.apps.secret.models import Secret
from smarter.apps.secret.urls import SecretReverseNames
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.apps.vectorstore.urls import VectorstoreReverseNames
from smarter.common.conf import smarter_settings
from smarter.common.utils.decorators import snake_case
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
)

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

EXTENSIONS_DOCS_URL = "https://docs.smarter.sh/en/latest/smarter-platform/extensions.html"


def get_pending_deployments(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the number of llmclient deployments that are pending for the specified user.

    This function queries the database for all llmclient instances associated with the
    user's account that have not yet been deployed. The result is used to inform users
    of outstanding deployment actions required on their dashboard.

    The result is cached for a short duration to minimize database load and
    improve dashboard responsiveness.

    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :param user_profile: UserProfile instance. The user profile whose pending deployments are to be counted.
    :type user_profile: UserProfile
    :return: The number of pending llmclient deployments for the user.
    :rtype: int
    """

    @cache_results()
    def _get_pending_deployments(user_profile_id: int) -> int:
        logger.debug(
            "%s.get_pending_deployments() called with invalidate=%s for user_profile_id=%s",
            logger_prefix,
            invalidate,
            user_profile,
        )
        retval = LLMClient.objects.filter(deployed=False).with_ownership_permission_for(user=user_profile.user).count() or 0  # type: ignore
        logger.debug(
            "%s.get_pending_deployments() retrieved and cached pending deployments count: %s", logger_prefix, retval
        )
        return retval

    if not user_profile:
        logger.warning("%s.get_pending_deployments() called without user_profile. Returning None.", logger_prefix)
        return 0
    if invalidate and user_profile:
        _get_pending_deployments.invalidate(user_profile.id)  # type: ignore

    return _get_pending_deployments(user_profile.id)  # type: ignore


def get_llmclients(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of llmclients associated with the specified user.

    This function queries the database for all llmclient instances linked to
    the user's account, regardless of deployment status. The resulting count
    is used to display the user's available llmclients on the dashboard.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: UserProfile instance. The user profile whose llmclients are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.

    :return: The number of llmclients belonging to the user.
    :rtype: int
    """
    if not user_profile:
        logger.warning("%s.get_llmclients() called without user_profile. Returning None.", logger_prefix)
        return 0

    llmclients = LLMClient.get_cached_objects(invalidate=invalidate, user_profile=user_profile)
    return len(llmclients)


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
    if not user_profile:
        logger.warning("%s.get_plugins() called without user_profile. Returning None.", logger_prefix)
        return 0
    retval = PluginMeta.get_cached_plugins_for_user_profile_id(invalidate=invalidate, user_profile_id=user_profile.id)  # type: ignore
    return len(retval)


def get_api_keys(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of API keys associated with the specified user.

    This function queries the database for all API key records linked to
    llmclients owned by the user's account. The resulting count is used to
    display the user's available API keys on the dashboard.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: UserProfile instance. The user profile whose API keys are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :return: The number of API keys belonging to the user.
    :rtype: int
    """

    @cache_results()
    def _get_api_keys(user_profile_id: int) -> int:
        logger.debug(
            "%s.get_api_keys() called with invalidate=%s for user_profile_id=%s",
            logger_prefix,
            invalidate,
            user_profile,
        )
        retval = LLMClientAPIKey.objects.filter(llmclient__user_profile__id=user_profile_id).count() or 0
        logger.debug("%s.get_api_keys() retrieved and cached API keys count: %s", logger_prefix, retval)
        return retval

    if not user_profile:
        logger.warning("%s.get_api_keys() called without user_profile. Returning None.", logger_prefix)
        return 0

    if invalidate and user_profile:
        _get_api_keys.invalidate(user_profile.id)  # type: ignore

    return _get_api_keys(user_profile.id)  # type: ignore


def get_custom_domains(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of custom domains associated with the specified user.

    This function queries the database for all custom domain records linked
    to llmclients owned by the user's account. The resulting count is used to
    display the user's available custom domains on the dashboard.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: UserProfile instance. The user profile whose custom domains are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :return: The number of custom domains belonging to the user.
    :rtype: int
    """

    @cache_results()
    def _get_custom_domains(user_profile_id: int) -> int:
        logger.debug(
            "%s.get_custom_domains() called with invalidate=%s for user_profile_id=%s",
            logger_prefix,
            invalidate,
            user_profile,
        )
        retval = LLMClientCustomDomain.objects.filter(user_profile__id=user_profile_id).count() or 0
        logger.debug("%s.get_custom_domains() retrieved and cached custom domains count: %s", logger_prefix, retval)
        return retval

    if not user_profile:
        logger.warning("%s.get_custom_domains() called without user_profile. Returning None.", logger_prefix)
        return 0

    if invalidate and user_profile:
        _get_custom_domains.invalidate(user_profile.id)  # type: ignore

    return _get_custom_domains(user_profile.id)  # type: ignore


def get_mcpclients(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of MCPClients available to the specified user.

    This function counts the MCPClients that the user owns, and those shared with
    them. The resulting count is used to display the user's available MCPClients
    on the dashboard.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: UserProfile instance. The user profile whose MCPClients are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :return: The number of MCPClients available to the user.
    :rtype: int
    """
    if not user_profile:
        logger.warning("%s.get_mcpclients() called without user_profile. Returning 0.", logger_prefix)
        return 0

    if invalidate:
        invalidate_cached_mcpclients_available_to_user_profile(user_profile=user_profile)
    retval = get_cached_mcpclients_available_to_user_profile(user_profile=user_profile).count()
    logger.debug("%s.get_mcpclients() retrieved and cached MCPClients count: %s", logger_prefix, retval)
    return retval


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
    if not user_profile:
        logger.warning("%s.get_secrets() called without user_profile. Returning None.", logger_prefix)
        return 0

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
    if not user_profile:
        logger.warning("%s.get_providers() called without user_profile. Returning 0.", logger_prefix)
        return 0

    retval = Provider.get_cached_providers_for_user(invalidate=invalidate, user=user_profile.user) or []
    return len(retval)


def get_guardrails(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of guardrails associated with the specified user's profile.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: The user profile whose guardrails are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :return: The number of guardrails belonging to the user profile.
    :rtype: int
    """
    if not user_profile:
        logger.warning("%s.get_guardrails() called without user_profile. Returning 0.", logger_prefix)
        return 0

    return Guardrail.get_cached_objects(invalidate=invalidate, user_profile=user_profile).count()


def get_vectorstores(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of vectorstores associated with the specified user's profile.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: The user profile whose vectorstores are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :return: The number of vectorstores belonging to the user profile.
    :rtype: int
    """
    if not user_profile:
        logger.warning("%s.get_vectorstores() called without user_profile. Returning 0.", logger_prefix)
        return 0

    return VectorstoreMeta.get_cached_objects(invalidate=invalidate, user_profile=user_profile).count()


def get_llmhosts(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the total number of LLMHosts associated with the specified user's profile.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: The user profile whose LLMHosts are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :return: The number of LLMHosts belonging to the user profile.
    :rtype: int
    """
    if not user_profile:
        logger.warning("%s.get_llmhosts() called without user_profile. Returning 0.", logger_prefix)
        return 0

    return LLMHost.get_cached_objects(invalidate=invalidate, user_profile=user_profile).count()


def get_extensions(invalidate: bool = False, user_profile: Optional[UserProfile] = None) -> int:
    """
    Returns the number of enabled extensions that the specified user's account may use.

    An extension is available to an account when it is available to every
    account, or to that account in particular. See
    :meth:`smarter.apps.llmtool.models.Extension.is_available_to`.

    The result is cached for a short duration to reduce database queries and
    improve dashboard performance.

    :param user_profile: The user profile whose account's extensions are to be counted.
    :type user_profile: UserProfile
    :param invalidate: Boolean, optional. If True, invalidates the cache before fetching.
    :return: The number of enabled extensions available to the user's account.
    :rtype: int
    """

    @cache_results()
    def _get_extensions(account_id: int) -> int:
        retval = (
            Extension.objects.filter(enabled=True)
            .filter(Q(all_accounts=True) | Q(accounts__id=account_id))
            .distinct()
            .count()
        )
        logger.debug("%s.get_extensions() retrieved and cached extensions count: %s", logger_prefix, retval)
        return retval

    if not user_profile:
        logger.warning("%s.get_extensions() called without user_profile. Returning 0.", logger_prefix)
        return 0

    if invalidate:
        _get_extensions.invalidate(user_profile.account_id)  # type: ignore

    return _get_extensions(user_profile.account_id)  # type: ignore


# pylint: disable=W0613
class MyResourcesView(SmarterAuthenticatedWebView):
    """API view for the "My Resources" React component on the dashboard."""

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this view."""
        class_name = f"{__name__}.{MyResourcesView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:

        user = get_resolved_user(request.user)
        user_profile = UserProfile.get_cached_object(user=user)  # type: ignore

        # user_profile_id is unused, but makes the cache key unique to the user.
        @cache_results()
        @snake_case()
        def _get_resources(user_profile_id: int) -> dict[str, object]:
            retval = {
                "pending_deployments": get_pending_deployments(user_profile=user_profile),
                "llmclients_qty": get_llmclients(user_profile=user_profile),
                "llmclients_url": reverse(PromptReverseNames.namespace, PromptReverseNames.listview),
                # the LLMClient list, narrowed to those that pending_deployments counts.
                "pending_deployments_url": (
                    reverse(PromptReverseNames.namespace, PromptReverseNames.listview) + f"?filter={PENDING_FILTER}"
                ),
                "plugins_qty": get_plugins(user_profile=user_profile),
                "plugins_url": reverse(PluginReverseNames.namespace, PluginReverseNames.listview),
                "mcpclients_qty": get_mcpclients(user_profile=user_profile),
                "mcpclients_url": reverse(MCPClientReverseNames.namespace, MCPClientReverseNames.listview),
                "providers_qty": get_providers(user_profile=user_profile),
                "providers_url": reverse(ProviderReverseNames.namespace, ProviderReverseNames.listview),
                "guardrails_qty": get_guardrails(user_profile=user_profile),
                "guardrails_url": reverse(GuardrailReverseNames.namespace, GuardrailReverseNames.listview),
                "secrets_qty": get_secrets(user_profile=user_profile),
                "secrets_url": reverse(SecretReverseNames.namespace, SecretReverseNames.listview),
                "vectorstores_qty": get_vectorstores(user_profile=user_profile),
                "vectorstores_url": (
                    reverse(VectorstoreReverseNames.namespace, VectorstoreReverseNames.listview)
                    if smarter_settings.enable_vectorstore
                    else None
                ),
                "custom_domains_qty": get_custom_domains(user_profile=user_profile),
                "custom_domains_url": reverse(
                    LLMClientReverseNames.namespace, LLMClientReverseNames.custom_domain_listview
                ),
                "llmhosts_qty": get_llmhosts(user_profile=user_profile),
                "llmhosts_url": reverse(LLMHostReverseNames.namespace, LLMHostReverseNames.listview),
                "extensions_qty": get_extensions(user_profile=user_profile),
                # only superusers may open the console's Extensions page.
                "extensions_url": (
                    reverse(ExtensionReverseNames.namespace, ExtensionReverseNames.listview)
                    if user.is_superuser
                    else EXTENSIONS_DOCS_URL
                ),
            }
            logger.debug("%s.post() cached context %s", self.formatted_class_name, logging.formatted_json(retval))
            return retval

        retval = _get_resources(user_profile.id)  # type: ignore[union-attr]
        logger.debug("%s.post()", self.formatted_class_name)
        return JsonResponse(retval, status=HTTPStatus.OK)
