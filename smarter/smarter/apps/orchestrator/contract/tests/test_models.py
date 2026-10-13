"""Test :mod:`smarter.apps.orchestrator.contract.models`, and the Orchestrators' real responses against the OpenAPI document."""

import json
from http import HTTPStatus
from typing import get_args

from django.test import RequestFactory
from rest_framework.test import APIClient

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.orchestrator.contract.models import (
    OrchestratorApiOrchestrator,
    OrchestratorApiStrategy,
)
from smarter.apps.orchestrator.models import Orchestrator
from smarter.apps.orchestrator.serializers import OrchestratorSerializer


class TestOrchestratorContract(OpenApiResponseMixin, TestAccountMixin):
    """Test the Orchestrator contract's model against the serializer, and the views' responses against the document."""

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
            [value for value, _ in Orchestrator._meta.get_field("strategy").choices],
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
