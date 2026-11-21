"""
The orchestration runtime: start an Orchestrator's run, then execute it, one step at a time (ADR-037).

A step is a prompt. It calls its harness LLMClient in-process, with
:func:`smarter.apps.llmclient.prompting.send_message`, through the same handler as the LLMClient prompt api, as the
LLMClient's owner, in a ``Prompt`` session of its own, so that tools, guardrails, the chat history, charges and
budgets apply to it exactly as to any other prompt. The user who started the run is each step's acting user, whom MCP
servers learn of.

.. code-block:: python

    run = start_run(orchestrator, user_profile, "Prepare the board pack for Q4 2025.")
    # a Celery task executes it: execute_orchestration_run.delay(run.pk)
    run.refresh_from_db()
    run.status, run.result

It runs the ``sequential``, ``parallel``, ``supervisor`` and ``router`` strategies, and a ``summarizer`` harness
after any of them. ``voting`` and ``debate`` are refused, by name.

A run sends a signal of :mod:`smarter.apps.orchestrator.signals` when it is queued, when it starts, after each step,
and when it finishes. Their receivers log the run.
"""

from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Optional

from django.db import transaction
from django.utils import timezone

from smarter.apps.account.models import User, UserProfile
from smarter.apps.account.models.budget import (
    SmarterBudgetExceeded,
    charge_authorization,
)
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.prompting import (
    SmarterLLMClientPromptError,
    assistant_text,
    extract_json_object,
    new_session,
    send_message,
)
from smarter.apps.orchestrator.exceptions import SmarterOrchestratorException
from smarter.apps.orchestrator.models import (
    OrchestrationRun,
    OrchestrationStep,
    Orchestrator,
    OrchestratorHarness,
)
from smarter.apps.orchestrator.models.orchestration_run import OrchestrationRunStatus
from smarter.apps.orchestrator.models.orchestrator import OrchestrationStrategy
from smarter.apps.orchestrator.signals import (
    orchestration_run_finished,
    orchestration_run_queued,
    orchestration_run_started,
    orchestration_step_finished,
)
from smarter.apps.prompt.models import Prompt
from smarter.common.conf import smarter_settings
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import required

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])

SUPPORTED_STRATEGIES = (
    OrchestrationStrategy.SEQUENTIAL,
    OrchestrationStrategy.PARALLEL,
    OrchestrationStrategy.SUPERVISOR,
    OrchestrationStrategy.ROUTER,
)
"""The strategies that this version runs.

The others are refused, by name.
"""

STEP_USER_AGENT = "smarter-orchestrator"
"""The user agent of a step's Prompt session, which no browser opened."""


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


COORDINATOR_ROLES = {
    OrchestrationStrategy.SUPERVISOR: OrchestratorHarness.Role.PLANNER,
    OrchestrationStrategy.ROUTER: OrchestratorHarness.Role.ROUTER,
}
"""The role of the harness that coordinates a run of each strategy that has one: it decides who answers."""


@dataclass
class RunPlan:
    """
    The harnesses of a run: those that answer, in order, the one that coordinates them, if any, and the summarizer.

    In ``sequential`` and ``parallel``, every active harness but the summarizer answers. In ``supervisor``, the
    first active planner coordinates, and in ``router``, the first active router; neither answers the objective.
    """

    participants: list[OrchestratorHarness]
    coordinator: Optional[OrchestratorHarness]
    summarizer: Optional[OrchestratorHarness]

    def all(self) -> list[OrchestratorHarness]:
        """
        Return every harness of the plan.

        :returns: The participants, then the coordinator and the summarizer, if any.
        """
        retval = list(self.participants)
        if self.coordinator is not None:
            retval.append(self.coordinator)
        if self.summarizer is not None:
            retval.append(self.summarizer)
        return retval

    def participant_named(self, name: object) -> Optional[OrchestratorHarness]:
        """
        Return the participant whose LLMClient has the name, e.g. a planner's or a router's choice.

        :param name: The name, as a coordinator wrote it.
        :returns: The participant, or None.
        """
        if not isinstance(name, str):
            return None
        for harness in self.participants:
            if harness.llmclient.name == name.strip():
                return harness
        return None


def plan_run(orchestrator: Orchestrator) -> RunPlan:
    """
    Return the plan of a run of the Orchestrator: its active harnesses, by role and execution order.

    :param orchestrator: The Orchestrator.
    :returns: The plan.
    """
    harnesses = orchestrator.harnesses.filter(is_active=True).select_related("llmclient__user_profile__user")  # type: ignore[attr-defined]
    harnesses = harnesses.order_by("execution_order", "pk")
    coordinator_role = COORDINATOR_ROLES.get(orchestrator.strategy)  # type: ignore[call-overload]
    plan = RunPlan(participants=[], coordinator=None, summarizer=None)
    for harness in harnesses:
        if harness.role == OrchestratorHarness.Role.SUMMARIZER:
            if plan.summarizer is None:
                plan.summarizer = harness
        elif coordinator_role is not None and harness.role == coordinator_role:
            if plan.coordinator is None:
                plan.coordinator = harness
        else:
            plan.participants.append(harness)
    return plan


