# -*- coding: utf-8 -*-
# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for account app.

These tasks are i/o intensive operations for creating billing records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""
import logging

from celery import shared_task as app

from .models import (
    CHARGE_TYPE_PLUGIN,
    CHARGE_TYPE_PROMPT_COMPLETION,
    Charge,
    UserProfile,
)


logger = logging.getLogger(__name__)


def _create_charge(charge_type, user_id, prompt_tokens, completion_tokens, total_tokens, model, reference):
    user = UserProfile.objects.get(id=user_id).user
    account = UserProfile.objects.get(user=user).account

    charge = Charge(
        account=account,
        user=user,
        charge_type=charge_type,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=model,
        reference=reference,
    )
    charge.save()


@app.task
def create_prompt_completion_charge(user_id, prompt_tokens, completion_tokens, total_tokens, model, reference):
    """Create a charge record."""
    logger.info("Creating prompt completion charge record for user_id: %s", user_id)

    _create_charge(
        CHARGE_TYPE_PROMPT_COMPLETION, user_id, prompt_tokens, completion_tokens, total_tokens, model, reference
    )


@app.task
def create_plugin_charge(user_id, prompt_tokens, completion_tokens, total_tokens, model, reference):
    """Create a charge record."""
    logger.info("Creating plugin charge record for user_id: %s", user_id)

    _create_charge(CHARGE_TYPE_PLUGIN, user_id, prompt_tokens, completion_tokens, total_tokens, model, reference)
