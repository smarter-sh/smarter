# pylint: disable=unused-argument,too-many-locals
"""Celery tasks for the plugin app."""

import time
from typing import TYPE_CHECKING, Optional

from cache_results import cache_results

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.utils import (
    get_cached_user_for_user_id,
)
from smarter.apps.llmtool.manifest.controller import PluginController
from smarter.apps.llmtool.models import PluginMeta
from smarter.apps.llmtool.plugin.base import SmarterPluginError
from smarter.apps.prompt.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType, required
from smarter.workers.celery import app

from .models import PluginSelectorHistory

if TYPE_CHECKING:
    from .runner import ToolCallResult

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.TASK_LOGGING, SmarterWaffleSwitches.PLUGIN_LOGGING]
)
tool_worker_logger = logging.getSmarterLogger(__name__)
"""The tool worker's logger, which no switch silences: the tool worker has no database to read one from."""


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.app_llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.app_llmclient_tasks_celery_max_retries,
    queue=smarter_settings.app_llmclient_tasks_celery_task_queue,
)
def create_plugin_selector_history(*args, **kwargs):
    """
    Create plugin selector history.

    This Celery task records a user's plugin selection event, including search terms, input text, messages,
    and session key. It is typically called when a user interacts with the plugin selector UI.

    :param args: Positional arguments (unused).
    :type args: tuple
    :param kwargs: Keyword arguments containing context for the selector history.
    :type kwargs: dict

    **Expected kwargs:**
        - user_id (int): The ID of the user performing the selection.
        - plugin_id (int): The ID of the selected plugin.
        - input_text (str, optional): The user's input text.
        - messages (list[dict], optional): List of message objects.
        - search_term (str, optional): The search term used by the user.
        - session_key (str, optional): The prompt session key.

    :return: None

    .. important::

        - invoked by the ``plugin_selected`` signal.
        - This task will not create a history record if the plugin or user profile cannot be resolved.
        - If the plugin controller cannot be instantiated, an error is logged and no history is created.

    .. seealso::

        - :class:`PluginSelectorHistory`
        - :class:`PluginController`
        - :class:`SmarterPluginError`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.llmtool.tasks import create_plugin_selector_history

        create_plugin_selector_history.apply_async(
            kwargs={
                "user_id": 42,
                "plugin_id": 7,
                "input_text": "Show me weather plugins",
                "search_term": "weather",
                "session_key": "abc123"
            }
        )
    """

    @cache_results()
    def cached_plugin_by_id(plugin_id: int) -> Optional[PluginMeta]:
        """Retrieve PluginMeta by ID with caching."""
        try:
            return PluginMeta.objects.get(id=plugin_id)
        except PluginMeta.DoesNotExist:
            return None

    user = None
    user_profile = None
    user_profile_id = kwargs.get("user_profile_id")
    if user_profile_id:
        user_profile = UserProfile.get_cached_object(pk=user_profile_id)
    user_id = kwargs.get("user_id")
    if user_id and not user_profile:
        try:
            user = get_cached_user_for_user_id(user_id=user_id)
        except User.DoesNotExist:
            # the user was deleted after this task was queued, which a retry cannot fix.
            logger.warning(
                "user_id: %s no longer exists. Plugin selector history is not recorded.",
                user_id,
            )
            return
        user_profile = UserProfile.get_cached_object(user=user) if user else None
    if not user_profile:
        raise SmarterPluginError(
            f"UserProfile could not be resolved for user_id: {user_id}, user_profile_id: {user_profile_id}"
        )
    plugin_id = kwargs.get("plugin_id")
    plugin_meta = cached_plugin_by_id(plugin_id) if plugin_id else None
    if plugin_meta is None:
        logger.error(
            "plugin_id: %s, user_profile: %s, error: plugin not found",
            plugin_id,
            user_profile,
        )
        return
    try:
        # to catch a race situation in unit tests.
        plugin_controller = PluginController(
            user_profile=user_profile,
            plugin_meta=plugin_meta,
        )
        if not plugin_controller or not plugin_controller.plugin:
            raise SmarterPluginError(
                f"PluginController could not be created for plugin_id: {plugin_id}, user_profile: {user_profile}"
            )
        plugin = plugin_controller.plugin
    except SmarterPluginError as e:
        logger.error(
            "plugin_id: %s, user_profile: %s, error: %s",
            plugin_id,
            user_profile,
            e,
        )
        return

    logger.info(
        "plugin_id: %s, user_profile: %s",
        plugin.id,
        user_profile,
    )
    input_text: Optional[str] = kwargs.get("input_text")
    messages: Optional[list[SmarterDictType]] = kwargs.get("messages")
    search_term: Optional[str] = kwargs.get("search_term")
    session_key: Optional[str] = kwargs.get(SMARTER_CHAT_SESSION_KEY_NAME)

    PluginSelectorHistory.objects.create(
        plugin_selector=required(plugin.plugin_selector, "plugin_selector"),
        search_term=search_term,
        messages={"input_text": input_text} if input_text else messages,
        session_key=session_key,
    )


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=smarter_settings.app_llmclient_tasks_celery_retry_backoff,
    max_retries=smarter_settings.app_llmclient_tasks_celery_max_retries,
    queue=smarter_settings.app_llmclient_tasks_celery_task_queue,
)
def create_plugin_charge(*args, **kwargs):
    """
    Record a charge for a plugin call.

    Not implemented: it does nothing.

    :param args: Ignored.
    :param kwargs: Ignored.
    """


