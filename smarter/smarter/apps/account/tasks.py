# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for account app.

These tasks are i/o intensive operations for creating billing records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""
import logging

from smarter.smarter_celery import app

from .models import (
    CHARGE_TYPE_PLUGIN,
    CHARGE_TYPE_PROMPT_COMPLETION,
    Charge,
    UserProfile,
)


logger = logging.getLogger(__name__)


def aggregate_charges():
    """summarize detail charges into aggregate records."""

    # FIX NOTE: implement me.
    logger.info("Aggregating charges.")


@app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def create_charge(
    charge_type: str,
    user_id: int,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    model: str,
    reference: str,
):
    user_profile = UserProfile.objects.get(user__id=user_id)

    charge = Charge(
        account=user_profile.account,
        user=user_profile.user,
        charge_type=charge_type,
        completion_tokens=completion_tokens,
        prompt_tokens=prompt_tokens,
        total_tokens=total_tokens,
        model=model,
        reference=reference,
    )
    charge.save()


def create_prompt_completion_charge(
    reference: str,
    user_id: int,
    model: str,
    completion_tokens: int,
    prompt_tokens: int,
    total_tokens: int,
    fingerprint: str,
):
    """Create a charge record."""
    logger.info("Creating prompt completion charge record for user_id: %s, reference: %s", user_id, fingerprint)

    create_charge.delay(
        charge_type=CHARGE_TYPE_PROMPT_COMPLETION,
        user_id=user_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=model,
        reference=fingerprint,
    )


def create_plugin_charge(
    reference: str,
    user_id: int,
    model: str,
    completion_tokens: int,
    prompt_tokens: int,
    total_tokens: int,
    fingerprint: str,
):
    """Create a charge record."""
    logger.info("Creating plugin charge record for user_id: %s, reference: %s", user_id, fingerprint)

    create_charge.delay(
        charge_type=CHARGE_TYPE_PLUGIN,
        user_id=user_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=model,
        reference=fingerprint,
    )
