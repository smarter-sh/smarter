"""
The SAM resource apps' feature flags: one ``smarter_settings.enable_<app>`` flag per app.

Each SAM resource app (Connection, Guardrail, LLMClient, ...) can be turned off with its
``SMARTER_ENABLE_<APP>`` environment variable. Every flag defaults to true. A disabled app is off
everywhere:

- its web console pages, its web console api (``/api/web/``) and its REST api (``/api/v1/``)
  are not mounted (:func:`sam_app_urlpatterns`),
- the cli api refuses its kinds, e.g. ``smarter apply`` of a Guardrail manifest
  (:func:`raise_if_kind_disabled`),
- its AppConfig doesn't connect its signal receivers
  (:class:`smarter.lib.django.apps.SmarterAppConfig`).

The account, prompt and other core apps have no flag: the platform doesn't work without them.
Their kinds (Account, User, Budget, AuthToken, Prompt) are always enabled.
"""

from types import ModuleType
from typing import NamedTuple, Optional

from django.urls import URLResolver, include, path
from smarter_types import SAMKinds

from smarter.common.conf.settings.features import FeatureSettings
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.common.utils.utils import ENVIRONMENT_VARIABLE_PREFIX
from smarter.lib import logging
from smarter.lib.manifest.exceptions import SAMBadRequestError

logger = logging.getSmarterLogger(__name__)


class SamApp(NamedTuple):
    """A SAM resource app, the feature flag that enables it, and the manifest kinds it owns."""

    app_label: str
    """The Django app label, e.g. ``guardrail``."""

    setting: str
    """The name of the ``smarter_settings`` flag that enables the app, e.g. ``app_guardrail_enable``."""

    label: str
    """The app's name in messages, e.g. ``Guardrail``."""

    kinds: tuple[str, ...]
    """The manifest kinds that the app owns, e.g. ``("Guardrail",)``."""

    @property
    def env_name(self) -> str:
        """The environment variable that sets the flag, e.g. ``SMARTER_APP_GUARDRAIL_ENABLE``."""
        return f"{ENVIRONMENT_VARIABLE_PREFIX}{self.setting.upper()}"

    def is_enabled(self, settings: FeatureSettings) -> bool:
        """
        Whether the app is enabled.

        :param settings: The settings that hold the flag, normally ``smarter_settings``.
        :returns: The value of the app's flag.
        """
        enabled = getattr(settings, self.setting)
        return bool(enabled)


SAM_APPS: tuple[SamApp, ...] = (
    SamApp(
        "connection",
        "app_connection_enable",
        "Connection",
        (SAMKinds.API_CONNECTION.value, SAMKinds.SQL_CONNECTION.value),
    ),
    SamApp("guardrail", "app_guardrail_enable", "Guardrail", (SAMKinds.GUARDRAIL.value,)),
    SamApp(
        "llmclient",
        "app_llmclient_enable",
        "LLMClient",
        (SAMKinds.LLM_CLIENT.value, SAMKinds.CUSTOM_DOMAIN.value),
    ),
    SamApp(
        "llmhost",
        "app_llmhost_enable",
        "LLMHost",
        (SAMKinds.LLM_HOST.value, SAMKinds.LLM_HOST_COMPUTE.value),
    ),
    SamApp(
        "llmtool",
        "app_llmtool_enable",
        "LLMTool",
        (
            SAMKinds.API_PLUGIN.value,
            SAMKinds.IMAGE_SEARCH_PLUGIN.value,
            SAMKinds.SKILL_PLUGIN.value,
            SAMKinds.SQL_PLUGIN.value,
            SAMKinds.STATIC_PLUGIN.value,
            SAMKinds.WEBSEARCH_PLUGIN.value,
        ),
    ),
    SamApp("mcpclient", "app_mcpclient_enable", "MCPClient", (SAMKinds.MCP_CLIENT.value,)),
    SamApp("orchestrator", "app_orchestrator_enable", "Orchestrator", (SAMKinds.ORCHESTRATOR.value,)),
    SamApp("provider", "app_provider_enable", "Provider", (SAMKinds.PROVIDER.value,)),
    SamApp("proxy", "app_proxy_enable", "Proxy", (SAMKinds.PROXY.value,)),
    SamApp("secret", "app_secret_enable", "Secret", (SAMKinds.SECRET.value,)),
    SamApp("vectorsearch", "app_vectorsearch_enable", "VectorSearch", (SAMKinds.VECTORSEARCH.value,)),
    SamApp("vectorstore", "app_vectorstore_enable", "Vectorstore", (SAMKinds.VECTORSTORE.value,)),
)
"""Every SAM resource app that has a feature flag."""


CORE_KINDS: tuple[str, ...] = (
    SAMKinds.ACCOUNT.value,
    SAMKinds.AUTH_TOKEN.value,
    SAMKinds.BUDGET.value,
    SAMKinds.PROMPT.value,
    SAMKinds.USER.value,
)
"""The kinds of the core apps, which have no feature flag and are always enabled."""


class SAMKindDisabledError(SAMBadRequestError):
    """A manifest's kind belongs to a SAM app that this platform has disabled."""