@app.task(queue=smarter_settings.app_llmclient_tasks_celery_task_queue)
def check_extension_updates() -> list[str]:
    """
    Record the newest compatible version of every extension installed from the registry.

    Run daily by Celery beat, so that the admin console can say when an update is available.
    Does nothing while the registry is disabled.

    :returns: The slugs of the extensions for which an update is available.
    :rtype: list[str]
    """
    # pylint: disable=import-outside-toplevel
    from .extension.exceptions import SmarterExtensionRegistryError
    from .extension.registry import check_for_updates, is_enabled

    if not is_enabled():
        logger.info("the extension registry is disabled")
        return []
    try:
        return [extension.slug for extension in check_for_updates(refresh=True)]
    except SmarterExtensionRegistryError as e:
        logger.warning("could not check for updates: %s", e)
        return []


def describe_tool_call_outcome(result: "ToolCallResult") -> str:
    """
    Describe a tool call's outcome for the tool worker's log, without its value or its failure's text.

    A failure's text can hold what the tool or its server answered, e.g. a database driver's message
    with a user name, so only the kind of outcome and the HTTP status are logged.

    :param result: The call's result.
    :returns: ``succeeded``, ``tool error`` or ``failed``, with `` (HTTP <status>)`` when there was a
        response.
    """
    if result.failure is not None:
        outcome = "failed"
    elif result.is_error:
        outcome = "tool error"
    else:
        outcome = "succeeded"
    if result.status_code is not None:
        outcome = f"{outcome} (HTTP {result.status_code})"
    return outcome


def describe_tool_call_label(label_json: Optional[str]) -> str:
    """
    Describe the label that the app sent with a tool call, for the tool worker's log.

    :param label_json: The :class:`~smarter.apps.llmtool.runner.models.ToolCallLabel`, as JSON, or None.
    :returns: The label's description, or ``unlabeled``.
    """
    # pylint: disable=import-outside-toplevel
    from .runner import ToolCallLabel

    if not label_json:
        return "unlabeled"
    try:
        label = ToolCallLabel.model_validate_json(label_json)
    # a label that can't be read never stops the call.
    # pylint: disable=broad-exception-caught
    except Exception:
        return "unreadable label"
    description = label.describe()
    return description


@app.task(
    queue=smarter_settings.app_tools_tasks_celery_task_queue,
    ignore_result=False,
    acks_late=False,
)
def run_tool_call(kind: str, call_json: str, label_json: Optional[str] = None) -> str:
    """
    Run one resolved LLM tool call, in the tool worker, ``smarter-worker-tools``, and return its result.

    :class:`~smarter.apps.llmtool.runner.runner.RemoteToolRunner` sends it, and waits for its result
    (ADR-038). The call is rebuilt from its JSON with its kind's model, run in this process by its kind's
    executor, and its :class:`~smarter.apps.llmtool.runner.models.ToolCallResult` returned as JSON.

    It never retries: a tool call can change something, and must not run twice. It never raises, and logs
    neither the call, which holds credentials, nor its result; nor does Celery, in the tool worker
    (:func:`smarter.lib.celery_conf.hide_tool_calls_from_logs`). It logs one line per call: its kind, its
    label (the tool, the LLMClient, the masked chat session and the request), its outcome and how long it
    took.

    :param kind: The call's ``kind``, e.g. ``mcp``.
    :param call_json: The resolved call, as JSON.
    :param label_json: The call's :class:`~smarter.apps.llmtool.runner.models.ToolCallLabel`, as JSON, or
        None for a call that the app didn't label.
    :returns: The result, as JSON.
    """
    # pylint: disable=import-outside-toplevel
    from .runner import (
        InProcessToolRunner,
        ToolCallResult,
        call_model_for,
        running_in_tool_worker,
    )

    started = time.monotonic()
    try:
        model = call_model_for(kind)
        call = model.model_validate_json(call_json)
    # a call that can't be rebuilt is reported to the LLM, rather than raised to Celery.
    # pylint: disable=broad-exception-caught
    except Exception as e:
        result = ToolCallResult(failure=f"the tool worker could not read the {kind} call: {type(e).__name__}")
        log_tool_call(kind, label_json, result, started)
        return result.model_dump_json()
    try:
        with running_in_tool_worker():
            result = InProcessToolRunner().run(call)
    # an executor reports its failures in its result; one that raises is reported the same way, by its
    # type only: Celery would log the exception with the task's arguments, and its message can hold a
    # url with a credential.
    # pylint: disable=broad-exception-caught
    except Exception as e:
        result = ToolCallResult(failure=f"the tool worker could not run the {kind} call: {type(e).__name__}")
    log_tool_call(kind, label_json, result, started)
    return result.model_dump_json()


def log_tool_call(kind: str, label_json: Optional[str], result: "ToolCallResult", started: float) -> None:
    """
    Log one line for a tool call that the tool worker ran: what it was for, and how it ended.

    It logs at INFO, through :data:`tool_worker_logger`, which no waffle switch silences: the tool worker
    has no database to read a switch from. A call that couldn't be made, or that the tool answered with an
    error, is a WARNING.

    :param kind: The call's ``kind``.
    :param label_json: The call's label, as JSON, or None.
    :param result: The call's result.
    :param started: When the task started, from :func:`time.monotonic`.
    """
    elapsed = time.monotonic() - started
    task_id = run_tool_call.request.id or "-"
    description = describe_tool_call_label(label_json)
    outcome = describe_tool_call_outcome(result)
    level = logging.INFO
    if result.failure is not None or result.is_error:
        level = logging.WARNING
    tool_worker_logger.log(
        level,
        "%s call %s %s in %.3fs: %s",
        kind,
        task_id,
        outcome,
        elapsed,
        description,
    )
