"""Test :mod:`smarter.apps.llmclient.cors`, the per-LLMClient CORS origins."""

from unittest.mock import patch

from django.test import Client, RequestFactory, override_settings

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.cors import (
    allow_llmclient_origins,
    llmclient_for_cors,
    origin_allowed,
)
from smarter.apps.llmclient.models import LLMClient
from smarter.common.conf import smarter_settings

ORIGIN = "https://www.example.com"
MODULE = "smarter.apps.llmclient.cors"


class TestLLMClientCors(TestAccountMixin):
    """Test that an LLMClient's allowedOrigins may call its configuration and prompt apis."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(name=f"test_cors_{self.hash_suffix}", user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        LLMClient.objects.filter(pk=self.llmclient.pk).update(allowed_origins=[ORIGIN])
        self.llmclient.refresh_from_db()
        self.factory = RequestFactory()

    def api_request(self, path: str = "prompt/", **headers):
        return self.factory.post(f"/api/v1/llm-clients/{self.llmclient.hashed_id}/{path}", **headers)

    def test_llmclient_for_platform_api_paths(self):
        with patch(f"{MODULE}.LLMClient.get_cached_object", return_value=self.llmclient) as get:
            for path in ("prompt/", "config/", "prompt/config/"):
                with self.subTest(path=path):
                    self.assertEqual(llmclient_for_cors(self.api_request(path)), self.llmclient)
            get.assert_called_with(pk=self.llmclient.id)
            # an integer id, as in the legacy paths.
            request = self.factory.post(f"/api/v1/llm-clients/{self.llmclient.id}/config/")
            self.assertEqual(llmclient_for_cors(request), self.llmclient)

    def test_llmclient_for_an_unknown_id(self):
        with patch(f"{MODULE}.LLMClient.get_cached_object", side_effect=LLMClient.DoesNotExist):
            self.assertIsNone(llmclient_for_cors(self.api_request()))

    def test_llmclient_for_a_deployed_host(self):
        host = f"cors.{self.account.account_number}.api.example.com"
        with patch(f"{MODULE}.get_cached_llmclient_by_request", return_value=self.llmclient):
            for path in ("/", "/config/", "/prompt/"):
                with self.subTest(path=path):
                    request = self.factory.post(path, HTTP_HOST=host)
                    with override_settings(ALLOWED_HOSTS=["*"]):
                        self.assertEqual(llmclient_for_cors(request), self.llmclient)

    def test_llmclient_for_other_requests(self):
        with patch(f"{MODULE}.get_cached_llmclient_by_request", return_value=self.llmclient) as resolve:
            # another path of a deployed host, and the platform's own hosts, are never an LLMClient's apis.
            with override_settings(ALLOWED_HOSTS=["*"]):
                self.assertIsNone(llmclient_for_cors(self.factory.post("/dashboard/", HTTP_HOST="x.example.com")))
                platform = str(smarter_settings.environment_platform_domain)
                self.assertIsNone(llmclient_for_cors(self.factory.post("/config/", HTTP_HOST=platform)))
            resolve.assert_not_called()

    def test_llmclient_for_a_host_that_cannot_be_resolved(self):
        with (
            override_settings(ALLOWED_HOSTS=["*"]),
            patch(f"{MODULE}.get_cached_llmclient_by_request", side_effect=RuntimeError("no")),
        ):
            self.assertIsNone(llmclient_for_cors(self.factory.post("/config/", HTTP_HOST="x.example.com")))

    def test_origin_allowed(self):
        self.assertTrue(origin_allowed(ORIGIN, self.llmclient))
        self.assertTrue(origin_allowed("HTTPS://www.example.com/", self.llmclient))
        self.assertFalse(origin_allowed("https://evil.example.com", self.llmclient))
        self.assertFalse(origin_allowed(None, self.llmclient))
        self.assertFalse(origin_allowed(ORIGIN, None))

    def test_receiver(self):
        with patch(f"{MODULE}.LLMClient.get_cached_object", return_value=self.llmclient):
            self.assertTrue(allow_llmclient_origins(None, request=self.api_request(HTTP_ORIGIN=ORIGIN)))
            self.assertFalse(
                allow_llmclient_origins(None, request=self.api_request(HTTP_ORIGIN="https://evil.example.com"))
            )
            self.assertFalse(allow_llmclient_origins(None, request=self.api_request()))

    def test_preflight_through_the_cors_middleware(self):
        """Test that django-cors-headers allows the LLMClient's origin, and only that one."""
        client = Client()
        url = f"/api/v1/llm-clients/{self.llmclient.hashed_id}/prompt/"
        preflight = {
            "HTTP_ACCESS_CONTROL_REQUEST_METHOD": "POST",
            "HTTP_ACCESS_CONTROL_REQUEST_HEADERS": "content-type,x-smarter-capabilities,authorization",
        }
        response = client.options(url, HTTP_ORIGIN=ORIGIN, **preflight)
        self.assertEqual(response.headers.get("access-control-allow-origin"), ORIGIN)
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        self.assertIn("x-smarter-capabilities", response.headers.get("access-control-allow-headers", ""))

        response = client.options(url, HTTP_ORIGIN="https://evil.example.com", **preflight)
        self.assertIsNone(response.headers.get("access-control-allow-origin"))