def check_may_run(orchestrator: Orchestrator, user: User) -> None:
    """
    Refuse a run that may not start.

    That is an inactive Orchestrator, a strategy that can't run yet, no harness to answer, no planner for a
    supervisor or router for a router, or a harness LLMClient that the user may not read. An Orchestrator must not
    become a way around an account's sharing, so the user who starts a run must be able to read every LLMClient that
    it calls (ADR-037).

    :param orchestrator: The Orchestrator.
    :param user: The user who starts the run.
    :raises OrchestrationRefused: If the run may not start.
    """
    if not orchestrator.is_active:
        raise OrchestrationRefused(f"The Orchestrator {orchestrator.name} is not active.")
    if orchestrator.strategy not in SUPPORTED_STRATEGIES:
        raise OrchestrationRefused(
            f"The strategy '{orchestrator.strategy}' can't run yet: only sequential, parallel, supervisor and router can."
        )
    plan = plan_run(orchestrator)
    if not plan.participants:
        raise OrchestrationRefused(f"The Orchestrator {orchestrator.name} has no active harness to run.")
    coordinator_role = COORDINATOR_ROLES.get(orchestrator.strategy)  # type: ignore[call-overload]
    if coordinator_role is not None and plan.coordinator is None:
        raise OrchestrationRefused(
            f"The strategy '{orchestrator.strategy}' needs an active harness with the role {coordinator_role}."
        )
    llmclient_ids = {harness.llmclient.pk for harness in plan.all()}
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
    orchestration_run_queued.send(sender=start_run, run=run)
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


def new_step_prompt(run: OrchestrationRun, llmclient: LLMClient) -> Prompt:
    """
    Return a new Prompt session for a step, owned by its LLMClient's owner.

    :param run: The run.
    :param llmclient: The step's LLMClient.
    :returns: The session.
    """
    url = f"{smarter_settings.environment_url}/api/v1/orchestrators/{run.orchestrator.hashed_id}/runs/{run.pk}/"
    prompt = new_session(llmclient, url, STEP_USER_AGENT)
    return prompt


def call_llmclient(run: OrchestrationRun, prompt: Prompt, message: str) -> tuple[str, str]:
    """
    Send one message to a step's LLMClient, as its prompt api does, as its owner, with the run's starter acting.

    :param run: The run.
    :param prompt: The step's session, whose LLMClient answers.
    :param message: The message.
    :returns: The text it answered, and an error, or an empty string if it succeeded.
    """
    starter = None
    if run.started_by is not None:
        starter = run.started_by.user
    try:
        result = send_message(prompt, message, acting=starter)
    except SmarterLLMClientPromptError as e:
        return "", str(e)
    text = assistant_text(result)
    if not text:
        return "", "The LLMClient gave no answer."
    return text, ""


class IterationsExhausted(SmarterOrchestratorException):
    """A run that has taken ``maxIterations`` steps, and may take no more."""


