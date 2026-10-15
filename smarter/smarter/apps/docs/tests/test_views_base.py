"""Test how :class:`smarter.apps.docs.views.base.DocsBaseView` reports an error response from its brokered api view."""

from http import HTTPStatus

from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.docs.views.base import (
    DocsBrokeredResponseError,
    brokered_error_description,
    brokered_error_response,
)
from smarter.lib import json


class TestDocsBrokeredErrors(TestAccountMixin):
    """Test the error page for an error response from a brokered smarter.sh/api view."""

    def setUp(self):
        super().setUp()
        self.request = RequestFactory().get("/provider/providers/abc/")
        self.request.user = self.admin_user

    def test_description_of_a_journaled_error(self):
        content = json.dumps({"error": {"description": "Failed to describe Provider openai"}}).encode()
        self.assertEqual(brokered_error_description(content), "Failed to describe Provider openai")

    def test_description_of_other_responses(self):
        for content in (b"not json", b"\xff", json.dumps({"data": {}}).encode(), json.dumps(["error"]).encode()):
            with self.subTest(content=content):
                self.assertIsNone(brokered_error_description(content))

    def test_error_carries_status_and_description(self):
        error = DocsBrokeredResponseError(status_code=HTTPStatus.NOT_FOUND, description="Not found")
        self.assertEqual(error.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(error.description, "Not found")
        self.assertIn("404", str(error))

    def test_error_pages(self):
        """Each api status gets the matching error page, and every page but the 500 gets the api's description."""
        expected = {
            HTTPStatus.BAD_REQUEST: HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNAUTHORIZED: HTTPStatus.FORBIDDEN,
            HTTPStatus.FORBIDDEN: HTTPStatus.FORBIDDEN,
            HTTPStatus.NOT_FOUND: HTTPStatus.NOT_FOUND,
            HTTPStatus.CONFLICT: HTTPStatus.BAD_REQUEST,
            HTTPStatus.INTERNAL_SERVER_ERROR: HTTPStatus.INTERNAL_SERVER_ERROR,
        }
        for api_status, page_status in expected.items():
            with self.subTest(api_status=api_status):
                error = DocsBrokeredResponseError(status_code=api_status, description=f"api said {api_status.value}")
                response = brokered_error_response(self.request, error)
                self.assertEqual(response.status_code, page_status)
                message = response.context["message"]  # type: ignore[attr-defined]
                if page_status == HTTPStatus.INTERNAL_SERVER_ERROR:
                    self.assertNotIn("api said", message)
                else:
                    self.assertEqual(message, f"api said {api_status.value}")
