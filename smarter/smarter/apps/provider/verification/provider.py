# pylint: disable=W0613,C0115,R0913
"""
Verification functions for the Provider model.
This module contains functions to verify various aspects of a provider, such as API connectivity,
logo, contact email, support email, website URL, terms of service URL, privacy policy URL, TOS acceptance, and production API key.
"""
import logging

from smarter.apps.provider.models import (
    Provider,
    ProviderStatus,
    ProviderVerificationTypes,
)
from smarter.apps.provider.signals import (
    provider_activated,
    provider_verification_failure,
    provider_verification_success,
)
from smarter.apps.provider.utils import (
    get_provider_verification_for_type,
    set_provider_verification,
    test_web_page,
)
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text


logger = logging.getLogger(__name__)
module_prefix = "smarter.apps.provider.verification.provider."


def verify_provider_api_connectivity(provider: Provider, **kwargs) -> bool:
    """
    Verify the API connectivity of the provider.
    """
    provider_verification = get_provider_verification_for_type(
        provider=provider, verification_type=ProviderVerificationTypes.API_CONNECTIVITY
    )
    if provider_verification.is_valid:
        return True

    success = provider.test_connectivity()

    set_provider_verification(provider_verification=provider_verification, is_successful=success)
    return success


def verify_provider_logo(provider: Provider, **kwargs) -> bool:
    """
    Verify the logo of the provider.
    """

    provider_verification = get_provider_verification_for_type(
        provider=provider, verification_type=ProviderVerificationTypes.LOGO
    )
    if provider_verification.is_valid:
        return True

    success = provider.logo is not None
    if not provider.logo.name.endswith((".png", ".jpg", ".jpeg", ".svg")):
        success = False

    set_provider_verification(provider_verification=provider_verification, is_successful=success)
    return success


def verify_provider_contact_email(provider: Provider, **kwargs) -> bool:
    """
    Verify the contact email of the provider.
    """

    provider_verification = get_provider_verification_for_type(
        provider=provider, verification_type=ProviderVerificationTypes.CONTACT_EMAIL
    )
    if provider_verification.is_valid:
        return True

    success = provider.contact_email is not None and provider.contact_email_verified is not None
    set_provider_verification(provider_verification=provider_verification, is_successful=success)
    return success


def verify_provider_support_email(provider: Provider, **kwargs) -> bool:
    """
    Verify the support email of the provider.
    """

    provider_verification = get_provider_verification_for_type(
        provider=provider, verification_type=ProviderVerificationTypes.SUPPORT_EMAIL
    )
    if provider_verification.is_valid:
        return True

    success = provider.support_email is not None and provider.support_email_verified is not None
    set_provider_verification(provider_verification=provider_verification, is_successful=success)
    return success


def verify_provider_website_url(provider: Provider, **kwargs) -> bool:
    """
    Verify the website URL of the provider.
    """
    provider_verification = get_provider_verification_for_type(
        provider=provider, verification_type=ProviderVerificationTypes.WEBSITE_URL
    )
    if provider_verification.is_valid:
        return True

    success = provider.website is not None and test_web_page(provider.website, test_str="")
    set_provider_verification(provider_verification=provider_verification, is_successful=success)
    return success


def verify_provider_terms_of_service_url(provider: Provider, **kwargs) -> bool:
    """
    Verify the terms of service URL of the provider.
    """
    provider_verification = get_provider_verification_for_type(
        provider=provider, verification_type=ProviderVerificationTypes.TOS_URL
    )
    if provider_verification.is_valid:
        return True

    success = provider.terms_of_service_url is not None and test_web_page(
        provider.terms_of_service_url, test_str="Terms of Service"
    )
    set_provider_verification(provider_verification=provider_verification, is_successful=success)
    return success


def verify_provider_privacy_policy_url(provider: Provider, **kwargs) -> bool:
    """
    Verify the privacy policy URL of the provider.
    """
    provider_verification = get_provider_verification_for_type(
        provider=provider, verification_type=ProviderVerificationTypes.PRIVACY_POLICY_URL
    )
    if provider_verification.is_valid:
        return True

    success = provider.privacy_policy_url is not None and test_web_page(
        provider.privacy_policy_url, test_str="Privacy Policy"
    )
    set_provider_verification(provider_verification=provider_verification, is_successful=success)
    return success


def verify_provider_tos_accepted(provider: Provider, **kwargs) -> bool:
    """
    Verify if the provider has accepted the terms of service.
    """
    provider_verification = get_provider_verification_for_type(
        provider=provider, verification_type=ProviderVerificationTypes.TOS_ACCEPTANCE
    )
    if provider_verification.is_valid:
        return True

    success = provider.tos_accepted
    set_provider_verification(provider_verification=provider_verification, is_successful=success)
    return success


def verify_provider_production_api_key(provider: Provider, **kwargs) -> bool:
    """
    Verify the production API key of the provider.
    """
    provider_verification = get_provider_verification_for_type(
        provider=provider, verification_type=ProviderVerificationTypes.PRODUCTION_API_KEY
    )
    if provider_verification.is_valid:
        return True

    success = provider.production_api_key is not None and len(provider.production_api_key) > 0
    set_provider_verification(provider_verification=provider_verification, is_successful=success)
    return success


def verify_provider(provider_id, **kwargs):
    """
    Run test bank on provider.
    """
    prefix = formatted_text(module_prefix + "verify_provider()")
    try:
        provider = Provider.objects.get(id=provider_id)
    except Provider.DoesNotExist:
        logger.error("%s Provider with id %s does not exist", prefix, provider_id)
        return

    logger.info("%s Testing provider: %s", prefix, provider.name)
    if provider.is_active:
        logger.warning("%s Provider %s is already active.", prefix, provider.name)

    # blackball method
    success = True

    if provider.is_deprecated:
        logger.warning("%s Provider %s is deprecated, cannot verify.", prefix, provider.name)
        success = False

    if provider.is_suspended:
        logger.warning("%s Provider %s is suspended, cannot verify.", prefix, provider.name)
        success = False

    if provider.is_flagged:
        logger.warning("%s Provider %s is flagged, cannot verify.", prefix, provider.name)
        success = False

    # verify api_url with api_key
    success = success and verify_provider_api_connectivity(provider=provider)
    success = success and verify_provider_logo(provider=provider)
    success = success and verify_provider_contact_email(provider=provider)
    success = success and verify_provider_support_email(provider=provider)
    success = success and verify_provider_website_url(provider=provider)
    success = success and verify_provider_terms_of_service_url(provider=provider)
    success = success and verify_provider_privacy_policy_url(provider=provider)
    success = success and verify_provider_tos_accepted(provider=provider)
    success = success and verify_provider_production_api_key(provider=provider)

    if not provider.can_activate:
        logger.error("%s Provider %s cannot be activated.", prefix, provider.name)
        success = False

    if success:
        provider_verification_success.send(sender=Provider, provider=provider)
        provider.status = ProviderStatus.VERIFIED
        provider.is_verified = True
        if provider.can_activate:
            try:
                provider.activate()
                provider.save(update_fields=["status", "is_verified"])
                provider_activated.send(sender=Provider, provider=provider)
            except SmarterValueError as exc:
                logger.error("%s Activation failed for provider: %s, error: %s", prefix, provider.name, exc)
    else:
        provider.status = ProviderStatus.FAILED
        provider.is_verified = False
        provider.is_active = False
        provider.save(update_fields=["status", "is_active", "is_verified"])
        logger.error("%s Verification failed for provider: %s", prefix, provider.name)
        provider_verification_failure.send(sender=Provider, provider=provider)