@dataclass
class RunContext:
    """
    A run while it executes: its plan, and one Prompt session per harness, so that a harness that answers twice, e.g.

    a planner, keeps its conversation.
    """

    run: OrchestrationRun
    plan: RunPlan
    sessions: dict[int, Prompt] = field(default_factory=dict)

    def session(self, harness: OrchestratorHarness) -> Prompt:
        """
        Return the harness's session in this run, a new one the first time.

        :param harness: The harness.
        :returns: The session.
        """
        prompt = self.sessions.get(harness.pk)
        if prompt is None:
            prompt = new_step_prompt(self.run, harness.llmclient)
            self.sessions[harness.pk] = prompt
        return prompt

    def step(self, harness: OrchestratorHarness, message: str) -> StepOutput:
        """
        Execute one step: check the iterations left and the budgets, call the harness's LLMClient, and record it.

        :param harness: The step's harness.
        :param message: The message to send.
        :returns: What the step produced.
        :raises IterationsExhausted: If the run has taken ``maxIterations`` steps.
        """
        run = self.run
        if run.iteration_count >= run.orchestrator.max_iterations:
            raise IterationsExhausted(f"The run reached its maxIterations, {run.orchestrator.max_iterations}.")
        llmclient = harness.llmclient
        run.iteration_count += 1
        run.save(update_fields=["iteration_count", "updated_at"])
        locators = [run.orchestrator.record_locator, llmclient.record_locator]
        if run.started_by is not None:
            locators.append(run.started_by.record_locator)
        prompt = self.session(harness)
        try:
            charge_authorization(locators, on_behalf_of=STEP_USER_AGENT)
            text, error = call_llmclient(run, prompt, message)
        except SmarterBudgetExceeded as e:
            text, error = "", str(e.message)
        # a step's failure is recorded, and its message kept from the log: it may quote the LLM provider.
        except Exception as e:  # pylint: disable=broad-except
            logger.error(
                "step %s of run %s failed: %s",
                run.iteration_count,
                run.pk,
                type(e).__name__,
            )
            text, error = "", "The step failed."
        status = OrchestrationStep.StepStatus.SUCCEEDED
        if error:
            status = OrchestrationStep.StepStatus.FAILED
        step = OrchestrationStep.objects.create(
            run=run,
            harness=harness,
            prompt=prompt,
            sequence=run.iteration_count,
            status=status,
            error_message=error or None,
        )
        orchestration_step_finished.send(sender=self.__class__, run=run, step=step)
        if error:
            return StepOutput(harness_name=llmclient.name, text=error, failed=True)
        return StepOutput(harness_name=llmclient.name, text=text, failed=False)

    def required_step(self, harness: OrchestratorHarness, message: str) -> StepOutput:
        """
        Execute one step whose failure ends the run, e.g. a coordinator's or the summarizer's.

        :param harness: The step's harness.
        :param message: The message to send.
        :returns: What the step produced.
        :raises OrchestrationStepFailed: If it failed.
        """
        output = self.step(harness, message)
        if output.failed:
            raise OrchestrationStepFailed(f"{output.harness_name} failed: {output.text}")
        return output


def roster(plan: RunPlan) -> str:
    """
    Return the list of the harnesses that a coordinator may choose from: each LLMClient's name and description.

    :param plan: The run's plan.
    :returns: One line per participant.
    """
    lines = []
    for harness in plan.participants:
        description = harness.llmclient.description or "no description"
        lines.append(f"- {harness.llmclient.name}: {description}")
    return "\n".join(lines)


def coordinator_message(lines: list[str], instructions: Optional[str]) -> str:
    """
    Return a message to a coordinator: its lines, then its harness's instructions.

    :param lines: The message's paragraphs.
    :param instructions: The coordinator's ``config.instructions``, if any.
    :returns: The message.
    """
    parts = list(lines)
    if instructions:
        parts.append(instructions)
    return "\n\n".join(parts)


def run_fixed(context: RunContext) -> list[StepOutput]:
    """
    Run ``sequential`` or ``parallel``: every participant, in order.

    In ``sequential``, each receives the outputs before it, and a failed step ends the run. In ``parallel``, each
    receives only the objective, and a failed step is passed on to the summarizer.

    :param context: The run.
    :returns: The participants' outputs.
    :raises OrchestrationStepFailed: If a step of a sequential run failed.
    """
    run = context.run
    sequential = run.orchestrator.strategy == OrchestrationStrategy.SEQUENTIAL
    outputs: list[StepOutput] = []
    for harness in context.plan.participants:
        earlier: list[StepOutput] = []
        if sequential:
            earlier = outputs
        message = step_message(run.objective, earlier, harness_instructions(harness))
        output = context.step(harness, message)
        outputs.append(output)
        if output.failed and sequential:
            raise OrchestrationStepFailed(f"{output.harness_name} failed: {output.text}")
    return outputs


def run_router(context: RunContext) -> list[StepOutput]:
    """
    Run ``router``: the router chooses one participant, which answers the objective.

    :param context: The run.
    :returns: The chosen participant's output.
    :raises OrchestrationStepFailed: If the router failed, chose no participant, or the chosen one failed.
    """
    run = context.run
    router = required(context.plan.coordinator, "router")
    message = coordinator_message(
        [
            f"Objective: {run.objective}",
            f"Choose the one assistant best suited to the objective:\n{roster(context.plan)}",
            'Answer with only JSON: {"harness": "<the assistant\'s name>"}',
        ],
        harness_instructions(router),
    )
    choice = context.required_step(router, message)
    decision = extract_json_object(choice.text) or {}
    chosen = context.plan.participant_named(decision.get("harness"))
    if chosen is None:
        raise OrchestrationStepFailed(f"{choice.harness_name} chose no assistant of this Orchestrator.")
    answer = context.required_step(chosen, step_message(run.objective, [], harness_instructions(chosen)))
    return [answer]


SUPERVISOR_PROTOCOL = (
    'Answer with only JSON. To ask an assistant something: {"next": "<the assistant\'s name>", "message": '
    '"<what to ask it>"}. When the objective is achieved: {"done": true, "result": "<the final answer>"}.'
)
"""How a supervisor's planner answers, which every message to it repeats."""


