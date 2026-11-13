"""Test :mod:`smarter.apps.llmhost.contract.models`."""

import json
from dataclasses import asdict
from decimal import Decimal
from typing import get_args

from django.db.models import Field

from smarter.apps.account.serializers import user_can_delete
from smarter.apps.llmhost.contract.models import (
    LLMHostApiCatalogModel,
    LLMHostApiFormat,
    LLMHostApiInferenceEngine,
    LLMHostApiLLMHost,
    LLMHostApiModelSource,
    LLMHostApiModelTask,
    LLMHostApiQuantization,
    LLMHostApiStatusValue,
    money,
)
from smarter.apps.llmhost.models import LLMHost
from smarter.apps.llmhost.serializers import LLMHostSerializer
from smarter.apps.llmhost.services.discovery import ModelInfo
from smarter.apps.llmhost.services.observability import LLMHostObservation
from smarter.apps.llmhost.tests.base_classes import LLMHostTestBase
from smarter.lib.typing import required


class TestLLMHostContractModels(LLMHostTestBase):
    """Test the LLMHost contract's models against the serializer and dicts whose output they replace."""

    def test_choices(self):
        cases = [
            (LLMHostApiModelSource, "model_source"),
            (LLMHostApiModelTask, "model_task"),
            (LLMHostApiQuantization, "quantization"),
            (LLMHostApiInferenceEngine, "inference_engine"),
            (LLMHostApiFormat, "api_format"),
            (LLMHostApiStatusValue, "status"),
        ]
        for literal, field in cases:
            with self.subTest(field=field):
                model_field = LLMHost._meta.get_field(field)
                assert isinstance(model_field, Field)
                choices = required(model_field.choices, f"{field}.choices")
                self.assertEqual(list(get_args(literal)), [value for value, _ in choices])

    def test_llmhost_is_the_serializers_output(self):
        llmhost = self.new_llmhost("test_llmhost_contract_models")
        model = LLMHostApiLLMHost.from_model(llmhost)
        self.assertEqual(
            model.model_dump(mode="json"), json.loads(json.dumps(LLMHostSerializer(llmhost).data, default=str))
        )
        self.assertEqual(
            LLMHostApiLLMHost.from_model(llmhost, self.admin_user).can_delete,
            user_can_delete(llmhost, "LLMHost", self.admin_user),
        )

    def test_money(self):
        self.assertEqual(money(None), None)
        self.assertEqual(money(Decimal("1.5")), "1.5000")

    def test_observation_keys(self):
        """The observation's keys are the ones that LLMHostObservation.to_dict() returned."""
        self.assertEqual(
            sorted(LLMHostObservation(status="inactive").to_dict()),
            sorted(
                [
                    "status",
                    "message",
                    "replicas",
                    "readyReplicas",
                    "healthy",
                    "endpoint",
                    "publicUrl",
                    "pods",
                    "checkedAt",
                ]
            ),
        )

    def test_catalog_model_is_the_model_info(self):
        """A catalog's model keeps the snake_case keys of ModelInfo.to_dict()."""
        info = ModelInfo(catalog="builtin", source="huggingface", repository="BAAI/bge-m3", parameter_count=1)
        self.assertEqual(LLMHostApiCatalogModel.from_model_info(info).model_dump(mode="json"), asdict(info))
