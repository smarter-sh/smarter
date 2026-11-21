# pylint: disable=W0613,C0115,R0913
"""
Celery tasks for prompt app.

These tasks are i/o intensive operations for creating prompt and plugin history records with
Celery workers in order to avoid blocking the main app thread. This is advance work to lay groundwork for
future high-traffic scenarios.

- :func:`purge_prompt_history` deletes the prompt history (PromptHistory, PromptToolCall,
  PromptPluginUsage, and idle Prompts) older than ``smarter_settings.prompt_history_max_age``
  days. Celery Beat runs it daily.
"""

import datetime
from typing import Optional

from django.db import DataError
from django.db.models import QuerySet
from django.utils import timezone

from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmtool.models import PluginMeta
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.workers.celery import app

from .models import Prompt, PromptHistory, PromptPluginUsage, PromptToolCall


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.TASK_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.PROMPT_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_level = logger.getEffectiveLevel()

# Errors that fail the same way on every retry, e.g. a value too long for its column.
NOT_RETRYABLE = (DataError,)

PROMPT_HISTORY_PURGE_BATCH_SIZE = 1000
"""The most rows that :func:`purge_prompt_history` deletes from a table in one statement."""


@app.task(
    autoretry_for=(Exception,),
    dont_autoretry_for=NOT_RETRYABLE,
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.llmclient_tasks_celery_task_queue,
)
def create_prompt_history(prompt_id, request, response, messages):
    """
    Celery task: save a PromptHistory row for a finished prompt.

    Logs an error and saves nothing if the Prompt does not exist.

    :param prompt_id: The id of the Prompt.
    :param request: The request sent to the LLM, as JSON.
    :param response: The LLM's response, as JSON.
    :param messages: The conversation's messages.
    """
    logger.debug("prompt_id: %s", prompt_id)
    try:
        prompt = Prompt.objects.get(id=prompt_id)
    except Prompt.DoesNotExist:
        logger.error(
            "prompt_id: %s does not exist",
            prompt_id,
        )
        return
    PromptHistory.objects.create(prompt=prompt, request=request, response=response, messages=messages)


@app.task(
    autoretry_for=(Exception,),
    dont_autoretry_for=NOT_RETRYABLE,
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.llmclient_tasks_celery_task_queue,
)
def aggregate_prompt_history():
    """Summarize detail llmclient history into aggregate records."""
    logger.debug("called")


@app.task(
    autoretry_for=(Exception,),
    dont_autoretry_for=NOT_RETRYABLE,
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.llmclient_tasks_celery_task_queue,
)
def create_prompt(session_key, llmclient_id):
    """
    Create prompt record with flattened LLM response.

    DELETE THIS? IT IS NOT USED.
    """
    llmclient = LLMClient.objects.get(id=llmclient_id)
    Prompt.objects.create(session_key=session_key, llmclient=llmclient)


@app.task(
    autoretry_for=(Exception,),
    dont_autoretry_for=NOT_RETRYABLE,
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.llmclient_tasks_celery_task_queue,
)
def create_prompt_tool_call_history(prompt_id, plugin_meta_id, function_name, function_args, request, response):
    """
    Celery task: save a PromptToolCall row for a tool call made during a prompt.

    :param prompt_id: The id of the Prompt.
    :param plugin_meta_id: The id of the called plugin's PluginMeta, or None for a tool that is not a plugin.
    :param function_name: The called function's name.
    :param function_args: The function's arguments.
    :param request: The tool call's request.
    :param response: The tool's response.
    :raises SmarterValueError: when the Prompt, or a given PluginMeta, does not exist.
    """
    logger.debug("called")
    prompt = None
    plugin_meta = None

    try:
        prompt = Prompt.objects.get(id=prompt_id)
    except Prompt.DoesNotExist as e:
        raise SmarterValueError(f"Prompt with id {prompt_id} does not exist") from e

    try:
        if plugin_meta_id:
            plugin_meta = PluginMeta.objects.get(id=plugin_meta_id)
    except PluginMeta.DoesNotExist as e:
        raise SmarterValueError(f"PluginMeta with id {plugin_meta_id} does not exist") from e

    PromptToolCall.objects.create(
        prompt=prompt,
        plugin=plugin_meta,
        function_name=function_name,
        function_args=function_args,
        request=request,
        response=response,
    )


