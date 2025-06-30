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
from django.conf import settings
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Sum

from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

# Smarter stuff
from smarter.smarter_celery import app

# Account stuff
from .models import Account, Charge, DailyBillingRecord
from .utils import (
    get_cached_admin_user_for_account,
    get_cached_user_for_user_id,
    get_cached_user_profile,
)


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.TASK_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)
        and level <= logging.INFO
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
module_prefix = "smarter.apps.account.tasks."


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def create_charge(*args, **kwargs):
    """Create a charge record."""

    account: Account = None
    user = None
    user_profile = None

    user_id = kwargs.get("user_id")
    if user_id:
        user = get_cached_user_for_user_id(user_id)
        if user:
            user_profile = get_cached_user_profile(user=user)
            if user_profile:
                account = user_profile.account
    else:
        account_id = kwargs.get("account_id")
        if account_id:
            account = Account.objects.get(id=account_id)
            if account:
                user = get_cached_admin_user_for_account(account=account)

    session_key = kwargs.get(SMARTER_CHAT_SESSION_KEY_NAME)
    provider = kwargs.get("provider")
    charge_type = kwargs.get("charge_type")
    prompt_tokens = kwargs.get("prompt_tokens")
    completion_tokens = kwargs.get("completion_tokens")
    total_tokens = kwargs.get("total_tokens")
    model = kwargs.get("model")
    reference = kwargs.get("reference")
    prefix = formatted_text(module_prefix + "create_charge()")

    logger.info(
        "%s. user_id %s, charge_type %s, reference %s",
        prefix,
        user_id,
        charge_type,
        reference,
    )

    try:
        Charge.objects.create(
            account=account,
            session_key=session_key,
            provider=provider,
            user=user,
            charge_type=charge_type,
            completion_tokens=completion_tokens,
            prompt_tokens=prompt_tokens,
            total_tokens=total_tokens,
            model=model,
            reference=reference or "undefined charge reference",
        )
    # pylint: disable=W0703
    except Exception as e:
        logger.error("%s - error creating charge: %s", prefix, e)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def aggregate_charges():
    """top-level wrapper for celery aggregation tasks"""

    prefix = formatted_text(module_prefix + "aggregate_charges()")
    logger.info(prefix)
    aggregate_daily_billing_records()


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=settings.SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF,
    max_retries=settings.SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES,
    queue=settings.SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE,
)
def aggregate_daily_billing_records():
    """
    Aggregate daily records and delete individual Charge records.
    Runs as a Celery task called from Celery Beat. This task is idempotent
    and can be run multiple times without issue.
    """
    MAX_AGGREGATION_ERROR_THRESHOLD = 10
    message_prefix = formatted_text(module_prefix + "aggregate_daily_billing_records()")

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

    logger.info("%s - begin.", message_prefix)
    i = 0
    i_error_count = 0

    working_queryset = Charge.objects.values("user", "account", "created_at__date", "charge_type").distinct()
    logger.info("%s found %s pending billing items", working_queryset.count(), message_prefix)

    for charge_identity in working_queryset:
        user = charge_identity["user"]
        account = charge_identity["account"]
        created_at_date = charge_identity["created_at__date"]
        charge_type = charge_identity["charge_type"]

        try:
            aggregate(user, account, created_at_date, charge_type)
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