def run_supervisor(context: RunContext) -> list[StepOutput]:
    """
    Run ``supervisor``: the planner asks participants, one at a time, until it says the objective is achieved.

    Each participant's answer, or its failure, goes back to the planner, in the planner's own session, so that it
    keeps the conversation. An answer that isn't a decision is sent back to it too. ``maxIterations`` bounds the
    loop.

    :param context: The run.
    :returns: The participants' outputs, then the planner's result.
    :raises OrchestrationStepFailed: If the planner failed.
    :raises IterationsExhausted: If the planner didn't finish within ``maxIterations`` steps.
    """
    run = context.run
    planner = required(context.plan.coordinator, "planner")
    instructions = harness_instructions(planner)
    outputs: list[StepOutput] = []
    lines = [
        f"Objective: {run.objective}",
        f"You may ask these assistants, one at a time:\n{roster(context.plan)}",
        SUPERVISOR_PROTOCOL,
    ]
    while True:
        decision_output = context.required_step(planner, coordinator_message(lines, instructions))
        decision = extract_json_object(decision_output.text) or {}
        if decision.get("done") is True:
            result = decision.get("result")
            text = str(result) if result else decision_output.text
            outputs.append(StepOutput(harness_name=decision_output.harness_name, text=text, failed=False))
            return outputs
        worker = context.plan.participant_named(decision.get("next"))
        if worker is None:
            lines = ["That answer named no assistant of this Orchestrator, and didn't finish.", SUPERVISOR_PROTOCOL]
            continue
        question = str(decision.get("message") or run.objective)
        worker_message = step_message(run.objective, [], harness_instructions(worker))
        output = context.step(worker, f"{worker_message}\n\n{question}")
        outputs.append(output)
        if output.failed:
            lines = [f"{output.harness_name} could not answer: {output.text}", SUPERVISOR_PROTOCOL]
        else:
            lines = [f"{output.harness_name} answered:\n{output.text}", SUPERVISOR_PROTOCOL]


STRATEGY_RUNNERS = {
    OrchestrationStrategy.SEQUENTIAL: run_fixed,
    OrchestrationStrategy.PARALLEL: run_fixed,
    OrchestrationStrategy.ROUTER: run_router,
    OrchestrationStrategy.SUPERVISOR: run_supervisor,
}
"""The function that runs each strategy that this version runs."""


def run_strategy(run: OrchestrationRun) -> str:
    """
    Execute the run's steps, by its strategy, then its summarizer, and return its result: the last output's text.

    A summarizer, if there is one, answers last, from every output.

    :param run: The run.
    :returns: The result.
    :raises OrchestrationStepFailed: If a step whose failure ends the run failed.
    :raises IterationsExhausted: If ``maxIterations`` stopped the run.
    """
    context = RunContext(run=run, plan=plan_run(run.orchestrator))
    runner = STRATEGY_RUNNERS[run.orchestrator.strategy]  # type: ignore[index]
    outputs = runner(context)
    summarizer = context.plan.summarizer
    if summarizer is not None:
        message = step_message(run.objective, outputs, harness_instructions(summarizer))
        outputs.append(context.required_step(summarizer, message))
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
    orchestration_run_finished.send(sender=finish, run=run)


def execute_run(run_id: int) -> None:
    """
    Execute a pending run, and record its result, or why it failed.

    A run that isn't pending is left as it is.

    :param run_id: The run's id.
    """
    run = OrchestrationRun.objects.select_related("orchestrator", "started_by__user").filter(pk=run_id).first()
    if run is None or run.status != OrchestrationRunStatus.PENDING:
        logger.warning("run %s is not pending", run_id)
        return
    run.status = OrchestrationRunStatus.RUNNING
    run.started_at = timezone.now()
    run.save()
    orchestration_run_started.send(sender=execute_run, run=run)
    try:
        result = run_strategy(run)
    except OrchestrationStepFailed as e:
        finish(run, OrchestrationRunStatus.FAILED, error=str(e))
        return
    except IterationsExhausted as e:
        finish(run, OrchestrationRunStatus.MAX_ITERATIONS_EXCEEDED, error=str(e))
        return
    except Exception as e:  # pylint: disable=broad-except
        logger.error("run %s failed: %s", run_id, type(e).__name__)
        finish(run, OrchestrationRunStatus.FAILED, error="The run failed.")
        return
    finish(run, OrchestrationRunStatus.SUCCEEDED, result=result)


__all__ = [
    "IterationsExhausted",
    "OrchestrationRefused",
    "OrchestrationStepFailed",
    "RunContext",
    "RunPlan",
    "StepOutput",
    "SUPPORTED_STRATEGIES",
    "check_may_run",
    "execute_run",
    "plan_run",
    "start_run",
    "step_message",
]
