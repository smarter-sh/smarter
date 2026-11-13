"""
Test running a Vectorsearch, :mod:`smarter.apps.vectorsearch.api.v1.views.default`.

The vectorstore is in-memory Qdrant, with fake embeddings and a fake cluster, and every response is validated
against the Smarter api's OpenAPI document.
"""

from http import HTTPStatus
from unittest.mock import patch

from rest_framework.test import APIClient

from smarter.apps.account.models.budget import SmarterBudgetExceeded
from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.vectorsearch.api.v1.views import default
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorstore.tests.base_classes import VectorstoreTestBase

TEMPLATE = "/vectorsearches/{id}/vectorsearch/"


class TestVectorsearchRun(OpenApiResponseMixin, VectorstoreTestBase):
    """Test POST /api/v1/vectorsearches/<hashed_id>/vectorsearch/."""

    def setUp(self):
        super().setUp()
        self.vectorstore_service = self.ready_service("test_vectorsearch_run")
        self.vectorstore = self.vectorstore_service.vectorstore
        for name, topic in (("a.txt", "Smarter manifests describe AI applications. "), ("b.txt", "Cats sleep. ")):
            document, _ = self.vectorstore_service.add_document(name=name, text=topic * 20, metadata={"topic": name})
            self.vectorstore_service.load_document(document)
        self.vectorsearch = Vectorsearch.objects.create(
            name=f"test_vectorsearch_run_{self.hash_suffix}",
            user_profile=self.user_profile,
            vectorstore=self.vectorstore,
            k=2,
        )
        self.addCleanup(Vectorsearch.objects.filter(pk=self.vectorsearch.pk).delete)
        patcher = patch.object(
            default.DefaultVectorsearchApiView, "get_service", lambda view, vectorstore: self.vectorstore_service
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = APIClient()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def run_search(self, body, status: int = HTTPStatus.OK, client=None, hashed_id=None) -> dict:
        """Run the Vectorsearch, assert the status, and validate the response against the document."""
        path = "/api/v1" + TEMPLATE.format(id=hashed_id or self.vectorsearch.hashed_id)
        response = (client or self.client).post(path, data=body, format="json")
        self.assertEqual(response.status_code, status, response.content[:500])
        self.assertValidResponse(TEMPLATE, "post", response.json(), status)
        return response.json()

    def test_run(self):
        """A run returns the Vectorsearch's k results, most similar first."""
        data = self.run_search({"query": "manifests"})
        self.assertEqual(data["vectorsearch"], self.vectorsearch.name)
        self.assertEqual(data["vectorstore"], self.vectorstore.name)
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["metadata"]["document"], "a.txt")

    def test_run_by_id(self):
        """A run is also reached by the Vectorsearch's numeric id."""
        response = self.client.post(
            f"/api/v1/vectorsearches/{self.vectorsearch.pk}/vectorsearch/", data={"query": "cats"}, format="json"
        )
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])

    def test_filters(self):
        """The request's filter narrows the results, and the Vectorsearch's own filter wins over it."""
        data = self.run_search({"query": "manifests", "filter": {"topic": "b.txt"}})
        self.assertEqual({result["metadata"]["document"] for result in data["results"]}, {"b.txt"})
        self.vectorsearch.metadata_filter = {"topic": "a.txt"}
        self.vectorsearch.save()
        data = self.run_search({"query": "cats", "filter": {"topic": "b.txt"}})
        self.assertEqual({result["metadata"]["document"] for result in data["results"]}, {"a.txt"})

    def test_errors(self):
        """An invalid request, a disabled Vectorsearch, a failed search and a budget are refused."""
        self.assertIn("not valid", self.run_search({}, HTTPStatus.BAD_REQUEST)["detail"])
        self.assertIn("query", self.run_search({"query": " "}, HTTPStatus.BAD_REQUEST)["detail"])
        with patch.object(default, "charge_authorization", side_effect=SmarterBudgetExceeded("over budget")):
            self.assertEqual(self.run_search({"query": "x"}, HTTPStatus.PAYMENT_REQUIRED)["detail"], "over budget")
        self.vectorsearch.is_enabled = False
        self.vectorsearch.save()
        self.assertIn("disabled", self.run_search({"query": "x"}, HTTPStatus.BAD_REQUEST)["detail"])

    def test_not_found(self):
        """A Vectorsearch that doesn't exist, or that the user may not read, is a 404."""
        missing = Vectorsearch(id=999999999)
        self.run_search({"query": "x"}, HTTPStatus.NOT_FOUND, hashed_id=missing.hashed_id)
        response = self.client.post("/api/v1/vectorsearches/0/vectorsearch/", data={"query": "x"}, format="json")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_anonymous(self):
        """A request without an api key or a session is refused."""
        self.assertIn(
            APIClient()
            .post("/api/v1" + TEMPLATE.format(id=self.vectorsearch.hashed_id), {"query": "x"}, format="json")
            .status_code,
            (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN),
        )
