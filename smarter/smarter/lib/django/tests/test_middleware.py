"""Test BlockSensitiveFilesMiddleware."""

import unittest

from django.http import HttpResponse
from django.test import RequestFactory

from smarter.apps.account.mixins import AccountMixin
from smarter.lib.django.middleware import BlockSensitiveFilesMiddleware


class TestBlockSensitiveFilesMiddleware(unittest.TestCase, AccountMixin):
    """Test BlockSensitiveFilesMiddleware."""

    def setUp(self):
        self.middleware = BlockSensitiveFilesMiddleware(lambda req: HttpResponse())
        self.factory = RequestFactory()

    def test_non_sensitive_file(self):
        request = self.factory.get("/non_sensitive_file.txt")
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_sensitive_file(self):
        for sensitive_file in self.middleware.sensitive_files:
            request = self.factory.get("/" + sensitive_file)
            response = self.middleware(request)
            self.assertEqual(response.status_code, 403)
