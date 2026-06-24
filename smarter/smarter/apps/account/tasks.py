# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for account app.

These tasks are i/o intensive operations for creating billing records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""

# python stuff
import datetime

# django stuff
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Sum

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

# Smarter stuff
from smarter.workers.celery import app

# Account stuff
from .models import Charge, DailyBillingRecord, UserProfile

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.ACCOUNT_LOGGING]
)
module_prefix = "smarter.apps.account.tasks."


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llm_client_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llm_client_tasks_celery_max_retries,
    queue=smarter_settings.llm_client_tasks_celery_task_queue,
)
def create_charge(*args, **kwargs):
    """
    Create a charge record for a user or account.

    This task is automatically retried on failure, with backoff and maximum retries configured via Celery settings.

    :param resource_locator: String. The TimestampedModel.resource_locator of the resource that this charge is associated with.
    :param charge_type: String, optional. The type of charge (e.g., usage, subscription).
    :param prompt_tokens: Integer, optional. Number of prompt tokens used.
    :param completion_tokens: Integer, optional. Number of completion tokens used.
    :param total_tokens: Integer, optional. Total number of tokens used.

    **Example usage**::

        # Create a charge for a user profile
        create_charge.delay(resource_locator="record_123", charge_type="usage", prompt_tokens=100, completion_tokens=50, total_tokens=150)
    """

    resource_locator = kwargs.get("resource_locator")
    charge_type = kwargs.get("charge_type")
    prompt_tokens = kwargs.get("prompt_tokens")
    completion_tokens = kwargs.get("completion_tokens")
    total_tokens = kwargs.get("total_tokens")
    prefix = logging.formatted_text(module_prefix + "create_charge()")

    logger.info(
        "%s. resource_locator %s, charge_type %s, prompt_tokens %s, completion_tokens %s, total_tokens %s",
        prefix,
        resource_locator,
        charge_type,
        prompt_tokens,
        completion_tokens,
        total_tokens,
    )

    try:
        Charge.objects.create(
            resource_locator=resource_locator,
            charge_type=charge_type,
            completion_tokens=completion_tokens,
            prompt_tokens=prompt_tokens,
            total_tokens=total_tokens,
        )
    # pylint: disable=W0703
    except Exception as e:
        logger.error("%s - error creating charge: %s", prefix, e)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llm_client_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llm_client_tasks_celery_max_retries,
    queue=smarter_settings.llm_client_tasks_celery_task_queue,
)
def aggregate_charges():
    """
    Top-level Celery task for aggregating charge records.

    This task triggers the aggregation of daily billing records by calling
    :func:`aggregate_daily_billing_records`. It is typically scheduled via Celery Beat.

    **Example usage**::

        # Trigger aggregation from code
        aggregate_charges.delay()

        # Schedule with Celery Beat for daily aggregation
        # (see your Celery Beat configuration)
    """

    prefix = logging.formatted_text(module_prefix + "aggregate_charges()")
    logger.info(prefix)
    aggregate_daily_billing_records()


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llm_client_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llm_client_tasks_celery_max_retries,
    queue=smarter_settings.llm_client_tasks_celery_task_queue,
)
def aggregate_daily_billing_records():
    """
    Aggregate daily billing records and delete individual Charge records.

    This Celery task is typically scheduled via Celery Beat and is designed to be idempotent,
    meaning it can be safely run multiple times without causing duplicate records.

    .. note::

           - This task aggregates all charges for each user/account/date/charge_type combination,
           - updates or creates a corresponding DailyBillingRecord, and deletes the original Charge records.

    **Example usage**::

        # Trigger aggregation from code
        aggregate_daily_billing_records.delay()

        # Schedule with Celery Beat for daily aggregation
        # (see your Celery Beat configuration)
    """
    MAX_AGGREGATION_ERROR_THRESHOLD = 10
    message_prefix = logging.formatted_text(module_prefix + "aggregate_daily_billing_records()")

    def aggregate(user_profile: UserProfile, created_at_date: datetime.date, charge_type: str):
        """Handle aggregation of one set of charges."""
        with transaction.atomic():
            aggregation_queryset = Charge.objects.filter(
                user_profile=user_profile, created_at__date=created_at_date, charge_type=charge_type
            )

            aggregated_data = aggregation_queryset.aggregate(
                prompt_tokens=Sum("prompt_tokens"),
                completion_tokens=Sum("completion_tokens"),
                total_tokens=Sum("total_tokens"),
            )

            try:
                record = DailyBillingRecord.objects.get(
                    user_profile=user_profile, date=created_at_date, charge_type=charge_type
                )
                record.prompt_tokens += aggregated_data["prompt_tokens"]
                record.completion_tokens += aggregated_data["completion_tokens"]
                record.total_tokens += aggregated_data["total_tokens"]
                record.save()
            except DailyBillingRecord.DoesNotExist:
                DailyBillingRecord.objects.create(
                    user_profile=user_profile,
                    date=created_at_date,
                    charge_type=charge_type,
                    prompt_tokens=aggregated_data["prompt_tokens"],
                    completion_tokens=aggregated_data["completion_tokens"],
                    total_tokens=aggregated_data["total_tokens"],
                )

            aggregation_queryset.delete()

    logger.info("%s - begin.", message_prefix)
    i = 0
    i_error_count = 0

    working_queryset = Charge.objects.values("user_profile", "created_at__date", "charge_type").distinct()
    logger.info("%s found %s pending billing items", working_queryset.count(), message_prefix)

    for charge_identity in working_queryset:
        user_profile = charge_identity["user_profile"]
        created_at_date = charge_identity["created_at__date"]
        charge_type = charge_identity["charge_type"]

        try:
            aggregate(user_profile, created_at_date, charge_type)
        except (DatabaseError, IntegrityError) as e:
            logger.error("%s - error processing billing item %s: %s", message_prefix, charge_identity, e)
            i_error_count += 1
            if i_error_count >= MAX_AGGREGATION_ERROR_THRESHOLD:
                logger.error("%s - exceeded error threshold, aborting.", message_prefix)
                break
        # pylint: disable=W0718
        except Exception as e:
            logger.error("%s - unknown error processing billing item %s: %s", message_prefix, charge_identity, e)
            i_error_count += 1
            if i_error_count >= MAX_AGGREGATION_ERROR_THRESHOLD:
                logger.error("%s - exceeded error threshold, aborting.", message_prefix)
                break

        i += 1
        if i % 100 == 0:
            logger.info("%s processed %s billing items", message_prefix, i)

    logger.info("%s - finished.", message_prefix)
