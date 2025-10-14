"""Provider Signal receivers"""

# pylint: disable=W0613

import logging
from typing import Union

from django.db.models.signals import post_save
from django.dispatch import receiver

from smarter.common.conf import settings as smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .models import (
    Provider,
    ProviderModel,
    ProviderModelVerification,
    ProviderVerification,
)
from .signals import (
    model_verification_failure,
    model_verification_requested,
    model_verification_success,
    provider_activated,
    provider_deactivated,
    provider_deprecated,
    provider_flagged,
    provider_suspended,
    provider_undeprecated,
    provider_unflagged,
    provider_unsuspended,
    provider_verification_failure,
    provider_verification_requested,
    provider_verification_success,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.RECEIVER_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
module_prefix = "smarter.apps.provider.receivers"


def get_prefix(function_name: str = "") -> str:
    """Get the module prefix for logging."""
    return (
        formatted_text(module_prefix + "." + function_name + "()") if function_name else formatted_text(module_prefix)
    )


# ------------------------------------------------------------------------------
# Model verification handlers
@receiver(model_verification_requested, dispatch_uid="model_verification_requested_receiver")
def handle_model_verification_requested(sender, instance: ProviderModel, **kwargs):
    """Handle model verification requested signal."""
    prefix = get_prefix("handle_model_verification_requested")
    logger.info("%s Model verification requested for model: %s", prefix, instance.name)

    # pylint: disable=C0415
    from .tasks import verify_provider_model

    verify_provider_model.delay(provider_model_id=instance.id)


@receiver(model_verification_success, dispatch_uid="model_verification_success_receiver")
def handle_model_verification_success(
    sender,
    provider_model: ProviderModel = None,
    provider_model_verification: ProviderModelVerification = None,
    **kwargs,
):
    """Handle model verification success signal."""
    prefix = get_prefix("handle_model_verification_success")
    if provider_model_verification:
        logger.info(
            "%s Model verification successful for model: %s with verification: %s",
            prefix,
            provider_model.name,
            provider_model_verification.verification_type,
        )
    elif provider_model:
        logger.info("%s Model verification successful for model: %s", prefix, provider_model.name)
    else:
        logger.info("%s Model verification successful for an unknown model for an unknown reason", prefix)


@receiver(model_verification_failure, dispatch_uid="model_verification_failure_receiver")
def handle_model_verification_failure(
    sender,
    provider_model: Union[ProviderModel, None] = None,
    provider_model_verification: Union[ProviderModelVerification, None] = None,
    **kwargs,
):
    """Handle model verification failure signal."""
    prefix = get_prefix("handle_model_verification_failure")
    if provider_model_verification:
        logger.error(
            "%s Model verification failed for model: %s with verification: %s",
            prefix,
            provider_model.name if provider_model else "Unknown",
            provider_model_verification.verification_type if provider_model_verification else "Unknown",
        )
    elif provider_model:
        logger.error(
            "%s Model verification failed for model: %s", prefix, provider_model.name if provider_model else "Unknown"
        )
    else:
        logger.error("%s Model verification failed for an unknown model for an unknown reason", prefix)


# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Provider handlers
# ------------------------------------------------------------------------------


@receiver(provider_verification_requested, dispatch_uid="verification_requested_receiver")
def handle_provider_verification_requested(sender, instance: Provider, **kwargs):
    """Handle test requested signal."""
    prefix = get_prefix("handle_provider_verification_requested")
    logger.info("%s Test requested for provider: %s", prefix, instance.name)

    # pylint: disable=C0415
    from .tasks import verify_provider

    verify_provider.delay(provider_id=instance.id)


@receiver(provider_verification_success, dispatch_uid="verification_success_receiver")
def handle_provider_verification_success(
    sender, provider: Provider = None, provider_verification: ProviderVerification = None, **kwargs
):
    """Handle test passed signal."""
    prefix = get_prefix("handle_provider_verification_success")
    if provider_verification:
        logger.info(
            "%s Test passed for provider: %s with verification: %s",
            prefix,
            provider.name,
            provider_verification.verification_type,
        )
    elif provider:
        logger.info("%s Test passed for provider: %s", prefix, provider.name)
    else:
        logger.info("%s Test passed for an unknown provider for an unknown reason", prefix)


@receiver(provider_verification_failure, dispatch_uid="verification_failure_receiver")
def handle_provider_verification_failure(
    sender, provider: Provider = None, provider_verification: ProviderVerification = None, **kwargs
):
    """Handle test failed signal."""
    prefix = get_prefix("handle_provider_verification_failure")
    if provider_verification:
        logger.error(
            "%s Test failed for provider: %s with verification: %s",
            prefix,
            provider.name,
            provider_verification.verification_type,
        )
    elif provider:
        logger.error("%s Test failed for provider: %s", prefix, provider.name)
    else:
        logger.error("%s Test failed for an unknown provider for an unknown reason", prefix)


@receiver(provider_deactivated, dispatch_uid="provider_deactivated_receiver")
def handle_provider_deactivated(sender, instance: Provider, **kwargs):
    """Handle provider deactivated signal."""
    prefix = get_prefix("handle_provider_deactivated")
    logger.info("%s Provider deactivated: %s", prefix, instance.name)


@receiver(provider_activated, dispatch_uid="provider_activated_receiver")
def handle_provider_activated(sender, instance: Provider, **kwargs):
    """Handle provider activated signal."""
    prefix = get_prefix("handle_provider_activated")
    logger.info("%s Provider activated: %s", prefix, instance.name)


@receiver(provider_activated, dispatch_uid="provider_verified_receiver")
def handle_provider_verified(sender, instance: Provider, **kwargs):
    """Handle provider verified signal."""
    prefix = get_prefix("handle_provider_verified")
    logger.info("%s Provider verified: %s", prefix, instance.name)


@receiver(provider_suspended, dispatch_uid="provider_suspended_receiver")
def handle_provider_suspended(sender, instance: Provider, **kwargs):
    """Handle provider suspended signal."""
    prefix = get_prefix("handle_provider_suspended")
    logger.info("%s Provider suspended: %s", prefix, instance.name)


@receiver(provider_unsuspended, dispatch_uid="provider_unsuspended_receiver")
def handle_provider_unsuspended(sender, instance: Provider, **kwargs):
    """Handle provider unsuspended signal."""
    prefix = get_prefix("handle_provider_unsuspended")
    logger.info("%s Provider unsuspended: %s", prefix, instance.name)


@receiver(provider_deprecated, dispatch_uid="provider_deprecated_receiver")
def handle_provider_deprecated(sender, instance: Provider, **kwargs):
    """Handle provider deprecated signal."""
    prefix = get_prefix("handle_provider_deprecated")
    logger.info("%s Provider deprecated: %s", prefix, instance.name)


@receiver(provider_undeprecated, dispatch_uid="provider_undeprecated_receiver")
def handle_provider_undeprecated(sender, instance: Provider, **kwargs):
    """Handle provider undeprecated signal."""
    prefix = get_prefix("handle_provider_undeprecated")
    logger.info("%s Provider undeprecated: %s", prefix, instance.name)


@receiver(provider_flagged, dispatch_uid="provider_flagged_receiver")
def handle_provider_flagged(sender, instance: Provider, **kwargs):
    """Handle provider flagged signal."""
    prefix = get_prefix("handle_provider_flagged")
    logger.info("%s Provider flagged: %s", prefix, instance.name)


@receiver(provider_unflagged, dispatch_uid="provider_unflagged_receiver")
def handle_provider_unflagged(sender, instance: Provider, **kwargs):
    """Handle provider unflagged signal."""
    prefix = get_prefix("handle_provider_unflagged")
    logger.info("%s Provider unflagged: %s", prefix, instance.name)


@receiver(post_save, sender=Provider)
def log_provider_save(sender, instance: Provider, created: bool, **kwargs):
    """Create default completion models when a new provider is created."""
    prefix = get_prefix("log_provider_save")
    if created:
        logger.info("%s Created Provider: %s", prefix, instance.name)
    else:
        logger.info("%s Updated Provider: %s", prefix, instance.name)


# ------------------------------------------------------------------------------
# Provider Model handlers
# ------------------------------------------------------------------------------


@receiver(post_save, sender=ProviderModel)
def provider_model_save(sender, instance: ProviderModel, created: bool, **kwargs):
    """Log when a completion model is saved."""
    prefix = get_prefix("provider_model_save")
    # pylint: disable=W0212
    supports_fields = [f.name for f in instance._meta.fields if f.name.startswith("supports_")]

    # determine whether we need to run verifications
    if created:
        logger.info("%s Created Completion Model: %s for Provider: %s", prefix, instance.name, instance.provider.name)
        model_verification_requested.send(
            sender=ProviderModel,
            instance=instance,
            provider=instance.provider,
        )
    else:
        logger.info("%s Updated Completion Model: %s for Provider: %s", prefix, instance.name, instance.provider.name)
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            for field in supports_fields:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                if not old_value and new_value:
                    model_verification_requested.send(
                        sender=ProviderModel,
                        instance=instance,
                        provider=instance.provider,
                    )
                    break
        except sender.DoesNotExist:
            pass


# ------------------------------------------------------------------------------
# Provider Model Verification handlers
# ------------------------------------------------------------------------------


@receiver(post_save, sender=ProviderModelVerification)
def provider_model_verification_save(sender, instance: ProviderModelVerification, created: bool, **kwargs):
    """Log when a provider model verification is saved."""
    prefix = get_prefix("provider_model_verification_save")
    if created:
        logger.info(
            "%s Created Model Verification: %s for Provider Model: %s",
            prefix,
            instance.verification_type,
            instance.provider_model.name,
        )
    else:
        logger.info(
            "%s Updated Model Verification: %s for Provider Model: %s",
            prefix,
            instance.verification_type,
            instance.provider_model.name,
        )
