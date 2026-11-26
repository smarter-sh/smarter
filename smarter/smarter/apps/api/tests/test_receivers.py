"""Test :mod:`smarter.apps.api.receivers`, the receivers of the api app's signals."""

import logging
from http import HTTPStatus
from unittest.mock import MagicMock

from smarter.apps.api import receivers
from smarter.apps.api.signals import (
    api_request_completed,
    api_request_failed,
    api_request_initiated,
)
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.log_capture import WrappedLoggerCapture


class TestApiReceivers(SmarterTestBase):
    """Test that each api request signal is logged once, at its level."""

    def setUp(self):
        super().setUp()
        self.capture = WrappedLoggerCapture(self, receivers.logger)
        self.view = MagicMock()
        self.request = MagicMock(path="/api/v1/cli/apply/", method="POST")
        self.request.user = MagicMock(pk=42, username="a_person_name", is_authenticated=True)
        self.request.user.__str__.return_value = "a_person_name"

    def test_initiated_and_completed(self):
        api_request_initiated.send(sender=self.__class__, instance=self.view, request=self.request)
        api_request_completed.send(sender=self.__class__, instance=self.view, request=self.request, response=None)
        info = self.capture.messages(logging.INFO)
        self.assertEqual(len(info), 2)
        self.assertIn("/api/v1/cli/apply/ - POST - user_id=42", info[0])
        self.assertIn("/api/v1/cli/apply/ - POST - user_id=42", info[1])

    def test_username_is_not_logged(self):
        """The user is logged by id, never by username, which is often a person's name."""
        api_request_initiated.send(sender=self.__class__, instance=self.view, request=self.request)
        api_request_completed.send(sender=self.__class__, instance=self.view, request=self.request, response=None)
        text = self.capture.text(logging.INFO)
        self.assertNotIn("a_person_name", text)
        self.assertIn("user_id=42", text)

    def test_anonymous_user(self):
        """An anonymous user is logged as anonymous."""
        self.request.user = MagicMock(pk=None, is_authenticated=False)
        api_request_initiated.send(sender=self.__class__, instance=self.view, request=self.request)
        self.assertIn("/api/v1/cli/apply/ - POST - anonymous", self.capture.text(logging.INFO))

    def test_user_for_log_without_a_user(self):
        """A request without a user is logged as N/A."""
        request = MagicMock(spec=["path", "method"])
        self.assertEqual(receivers.user_for_log(request), "N/A")

    def test_client_error_is_a_warning(self):
        """A client error logs the description that the client is told, at WARNING, without a traceback."""
        api_request_failed.send(
            sender=self.__class__,
            instance=self.view,
            request=self.request,
            response=None,
            exception=PermissionError("denied"),
            status=HTTPStatus.FORBIDDEN.value,
            description="no Authorization header",
        )
        self.assertIn("403 <class 'PermissionError'>: no Authorization header", self.capture.text(logging.WARNING))
        self.assertEqual(self.capture.count(logging.ERROR), 0)

    def test_server_error_is_an_error_with_its_traceback(self):
        """A 500 logs the exception at ERROR, with the traceback of the exception being handled."""
        try:
            raise RuntimeError("a bug")
        except RuntimeError as e:
            api_request_failed.send(
                sender=self.__class__,
                instance=self.view,
                request=self.request,
                response=None,
                exception=e,
                status=HTTPStatus.INTERNAL_SERVER_ERROR.value,
                description="a bug report",
            )
        self.assertIn("<class 'RuntimeError'>: a bug", self.capture.text(logging.ERROR))
        self.assertTrue(self.capture.mock.log.call_args.kwargs.get("exc_info"))
        self.assertEqual(self.capture.count(logging.WARNING), 0)
