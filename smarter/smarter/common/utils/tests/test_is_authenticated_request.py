"""Test is_authenticated_request utility."""

from unittest.mock import Mock

from django.core.handlers.asgi import ASGIRequest

from smarter.common.utils.request import is_authenticated_request
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestRequestUtils(SmarterTestBase):
    """Test is_authenticated_request utility."""

    def test_authenticated_user(self):
        mock_user = Mock()
        mock_user.is_authenticated = True
        mock_request = Mock(spec=ASGIRequest)
        mock_request.user = mock_user
        result = is_authenticated_request(mock_request)
        self.assertTrue(result)

    def test_unauthenticated_user(self):
        mock_user = Mock()
        mock_user.is_authenticated = False
        mock_request = Mock(spec=ASGIRequest)
        mock_request.user = mock_user
        result = is_authenticated_request(mock_request)
        self.assertFalse(result)

    def test_no_user_attribute(self):
        mock_request = Mock(spec=ASGIRequest)
        if hasattr(mock_request, "user"):
            del mock_request.user
        result = is_authenticated_request(mock_request)
        self.assertFalse(result)

    def test_user_no_is_authenticated(self):
        mock_user = Mock()
        if hasattr(mock_user, "is_authenticated"):
            del mock_user.is_authenticated
        mock_request = Mock(spec=ASGIRequest)
        mock_request.user = mock_user
        result = is_authenticated_request(mock_request)
        self.assertFalse(result)

    def test_invalid_request_type(self):

        class NotARequest:
            """A class that does not resemble a request object."""

        not_a_request = NotARequest()
        result = is_authenticated_request(not_a_request)  # type: ignore
        self.assertFalse(result)

    def test_none_request(self):
        result = is_authenticated_request(None)
        self.assertFalse(result)
