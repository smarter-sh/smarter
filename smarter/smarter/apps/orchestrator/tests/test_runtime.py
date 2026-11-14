"""
Test :mod:`smarter.apps.orchestrator.runtime`: starting a run, and executing its steps (ADR-037).

The provider's handler is replaced with a fake that answers each step, so no LLM is called.
"""

import json
from http import HTTPStatus
from typing import Optional
from unittest.mock import patch

from smarter.apps.account.models import UserProfile
from smarter.apps.account.models.budget import SmarterBudgetExceeded
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.orchestrator import runtime
from smarter.apps.orchestrator.models import (
    OrchestrationRun,
    OrchestrationStep,
    Orchestrator,
    OrchestratorHarness,
)
from smarter.apps.orchestrator.models.orchestration_run import OrchestrationRunStatus
from smarter.apps.orchestrator.models.orchestrator import OrchestrationStrategy
from smarter.apps.provider.services.text_completion.providers import (
    smarter_compatible_client,
)

ROLE = OrchestratorHarness.Role


def lambda_response(text: str, status: int = HTTPStatus.OK.value) -> dict:
    """A prompt's result, as the provider's handler returns it, whose assistant answered ``text``."""
    body = {
        "id": "chatcmpl-1",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
        "smarter": {"messages": [{"role": "assistant", "content": text}]},
    }
    return {"isBase64Encoded": False, "statusCode": status, "headers": {}, "body": json.dumps(body)}


class FakeHandler:
    """The provider's handler: answers each step with its LLMClient's name, and records what it received."""

    def __init__(self, fail_for: str = "", script: Optional[dict[str, list[str]]] = None):
        self.calls: list[tuple] = []
        self.fail_for = fail_for
        self.script = script or {}

    def __call__(self, user_profile, prompt, data, plugins=None):
        self.calls.append((user_profile, prompt, data))
        name = prompt.llmclient.name
        if name == self.fail_for:
            return lambda_response("", status=HTTPStatus.INTERNAL_SERVER_ERROR.value)
        answers = self.script.get(name)
        if answers:
            return lambda_response(answers.pop(0))
        return lambda_response(f"the answer of {name}")

    def names(self) -> list[str]:
        """The LLMClients called, in order."""
        return [prompt.llmclient.name for _, prompt, _ in self.calls]


