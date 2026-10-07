"""Test the journaled json responses of :mod:`smarter.lib.journal.http` with the journal switch on."""

import unittest
from http import HTTPStatus
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.exceptions import SmarterValueError
from smarter.lib import json
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


class TestJournaledResponses(TestAccountMixin):
    """Test the journaled responses, and that each is journaled, for an authenticated and an anonymous request."""

    def setUp(self):
        super().setUp()
        patcher = patch("smarter.lib.django.waffle.switch_is_active", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)
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
        self.assertEqual(journal.response["data"], {"a": 1})
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
        with patch("smarter.lib.journal.http.SAMJournal.objects.create", side_effect=Exception("db down")):
            response = SmarterJournaledJsonResponse(
                request=self.request(self.admin_user),
                data={"data": 1},
                command=SmarterJournalCliCommands.GET,
                status=HTTPStatus.OK,
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_error_response(self):
        """Test the error response's description: from the exception's message, a string, or as given."""
        for error, description in (
            (SmarterValueError("a message"), None),
            ("a string error", None),
            (ValueError("x"), "a description"),
            (None, None),
        ):
            with self.subTest(error=error):
                response = SmarterJournaledJsonErrorResponse(
                    request=self.request(self.admin_user),
                    e=error,  # type: ignore[arg-type]
                    thing="Guardrail",
                    command=SmarterJournalCliCommands.APPLY,
                    description=description,
                    status=HTTPStatus.BAD_REQUEST,
                )
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
                self.assertIn("error", json.loads(response.content))
                self.assertEqual(self.journal(response).status_code, HTTPStatus.BAD_REQUEST)
