# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for account app.

These tasks are i/o intensive operations for creating billing records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.
"""

from decimal import Decimal

from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.workers.celery import app

from .models.budget import evaluate_budgets
from .models.charge import Charge, aggregate_charges
from .models.llm_prices import LLMPrices

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.ACCOUNT_LOGGING]
)
logger_level = logger.getEffectiveLevel()
module_prefix = "smarter.apps.account.tasks."


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.llmclient_tasks_celery_task_queue,
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
    :param total_cost: Decimal or str, optional. The cost in USD, if the caller knows it, e.g. of compute.
    :param provider: String, optional. The LLM provider's name, to price the tokens with LLMPrices.
    :param model: String, optional. The LLM's name, to price the tokens with LLMPrices.

    **Example usage**::

        # Create a charge for a user profile
        create_charge.delay(resource_locator="record_123", charge_type="usage", prompt_tokens=100, completion_tokens=50, total_tokens=150)
    """

    resource_locator = kwargs.get("resource_locator")
    charge_type = kwargs.get("charge_type")
    prompt_tokens = kwargs.get("prompt_tokens")
    completion_tokens = kwargs.get("completion_tokens")
    total_tokens = kwargs.get("total_tokens")
    total_cost = kwargs.get("total_cost")
    prefix = logging.formatted_text(module_prefix + "create_charge()")
    if total_cost is None:
        total_cost = LLMPrices.cost_of(
            charge_type=charge_type,
            provider=kwargs.get("provider"),
            model=kwargs.get("model"),
            total_tokens=total_tokens or 0,
        )

    logger.debug(
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
            total_cost=Decimal(str(total_cost)),
        )
    # pylint: disable=W0703
    except Exception as e:
        logger.error("%s - error creating charge: %s", prefix, e)


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.llmclient_tasks_celery_task_queue,
)
def aggregate_records():
    """
    Top-level Celery task for aggregating charge records.

    This task triggers the aggregation of daily billing records by calling
    :func:`aggregate_charges`. It is typically scheduled via Celery Beat.

    **Example usage**::

        # Trigger aggregation from code
        aggregate_records.delay()

        # Schedule with Celery Beat for daily aggregation
        # (see your Celery Beat configuration)
    """

    prefix = logging.formatted_text(module_prefix + "aggregate_records()")
    logger.info(prefix)

    aggregate_charges()


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.llmclient_tasks_celery_task_queue,
)
def evaluate_budget_constraints() -> int:
    """
    Top-level Celery task for enforcing budgets.

    Removes expired resource locks and re-evaluates every budget attached to a resource, so that
    budgets roll over at the end of their billing period. Scheduled hourly via Celery Beat.

    :returns: The number of locked resources.
    """
    prefix = logging.formatted_text(module_prefix + "evaluate_budget_constraints()")
    retval = evaluate_budgets()
    logger.info("%s %s resources are locked by a budget.", prefix, retval)
    return retval
