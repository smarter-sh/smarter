"""Test :class:`smarter.apps.llmclient.middleware.security.SmarterSecurityMiddleware` on a deployed LLMClient's host."""

from http import HTTPStatus
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.middleware.security import SmarterSecurityMiddleware
from smarter.apps.llmclient.models import LLMClient
from smarter.common.conf import smarter_settings

MODULE = "smarter.apps.llmclient.middleware.security"


class TestSmarterSecurityMiddleware(TestAccountMixin):
    """
    Test which paths of a deployed LLMClient's host the middleware lets through.

    The host is not in ``allowed_hosts`` and not a local host, as in production, so a request passes
    only if it resolves to an LLMClient.
    """

    def setUp(self):
        super().setUp()
        # request.get_host() accepts the deployed host, as it does in production.
        allowed_hosts = override_settings(ALLOWED_HOSTS=["*"])
        allowed_hosts.enable()
        self.addCleanup(allowed_hosts.disable)
        self.llmclient = LLMClient.objects.create(
            name=f"security_middleware_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        self.host = (
            f"{self.llmclient.rfc1034_compliant_name}.{self.account.account_number}."
            f"{smarter_settings.environment_api_domain}"
        )
        self.middleware = SmarterSecurityMiddleware(lambda request: HttpResponse("ok"))

        settings_mock = MagicMock()
        settings_mock.allowed_hosts = []
        settings_mock.internal_ip_prefixes = []
        validator_mock = MagicMock()
        validator_mock.LOCAL_HOSTS = []
        patchers = (
            patch(f"{MODULE}.waffle.switch_is_active", return_value=True),
            patch(f"{MODULE}.smarter_settings", settings_mock),
            patch(f"{MODULE}.SmarterValidator", validator_mock),
        )
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def process(self, path: str):
        request = RequestFactory().get(path, HTTP_HOST=self.host)
        request.user = AnonymousUser()
        return self.middleware.process_request(request)

    def test_the_deployed_hosts_paths_pass(self):
        """
        The endpoints page and its message catalog pass (issue #962).

        The page at ``/`` requests ``/jsi18n/`` from the same host, which used to receive 400.
        """
        for path in ("/", "/config/", "/prompt/", "/jsi18n/"):
            with self.subTest(path=path):
                self.assertIsNone(self.process(path))

    def test_other_paths_are_rejected(self):
        """A path that the host doesn't serve, e.g. a scanner's, receives 400."""
        for path in ("/wp-json/", "/jsi18n/extra/"):
            with self.subTest(path=path), self.assertLogs(MODULE, level="WARNING"):
                response = self.process(path)
            self.assertIsNotNone(response)
            self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