class TestOrchestrationRuntime(TestAccountMixin):
    """Test that runs start only when they may, and that their steps run in order, as their LLMClients' owners."""

    orchestrator: Orchestrator
    llmclients: dict[str, LLMClient]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmclients = {}
        for name in ("first", "second", "summary", "planner", "router"):
            cls.llmclients[name] = LLMClient.objects.create(
                name=f"test_runtime_{name}_{cls.hash_suffix}", user_profile=cls.user_profile, deployed=False
            )
        cls.orchestrator = Orchestrator.objects.create(
            name=f"test_runtime_{cls.hash_suffix}", user_profile=cls.user_profile, max_iterations=10
        )
        harnesses = (
            ("first", ROLE.EXECUTOR, 0),
            ("second", ROLE.EXECUTOR, 1),
            ("summary", ROLE.SUMMARIZER, 2),
            ("planner", ROLE.PLANNER, 3),
            ("router", ROLE.ROUTER, 4),
        )
        for name, role, order in harnesses:
            OrchestratorHarness.objects.create(
                orchestrator=cls.orchestrator,
                llmclient=cls.llmclients[name],
                role=role,
                execution_order=order,
                is_active=role not in (ROLE.PLANNER, ROLE.ROUTER),
                config={"instructions": f"Write as {name}."},
            )

    @classmethod
    def tearDownClass(cls):
        Orchestrator.objects.filter(pk=cls.orchestrator.pk).delete()
        LLMClient.objects.filter(pk__in=[llmclient.pk for llmclient in cls.llmclients.values()]).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        Orchestrator.objects.filter(pk=self.orchestrator.pk).update(
            strategy=OrchestrationStrategy.SEQUENTIAL, max_iterations=10, is_active=True
        )
        self.orchestrator.refresh_from_db()
        OrchestratorHarness.objects.filter(orchestrator=self.orchestrator, role__in=[ROLE.PLANNER, ROLE.ROUTER]).update(
            is_active=False
        )
        self.addCleanup(OrchestrationRun.objects.filter(orchestrator=self.orchestrator).delete)

    def use_strategy(self, strategy: str, coordinator_role: str) -> None:
        """Run the strategy, with its coordinator active."""
        Orchestrator.objects.filter(pk=self.orchestrator.pk).update(strategy=strategy)
        OrchestratorHarness.objects.filter(orchestrator=self.orchestrator, role=coordinator_role).update(is_active=True)
        self.orchestrator.refresh_from_db()

    def use(self, handler: FakeHandler) -> FakeHandler:
        """Make the provider's handler the fake, until the end of the test."""
        patcher = patch.object(smarter_compatible_client, "get_smarter_harness", return_value=handler)
        patcher.start()
        self.addCleanup(patcher.stop)
        return handler

    def new_run(self, objective: str = "Prepare the board pack.") -> OrchestrationRun:
        """A pending run, started by the admin user."""
        return OrchestrationRun.objects.create(
            orchestrator=self.orchestrator, objective=objective, started_by=self.user_profile
        )

    def executed(self, run: OrchestrationRun) -> OrchestrationRun:
        """The run, after its execution."""
        runtime.execute_run(run.pk)
        run.refresh_from_db()
        return run

    # -------------------------------------------------------------------------
    # starting a run
    # -------------------------------------------------------------------------
    def test_start_run_queues_a_pending_run(self):
        """A run starts pending, recorded with who started it, and its execution is queued."""
        with patch("smarter.apps.orchestrator.tasks.execute_orchestration_run.delay") as delay:
            run = runtime.start_run(self.orchestrator, self.user_profile, "Prepare the board pack.")
        self.assertEqual(run.status, OrchestrationRunStatus.PENDING)
        self.assertEqual(run.started_by, self.user_profile)
        delay.assert_called_once_with(run.pk)

    def test_refused_runs(self):
        """An inactive Orchestrator, a strategy that can't run yet, or one without harnesses, may not run."""
        refusals = (
            ({"is_active": False}, "is not active"),
            ({"strategy": OrchestrationStrategy.DEBATE}, "can't run yet"),
        )
        for update, message in refusals:
            with self.subTest(update=update):
                Orchestrator.objects.filter(pk=self.orchestrator.pk).update(**update)
                self.orchestrator.refresh_from_db()
                with self.assertRaisesRegex(runtime.OrchestrationRefused, message) as refused:
                    runtime.check_may_run(self.orchestrator, self.admin_user)
                self.assertEqual(refused.exception.status, HTTPStatus.BAD_REQUEST)
                self.setUp()
        empty = Orchestrator.objects.create(
            name=f"test_runtime_empty_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(empty.delete)
        with self.assertRaisesRegex(runtime.OrchestrationRefused, "no active harness"):
            runtime.check_may_run(empty, self.admin_user)

    def test_runner_may_use_every_harness(self):
        """A user who may not read every harness LLMClient may not run the Orchestrator: 403, which names none."""
        runtime.check_may_run(self.orchestrator, self.non_admin_user)
        outsider, outsider_account, _ = mortal_user_factory()
        self.addCleanup(outsider_account.delete)
        self.addCleanup(outsider.delete)
        with self.assertRaises(runtime.OrchestrationRefused) as refused:
            runtime.check_may_run(self.orchestrator, outsider)
        self.assertEqual(refused.exception.status, HTTPStatus.FORBIDDEN)
        self.assertNotIn(self.llmclients["first"].name, str(refused.exception))

    # -------------------------------------------------------------------------
    # executing a run
    # -------------------------------------------------------------------------
    def test_sequential_run(self):
        """Each harness gets the outputs before it and its instructions; the summarizer's answer is the result."""
        handler = self.use(FakeHandler())
        run = self.executed(self.new_run())
        self.assertEqual(run.status, OrchestrationRunStatus.SUCCEEDED, run.error_message)
        self.assertEqual(run.result, {"text": f"the answer of {self.llmclients['summary'].name}"})
        self.assertEqual(run.iteration_count, 3)
        steps = list(OrchestrationStep.objects.filter(run=run).order_by("sequence"))
        expected = [self.llmclients[name].name for name in ("first", "second", "summary")]
        self.assertEqual([step.harness.llmclient.name for step in steps], expected)
        self.assertTrue(all(step.status == OrchestrationStep.StepStatus.SUCCEEDED for step in steps))

        messages = [data["messages"][0]["content"] for _, _, data in handler.calls]
        self.assertIn("Objective: Prepare the board pack.", messages[0])
        self.assertIn("Write as first.", messages[0])
        self.assertIn(f"{self.llmclients['first'].name} answered:\nthe answer of", messages[1])
        self.assertIn(f"{self.llmclients['second'].name} answered", messages[2])
        # each step runs as its LLMClient's owner, in a session of its own.
        for user_profile, prompt, data in handler.calls:
            self.assertEqual(user_profile, prompt.llmclient.user_profile)
            self.assertEqual(data["session_key"], prompt.session_key)
        self.assertEqual(len({prompt.pk for _, prompt, _ in handler.calls}), 3)

    def test_parallel_run(self):
        """Each harness gets only the objective; a failed step is passed on to the summarizer, which answers."""
        Orchestrator.objects.filter(pk=self.orchestrator.pk).update(strategy=OrchestrationStrategy.PARALLEL)
        handler = self.use(FakeHandler(fail_for=self.llmclients["first"].name))
        run = self.executed(self.new_run())
        self.assertEqual(run.status, OrchestrationRunStatus.SUCCEEDED, run.error_message)
        messages = [data["messages"][0]["content"] for _, _, data in handler.calls]
        self.assertNotIn("answered", messages[1])
        self.assertIn(f"{self.llmclients['first'].name} could not answer", messages[2])
        statuses = list(OrchestrationStep.objects.filter(run=run).order_by("sequence").values_list("status", flat=True))
        self.assertEqual(statuses, ["failed", "succeeded", "succeeded"])

    def test_sequential_run_stops_at_a_failed_step(self):
        """A failed step ends a sequential run, which keeps the steps it took."""
        self.use(FakeHandler(fail_for=self.llmclients["second"].name))
        run = self.executed(self.new_run())
        self.assertEqual(run.status, OrchestrationRunStatus.FAILED)
        self.assertIn(self.llmclients["second"].name, run.error_message or "")
        self.assertEqual(OrchestrationStep.objects.filter(run=run).count(), 2)

    def test_max_iterations(self):
        """A run stops when it has taken maxIterations steps."""
        Orchestrator.objects.filter(pk=self.orchestrator.pk).update(max_iterations=1)
        self.use(FakeHandler())
        run = self.executed(self.new_run())
        self.assertEqual(run.status, OrchestrationRunStatus.MAX_ITERATIONS_EXCEEDED)
        self.assertEqual(OrchestrationStep.objects.filter(run=run).count(), 1)

    def test_budget_stops_a_step(self):
        """A budget that has run out fails the step, before its LLMClient is called."""
        handler = self.use(FakeHandler())
        exceeded = SmarterBudgetExceeded("The budget is spent.", resource_locator="llmclient-x")
        with patch.object(runtime, "charge_authorization", side_effect=exceeded):
            run = self.executed(self.new_run())
        self.assertEqual(run.status, OrchestrationRunStatus.FAILED)
        self.assertIn("The budget is spent.", run.error_message or "")
        self.assertEqual(handler.calls, [])

    def test_an_unexpected_error_fails_the_step(self):
        """An exception in a step fails it, with a message that quotes nothing of the exception."""
        self.use(FakeHandler())
        with patch.object(runtime, "call_llmclient", side_effect=RuntimeError("provider secret")):
            run = self.executed(self.new_run())
        self.assertEqual(run.status, OrchestrationRunStatus.FAILED)
        self.assertNotIn("provider secret", run.error_message or "")
        self.assertEqual(OrchestrationStep.objects.filter(run=run).get().error_message, "The step failed.")

    def test_a_run_that_is_not_pending_is_left_alone(self):
        """A run that already ran, e.g. delivered twice, isn't executed again, and an unknown run is ignored."""
        handler = self.use(FakeHandler())
        run = self.new_run()
        OrchestrationRun.objects.filter(pk=run.pk).update(status=OrchestrationRunStatus.SUCCEEDED)
        runtime.execute_run(run.pk)
        runtime.execute_run(999999999)
        self.assertEqual(handler.calls, [])

    def test_steps_act_for_the_runner(self):
        """The user who started the run is each step's acting user."""
        member = UserProfile.objects.get(pk=self.non_admin_user_profile.pk)
        run = OrchestrationRun.objects.create(orchestrator=self.orchestrator, objective="x", started_by=member)
        self.use(FakeHandler())
        with patch.object(runtime, "acting_user", wraps=runtime.acting_user) as acting:
            self.executed(run)
        self.assertEqual({call.args[0] for call in acting.call_args_list}, {self.non_admin_user})

    # -------------------------------------------------------------------------
    # messages and answers
    # -------------------------------------------------------------------------
    def test_assistant_text_and_instructions(self):
        """The last assistant message is the answer, and only non-empty text instructions count."""
        result = {
            "messages": [{"role": "assistant", "content": "a"}, {"role": "tool"}, {"role": "assistant", "content": "b"}]
        }
        self.assertEqual(runtime.assistant_text(result), "b")
        self.assertEqual(runtime.assistant_text({}), "")
        harness = OrchestratorHarness(config={"instructions": "  "})
        self.assertIsNone(runtime.harness_instructions(harness))
        harness.config = "not a dict"
        self.assertIsNone(runtime.harness_instructions(harness))

    def test_an_empty_answer_fails_the_step(self):
        """A step whose LLMClient answers nothing fails."""
        self.use(FakeHandler())
        with patch.object(runtime, "assistant_text", return_value=""):
            run = self.executed(self.new_run())
        self.assertEqual(run.status, OrchestrationRunStatus.FAILED)
        self.assertIn("gave no answer", OrchestrationStep.objects.filter(run=run).get().error_message or "")

    # -------------------------------------------------------------------------
    # router and supervisor
    # -------------------------------------------------------------------------
    def test_router_run(self):
        """The router chooses one assistant, which answers; the summarizer answers last.

        The router doesn't answer.
        """
        self.use_strategy(OrchestrationStrategy.ROUTER, ROLE.ROUTER)
        second = self.llmclients["second"].name
        router = self.llmclients["router"].name
        handler = self.use(FakeHandler(script={router: [f'Here it is: ```json\n{{"harness": "{second}"}}\n```']}))
        run = self.executed(self.new_run())
        self.assertEqual(run.status, OrchestrationRunStatus.SUCCEEDED, run.error_message)
        self.assertEqual(handler.names(), [router, second, self.llmclients["summary"].name])
        router_message = handler.calls[0][2]["messages"][0]["content"]
        self.assertIn(f"- {self.llmclients['first'].name}:", router_message)
        self.assertNotIn(f"- {router}:", router_message)

    def test_router_that_chooses_no_assistant(self):
        """A router whose answer names no participant fails the run."""
        self.use_strategy(OrchestrationStrategy.ROUTER, ROLE.ROUTER)
        router = self.llmclients["router"].name
        self.use(FakeHandler(script={router: ['{"harness": "no_such_assistant"}']}))
        run = self.executed(self.new_run())
        self.assertEqual(run.status, OrchestrationRunStatus.FAILED)
        self.assertIn("chose no assistant", run.error_message or "")

    def test_supervisor_run(self):
        """The planner asks assistants until it finishes; it keeps one session, and is told each answer."""
        self.use_strategy(OrchestrationStrategy.SUPERVISOR, ROLE.PLANNER)
        first = self.llmclients["first"].name
        planner = self.llmclients["planner"].name
        script = {
            planner: [
                json.dumps({"next": first, "message": "What is the headcount?"}),
                "I am not sure.",
                json.dumps({"done": True, "result": "The headcount is 40."}),
            ]
        }
        handler = self.use(FakeHandler(script=script))
        run = self.executed(self.new_run())
        self.assertEqual(run.status, OrchestrationRunStatus.SUCCEEDED, run.error_message)
        self.assertEqual(handler.names(), [planner, first, planner, planner, self.llmclients["summary"].name])
        messages = [data["messages"][0]["content"] for _, _, data in handler.calls]
        self.assertIn("What is the headcount?", messages[1])
        self.assertIn(f"{first} answered:\nthe answer of {first}", messages[2])
        self.assertIn("named no assistant", messages[3])
        self.assertIn("planner answered:\nThe headcount is 40.", messages[4].replace(planner, "planner"))
        planner_sessions = {prompt.pk for _, prompt, _ in handler.calls if prompt.llmclient.name == planner}
        self.assertEqual(len(planner_sessions), 1)

    def test_supervisor_that_never_finishes(self):
        """A planner that never finishes is stopped by maxIterations."""
        self.use_strategy(OrchestrationStrategy.SUPERVISOR, ROLE.PLANNER)
        Orchestrator.objects.filter(pk=self.orchestrator.pk).update(max_iterations=3)
        first = self.llmclients["first"].name
        planner = self.llmclients["planner"].name
        ask = json.dumps({"next": first})
        self.use(FakeHandler(script={planner: [ask, ask, ask]}))
        run = self.executed(self.new_run())
        self.assertEqual(run.status, OrchestrationRunStatus.MAX_ITERATIONS_EXCEEDED)
        self.assertEqual(run.iteration_count, 3)

    def test_coordinator_is_required(self):
        """A supervisor without a planner, or a router without a router, may not run."""
        for strategy in (OrchestrationStrategy.SUPERVISOR, OrchestrationStrategy.ROUTER):
            with self.subTest(strategy=strategy):
                Orchestrator.objects.filter(pk=self.orchestrator.pk).update(strategy=strategy)
                self.orchestrator.refresh_from_db()
                with self.assertRaisesRegex(runtime.OrchestrationRefused, "needs an active harness with the role"):
                    runtime.check_may_run(self.orchestrator, self.admin_user)

    def test_parse_decision(self):
        """A coordinator's JSON is found in prose or a code block; anything else is no decision."""
        self.assertEqual(runtime.parse_decision('Sure: ```json\n{"harness": "a"}\n```'), {"harness": "a"})
        for text in ("no json here", "{not json}", "[1, 2]", "} backwards {"):
            with self.subTest(text=text):
                self.assertIsNone(runtime.parse_decision(text))
