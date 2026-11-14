"""
The orchestration runtime: start an Orchestrator's run, then execute it, one step at a time (ADR-037).

A step is a prompt. It calls its harness LLMClient through the same handler as the LLMClient prompt api, as the
LLMClient's owner, in a ``Prompt`` session of its own, so that tools, guardrails, the journal, charges and budgets
apply to it exactly as to any other prompt. The user who started the run is each step's acting user, whom MCP
servers learn of.

.. code-block:: python

    run = start_run(orchestrator, user_profile, "Prepare the board pack for Q4 2025.")
    # a Celery task executes it: execute_orchestration_run.delay(run.pk)
    run.refresh_from_db()
    run.status, run.result

The first version runs the ``sequential`` and ``parallel`` strategies, and a ``summarizer`` harness after either.
"""

from dataclasses import dataclass
from http import HTTPStatus
from typing import Optional

from django.db import transaction
from django.utils import timezone

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.models.budget import (
    SmarterBudgetExceeded,
    charge_authorization,
)
from smarter.apps.llmclient.models import LLMClient, LLMClientPlugin
from smarter.apps.mcpserver.services.acting_user import acting_user
from smarter.apps.orchestrator.exceptions import SmarterOrchestratorException
from smarter.apps.orchestrator.models import (
    OrchestrationRun,
    OrchestrationStep,
    Orchestrator,
    OrchestratorHarness,
)
from smarter.apps.orchestrator.models.orchestration_run import OrchestrationRunStatus
from smarter.apps.orchestrator.models.orchestrator import OrchestrationStrategy
from smarter.apps.prompt.contract.builders import prompt_result_v2
from smarter.apps.prompt.models import Prompt
from smarter.common.conf import smarter_settings
from smarter.common.utils import hash_factory
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])
logger_prefix = logging.SmarterFormattedText.text(__name__)

SUPPORTED_STRATEGIES = (OrchestrationStrategy.SEQUENTIAL, OrchestrationStrategy.PARALLEL)
"""The strategies that this version runs.

The others are refused, by name.
"""

STEP_USER_AGENT = "smarter-orchestrator"
"""The user agent of a step's Prompt session, which no browser opened."""

STEP_IP_ADDRESS = "127.0.0.1"
"""The ip address of a step's Prompt session: the platform's own."""


class OrchestrationRefused(SmarterOrchestratorException):
    """A run that may not start, with the http status that says why."""

    def __init__(self, message: str, status: int = HTTPStatus.BAD_REQUEST):
        super().__init__(message)
        self.status = status


class OrchestrationStepFailed(SmarterOrchestratorException):
    """A step that failed, which ends a sequential run."""


@dataclass
class StepOutput:
    """What one step produced: its harness's name, and the text its LLMClient answered, or why it failed."""

    harness_name: str
    text: str
    failed: bool


def planned_harnesses(orchestrator: Orchestrator) -> tuple[list[OrchestratorHarness], Optional[OrchestratorHarness]]:
    """
    Return the active harnesses that a run calls, in order, and its summarizer, if it has one.

    :param orchestrator: The Orchestrator.
    :returns: Every active harness that isn't a summarizer, by execution order, and the first active summarizer.
    """
    harnesses = orchestrator.harnesses.filter(is_active=True).select_related("llmclient__user_profile__user")  # type: ignore[attr-defined]
    harnesses = harnesses.order_by("execution_order", "pk")
    participants = []
    summarizer = None
    for harness in harnesses:
        if harness.role != OrchestratorHarness.Role.SUMMARIZER:
            participants.append(harness)
        elif summarizer is None:
            summarizer = harness
    return participants, summarizer


def check_may_run(orchestrator: Orchestrator, user: User) -> None:
    """
    Refuse a run that may not start: an inactive Orchestrator, a strategy that can't run yet, no harness, or a.

    harness LLMClient that the user may not read.

    An Orchestrator must not become a way around an account's sharing, so the user who starts a run must be able to
    read every LLMClient that it calls (ADR-037).

    :param orchestrator: The Orchestrator.
    :param user: The user who starts the run.
    :raises OrchestrationRefused: If the run may not start.
    """
    if not orchestrator.is_active:
        raise OrchestrationRefused(f"The Orchestrator {orchestrator.name} is not active.")
    if orchestrator.strategy not in SUPPORTED_STRATEGIES:
        raise OrchestrationRefused(
            f"The strategy '{orchestrator.strategy}' can't run yet: only sequential and parallel can."
        )
    participants, summarizer = planned_harnesses(orchestrator)
    if not participants:
        raise OrchestrationRefused(f"The Orchestrator {orchestrator.name} has no active harness to run.")
    harnesses = list(participants)
    if summarizer is not None:
        harnesses.append(summarizer)
    llmclient_ids = {harness.llmclient.pk for harness in harnesses}
    readable = LLMClient.objects.filter(pk__in=llmclient_ids).with_read_permission_for(user)  # type: ignore[attr-defined]
    if readable.count() != len(llmclient_ids):
        # which one is not said: an LLMClient that the user may not read is not disclosed.
        raise OrchestrationRefused(
            f"You may not use every LLMClient of the Orchestrator {orchestrator.name}.", status=HTTPStatus.FORBIDDEN
        )


