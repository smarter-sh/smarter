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

from django.http import HttpRequest, JsonResponse
from django.urls import reverse

from smarter.__version__ import __version__
from smarter.apps.account.models import (
    UserProfile,
    get_resolved_user,
)
from smarter.apps.chatbot.models import ChatBot, ChatBotAPIKey, ChatBotCustomDomain
from smarter.apps.connection.models import ConnectionBase
from smarter.apps.connection.urls import ConnectionReverseViews
from smarter.apps.plugin.models import (
    PluginMeta,
)
from smarter.apps.plugin.urls import PluginReverseViews
from smarter.apps.prompt.urls import PromptReverseViews
from smarter.apps.provider.models import Provider
from smarter.apps.provider.urls import ProviderReverseViews
from smarter.apps.secret.models import Secret
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.views import (
    SmarterAuthenticatedWebView,
)

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)


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

    @cache_results()
    def _get_pending_deployments(user_profile_id: int) -> int:
        logger.debug(
            "%s.get_pending_deployments() called with invalidate=%s for user_profile_id=%s",
            logger_prefix,
            invalidate,
            user_profile,
        )
        return ChatBot.objects.filter(deployed=False).with_ownership_permission_for(user=user_profile.user).count() or 0  # type: ignore

    if not user_profile:
        logger.warning("%s.get_pending_deployments() called without user_profile. Returning None.", logger_prefix)
        return 0
    if invalidate and user_profile:
        _get_pending_deployments.invalidate(user_profile.id)  # type: ignore

    return _get_pending_deployments(user_profile.id)  # type: ignore


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
    if not user_profile:
        logger.warning("%s.get_chatbots() called without user_profile. Returning None.", logger_prefix)
        return 0

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
    if not user_profile:
        logger.warning("%s.get_plugins() called without user_profile. Returning None.", logger_prefix)
        return 0
    retval = PluginMeta.get_cached_plugins_for_user_profile_id(invalidate=invalidate, user_profile_id=user_profile.id)  # type: ignore
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

    @cache_results()
    def _get_api_keys(user_profile_id: int) -> int:
        logger.debug(
            "%s.get_api_keys() called with invalidate=%s for user_profile_id=%s",
            logger_prefix,
            invalidate,
            user_profile,
        )
        return ChatBotAPIKey.objects.filter(chatbot__user_profile__id=user_profile_id).count() or 0

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

    @cache_results()
    def _get_custom_domains(user_profile_id: int) -> int:
        logger.debug(
            "%s.get_custom_domains() called with invalidate=%s for user_profile_id=%s",
            logger_prefix,
            invalidate,
            user_profile,
        )
        return ChatBotCustomDomain.objects.filter(chatbot__user_profile__id=user_profile_id).count() or 0

    if not user_profile:
        logger.warning("%s.get_custom_domains() called without user_profile. Returning None.", logger_prefix)
        return 0

    if invalidate and user_profile:
        _get_custom_domains.invalidate(user_profile.id)  # type: ignore

    return _get_custom_domains(user_profile.id)  # type: ignore


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
    if not user_profile:
        logger.warning("%s.get_connections() called without user_profile. Returning None.", logger_prefix)
        return 0

    retval = ConnectionBase.get_cached_connections_for_user(invalidate=invalidate, user=user_profile.user) or []
    return len(retval)


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


# pylint: disable=W0613
class MyResourcesView(SmarterAuthenticatedWebView):
    """
    API view for the "My Resources" React component on the dashboard.

    """

    def post(self, request: HttpRequest, *args, **kwargs):

        prompt_reverse_name = ":".join([PromptReverseViews.namespace, PromptReverseViews.listview])
        plugin_reverse_name = ":".join([PluginReverseViews.namespace, PluginReverseViews.listview])
        connection_reverse_name = ":".join([ConnectionReverseViews.namespace, ConnectionReverseViews.listview])
        provider_reverse_name = ":".join([ProviderReverseViews.namespace, ProviderReverseViews.listview])

        user = get_resolved_user(request.user)
        user_profile = UserProfile.get_cached_object(user=user)  # type: ignore

        retval = {
            "pending_deployments": get_pending_deployments(user_profile=user_profile),
            "chatbots_qty": get_chatbots(user_profile=user_profile),
            "chatbots_url": reverse(prompt_reverse_name),
            "plugins_qty": get_plugins(user_profile=user_profile),
            "plugins_url": reverse(plugin_reverse_name),
            "connections_qty": get_connections(user_profile=user_profile),
            "connections_url": reverse(connection_reverse_name),
            "providers_qty": get_providers(user_profile=user_profile),
            "providers_url": reverse(provider_reverse_name),
        }

        logger.debug("%s.post() returning: %s", self.formatted_class_name, logging.formatted_json(retval))
        return JsonResponse(retval, status=HTTPStatus.OK)
