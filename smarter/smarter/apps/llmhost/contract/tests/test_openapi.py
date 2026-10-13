"""Test that the LLMHosts' real REST responses are valid under the Smarter api's OpenAPI document."""

from http import HTTPStatus

from rest_framework.test import APIClient

from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.llmhost.tests.base_classes import LLMHostTestBase


class TestLLMHostOpenApi(OpenApiResponseMixin, LLMHostTestBase):
    """Every LLMHost operation's real response, on the fake cluster and the builtin catalog, against the document."""

    def setUp(self):
        super().setUp()
        self.llmhost = self.new_llmhost("test_llmhost_openapi")
        self.client = APIClient()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def call(self, method: str, template: str, status: int, query: str = ""):
        """Call an operation, assert its status, and validate its response against the document."""
        path = "/api/v1" + template.format(id=self.llmhost.hashed_id) + query
        response = getattr(self.client, method)(path, format="json")
        self.assertEqual(response.status_code, status, response.content)
        self.assertValidResponse(template, method, response.json(), status)
        return response.json()

    def test_reads_and_discovery(self):
        self.call("get", "/llmhosts/", HTTPStatus.OK)
        self.call("get", "/llmhosts/{id}/", HTTPStatus.OK)
        self.call("get", "/llmhosts/report/", HTTPStatus.OK)
        self.assertTrue(
            self.call("get", "/llmhosts/discover/", HTTPStatus.OK, "?catalog=builtin&task=embedding")["models"]
        )
        self.call("get", "/llmhosts/discover/", HTTPStatus.SERVICE_UNAVAILABLE, "?catalog=nope")
        self.call("get", "/llmhosts/discover/", HTTPStatus.BAD_REQUEST, "?limit=x")
        self.call("get", "/llmhosts/discover/manifest/", HTTPStatus.OK, "?catalog=builtin&repository=BAAI/bge-m3")
        self.call("get", "/llmhosts/discover/manifest/", HTTPStatus.BAD_REQUEST)
        response = self.client.get("/api/v1/llmhosts/999999999/")
        self.assertValidResponse("/llmhosts/{id}/", "get", response.json(), HTTPStatus.NOT_FOUND)

    def test_lifecycle(self):
        self.call("get", "/llmhosts/{id}/plan/", HTTPStatus.OK)
        self.call("post", "/llmhosts/{id}/deploy/", HTTPStatus.ACCEPTED)
        self.simulate_ready(self.llmhost)
        status = self.call("get", "/llmhosts/{id}/status/", HTTPStatus.OK)
        self.assertEqual(status["llmhost"], self.llmhost.name)
        self.cluster.pod_logs = "INFO started"
        self.call("get", "/llmhosts/{id}/logs/", HTTPStatus.OK)
        self.call("get", "/llmhosts/{id}/logs/", HTTPStatus.BAD_REQUEST, "?tail=x")
        self.call("post", "/llmhosts/{id}/undeploy/", HTTPStatus.OK, "?purge=true")
        self.cluster.ready = False
        self.call("post", "/llmhosts/{id}/deploy/", HTTPStatus.SERVICE_UNAVAILABLE)
