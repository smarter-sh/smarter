"""Test :mod:`smarter.apps.orchestrator.contract.models`, and the Orchestrators' real responses against the OpenAPI document."""

import json
from http import HTTPStatus
from typing import get_args
from unittest.mock import patch

from django.test import RequestFactory
from rest_framework.test import APIClient

from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.orchestrator.contract.models import (
    OrchestratorApiHarnessRole,
    OrchestratorApiOrchestrator,
    OrchestratorApiRunStatus,
    OrchestratorApiStepStatus,
    OrchestratorApiStrategy,
)
from smarter.apps.orchestrator.models import (
    OrchestrationRun,
    OrchestrationStep,
    Orchestrator,
    OrchestratorHarness,
)
from smarter.apps.orchestrator.models.orchestration_run import OrchestrationRunStatus
from smarter.apps.orchestrator.serializers import OrchestratorSerializer
from smarter.lib.typing import required


class TestOrchestratorContract(OpenApiResponseMixin, TestAccountMixin):
    """Test the Orchestrator contract's model against the serializer, and the views' responses against the document."""

    llmclient: LLMClient
    orchestrator: Orchestrator

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmclient = LLMClient.objects.create(
            name=f"test_orchestrator_contract_{cls.hash_suffix}", user_profile=cls.user_profile, deployed=False
        )
        cls.orchestrator = Orchestrator.objects.create(
            name=f"test_orchestrator_contract_{cls.hash_suffix}", user_profile=cls.user_profile
        )
        cls.orchestrator.llmclients.add(cls.llmclient)
        cls.orchestrator.tags.add("research")

    @classmethod
    def tearDownClass(cls):
        Orchestrator.objects.filter(pk=cls.orchestrator.pk).delete()
        LLMClient.objects.filter(pk=cls.llmclient.pk).delete()
        super().tearDownClass()

    def test_strategy_is_the_choices(self):
        self.assertEqual(
            list(get_args(OrchestratorApiStrategy)),
            [value for value, _ in required(Orchestrator._meta.get_field("strategy").choices, "strategy.choices")],
        )

    def test_model_is_the_serializers_output(self):
        request = RequestFactory().get("/")
        request.user = self.admin_user
        serialized = json.loads(
            json.dumps(OrchestratorSerializer(self.orchestrator, context={"request": request}).data, default=str)
        )
        model = OrchestratorApiOrchestrator.from_model(self.orchestrator, self.admin_user).model_dump(mode="json")
        self.assertEqual(model, serialized)
        self.assertEqual(model["llmclients"], [self.llmclient.pk])
        self.assertTrue(model["canDelete"])

    def test_responses(self):
        client = APIClient()
        client.force_login(self.admin_user)
        for template, path in {
            "/orchestrators/": "/orchestrators/",
            "/orchestrators/{id}/": f"/orchestrators/{self.orchestrator.pk}/",
        }.items():
            with self.subTest(path=template):
                response = client.get(f"/api/v1{path}")
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
                self.assertValidResponse(template, "get", response.json())
        response = client.get(f"/api/v1/orchestrators/{self.orchestrator.hashed_id}/")
        self.assertEqual(response.json()["id"], self.orchestrator.pk)
        for path in ("/orchestrators/999999999/", "/orchestrators/rNotAHashedIdx/"):
            with self.subTest(path=path):
                response = client.get(f"/api/v1{path}")
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
                self.assertValidResponse("/orchestrators/{id}/", "get", response.json(), HTTPStatus.NOT_FOUND)
        client.force_login(self.non_admin_user)
        response = client.get("/api/v1/orchestrators/")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertValidResponse("/orchestrators/", "get", response.json(), HTTPStatus.FORBIDDEN)