def start_run(orchestrator: Orchestrator, user_profile: UserProfile, objective: str) -> OrchestrationRun:
    """
    Start a run of the Orchestrator: check that it may start, record it, and queue its execution.

    :param orchestrator: The Orchestrator.
    :param user_profile: The profile of the user who starts it.
    :param objective: What the run is to achieve, e.g. "Prepare the board pack for Q4 2025."
    :returns: The run, ``pending``.
    :raises OrchestrationRefused: If the run may not start.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.orchestrator.tasks import execute_orchestration_run

    check_may_run(orchestrator, user_profile.user)
    run = OrchestrationRun.objects.create(orchestrator=orchestrator, objective=objective, started_by=user_profile)
    run_id = run.pk
    transaction.on_commit(lambda: execute_orchestration_run.delay(run_id))
    logger.info("%s.start_run() queued run %s of orchestrator %s", logger_prefix, run_id, orchestrator.pk)
    return run


def step_message(objective: str, earlier: list[StepOutput], instructions: Optional[str]) -> str:
    """
    Return the one user message that a step sends to its LLMClient.

    :param objective: The run's objective.
    :param earlier: The outputs of the steps that this one builds on, labeled by harness.
    :param instructions: The harness's own ``config.instructions``, if any.
    :returns: The message.
    """
    parts = [f"Objective: {objective}"]
    for output in earlier:
        if output.failed:
            parts.append(f"{output.harness_name} could not answer: {output.text}")
        else:
            parts.append(f"{output.harness_name} answered:\n{output.text}")
    if instructions:
        parts.append(instructions)
    return "\n\n".join(parts)


def harness_instructions(harness: OrchestratorHarness) -> Optional[str]:
    """
    Return the harness's ``config.instructions``, which its step's message ends with.

    :param harness: The harness.
    :returns: The instructions, or None.
    """
    config = harness.config if isinstance(harness.config, dict) else {}
    instructions = config.get("instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        return None
    return instructions.strip()


def assistant_text(result: dict) -> str:
    """
    Return the text that the LLMClient answered, from a prompt's result in version 2 of the chat contract.

    :param result: The result, as :func:`smarter.apps.prompt.contract.builders.prompt_result_v2` returns it.
    :returns: The last assistant message's text, or an empty string.
    """
    retval = ""
    for message in result.get("messages") or []:
        if message.get("role") != "assistant":
            continue
        content = message.get("content")
        if isinstance(content, str):
            retval = content
    return retval


def new_step_prompt(run: OrchestrationRun, llmclient: LLMClient) -> Prompt:
    """
    Return a new Prompt session for a step, owned by its LLMClient's owner.

    :param run: The run.
    :param llmclient: The step's LLMClient.
    :returns: The session.
    """
    url = f"{smarter_settings.environment_url}/api/v1/orchestrators/{run.orchestrator.hashed_id}/runs/{run.pk}/"
    prompt = Prompt.objects.create(
        session_key=hash_factory(length=64),
        user_profile=llmclient.user_profile,
        llmclient=llmclient,
        ip_address=STEP_IP_ADDRESS,
        user_agent=STEP_USER_AGENT,
        url=url,
    )
    return prompt


def call_llmclient(run: OrchestrationRun, llmclient: LLMClient, prompt: Prompt, message: str) -> tuple[str, str]:
    """
    Send one message to an LLMClient, as its prompt api does, as its owner, with the run's starter acting.

    :param run: The run.
    :param llmclient: The LLMClient.
    :param prompt: The step's session.
    :param message: The message.
    :returns: The text it answered, and an error, or an empty string if it succeeded.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.provider.services.text_completion.providers import (
        smarter_compatible_client,
    )

    handler = smarter_compatible_client.get_smarter_harness(request=None, provider_name=llmclient.provider)
    plugins = LLMClientPlugin.plugins(llmclient=llmclient)
    data = {"session_key": prompt.session_key, "messages": [{"role": "user", "content": message}]}
    starter = run.started_by.user if run.started_by else None
    with acting_user(starter):
        response = handler(llmclient.user_profile, prompt, data, plugins=plugins)
    result, error, _ = prompt_result_v2(response)
    text = assistant_text(result)
    if error:
        description = str(error.get("description") or "The LLM provider failed.")
        return text, description
    if not text:
        return text, "The LLMClient gave no answer."
    return text, ""


