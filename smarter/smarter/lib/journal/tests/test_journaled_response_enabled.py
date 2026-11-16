"""Test the journaled json responses of :mod:`smarter.lib.journal.http` with the journal switch on."""

from http import HTTPStatus
from typing import Optional
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json
from smarter.lib.django.http.serializers import HttpAuthenticatedRequestSerializer
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)
from smarter.lib.journal.http import (
    SmarterJournaledJsonErrorResponse,
    SmarterJournaledJsonResponse,
)
from smarter.lib.journal.models import SAMJournal
from smarter.lib.journal.tasks import write_journal_entry
from smarter.lib.unittest.narrowing import json_object


class TestJournaledResponses(TestAccountMixin):
    """Test the journaled responses, and that each is journaled, for an authenticated and an anonymous request."""

    def setUp(self):
        super().setUp()
        patcher = patch("smarter.lib.django.waffle.switch_is_active", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        # .delay() isn't eager in tests: save the entry in this process, in the test database.
        queue_patcher = patch(
            "smarter.lib.journal.http.queue_journal_entry",
            side_effect=lambda record, sources=(): write_journal_entry(record),
        )
        queue_patcher.start()
        self.addCleanup(queue_patcher.stop)
        self.factory = RequestFactory()

    def request(self, user=None):
        request = self.factory.post("/api/v1/cli/apply/", HTTP_HOST="localhost:9357")
        request.user = user or AnonymousUser()
        return request

    def journal(self, response) -> SAMJournal:
        key = json.loads(response.content)[SmarterJournalApiResponseKeys.METADATA][SCLIResponseMetadata.KEY]
        journal = SAMJournal.objects.get(key=key)
        self.addCleanup(journal.delete)
        return journal

    def test_authenticated_request(self):
        """Test that an authenticated request is journaled, with its user and status code."""
        response = SmarterJournaledJsonResponse(
            request=self.request(self.admin_user),
            data={"data": {"a": 1}},
            thing="Guardrail",
            command=SmarterJournalCliCommands.APPLY,
            status=HTTPStatus.OK,
        )
        journal = self.journal(response)
        self.assertEqual(journal.user, self.admin_user)
        self.assertEqual(journal.command, "apply")
        stored = journal.response
        assert isinstance(stored, dict)
        self.assertEqual(stored["data"], {"a": 1})
        self.assertEqual(journal.status_code, HTTPStatus.OK)
        metadata = json.loads(response.content)[SmarterJournalApiResponseKeys.METADATA]
        self.assertEqual(metadata["command"], "apply")
        self.assertEqual(metadata["thing"], "Guardrail")

    def test_anonymous_request(self):
        """Test that an anonymous request is journaled, without a user."""
        response = SmarterJournaledJsonResponse(
            request=self.request(),
            data={"data": []},
            thing="Guardrail",
            command=SmarterJournalCliCommands.GET,
            status=HTTPStatus.OK,
            content_type="application/json",
            not_a_response_kwarg=True,
        )
        journal = self.journal(response)
        self.assertEqual(journal.command, "get")
        self.assertIsNone(journal.user)

    def test_response_without_thing_or_command(self):
        """Test that a response without a thing or a command is journaled, with them blank."""
        response = SmarterJournaledJsonResponse(
            request=self.request(self.admin_user),
            data={"data": {"a": 1}},
            status=HTTPStatus.OK,
        )
        journal = self.journal(response)
        self.assertEqual(journal.thing, "")
        self.assertEqual(journal.command, "")

    def test_non_dict_data(self):
        """Test that data that isn't a dict or a list is wrapped in a 'response' key."""
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=False):
            response = SmarterJournaledJsonResponse(
                request=self.request(), data="a string", command=SmarterJournalCliCommands.GET, safe=False
            )
        self.assertEqual(json.loads(response.content)["response"], "a string")

    def test_list_data(self):
        with patch("smarter.lib.django.waffle.switch_is_active", return_value=False):
            response = SmarterJournaledJsonResponse(
                request=self.request(), data=[1, 2], command=SmarterJournalCliCommands.GET
            )
        self.assertEqual(json.loads(response.content), [1, 2])

    def test_journal_error_is_not_raised(self):
        """Test that a failure to save the journal doesn't fail the response."""
        with (
            patch("smarter.lib.journal.http.queue_journal_entry", side_effect=Exception("db down")),
            patch("smarter.lib.journal.http.journal_entry_failed.send") as failed,
        ):
            response = SmarterJournaledJsonResponse(
                request=self.request(self.admin_user),
                data={"data": 1},
                command=SmarterJournalCliCommands.GET,
                status=HTTPStatus.OK,
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # the response has no key, because its entry was neither queued nor saved.
        metadata = json.loads(response.content)[SmarterJournalApiResponseKeys.METADATA]
        self.assertNotIn(SCLIResponseMetadata.KEY, metadata)
        failed.assert_called_once()

    def test_large_response_is_journaled(self):
        """Test that a response whose documents are stored as blobs and chains reads back unchanged."""
        messages = [{"role": "user", "content": f"message {i} " + "x" * 100} for i in range(20)]
        data = {"data": {"messages": messages, "system": "s" * 2000}}
        response = SmarterJournaledJsonResponse(
            request=self.request(self.admin_user),
            data=data,
            thing="LLMClient",
            command=SmarterJournalCliCommands.PROMPT,
            status=HTTPStatus.OK,
        )
        journal = self.journal(response)
        reread = SAMJournal.objects.get(key=journal.key)
        self.assertIsNotNone(reread.response_document)
        stored = reread.response
        assert isinstance(stored, dict)
        self.assertEqual(stored["data"], data["data"])
        self.assertEqual(reread.thing, "LLMClient")

    def test_error_response(self):
        """Test the error response's description: from the exception's message, or as given."""
        cases: tuple[tuple[Optional[Exception], Optional[str], Optional[str]], ...] = (
            (SmarterValueError("a message"), None, "a message"),
            (ValueError("x"), "a description", "a description"),
            (ValueError("x"), None, None),
            (None, None, None),
        )
        for error, description, expected in cases:
            with self.subTest(error=error):
                response = SmarterJournaledJsonErrorResponse(
                    request=self.request(self.admin_user),
                    e=error,
                    thing="Guardrail",
                    command=SmarterJournalCliCommands.APPLY,
                    description=description,
                    status=HTTPStatus.BAD_REQUEST,
                )
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
                body = json_object(json.loads(response.content), "body")
                error_body = json_object(body["error"], "error")
                self.assertEqual(error_body["description"], expected)
                self.assertEqual(self.journal(response).status_code, HTTPStatus.BAD_REQUEST)

    def test_error_response_cause_and_default_status(self):
        """Test that an error's cause is in the response, and that a status of 0 is a 500."""
        error = ValueError("failed")
        error.__cause__ = KeyError("missing")
        response = SmarterJournaledJsonErrorResponse(
            request=self.request(self.admin_user),
            e=error,
            command=SmarterJournalCliCommands.APPLY,
            status=0,
        )
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        body = json_object(json.loads(response.content), "body")
        error_body = json_object(body["error"], "error")
        self.assertEqual(error_body["cause"], "KeyError: 'missing'")
        self.journal(response)

    def test_request_that_cannot_be_serialized(self):
        """Test that a request that its serializer can't read is journaled with an empty request document."""
        with patch.object(HttpAuthenticatedRequestSerializer, "to_representation", side_effect=AttributeError("GET")):
            response = SmarterJournaledJsonResponse(
                request=self.request(self.admin_user),
                data={"data": 1},
                command=SmarterJournalCliCommands.GET,
            )
        journal = self.journal(response)
        self.assertEqual(journal.request, {})
        self.assertEqual(journal.user, self.admin_user)

    def test_request_without_a_user(self):
        """Test that a request that no authentication middleware saw is journaled as anonymous."""
        request = self.factory.post("/api/v1/cli/apply/", HTTP_HOST="localhost:9357")
        response = SmarterJournaledJsonResponse(
            request=request, data={"data": 1}, command=SmarterJournalCliCommands.GET
        )
        journal = self.journal(response)
        self.assertIsNone(journal.user)
