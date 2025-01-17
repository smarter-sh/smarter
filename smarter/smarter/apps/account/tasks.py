# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for account app.

These tasks are i/o intensive operations for creating billing records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""
# python stuff
import logging

# django stuff
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Sum

# Smarter stuff
from smarter.smarter_celery import app

# Account stuff
from .models import (
    CHARGE_TYPE_PLUGIN,
    CHARGE_TYPE_PROMPT_COMPLETION,
    Charge,
    DailyBillingRecord,
    UserProfile,
)


logger = logging.getLogger(__name__)


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


def aggregate_charges():
    """top-level wrapper for celery aggregation tasks"""

    logger.info("aggregate_charges()")
    aggregate_daily_billing_records.delay()


@app.task
def aggregate_daily_billing_records():
    """
    Aggregate daily records and delete individual Charge records.
    Runs as a Celery task called from Celery Beat. This task is idempotent
    and can be run multiple times without issue.
    """
    MAX_AGGREGATION_ERROR_THRESHOLD = 10

    def aggregate(user, account, created_at_date, charge_type):
        """Handle aggregation of one set of charges."""
        with transaction.atomic():
            aggregation_queryset = Charge.objects.filter(
                user=user, account=account, created_at__date=created_at_date, charge_type=charge_type
            )

            aggregated_data = aggregation_queryset.aggregate(
                prompt_tokens=Sum("prompt_tokens"),
                completion_tokens=Sum("completion_tokens"),
                total_tokens=Sum("total_tokens"),
            )

            try:
                record = DailyBillingRecord.objects.get(
                    user_id=user, account_id=account, date=created_at_date, charge_type=charge_type
                )
                record.prompt_tokens += aggregated_data["prompt_tokens"]
                record.completion_tokens += aggregated_data["completion_tokens"]
                record.total_tokens += aggregated_data["total_tokens"]
                record.save()
            except DailyBillingRecord.DoesNotExist:
                DailyBillingRecord.objects.create(
                    user_id=user,
                    account_id=account,
                    date=created_at_date,
                    charge_type=charge_type,
                    prompt_tokens=aggregated_data["prompt_tokens"],
                    completion_tokens=aggregated_data["completion_tokens"],
                    total_tokens=aggregated_data["total_tokens"],
                )

            aggregation_queryset.delete()

    logger.info("aggregate_daily_charges() - begin.")
    i = 0
    i_error_count = 0

    working_queryset = Charge.objects.values("user", "account", "created_at__date", "charge_type").distinct()
    logger.info("aggregate_daily_charges() found %s pending billing items", working_queryset.count())

    for charge_identity in working_queryset:
        user = charge_identity["user"]
        account = charge_identity["account"]
        created_at_date = charge_identity["created_at__date"]
        charge_type = charge_identity["charge_type"]

        try:
            aggregate(user, account, created_at_date, charge_type)
        except (DatabaseError, IntegrityError) as e:
            logger.error("aggregate_daily_charges() - error processing billing item %s: %s", charge_identity, e)
            i_error_count += 1
            if i_error_count >= MAX_AGGREGATION_ERROR_THRESHOLD:
                logger.error("aggregate_daily_charges() - exceeded error threshold, aborting.")
                break
        # pylint: disable=W0718
        except Exception as e:
            logger.error("aggregate_daily_charges() - unknown error processing billing item %s: %s", charge_identity, e)
            i_error_count += 1
            if i_error_count >= MAX_AGGREGATION_ERROR_THRESHOLD:
                logger.error("aggregate_daily_charges() - exceeded error threshold, aborting.")
                break

        i += 1
        if i % 100 == 0:
            logger.info("aggregate_daily_charges() processed %s billing items", i)

    logger.info("aggregate_daily_charges() - finished.")
