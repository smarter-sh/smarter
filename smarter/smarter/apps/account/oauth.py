"""
Whether the console offers sign-in with Google and with GitHub.

The sign-in page shows a provider's button, and the console's session api reports it, only when
the ``ENABLE_OAUTH2`` waffle switch is active, the provider's key and secret are set in
``smarter_settings``, and one of its authentication backends is in
``settings.AUTHENTICATION_BACKENDS``. See https://docs.djangoproject.com/en/6.0/topics/auth/customizing/.
"""

from django.conf import settings
from pydantic import SecretStr

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.VIEW_LOGGING]
)
logger_prefix = logging.SmarterFormattedText.text(__name__)

GOOGLE_OAUTH_BACKENDS = [
    "social_core.backends.google.GoogleOAuth2",
    "smarter.lib.social_core.backends.multitenant.GoogleOAuth2Multitenant",
]
"""The authentication backends that sign in with Google."""

GITHUB_OAUTH_BACKENDS = [
    "social_core.backends.github.GithubOAuth2",
    "smarter.lib.social_core.backends.multitenant.GithubOAuth2Multitenant",
]
"""The authentication backends that sign in with GitHub."""


def is_credential_set(credential: SecretStr) -> bool:
    """
    Whether an OAuth key or secret in ``smarter_settings`` has a value.

    :param credential: The key or secret.
    :returns: False when it is empty or the settings' placeholder for a missing value.
    """
    value = credential.get_secret_value()
    if value in ("", None, smarter_settings.default_missing_value):
        return False
    return True


def oauth_provider_enabled(provider: str, key: SecretStr, secret: SecretStr, backends: list[str]) -> bool:
    """
    Whether the console offers sign-in with one OAuth provider.

    :param provider: The provider's name, for the log, e.g. ``Google``.
    :param key: The provider's client key.
    :param secret: The provider's client secret.
    :param backends: The authentication backends that sign in with the provider.
    :returns: True when the switch is active, the key and secret are set, and a backend is configured.
    """
    if not waffle.switch_is_active(SmarterWaffleSwitches.ENABLE_OAUTH2):
        logger.debug(
            "%s.oauth_provider_enabled() %s: the %s switch is not active.",
            logger_prefix,
            provider,
            SmarterWaffleSwitches.ENABLE_OAUTH2,
        )
        return False
    if not is_credential_set(key):
        logger.debug("%s.oauth_provider_enabled() %s: the key is not set.", logger_prefix, provider)
        return False
    if not is_credential_set(secret):
        logger.debug("%s.oauth_provider_enabled() %s: the secret is not set.", logger_prefix, provider)
        return False
    for backend in backends:
        if backend in settings.AUTHENTICATION_BACKENDS:
            return True
    logger.warning(
        "%s.oauth_provider_enabled() %s credentials are set, but settings.AUTHENTICATION_BACKENDS has none of "
        "its backends: %s",
        logger_prefix,
        provider,
        backends,
    )
    return False


def google_oauth_enabled() -> bool:
    """
    Whether the console offers sign-in with Google.

    :returns: True when the switch, the Google key and secret, and a Google backend are all set.
    """
    return oauth_provider_enabled(
        "Google",
        smarter_settings.social_auth_google_oauth2_key,
        smarter_settings.social_auth_google_oauth2_secret,
        GOOGLE_OAUTH_BACKENDS,
    )


def github_oauth_enabled() -> bool:
    """
    Whether the console offers sign-in with GitHub.

    :returns: True when the switch, the GitHub key and secret, and a GitHub backend are all set.
    """
    return oauth_provider_enabled(
        "GitHub",
        smarter_settings.social_auth_github_key,
        smarter_settings.social_auth_github_secret,
        GITHUB_OAUTH_BACKENDS,
    )