@app.task(
    autoretry_for=(Exception,),
    dont_autoretry_for=NOT_RETRYABLE,
    retry_backoff=smarter_settings.llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.llmclient_tasks_celery_max_retries,
    queue=smarter_settings.llmclient_tasks_celery_task_queue,
)
def create_prompt_plugin_usage(*args, **kwargs):
    """Create plugin usage record."""
    prompt_id = kwargs.get("prompt_id", None)
    plugin_id = kwargs.get("plugin_id", None)

    logger.debug(
        "prompt_id=%s, plugin_id=%s",
        prompt_id,
        plugin_id,
    )
    if prompt_id is None:
        raise SmarterValueError("prompt_id is required")

    if plugin_id is None:
        raise SmarterValueError("plugin_id is required")

    input_text = kwargs.get("input_text", None)
    if input_text is None:
        raise SmarterValueError("input_text is required")
    try:
        prompt = Prompt.objects.get(id=prompt_id)
    except Prompt.DoesNotExist as e:
        raise SmarterValueError(f"Prompt with id {prompt_id} does not exist") from e

    try:
        plugin_meta = PluginMeta.objects.get(id=plugin_id)
    except PluginMeta.DoesNotExist as e:
        raise SmarterValueError(f"PluginMeta with id {plugin_id} does not exist") from e

    PromptPluginUsage.objects.create(
        prompt=prompt,
        plugin=plugin_meta,
        input_text=input_text,
    )


def delete_in_batches(queryset: QuerySet) -> int:
    """
    Delete the rows of ``queryset`` in batches of :data:`PROMPT_HISTORY_PURGE_BATCH_SIZE`.

    A large table isn't locked in one long delete, e.g. on the first purge of a platform that
    has kept its prompt history for years.

    :param queryset: The rows to delete.
    :returns: The number of rows deleted, including those deleted by a cascade.
    :rtype: int
    """
    model = queryset.model
    ordered = queryset.order_by("pk")
    ids = ordered.values_list("pk", flat=True)
    deleted = 0
    while True:
        batch = list(ids[:PROMPT_HISTORY_PURGE_BATCH_SIZE])
        if not batch:
            break
        rows = model.objects.filter(pk__in=batch)
        batch_deleted, _ = rows.delete()
        deleted += batch_deleted
    return deleted


@app.task(queue=smarter_settings.llmclient_tasks_celery_task_queue)
def purge_prompt_history(days: Optional[int] = None) -> dict[str, int]:
    """
    Delete the prompt history older than ``days``.

    Celery Beat runs it daily. It deletes the PromptHistory, PromptToolCall and
    PromptPluginUsage rows older than ``days``, then the Prompts (the chat sessions) that
    are older than ``days`` and have none of these rows left. A session that is still in use
    is kept, with its recent rows. A Prompt is deleted with :meth:`Prompt.delete`, which
    clears its cached lookup, and its OrchestrationSteps are deleted with it.

    :param days: The number of days of prompt history to keep. Defaults to
        ``smarter_settings.prompt_history_max_age``.
    :returns: The number of rows deleted, by model name.
    :rtype: dict[str, int]
    """
    if days is None:
        days = smarter_settings.prompt_history_max_age
    cutoff = timezone.now() - datetime.timedelta(days=days)

    deleted: dict[str, int] = {}
    for model in (PromptHistory, PromptToolCall, PromptPluginUsage):
        expired_rows = model.objects.filter(created_at__lt=cutoff)
        deleted[model.__name__] = delete_in_batches(expired_rows)

    idle_prompts = Prompt.objects.filter(
        created_at__lt=cutoff,
        prompthistory__isnull=True,
        prompttoolcall__isnull=True,
        promptpluginusage__isnull=True,
    )
    deleted_prompts = 0
    for prompt in idle_prompts.iterator():
        prompt.delete()
        deleted_prompts += 1
    deleted[Prompt.__name__] = deleted_prompts

    logger.info(
        "deleted the prompt history older than %s days: %s",
        days,
        deleted,
    )
    return deleted
