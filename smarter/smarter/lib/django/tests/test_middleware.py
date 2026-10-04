"""Test SmarterBlockSensitiveFilesMiddleware."""

from http import HTTPStatus
from unittest.mock import patch

from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory

from smarter.lib.django import waffle
from smarter.lib.django.middleware.sensitive_files import (
    EXACT_MATCHES,
    SmarterBlockSensitiveFilesMiddleware,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSmarterBlockSensitiveFilesMiddleware(SmarterTestBase):
    """Test SmarterBlockSensitiveFilesMiddleware."""

    # The middleware is tested with its waffle switch on, whatever the switch's value in the database.
    switch = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_SENSITIVE_FILES

    def setUp(self):
        super().setUp()
        original = waffle.switch_is_active
        patcher = patch(
            "smarter.lib.django.waffle.switch_is_active",
            side_effect=lambda name: True if name == self.switch else original(name),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.middleware = SmarterBlockSensitiveFilesMiddleware(lambda req: HttpResponse())
        self.factory = RequestFactory()

    def test_non_sensitive_file(self):
        request = self.factory.get("/non_sensitive_file.txt", REMOTE_ADDR="8.8.4.4")
        response = self.middleware(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_sensitive_file(self):
        # a different public ip for each file, so that the client is never throttled.
        for i, sensitive_file in enumerate(sorted(EXACT_MATCHES)):
            ip = f"8.9.{i // 250}.{i % 250 + 1}"
            self.addCleanup(cache.delete, self.middleware.get_throttle_key(ip))
            request = self.factory.get("/" + sensitive_file, REMOTE_ADDR=ip)
            response = self.middleware(request)
            self.assertEqual(
                response.status_code,
                HTTPStatus.FORBIDDEN,
                f"Expected 403 for {sensitive_file}, got {response.status_code}",
            )
