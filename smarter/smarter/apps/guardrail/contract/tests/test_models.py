"""Test :mod:`smarter.apps.guardrail.contract.models`."""

import copy
import json
from typing import get_args

from pydantic import ValidationError

from smarter.apps.account.serializers import user_can_delete
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.guardrail.api.v1.views.views import evaluate
from smarter.apps.guardrail.contract.models import (
    GuardrailApiAction,
    GuardrailApiCategory,
    GuardrailApiEvaluation,
    GuardrailApiEvent,
    GuardrailApiEventDisposition,
    GuardrailApiGuardrail,
    GuardrailApiMode,
    GuardrailApiStage,
    GuardrailApiStrategy,
)
from smarter.apps.guardrail.models import Guardrail, GuardrailEvent
from smarter.apps.guardrail.serializers import (
    GuardrailEventSerializer,
    GuardrailSerializer,
)
from smarter.apps.guardrail.tests.base_classes import GUARDRAIL_DEFAULTS

NAME = "test_guardrail_contract_models"


def serialized(serializer) -> dict:
    """A serializer's output, as the JSON that the api returned."""
    return json.loads(json.dumps(serializer.data, default=str))


class TestGuardrailContractModels(TestAccountMixin):
    """Test the Guardrail contract's models against the serializers whose output they replace."""

    def setUp(self):
        super().setUp()
        self.guardrail = Guardrail.objects.create(
            name=NAME, user_profile=self.user_profile, **copy.deepcopy(GUARDRAIL_DEFAULTS)
        )
        self.addCleanup(Guardrail.objects.filter(pk=self.guardrail.pk).delete)
        self.guardrail.tags.add("contract")
        self.event = GuardrailEvent.objects.create(
            guardrail=self.guardrail,
            guardrail_name=NAME,
            stage="input",
            category="custom",
            strategy="keyword",
            action="block",
            mode="enforce",
            disposition="blocked",
            severity=3,
        )
        self.addCleanup(GuardrailEvent.objects.filter(pk=self.event.pk).delete)

    def test_choices(self):
        """The Literals are the model fields' choices."""
        cases = [
            (GuardrailApiStage, Guardrail, "stage"),
            (GuardrailApiCategory, Guardrail, "category"),
            (GuardrailApiStrategy, Guardrail, "strategy"),
            (GuardrailApiAction, Guardrail, "action"),
            (GuardrailApiMode, Guardrail, "mode"),
            (GuardrailApiEventDisposition, GuardrailEvent, "disposition"),
        ]
        for literal, model, field in cases:
            with self.subTest(field=f"{model.__name__}.{field}"):
                self.assertEqual(list(get_args(literal)), [value for value, _ in model._meta.get_field(field).choices])

    def test_guardrail_is_the_serializers_output(self):
        model = GuardrailApiGuardrail.from_model(self.guardrail)
        self.assertEqual(model.model_dump(mode="json"), serialized(GuardrailSerializer(self.guardrail)))
        self.assertEqual(model.tags, ["contract"])

    def test_can_delete_is_the_users(self):
        self.assertIs(GuardrailApiGuardrail.from_model(self.guardrail).can_delete, False)
        self.assertEqual(
            GuardrailApiGuardrail.from_model(self.guardrail, self.admin_user).can_delete,
            user_can_delete(self.guardrail, "Guardrail", self.admin_user),
        )

    def test_event_is_the_serializers_output(self):
        """An event's keys are snake_case, as the serializer's were."""
        model = GuardrailApiEvent.from_model(self.event)
        self.assertEqual(model.model_dump(mode="json"), serialized(GuardrailEventSerializer(self.event)))
        self.assertIn("guardrail_name", model.model_dump(mode="json"))

    def test_evaluation(self):
        """A dry run is built as the model, whose JSON is camelCase."""
        evaluation = evaluate(self.guardrail, "this is forbidden", "input")
        self.assertIsInstance(evaluation, GuardrailApiEvaluation)
        self.assertTrue(evaluation.triggered)
        data = evaluation.model_dump(mode="json")
        self.assertEqual(data["disposition"], "blocked")
        self.assertIn("durationMs", data)
        self.assertEqual(GuardrailApiEvaluation.model_validate(data), evaluation)

    def test_extra_fields_are_forbidden(self):
        data = GuardrailApiEvent.from_model(self.event).model_dump(mode="json")
        with self.assertRaises(ValidationError):
            GuardrailApiEvent.model_validate({**data, "secret": "x"})
