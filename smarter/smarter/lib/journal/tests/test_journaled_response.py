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
        data = json.loads(resp.content.decode("utf-8"))
        self.assertIn("api", data)
        self.assertIn("thing", data)
        self.assertIn("metadata", data)
        self.assertEqual(data["metadata"]["key"], "journal-key")

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
        data = json.loads(resp.content.decode("utf-8"))
        self.assertIn("api", data)
        self.assertIn("thing", data)
        self.assertIn("metadata", data)
        self.assertEqual(data["metadata"]["key"], "journal-key")

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
    """Test the SmarterJournaledJsonErrorResponse class."""

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
        data = json.loads(resp.content.decode("utf-8"))
        # {'errorClass': 'Exception', 'stacktrace': 'trace', 'description': '', 'status': '401', 'args': 'url=http://testserver/api/', 'cause': 'Python Exception', 'context': 'thing=thing, command=command'}
        self.assertIn("error", data)
        self.assertIn("stacktrace", data["error"])
        self.assertIn("errorClass", data["error"])
        self.assertEqual(data["error"]["status"], str(HTTPStatus.UNAUTHORIZED))
        mock_logger.error.assert_called()
