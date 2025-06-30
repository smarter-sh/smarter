# pylint: disable=W0613
"""Utility functions for Provider app."""

import logging

import requests

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .models import (
    Provider,
    ProviderModel,
    ProviderModelVerification,
    ProviderModelVerificationTypes,
    ProviderVerification,
    ProviderVerificationTypes,
)
from .signals import (
    model_verification_failure,
    model_verification_success,
    provider_verification_failure,
    provider_verification_success,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.PROVIDER_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and level <= logging.INFO
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

module_prefix = "smarter.apps.provider.utils."


def get_provider_verification_for_type(
    provider: Provider, verification_type: ProviderVerificationTypes
) -> ProviderVerification:
    """
    Get the provider verification for a specific type.
    """
    prefix = formatted_text(module_prefix + "get_provider_verification_for_type()")
    logger.info("%s Getting provider verification for %s of type %s", prefix, provider.name, verification_type)

    instance, _ = ProviderVerification.objects.get_or_create(provider=provider, verification_type=verification_type)
    if instance.is_valid:
        logger.info("%s Provider verification for %s is still valid %s", prefix, provider, instance.updated_at)
    return instance


def get_model_verification_for_type(
    provider_model: ProviderModel, verification_type: ProviderModelVerificationTypes
) -> ProviderModelVerification:
    """
    Get the model verification for a specific type.
    """
    prefix = formatted_text(module_prefix + "get_model_verification_for_type()")
    logger.info("%s Getting model verification for %s of type %s", prefix, provider_model.name, verification_type)

    instance, _ = ProviderModelVerification.objects.get_or_create(
        provider_model=provider_model, verification_type=verification_type
    )
    if instance.is_valid:
        logger.info("%s Streaming verification for %s is still valid %s", prefix, provider_model, instance.updated_at)
    return instance


def set_model_verification(
    provider_model_verification: ProviderModelVerification, is_successful: bool, **kwargs
) -> None:
    """
    Set the model verification status.
    """
    prefix = formatted_text(module_prefix + "set_model_verification()")
    logger.info(
        "%s Setting model verification for %s to %s",
        prefix,
        provider_model_verification.provider_model.name,
        is_successful,
    )

    provider_model_verification.is_successful = is_successful
    provider_model_verification.save()
    if is_successful:
        model_verification_success.send(
            sender=ProviderModelVerification, provider_model_verification=provider_model_verification
        )
    else:
        model_verification_failure.send(
            sender=ProviderModelVerification, provider_model_verification=provider_model_verification
        )


def set_provider_verification(provider_verification: ProviderVerification, is_successful: bool, **kwargs) -> None:
    """
    Set the provider verification status.
    """
    prefix = formatted_text(module_prefix + "set_provider_verification()")
    logger.info(
        "%s Setting provider verification for %s to %s",
        prefix,
        provider_verification.provider.name,
        is_successful,
    )

    provider_verification.is_successful = is_successful
    provider_verification.save()
    if is_successful:
        provider_verification_success.send(sender=ProviderVerification, provider_verification=provider_verification)
    else:
        provider_verification_failure.send(sender=ProviderVerification, provider_verification=provider_verification)


def test_web_page(url: str, test_str: str) -> bool:
    """
    Test a web page to see if it is valid.
    """
    prefix = formatted_text(module_prefix + "test_web_page()")
    logger.info("%s Testing web page %s", prefix, url)

    try:
        response = requests.get(url, timeout=10)
        if (
            response.status_code == 200
            and ("<html" in response.text.lower() or "<!doctype html" in response.text.lower())
            and test_str.lower() in response.text.lower()
        ):
            logger.info("%s Web page test succeeded.", prefix)
            return True
        else:
            logger.error("%s Web page test failed: Non-200 status or missing documentation HTML.", prefix)
            return False
    except requests.RequestException as exc:
        logger.error("%s Web page test failed: %s", prefix, exc)
        return False
