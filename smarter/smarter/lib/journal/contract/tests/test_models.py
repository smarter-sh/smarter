"""Test :mod:`smarter.lib.journal.contract.models`."""

import json
from http import HTTPStatus
from typing import get_args

from pydantic import ValidationError
from rest_framework.test import APIClient

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.contract.models import (
    SAMJournalApiCommand,
    SAMJournalApiEntry,
    SAMJournalApiEntrySummary,
    SAMJournalApiEnvelope,
    SAMJournalApiErrorBody,
    SAMJournalApiErrorResponse,
    SAMJournalApiMetadata,
    SAMJournalApiOrmModel,
    SAMJournalApiResponse,
    SAMJournalApiThing,
)
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseErrorKeys,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)
from smarter.lib.journal.models import SAMJournal
from smarter.lib.journal.serializers import (
    SAMJournalMiniSerializer,
    SAMJournalSerializer,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

KEY = "0123456789abcdef" * 4


def error_body(**kwargs) -> SAMJournalApiErrorBody:
    values = {
        "errorClass": "ValueError",
        "stacktrace": "Traceback ...",
        "description": "a description",
        "status": HTTPStatus.BAD_REQUEST,
        "args": "url=http://localhost:9357/",
        "cause": "Python Exception",
        "context": "thing=Guardrail, command=apply",
        "thing": "Guardrail",
        "command": "apply",
        **kwargs,
    }
    return SAMJournalApiErrorBody(**values)


class TestChoices(SmarterTestBase):
    """Test that the Literals of a journal entry are the choices of the SAMJournal model."""

    def test_thing(self):
        choices = {value for value, _ in SAMJournal._meta.get_field("thing").choices}
        self.assertEqual(set(get_args(SAMJournalApiThing)), choices)
        self.assertEqual(choices, {value for value, _ in SmarterJournalThings.choices()})

    def test_command(self):
        choices = {value for value, _ in SAMJournal._meta.get_field("command").choices}
        self.assertEqual(set(get_args(SAMJournalApiCommand)), choices)
        self.assertEqual(choices, {value for value, _ in SmarterJournalCliCommands.choices()})


class TestEnvelope(SmarterTestBase):
    """Test SAMJournalApiEnvelope and SAMJournalApiMetadata."""

    def test_field_names_are_the_enum_keys(self):
        self.assertEqual(
            set(SAMJournalApiEnvelope.model_fields),
            {SmarterJournalApiResponseKeys.API, SmarterJournalApiResponseKeys.METADATA},
        )
        self.assertEqual(
            set(SAMJournalApiMetadata.model_fields),
            {SCLIResponseMetadata.COMMAND, SmarterJournalApiResponseKeys.THING, SCLIResponseMetadata.KEY},
        )

    def test_build(self):
        envelope = SAMJournalApiEnvelope.build(
            command=SmarterJournalCliCommands.APPLY, thing=SmarterJournalThings.GUARDRAIL
        )
        self.assertEqual(
            envelope.dump(), {"api": SmarterApiVersions.V1, "metadata": {"command": "apply", "thing": "Guardrail"}}
        )

    def test_build_without_command_or_thing(self):
        """Test that a missing command or thing is the string 'None', as the responses always returned it."""
        self.assertEqual(
            SAMJournalApiEnvelope.build(command=None, thing=None).dump()["metadata"],
            {"command": "None", "thing": "None"},
        )

    def test_key(self):
        metadata = SAMJournalApiMetadata(command="get", thing="Secret", key=KEY)
        self.assertEqual(metadata.model_dump()["key"], KEY)
        with self.assertRaises(ValidationError):
            SAMJournalApiMetadata(command="get", thing="Secret", key="not-a-key")


class TestErrorResponse(SmarterTestBase):
    """Test SAMJournalApiErrorBody and SAMJournalApiErrorResponse."""

    def test_field_names_are_the_enum_keys(self):
        keys = {
            value
            for name, value in vars(SmarterJournalApiResponseErrorKeys).items()
            if not name.startswith("_") and isinstance(value, str)
        }
        self.assertEqual(set(SAMJournalApiErrorBody.model_fields), keys)

    def test_dump(self):
        dumped = SAMJournalApiErrorResponse(error=error_body()).dump()
        self.assertEqual(dumped["error"]["status"], 400)
        self.assertIs(type(dumped["error"]["status"]), int)
        self.assertEqual(dumped["error"]["stacktrace"], "Traceback ...")

    def test_dump_without_stack_trace(self):
        dumped = SAMJournalApiErrorResponse(error=error_body()).dump(include_stack_trace=False)
        self.assertNotIn("stacktrace", dumped["error"])
        self.assertEqual(dumped["error"]["description"], "a description")

    def test_description_may_be_null(self):
        self.assertIsNone(SAMJournalApiErrorResponse(error=error_body(description=None)).dump()["error"]["description"])

    def test_response(self):
        """Test that a complete error response, with its envelope, validates."""
        body = {
            **SAMJournalApiErrorResponse(error=error_body()).dump(),
            **SAMJournalApiEnvelope.build(command="apply", thing="Guardrail").dump(),
        }
        response = SAMJournalApiResponse.model_validate(body)
        self.assertEqual(response.error.errorClass, "ValueError")  # type: ignore[union-attr]
        self.assertEqual(response.metadata.thing, "Guardrail")


class TestOrmModel(SmarterTestBase):
    """Test SAMJournalApiOrmModel."""

    def test_from_model(self):
        journal = SAMJournal.objects.create(
            thing=SmarterJournalThings.SECRET.value,
            command=SmarterJournalCliCommands.DESCRIBE.value,
            request={"url": "http://localhost:9357/"},
            response={"data": [1, "two", None]},
            status_code=HTTPStatus.OK,
        )
        self.addCleanup(journal.delete)
        model = SAMJournalApiOrmModel.from_model(journal)
        self.assertEqual(model.key, journal.key)
        self.assertIsNone(model.user)
        self.assertEqual(model.thing, "Secret")
        self.assertEqual(model.command, "describe")
        self.assertEqual(model.response, {"data": [1, "two", None]})
        self.assertEqual(model.status_code, 200)
        self.assertEqual(
            set(SAMJournalApiOrmModel.model_fields),
            {field.attname.removesuffix("_id") for field in SAMJournal._meta.concrete_fields},
        )

    def test_forbids_other_values(self):
        values = {"key": KEY, "thing": "Secret", "command": "get", "request": {}, "response": {}, "status_code": 200}
        SAMJournalApiOrmModel(**values)
        for field, value in (("thing", "NotAThing"), ("command", "not_a_command"), ("key", "short")):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                SAMJournalApiOrmModel(**{**values, field: value})
        with self.assertRaises(ValidationError):
            SAMJournalApiOrmModel(**values, extra=True)


class TestSAMJournalRestApiModels(OpenApiResponseMixin, TestAccountMixin):
    """Test the journal's REST models against the serializers, and the views' responses against the document."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = SAMJournal.objects.create(
            user=cls.admin_user,
            thing=SmarterJournalThings.GUARDRAIL.value,
            command=SmarterJournalCliCommands.APPLY.value,
            request={"url": "http://localhost:9357/api/v1/cli/apply/"},
            response={"data": {"a": 1}},
            status_code=HTTPStatus.OK,
        )
        cls.anonymous = SAMJournal.objects.create(
            user=None,
            thing=SmarterJournalThings.GUARDRAIL.value,
            command=SmarterJournalCliCommands.GET.value,
            request={},
            response={},
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    @classmethod
    def tearDownClass(cls):
        SAMJournal.objects.filter(pk__in=[cls.journal.pk, cls.anonymous.pk]).delete()
        super().tearDownClass()

    def test_models_are_the_serializers_output(self):
        for journal in (self.journal, self.anonymous):
            with self.subTest(user=journal.user):
                self.assertEqual(
                    SAMJournalApiEntry.from_model(journal).model_dump(mode="json"),
                    json.loads(json.dumps(SAMJournalSerializer(journal).data)),
                )
                self.assertEqual(
                    SAMJournalApiEntrySummary.from_model(journal).model_dump(mode="json"),
                    json.loads(json.dumps(SAMJournalMiniSerializer(journal).data)),
                )

    def test_responses(self):
        client = APIClient()
        client.force_login(self.admin_user)
        response = client.get("/api/v1/journal/", {"search": self.journal.key, "ordering": "-createdAt"})
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertValidResponse("/journal/", "get", response.json())
        self.assertEqual(response.json()["objects"][0]["key"], self.journal.key)
        response = client.get(f"/api/v1/journal/{self.journal.key}/")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertValidResponse("/journal/{key}/", "get", response.json())
        response = client.get(f"/api/v1/journal/{'0' * 64}/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertValidResponse("/journal/{key}/", "get", response.json(), HTTPStatus.NOT_FOUND)