class TestOrchestrationRunContract(OpenApiResponseMixin, TestAccountMixin):
    """Test the runs' contract models against the models' choices, and the run views' responses against the document."""

    llmclient: LLMClient
    orchestrator: Orchestrator

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.llmclient = LLMClient.objects.create(
            name=f"test_run_contract_{cls.hash_suffix}", user_profile=cls.user_profile, deployed=False
        )
        cls.orchestrator = Orchestrator.objects.create(
            name=f"test_run_contract_{cls.hash_suffix}", user_profile=cls.user_profile
        )
        OrchestratorHarness.objects.create(orchestrator=cls.orchestrator, llmclient=cls.llmclient)

    @classmethod
    def tearDownClass(cls):
        Orchestrator.objects.filter(pk=cls.orchestrator.pk).delete()
        LLMClient.objects.filter(pk=cls.llmclient.pk).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_login(self.non_admin_user)
        self.addCleanup(OrchestrationRun.objects.filter(orchestrator=self.orchestrator).delete)
        patcher = patch("smarter.apps.orchestrator.tasks.execute_orchestration_run.delay")
        self.delay = patcher.start()
        self.addCleanup(patcher.stop)

    def test_literals_are_the_choices(self):
        """The contract's statuses and roles are exactly the models' choices."""
        pairs = (
            (OrchestratorApiRunStatus, OrchestrationRunStatus.choices),
            (OrchestratorApiStepStatus, OrchestrationStep.StepStatus.choices),
            (OrchestratorApiHarnessRole, OrchestratorHarness.Role.choices),
        )
        for literal, choices in pairs:
            with self.subTest(literal=literal):
                self.assertEqual(list(get_args(literal)), [value for value, _ in choices])

    def runs_url(self, orchestrator_id: str) -> str:
        return f"/api/v1/orchestrators/{orchestrator_id}/runs/"

    def start(self, body: object, orchestrator_id: str = ""):
        """POST a run of the Orchestrator."""
        url = self.runs_url(orchestrator_id or self.orchestrator.hashed_id)
        return self.client.post(url, data=json.dumps(body), content_type="application/json")

    def test_start_and_read_a_run(self):
        """A member starts a run, 202, and reads it, as the document says; another user gets 404."""
        response = self.start({"objective": "Prepare the board pack."})
        self.assertEqual(response.status_code, HTTPStatus.ACCEPTED, response.content)
        self.assertValidResponse("/orchestrators/{id}/runs/", "post", response.json(), HTTPStatus.ACCEPTED)
        run = response.json()
        self.assertEqual(run["status"], "pending")
        self.assertEqual(run["startedBy"]["user"]["username"], self.non_admin_user.username)
        self.delay.assert_called_once_with(run["id"])

        run_url = f"{self.runs_url(str(self.orchestrator.pk))}{run['id']}/"
        response = self.client.get(run_url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertValidResponse("/orchestrators/{id}/runs/{run_id}/", "get", response.json())

        # the run holds what its starter may read: anyone else, a superuser excepted, is told it doesn't exist.
        self.client.force_login(self.admin_user)
        self.assertEqual(self.client.get(run_url).status_code, HTTPStatus.OK)
        outsider, outsider_account, _ = mortal_user_factory()
        self.addCleanup(outsider_account.delete)
        self.addCleanup(outsider.delete)
        self.client.force_login(outsider)
        response = self.client.get(run_url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertValidResponse("/orchestrators/{id}/runs/{run_id}/", "get", response.json(), HTTPStatus.NOT_FOUND)

    def test_list_runs(self):
        """The list holds the user's runs, newest first, as the document says; another user's never appear in it."""
        first = self.start({"objective": "first"}).json()
        second = self.start({"objective": "second"}).json()
        response = self.client.get(self.runs_url(self.orchestrator.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertValidResponse("/orchestrators/{id}/runs/", "get", response.json())
        self.assertEqual([run["id"] for run in response.json()], [second["id"], first["id"]])

        # a colleague who may read the Orchestrator sees none of this user's runs; a superuser sees them all.
        self.client.force_login(self.admin_user)
        self.assertEqual(len(self.client.get(self.runs_url(self.orchestrator.hashed_id)).json()), 2)
        other, other_account, _ = mortal_user_factory()
        self.addCleanup(other_account.delete)
        self.addCleanup(other.delete)
        UserProfile.objects.create(user=other, account=self.account, name=f"test_run_colleague_{self.hash_suffix}")
        self.client.force_login(other)
        response = self.client.get(self.runs_url(self.orchestrator.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertEqual(response.json(), [])

    def test_refused_starts(self):
        """A bad body is 400, an Orchestrator the user may not read 404, and one that can't run yet 400."""
        response = self.start({"objective": ""})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertValidResponse("/orchestrators/{id}/runs/", "post", response.json(), HTTPStatus.BAD_REQUEST)
        self.assertEqual(self.start({"objective": "x"}, "999999999").status_code, HTTPStatus.NOT_FOUND)

        Orchestrator.objects.filter(pk=self.orchestrator.pk).update(strategy="debate")
        self.addCleanup(Orchestrator.objects.filter(pk=self.orchestrator.pk).update, strategy="sequential")
        response = self.start({"objective": "x"})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("can't run yet", response.json()["detail"])
        self.delay.assert_not_called()

    def test_a_harness_the_user_may_not_read(self):
        """A user who may read the Orchestrator, but not every harness LLMClient, is refused with 403."""
        _, department, department_profile = mortal_user_factory()
        self.addCleanup(department.delete)
        hidden = LLMClient.objects.create(
            name=f"test_run_hidden_{self.hash_suffix}", user_profile=department_profile, deployed=False
        )
        self.addCleanup(hidden.delete)
        harness = OrchestratorHarness.objects.create(
            orchestrator=self.orchestrator, llmclient=hidden, execution_order=1
        )
        self.addCleanup(harness.delete)
        response = self.start({"objective": "x"})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertNotIn(hidden.name, response.json()["detail"])
        self.delay.assert_not_called()
