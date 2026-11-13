"""Test the SmarterJournaledJsonResponse class."""

from http import HTTPStatus
from unittest.mock import Mock, patch

from smarter.lib import json
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..http import SmarterJournaledJsonErrorResponse, SmarterJournaledJsonResponse

JOURNAL_KEY = "a" * 64


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
        mock_journal.key = JOURNAL_KEY
        mock_samjournal.objects.create.return_value = mock_journal

        data: SmarterDictType = {}
        resp = SmarterJournaledJsonResponse(
            request=mock_request,
            data=data,
            thing="thing",
            command="command",  # type: ignore[arg-type]  # a plain string stands in for the command
            status=HTTPStatus.CREATED,
        )
        self.assertEqual(resp.status_code, HTTPStatus.CREATED)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertIn("api", data)
        self.assertEqual(data["metadata"]["key"], JOURNAL_KEY)

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
        mock_journal.key = JOURNAL_KEY
        mock_samjournal.objects.create.return_value = mock_journal

        data: SmarterDictType = {}
        resp = SmarterJournaledJsonResponse(
            request=mock_request,
            data=data,
            thing="thing",
            command="command",  # type: ignore[arg-type]  # a plain string stands in for the command
            status=HTTPStatus.OK,
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        data = json.loads(resp.content.decode("utf-8"))
        self.assertIn("api", data)
        self.assertEqual(data["metadata"]["key"], JOURNAL_KEY)

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
        data: SmarterDictType = {}
        resp = SmarterJournaledJsonResponse(
            request=mock_request,
            data=data,
            thing="thing",
            command="command",  # type: ignore[arg-type]  # a plain string stands in for the command
            status=HTTPStatus.OK,
        )
        self.assertEqual(resp.status_code, HTTPStatus.OK)
        response_json = json.loads(resp.content.decode("utf-8"))
        self.assertIn("api", response_json)
        self.assertIn("thing", response_json["metadata"])
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
            command="command",  # type: ignore[arg-type]  # a plain string stands in for the command
            status=HTTPStatus.UNAUTHORIZED,
            stack_trace="trace",
        )
        self.assertEqual(resp.status_code, HTTPStatus.UNAUTHORIZED)
        data = json.loads(resp.content.decode("utf-8"))
        # {'errorClass': 'Exception', 'stacktrace': 'trace', 'description': '', 'status': '401', 'args': 'url=http://testserver/api/', 'cause': 'Python Exception', 'context': 'thing=thing, command=command'}
        self.assertIn("error", data)
        self.assertIn("stacktrace", data["error"])
        self.assertIn("errorClass", data["error"])
        self.assertEqual(str(data["error"]["status"]), str(HTTPStatus.UNAUTHORIZED))
        # a client error is a warning, logged without its stack trace.
        mock_logger.error.assert_not_called()
        mock_logger.warning.assert_called_once()
        self.assertIn("Exception", str(mock_logger.warning.call_args))
        self.assertNotIn("trace", str(mock_logger.warning.call_args))

    @patch("smarter.lib.journal.http.logger")
    def test_server_error_response_is_logged_as_an_error(self, mock_logger):
        """Test that a 5xx is logged at ERROR, with its stack trace."""
        mock_request = Mock()
        mock_request.build_absolute_uri.return_value = "http://testserver/api/"
        mock_request.META = {}
        mock_request.GET = {}
        mock_request.POST = {}
        mock_request.COOKIES = {}
        mock_request.headers = {}
        resp = SmarterJournaledJsonErrorResponse(
            request=mock_request,
            e=Exception("fail"),
            thing="thing",
            command="command",  # type: ignore[arg-type]  # a plain string stands in for the command
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            stack_trace="trace",
        )
        self.assertEqual(resp.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_called_once()
        self.assertIn("trace", str(mock_logger.error.call_args))

    @patch("smarter.lib.journal.http.logger")
    def test_error_response_without_stack_trace(self, mock_logger):
        """Test that include_stack_trace=False logs a server error's stack trace, but leaves it out of the response."""
        mock_request = Mock()
        mock_request.build_absolute_uri.return_value = "http://testserver/api/"
        mock_request.META = {}
        mock_request.GET = {}
        mock_request.POST = {}
        mock_request.COOKIES = {}
        mock_request.headers = {}
        resp = SmarterJournaledJsonErrorResponse(
            request=mock_request,
            e=Exception("fail"),
            thing="thing",
            command="command",  # type: ignore[arg-type]  # a plain string stands in for the command
            status=HTTPStatus.BAD_GATEWAY,
            stack_trace="trace",
            description="Upstream failed.",
            include_stack_trace=False,
        )
        data = json.loads(resp.content.decode("utf-8"))
        self.assertNotIn("stacktrace", data["error"])
        self.assertEqual(data["error"]["description"], "Upstream failed.")
        self.assertIn("trace", str(mock_logger.error.call_args))
