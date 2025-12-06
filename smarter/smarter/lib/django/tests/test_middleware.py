"""Test SmarterBlockSensitiveFilesMiddleware."""

from http import HTTPStatus

from django.http import HttpResponse
from django.test import RequestFactory

from smarter.apps.account.mixins import AccountMixin
from smarter.lib.django.middleware.sensitive_files import (
    SmarterBlockSensitiveFilesMiddleware,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSmarterBlockSensitiveFilesMiddleware(SmarterTestBase, AccountMixin):
    """Test SmarterBlockSensitiveFilesMiddleware."""

    def setUp(self):
        super().setUp()
        self.middleware = SmarterBlockSensitiveFilesMiddleware(lambda req: HttpResponse())
        self.factory = RequestFactory()

    def test_non_sensitive_file(self):
        request = self.factory.get("/non_sensitive_file.txt")
        response = self.middleware(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_sensitive_file(self):
        for sensitive_file in self.middleware.sensitive_files:
            request = self.factory.get("/" + sensitive_file)
            response = self.middleware(request)
            self.assertEqual(
                response.status_code,
                HTTPStatus.FORBIDDEN,
                f"Expected 403 for {sensitive_file}, got {response.status_code}",
            )
