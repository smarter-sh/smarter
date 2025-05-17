"""Test cases for the cache decorators."""

from unittest.mock import Mock, patch

from django.core.handlers.wsgi import WSGIRequest

from smarter.lib.unittest.base_classes import SmarterTestBase

from ..cache import cache_request, cache_results


class TestCacheResults(SmarterTestBase):
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

    @patch("smarter.lib.cache.cache")
    @patch("smarter.lib.cache.waffle")
    @patch("smarter.lib.cache.logger")
    def test_cache_miss(self, mock_logger, mock_waffle, mock_cache):
        mock_waffle.switch_is_active.return_value = True
        mock_cache.get.return_value = None

        @cache_results(logging_enabled=True)
        def func(x):
            return "computed"

        result = func(2)
        self.assertEqual(result, "computed")
        mock_cache.set.assert_called()
        mock_logger.info.assert_called()


class TestCacheRequest(SmarterTestBase):
    """test cache_request decorator"""

    @patch("smarter.lib.cache.cache")
    @patch("smarter.lib.cache.waffle")
    @patch("smarter.lib.cache.logger")
    def test_cache_request_hit_authenticated(self, mock_logger, mock_waffle, mock_cache):
        mock_waffle.switch_is_active.return_value = True
        mock_cache.get.return_value = "cached"

        @cache_request(logging_enabled=True)
        def func(request):
            return "computed"

        request = Mock(spec=WSGIRequest)
        request.build_absolute_uri.return_value = "http://testserver/api/"
        request.user.is_authenticated = True
        request.user.username = "bob"
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
        request.user.is_authenticated = False
        result = func(request)
        self.assertEqual(result, "computed")
        mock_cache.set.assert_called()
        mock_logger.info.assert_called()
