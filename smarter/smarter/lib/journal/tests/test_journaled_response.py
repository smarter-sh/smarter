"""Test the SmarterJournaledJsonResponse class."""

import json
from http import HTTPStatus
from unittest.mock import Mock, patch

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..http import SmarterJournaledJsonErrorResponse, SmarterJournaledJsonResponse


class TestSmarterJournaledJsonResponse(SmarterTestBase):
    """Test the SmarterJournaledJsonResponse class."""

    @patch("smarter.lib.journal.http.waffle")
    @patch("smarter.lib.journal.http.SAMJournal")
    def test_response_with_authenticated_user(self, mock_samjournal, mock_waffle):
        mock_waffle.switch_is_active.return_value = True
        mock_request = Mock()
        mock_request.user.is_authenticated = True
        mock_request.build_absolute_uri.return_value = "http://testserver/api/"
        mock_request.build_absolute_uri.return_value = "http://testserver/api/"
        mock_request.META = {}
        mock_request.GET = {}
        mock_request.POST = {}
        mock_request.COOKIES = {}
        mock_request.headers = {}
        mock_journal = Mock()
        mock_journal.key = "journal-key"
        mock_samjournal.objects.create.return_value = mock_journal

        data = {}
        resp = SmarterJournaledJsonResponse(
            request=mock_request,
            data=data,
            thing="thing",
            command="command",
            status=HTTPStatus.CREATED,
        )
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        self.assertIn("api", resp.data)
        self.assertIn("thing", resp.data)
        self.assertIn("metadata", resp.data)
        self.assertEqual(resp.data["metadata"]["key"], "journal-key")

    @patch("smarter.lib.journal.http.waffle")
    @patch("smarter.lib.journal.http.SAMJournal")
    def test_response_with_anonymous_user(self, mock_samjournal, mock_waffle):
        mock_waffle.switch_is_active.return_value = True
        mock_request = Mock()
        mock_request.user.is_authenticated = False
        mock_request.build_absolute_uri.return_value = "http://testserver/api/"
        mock_request.META = {}
        mock_request.GET = {}
        mock_request.POST = {}
        mock_request.COOKIES = {}
        mock_request.headers = {}
        mock_journal = Mock()
        mock_journal.key = "journal-key"
        mock_samjournal.objects.create.return_value = mock_journal

        data = {}
        resp = SmarterJournaledJsonResponse(
            request=mock_request,
            data=data,
            thing="thing",
            command="command",
            status=HTTPStatus.OK,
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        self.assertIn("api", resp.data)
        self.assertIn("thing", resp.data)
        self.assertIn("metadata", resp.data)
        self.assertEqual(resp.data["metadata"]["key"], "journal-key")

    @patch("smarter.lib.journal.http.waffle")
    def test_response_waffle_inactive(self, mock_waffle):
        mock_waffle.switch_is_active.return_value = False
        mock_request = Mock()
        mock_request.user.is_authenticated = True
        mock_request.build_absolute_uri.return_value = "http://testserver/api/"
        mock_request.build_absolute_uri.return_value = "http://testserver/api/"
        mock_request.META = {}
        mock_request.GET = {}
        mock_request.POST = {}
        mock_request.COOKIES = {}
        mock_request.headers = {}
        data = {}
        resp = SmarterJournaledJsonResponse(
            request=mock_request,
            data=data,
            thing="thing",
            command="command",
            status=HTTPStatus.OK,
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        response_json = json.loads(resp.content.decode("utf-8"))
        self.assertIn("api", response_json)
        self.assertIn("thing", response_json)
        self.assertIn("metadata", response_json)


class TestSmarterJournaledJsonErrorResponse(SmarterTestBase):
    @patch("smarter.lib.journal.http.logger")
    def test_error_response(self, mock_logger):
        mock_request = Mock()
        mock_request.build_absolute_uri.return_value = "http://testserver/api/"
        mock_request.build_absolute_uri.return_value = "http://testserver/api/"
        mock_request.META = {}
        mock_request.GET = {}
        mock_request.POST = {}
        mock_request.COOKIES = {}
        mock_request.headers = {}
        exc = Exception("fail")
        resp = SmarterJournaledJsonErrorResponse(
            request=mock_request,
            e=exc,
            thing="thing",
            command="command",
            status=HTTPStatus.UNAUTHORIZED,
            stack_trace="trace",
        )
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertIn("error", resp.data)
        self.assertIn("stack_trace", resp.data["error"])
        self.assertEqual(resp.data["error"]["status"], str(HTTPStatus.UNAUTHORIZED))
        mock_logger.error.assert_called()
