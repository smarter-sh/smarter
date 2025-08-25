"""Test cases for the cache decorators."""

from unittest.mock import Mock, patch

from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest

from smarter.apps.account.tests.mixins import TestAccountMixin

from ..cache import cache_request, cache_results


class TestBase(TestAccountMixin):
    """Base class for tests"""


class TestCacheResults(TestBase):
    """Test the cache_results decorator."""

    @patch("smarter.lib.cache.cache")
    @patch("smarter.lib.cache.waffle")
    @patch("smarter.lib.cache.logger")
    def test_cache_hit(self, mock_logger, mock_waffle, mock_cache):
        mock_waffle.switch_is_active.return_value = True
        mock_cache.get.return_value = "cached"

        @cache_results(logging_enabled=True)
        def func(x):
            return "computed"

        result = func(1)
        self.assertEqual(result, "cached")
        mock_logger.info.assert_called()

    def test_cache_miss(self):
        """
        Test that the function is called and result cached on a cache miss.
        This mainly exists to ensure that we can call the decorated function
        in these ways, and without any weird side effects.
        """

        @cache_results()
        def func():
            return "computed"

        result = func()
        self.assertEqual(func(), "computed")
        self.assertEqual(result, "computed")
        self.assertEqual(func.invalidate(), None)
        self.assertEqual(func(), "computed")


class TestCacheRequest(TestBase):
    """test cache_request decorator"""

    @patch("smarter.lib.cache.cache")
    @patch("smarter.lib.cache.waffle")
    @patch("smarter.lib.cache.logger")
    def test_cache_request_hit_authenticated_admin(self, mock_logger, mock_waffle, mock_cache):
        mock_waffle.switch_is_active.return_value = True
        mock_cache.get.return_value = "cached"

        @cache_request(logging_enabled=True)
        def func(request):
            return "computed"

        request = Mock(spec=WSGIRequest)
        request.build_absolute_uri.return_value = "http://testserver/api/"
        request.user = self.admin_user
        result = func(request)
        self.assertEqual(result, "cached")
        mock_logger.info.assert_called()

    @patch("smarter.lib.cache.cache")
    @patch("smarter.lib.cache.waffle")
    @patch("smarter.lib.cache.logger")
    def test_cache_request_hit_authenticated_mortal(self, mock_logger, mock_waffle, mock_cache):
        mock_waffle.switch_is_active.return_value = True
        mock_cache.get.return_value = "cached"

        @cache_request(logging_enabled=True)
        def func(request):
            return "computed"

        request = Mock(spec=WSGIRequest)
        request.build_absolute_uri.return_value = "http://testserver/api/"
        request.user = self.non_admin_user
        result = func(request)
        self.assertEqual(result, "cached")
        mock_logger.info.assert_called()

    @patch("smarter.lib.cache.cache")
    @patch("smarter.lib.cache.waffle")
    @patch("smarter.lib.cache.logger")
    def test_cache_request_miss_anonymous(self, mock_logger, mock_waffle, mock_cache):
        mock_waffle.switch_is_active.return_value = True
        mock_cache.get.return_value = None

        @cache_request(logging_enabled=True)
        def func(request):
            return "computed"

        request = Mock(spec=WSGIRequest)
        request.build_absolute_uri.return_value = "http://testserver/api/"
        request.user = AnonymousUser()
        result = func(request)
        self.assertEqual(result, "computed")
        mock_cache.set.assert_called()
        mock_logger.info.assert_called()