def run_step(run: OrchestrationRun, harness: OrchestratorHarness, message: str) -> StepOutput:
    """
    Execute one step: check the budgets, call the harness's LLMClient, and record the step.

    :param run: The run.
    :param harness: The step's harness.
    :param message: The message to send.
    :returns: What the step produced.
    """
    llmclient = harness.llmclient
    run.iteration_count += 1
    run.save(update_fields=["iteration_count", "updated_at"])
    locators = [run.orchestrator.record_locator, llmclient.record_locator]
    if run.started_by is not None:
        locators.append(run.started_by.record_locator)
    prompt = new_step_prompt(run, llmclient)
    try:
        charge_authorization(locators, on_behalf_of=STEP_USER_AGENT)
        text, error = call_llmclient(run, llmclient, prompt, message)
    except SmarterBudgetExceeded as e:
        text, error = "", str(e.message)
    # a step's failure is recorded, and its message kept from the log: it may quote the LLM provider.
    except Exception as e:  # pylint: disable=broad-except
        logger.error(
            "%s.run_step() step %s of run %s failed: %s", logger_prefix, run.iteration_count, run.pk, type(e).__name__
        )
        text, error = "", "The step failed."
    status = OrchestrationStep.StepStatus.SUCCEEDED
    if error:
        status = OrchestrationStep.StepStatus.FAILED
    OrchestrationStep.objects.create(
        run=run,
        harness=harness,
        prompt=prompt,
        sequence=run.iteration_count,
        status=status,
        error_message=error or None,
    )
    if error:
        return StepOutput(harness_name=llmclient.name, text=error, failed=True)
    return StepOutput(harness_name=llmclient.name, text=text, failed=False)


def run_strategy(run: OrchestrationRun) -> Optional[str]:
    """
    Execute the run's steps, by its strategy, and return its result: the last step's text.

    In ``sequential``, each harness receives the outputs before it, and a failed step ends the run. In
    ``parallel``, each receives only the objective, and a failed step is passed on to the summarizer. A summarizer,
    if there is one, runs last, over every output.

    :param run: The run.
    :returns: The result, or None if ``maxIterations`` stopped the run first.
    :raises OrchestrationStepFailed: If a step failed in a sequential run, or the summarizer failed.
    """
    orchestrator = run.orchestrator
    sequential = orchestrator.strategy == OrchestrationStrategy.SEQUENTIAL
    participants, summarizer = planned_harnesses(orchestrator)
    outputs: list[StepOutput] = []
    for harness in participants:
        if run.iteration_count >= orchestrator.max_iterations:
            return None
        earlier: list[StepOutput] = []
        if sequential:
            earlier = outputs
        message = step_message(run.objective, earlier, harness_instructions(harness))
        output = run_step(run, harness, message)
        outputs.append(output)
        if output.failed and sequential:
            raise OrchestrationStepFailed(f"{output.harness_name} failed: {output.text}")
    if summarizer is not None:
        if run.iteration_count >= orchestrator.max_iterations:
            return None
        message = step_message(run.objective, outputs, harness_instructions(summarizer))
        output = run_step(run, summarizer, message)
        outputs.append(output)
        if output.failed:
            raise OrchestrationStepFailed(f"{output.harness_name} failed: {output.text}")
    last = outputs[-1]
    return last.text


def finish(run: OrchestrationRun, status: str, result: Optional[str] = None, error: Optional[str] = None) -> None:
    """
    Record how a run ended.

    :param run: The run.
    :param status: Its final status.
    :param result: Its result's text, if any.
    :param error: Why it failed, if it did.
    """
    run.status = status
    run.completed_at = timezone.now()
    run.error_message = error
    if result is not None:
        run.result = {"text": result}
    run.save()
    logger.info("%s.finish() run %s %s after %s steps", logger_prefix, run.pk, status, run.iteration_count)


def execute_run(run_id: int) -> None:
    """
    Execute a pending run, and record its result, or why it failed.

    A run that isn't pending is left as it is.

    :param run_id: The run's id.
    """
    run = OrchestrationRun.objects.select_related("orchestrator", "started_by__user").filter(pk=run_id).first()
    if run is None or run.status != OrchestrationRunStatus.PENDING:
        logger.warning("%s.execute_run() run %s is not pending", logger_prefix, run_id)
        return
    run.status = OrchestrationRunStatus.RUNNING
    run.started_at = timezone.now()
    run.save()
    try:
        result = run_strategy(run)
    except OrchestrationStepFailed as e:
        finish(run, OrchestrationRunStatus.FAILED, error=str(e))
        return
    except Exception as e:  # pylint: disable=broad-except
        logger.error("%s.execute_run() run %s failed: %s", logger_prefix, run_id, type(e).__name__)
        finish(run, OrchestrationRunStatus.FAILED, error="The run failed.")
        return
    if result is None:
        finish(run, OrchestrationRunStatus.MAX_ITERATIONS_EXCEEDED, error="The run reached its maxIterations.")
        return
    finish(run, OrchestrationRunStatus.SUCCEEDED, result=result)


__all__ = [
    "OrchestrationRefused",
    "OrchestrationStepFailed",
    "StepOutput",
    "SUPPORTED_STRATEGIES",
    "check_may_run",
    "execute_run",
    "start_run",
    "step_message",
]
