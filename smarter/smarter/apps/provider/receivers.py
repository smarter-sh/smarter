"""Provider Signal receivers"""

# pylint: disable=W0613

from logging import getLogger

from django.db.models.signals import post_save
from django.dispatch import receiver

from smarter.common.helpers.console_helpers import formatted_text

from .models import Provider, ProviderCompletionModels
from .signals import (
    provider_activated,
    provider_deactivated,
    provider_deprecated,
    provider_flagged,
    provider_suspended,
    provider_undeprecated,
    provider_unflagged,
    provider_unsuspended,
    provider_verified,
    verification_failure,
    verification_requested,
    verification_success,
)


logger = getLogger(__name__)
module_prefix = "smarter.apps.provider.receivers"


@receiver(provider_deactivated, dispatch_uid="provider_deactivated_receiver")
def handle_provider_deactivated(sender, instance: Provider, **kwargs):
    """Handle provider deactivated signal."""
    prefix = formatted_text(module_prefix + ".handle_provider_deactivated()")
    logger.info("%s Provider deactivated: %s", prefix, instance.name)


@receiver(provider_activated, dispatch_uid="provider_activated_receiver")
def handle_provider_activated(sender, instance: Provider, **kwargs):
    """Handle provider activated signal."""
    prefix = formatted_text(module_prefix + ".handle_provider_activated()")
    logger.info("%s Provider activated: %s", prefix, instance.name)


@receiver(provider_verified, dispatch_uid="provider_verified_receiver")
def handle_provider_verified(sender, instance: Provider, **kwargs):
    """Handle provider verified signal."""
    prefix = formatted_text(module_prefix + ".handle_provider_verified()")
    logger.info("%s Provider verified: %s", prefix, instance.name)


@receiver(provider_suspended, dispatch_uid="provider_suspended_receiver")
def handle_provider_suspended(sender, instance: Provider, **kwargs):
    """Handle provider suspended signal."""
    prefix = formatted_text(module_prefix + ".handle_provider_suspended()")
    logger.info("%s Provider suspended: %s", prefix, instance.name)


@receiver(provider_unsuspended, dispatch_uid="provider_unsuspended_receiver")
def handle_provider_unsuspended(sender, instance: Provider, **kwargs):
    """Handle provider unsuspended signal."""
    prefix = formatted_text(module_prefix + ".handle_provider_unsuspended()")
    logger.info("%s Provider unsuspended: %s", prefix, instance.name)


@receiver(provider_deprecated, dispatch_uid="provider_deprecated_receiver")
def handle_provider_deprecated(sender, instance: Provider, **kwargs):
    """Handle provider deprecated signal."""
    prefix = formatted_text(module_prefix + ".handle_provider_deprecated()")
    logger.info("%s Provider deprecated: %s", prefix, instance.name)


@receiver(provider_undeprecated, dispatch_uid="provider_undeprecated_receiver")
def handle_provider_undeprecated(sender, instance: Provider, **kwargs):
    """Handle provider undeprecated signal."""
    prefix = formatted_text(module_prefix + ".handle_provider_undeprecated()")
    logger.info("%s Provider undeprecated: %s", prefix, instance.name)


@receiver(provider_flagged, dispatch_uid="provider_flagged_receiver")
def handle_provider_flagged(sender, instance: Provider, **kwargs):
    """Handle provider flagged signal."""
    prefix = formatted_text(module_prefix + ".handle_provider_flagged()")
    logger.info("%s Provider flagged: %s", prefix, instance.name)


@receiver(provider_unflagged, dispatch_uid="provider_unflagged_receiver")
def handle_provider_unflagged(sender, instance: Provider, **kwargs):
    """Handle provider unflagged signal."""
    prefix = formatted_text(module_prefix + ".handle_provider_unflagged()")
    logger.info("%s Provider unflagged: %s", prefix, instance.name)


@receiver(post_save, sender=Provider)
def log_provider_save(sender, instance: Provider, created: bool, **kwargs):
    """Create default completion models when a new provider is created."""
    prefix = formatted_text(module_prefix + ".log_provider_save()")
    if created:
        logger.info("%s Created Provider: %s", prefix, instance.name)
    else:
        logger.info("%s Updated Provider: %s", prefix, instance.name)


@receiver(post_save, sender=ProviderCompletionModels)
def log_provider_model_save(sender, instance: ProviderCompletionModels, created: bool, **kwargs):
    """Log when a completion model is saved."""
    prefix = formatted_text(module_prefix + ".log_provider_model_save()")
    if created:
        logger.info(
            "%s Created Completion Model: %s for Provider: %s", prefix, instance.model_name, instance.provider.name
        )
    else:
        logger.info(
            "%s Updated Completion Model: %s for Provider: %s", prefix, instance.model_name, instance.provider.name
        )


@receiver(verification_requested, dispatch_uid="verification_requested_receiver")
def handle_verification_requested(sender, instance: Provider, **kwargs):
    """Handle test requested signal."""
    prefix = formatted_text(module_prefix + ".handle_verification_requested()")
    logger.info("%s Test requested for provider: %s", prefix, instance.name)
    # pylint: disable=C0415
    from .tasks import test_provider

    test_provider.delay(provider_id=instance.id)


@receiver(verification_success, dispatch_uid="verification_success_receiver")
def handle_verification_success(sender, instance: Provider, **kwargs):
    """Handle test passed signal."""
    prefix = formatted_text(module_prefix + ".handle_verification_success()")
    logger.info("%s Test passed for provider: %s", prefix, instance.name)


@receiver(verification_failure, dispatch_uid="verification_failure_receiver")
def handle_verification_failure(sender, instance: Provider, **kwargs):
    """Handle test failed signal."""
    prefix = formatted_text(module_prefix + ".handle_verification_failure()")
    logger.error("%s Test failed for provider: %s", prefix, instance.name)
