"""Test that the vectorstores' real REST responses are valid under the Smarter api's OpenAPI document."""

from http import HTTPStatus
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.vectorstore.api.v1 import views
from smarter.apps.vectorstore.models import VectorstoreDocument
from smarter.apps.vectorstore.tests.base_classes import DATA_PATH, VectorstoreTestBase


class TestVectorstoreOpenApi(OpenApiResponseMixin, VectorstoreTestBase):
    """Every vectorstore operation's real response, with in-memory Qdrant and a fake Kubernetes, against the document."""

    def setUp(self):
        super().setUp()
        self.service = self.ready_service("test_vectorstore_openapi")
        self.vectorstore = self.service.vectorstore
        patcher = patch.object(views.VectorstoreViewBase, "get_service", lambda view, vectorstore: self.service)
        patcher.start()
        self.addCleanup(patcher.stop)
        patch("smarter.apps.vectorstore.tasks.load_vectorstore_document.delay").start()
        patch("smarter.apps.vectorstore.tasks.delete_vectorstore_document.delay").start()
        self.addCleanup(patch.stopall)
        self.client = APIClient()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def call(self, method: str, template: str, status: int, data=None, request_format="json", **kwargs):
        """Call an operation, assert its status, and validate its response against the document."""
        path = "/api/v1" + template.format(id=self.vectorstore.hashed_id, **kwargs)
        response = getattr(self.client, method)(path, data=data, format=request_format)
        self.assertEqual(response.status_code, status, response.content)
        self.assertValidResponse(template, method, response.json(), status)
        return response.json()

    def test_reads(self):
        self.call("get", "/vectorstores/", HTTPStatus.OK)
        self.call("get", "/vectorstores/{id}/", HTTPStatus.OK)
        self.call("get", "/vectorstores/{id}/status/", HTTPStatus.OK)
        response = self.client.get("/api/v1/vectorstores/999999999/")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.content)
        self.assertValidResponse("/vectorstores/{id}/", "get", response.json(), HTTPStatus.NOT_FOUND)

    def test_documents_and_search(self):
        with open(f"{DATA_PATH}/two-pages.pdf", "rb") as f:
            upload = SimpleUploadedFile("two-pages.pdf", f.read(), content_type="application/pdf")
        self.call("post", "/vectorstores/{id}/documents/", HTTPStatus.ACCEPTED, {"files": [upload]}, "multipart")
        added = self.call(
            "post", "/vectorstores/{id}/documents/", HTTPStatus.ACCEPTED, {"name": "faq", "text": "Answers. " * 40}
        )
        self.call("post", "/vectorstores/{id}/documents/", HTTPStatus.BAD_REQUEST, {"text": ""})
        listed = self.call("get", "/vectorstores/{id}/documents/", HTTPStatus.OK)
        self.assertEqual(len(listed["documents"]), 2)

        document = VectorstoreDocument.objects.get(pk=added["documents"][0]["id"])
        self.service.load_document(document)
        results = self.call("post", "/vectorstores/{id}/search/", HTTPStatus.OK, {"query": "answers", "k": 2})
        self.assertTrue(results["results"])
        self.call("post", "/vectorstores/{id}/search/", HTTPStatus.BAD_REQUEST, {"query": "x", "searchType": "nope"})
        self.call("delete", "/vectorstores/{id}/documents/{document_id}/", HTTPStatus.ACCEPTED, document_id=document.pk)

    def test_snapshots_and_deployment(self):
        self.mock_snapshots(self.service)
        snapshot = self.call("post", "/vectorstores/{id}/snapshots/", HTTPStatus.CREATED)
        self.call("get", "/vectorstores/{id}/snapshots/", HTTPStatus.OK)
        self.call(
            "post", "/vectorstores/{id}/snapshots/{snapshot_id}/restore/", HTTPStatus.OK, snapshot_id=snapshot["id"]
        )
        self.call("post", "/vectorstores/{id}/snapshots/{snapshot_id}/restore/", HTTPStatus.NOT_FOUND, snapshot_id=0)
        self.call("post", "/vectorstores/{id}/undeploy/", HTTPStatus.OK)
        self.call("post", "/vectorstores/{id}/deploy/", HTTPStatus.ACCEPTED)