def get_sam_app(setting: str) -> SamApp:
    """
    Return the SAM app that a flag enables.

    :param setting: The flag's name, e.g. ``app_guardrail_enable``.
    :returns: The app.
    :raises KeyError: If no SAM app has that flag.
    """
    for sam_app in SAM_APPS:
        if sam_app.setting == setting:
            return sam_app
    raise KeyError(setting)


def sam_app_of_kind(kind: str) -> Optional[SamApp]:
    """
    Return the SAM app that owns a manifest kind.

    :param kind: The kind, in any case, e.g. ``Guardrail`` or ``guardrail``.
    :returns: The app, or None for a core kind, e.g. ``Account``, or an unknown one.
    """
    lower_kind = kind.lower()
    for sam_app in SAM_APPS:
        for app_kind in sam_app.kinds:
            if app_kind.lower() == lower_kind:
                return sam_app
    return None


def kind_is_enabled(kind: str, settings: Optional[FeatureSettings] = None) -> bool:
    """
    Whether this platform accepts manifests of a kind.

    :param kind: The kind, in any case.
    :param settings: The settings that hold the flags. Defaults to ``smarter_settings``.
    :returns: False if the kind's SAM app is disabled, otherwise True, for core and unknown kinds too.
    """
    sam_app = sam_app_of_kind(kind)
    if sam_app is None:
        return True
    if settings is None:
        # pylint: disable=import-outside-toplevel
        from smarter.common.conf import smarter_settings

        settings = smarter_settings
    return sam_app.is_enabled(settings)


def raise_if_kind_disabled(kind: str, settings: Optional[FeatureSettings] = None) -> None:
    """
    Refuse a manifest kind whose SAM app is disabled.

    :param kind: The kind, in any case.
    :param settings: The settings that hold the flags. Defaults to ``smarter_settings``.
    :raises SAMKindDisabledError: If the kind's app is disabled. Its message names the environment
        variable that enables it.
    """
    if kind_is_enabled(kind, settings):
        return
    sam_app = sam_app_of_kind(kind)
    if sam_app is None:
        return
    raise SAMKindDisabledError(
        f"{kind} manifests are disabled on this platform. Set env `{sam_app.env_name}=true` to enable them."
    )


def reverse_if_enabled(setting: str, *args: str, urlconf: Optional[str] = None) -> Optional[str]:
    """
    Reverse a url of a SAM app, or return None while the app is disabled and its urls aren't mounted.

    :param setting: The app's flag, e.g. ``app_guardrail_enable``.
    :param args: The namespaces and the view name, as for :func:`smarter.lib.django.shortcuts.reverse`.
    :param urlconf: The urlconf to reverse against, or None for the active one.
    :returns: The url path, or None.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.common.conf import smarter_settings
    from smarter.lib.django.shortcuts import reverse

    sam_app = get_sam_app(setting)
    if not sam_app.is_enabled(smarter_settings):
        return None
    if urlconf is None:
        url = reverse(*args)
    else:
        url = reverse(*args, urlconf=urlconf)
    return url


class SamAppUrls(NamedTuple):
    """The urls of one SAM resource app in one urlconf, and the feature flag that mounts them."""

    setting: str
    """The name of the ``smarter_settings`` flag that mounts the urls, e.g. ``app_guardrail_enable``."""

    label: str
    """The urls' name in log messages, e.g. ``Guardrail``."""

    prefix: str
    """The urls' path prefix, e.g. ``guardrail/``."""

    urls: ModuleType
    """The app's urls module."""

    namespace: str
    """The urls' namespace."""


def sam_app_urlpatterns(settings: FeatureSettings, apps_urls: list[SamAppUrls], description: str) -> list[URLResolver]:
    """
    Return the url patterns of the SAM resource apps whose feature flag is true.

    Logs, for each one, whether its urls are mounted, and the environment variable that mounts them
    when they aren't.

    :param settings: The settings that hold the ``enable_<app>`` flags, normally ``smarter_settings``.
    :param apps_urls: The apps' urls and the flag that mounts each one.
    :param description: What the urls are, in log messages, e.g. ``web console pages``.
    :returns: One ``include()`` per enabled app, in the order of ``apps_urls``.
    """
    patterns: list[URLResolver] = []
    for app_urls in apps_urls:
        sam_app = get_sam_app(app_urls.setting)
        if not sam_app.is_enabled(settings):
            logger.info(
                "%s %s are %s. Set env `%s=true` to enable.",
                app_urls.label,
                description,
                SmarterReadyState.NOT_READY,
                sam_app.env_name,
            )
            continue
        pattern = path(app_urls.prefix, include(app_urls.urls, namespace=app_urls.namespace))
        patterns.append(pattern)
        logger.debug("%s %s are %s.", app_urls.label, description, SmarterReadyState.READY)
    return patterns


__all__ = [
    "CORE_KINDS",
    "SAM_APPS",
    "SAMKindDisabledError",
    "SamApp",
    "SamAppUrls",
    "get_sam_app",
    "kind_is_enabled",
    "raise_if_kind_disabled",
    "sam_app_of_kind",
    "sam_app_urlpatterns",
]
