"""Test the Vectorstore REST api: :mod:`smarter.apps.vectorstore.api.v1.views`."""

from http import HTTPStatus
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
)
from smarter.apps.plugin.plugin.safe_http import SafeResponse
from smarter.apps.vectorstore.api.v1 import views
from smarter.apps.vectorstore.api.v1.urls import VectorstoreApiV1ReverseViews as Names
from smarter.apps.vectorstore.models import VectorstoreDocument, VectorstoreMeta
from smarter.lib import json

from .base_classes import DATA_PATH, VectorstoreTestBase


def url(name: str, **kwargs) -> str:
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs)


class TestVectorstoreApi(VectorstoreTestBase):
    """Test the api views, and their permissions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_admin_user, cls.other_account, cls.other_user_profile = admin_user_factory()

    @classmethod
    def tearDownClass(cls):
        VectorstoreMeta.objects.filter(user_profile=cls.other_user_profile).delete()
        factory_account_teardown(
            user=cls.other_admin_user, account=cls.other_account, user_profile=cls.other_user_profile
        )
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.service = self.ready_service("test_api")
        self.vectorstore = self.service.vectorstore
        # the views use the test's service: its in-memory Qdrant and fake embeddings.
        patcher = patch.object(views.VectorstoreViewBase, "get_service", lambda view, vectorstore: self.service)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.delay = patch("smarter.apps.vectorstore.tasks.load_vectorstore_document.delay").start()
        self.addCleanup(patch.stopall)
        self.client = APIClient()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def request(self, method: str, path: str, data=None, status: int = HTTPStatus.OK, format="json") -> dict:
        response = getattr(self.client, method)(path, data=data, format=format)
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content) if response.content else {}

    def test_list_and_detail(self):
        """Test the list and detail, and that another account's vectorstore is not found."""
        other = self.new_vectorstore("test_api_other", user_profile=self.other_user_profile)
        self.client.force_login(self.non_admin_user)
        data = self.request("get", url(Names.list_view))
        names = [item["name"] for item in (data["results"] if isinstance(data, dict) else data)]
        self.assertIn(self.vectorstore.name, names)
        self.assertNotIn(other.name, names)
        detail = self.request("get", url(Names.vectorstore_by_hashed_id, hashed_id=self.vectorstore.hashed_id))
        self.assertEqual(detail["status"], "ready")
        self.request("get", url(Names.vectorstore_by_hashed_id, hashed_id=other.hashed_id), status=HTTPStatus.NOT_FOUND)

    def test_documents(self):
        """Test adding a PDF, text, and a URL; duplicates; listing; and deleting a document."""
        with open(f"{DATA_PATH}/two-pages.pdf", "rb") as f:
            upload = SimpleUploadedFile("two-pages.pdf", f.read(), content_type="application/pdf")
        path = url(Names.documents_by_hashed_id, hashed_id=self.vectorstore.hashed_id)
        data = self.request("post", path, {"files": [upload]}, status=HTTPStatus.ACCEPTED, format="multipart")
        self.assertEqual(data["documents"][0]["name"], "two-pages.pdf")
        self.assertTrue(data["queued"])
        self.assertNotIn("content", data["documents"][0])

        data = self.request("post", path, {"name": "faq", "text": "Answers. " * 40}, status=HTTPStatus.ACCEPTED)
        self.assertEqual(len(data["documents"]), 1)
        data = self.request("post", path, {"name": "again", "text": "Answers. " * 40}, status=HTTPStatus.ACCEPTED)
        self.assertEqual((len(data["documents"]), len(data["duplicates"])), (0, 1))

        response = SafeResponse(
            url="https://example.com/page.html",
            status_code=200,
            headers={"content-type": "text/html"},
            content=b"<p>A web page.</p>",
        )
        with patch.object(views, "fetch", return_value=response) as fetch:
            data = self.request("post", path, {"url": "https://example.com/page.html"}, status=HTTPStatus.ACCEPTED)
        fetch.assert_called_once()
        self.assertEqual(data["documents"][0]["source"], "url")
        self.assertEqual(self.delay.call_count, 3)

        self.request("post", path, {"text": ""}, status=HTTPStatus.BAD_REQUEST)
        bad = SimpleUploadedFile("a.docx", b"PK\x03\x04", content_type="application/octet-stream")
        self.request("post", path, {"files": [bad]}, status=HTTPStatus.BAD_REQUEST, format="multipart")

        listed = self.request("get", path)["documents"]
        self.assertEqual(len(listed), 3)
        document = VectorstoreDocument.objects.filter(vectorstore=self.vectorstore).first()
        with patch("smarter.apps.vectorstore.tasks.delete_vectorstore_document.delay") as delete:
            self.request(
                "delete",
                url(Names.document_by_hashed_id, hashed_id=self.vectorstore.hashed_id, document_id=document.pk),
                status=HTTPStatus.ACCEPTED,
            )
        delete.assert_called_once_with(document.pk)

    def test_owner_only(self):
        """Test that only the owner may add documents, deploy, or take snapshots; others may search."""
        self.client.force_login(self.non_admin_user)
        hashed_id = self.vectorstore.hashed_id
        self.request(
            "post",
            url(Names.documents_by_hashed_id, hashed_id=hashed_id),
            {"text": "x" * 50},
            status=HTTPStatus.NOT_FOUND,
        )
        self.request("post", url(Names.deploy_by_hashed_id, hashed_id=hashed_id), status=HTTPStatus.NOT_FOUND)
        self.request("post", url(Names.snapshots_by_hashed_id, hashed_id=hashed_id), status=HTTPStatus.NOT_FOUND)
        self.request("post", url(Names.search_by_hashed_id, hashed_id=hashed_id), {"query": "anything"})

    def test_search(self):
        document, _ = self.service.add_document(name="a.txt", text="Smarter manifests describe AI applications. " * 20)
        self.service.load_document(document)
        path = url(Names.search_by_hashed_id, hashed_id=self.vectorstore.hashed_id)
        results = self.request("post", path, {"query": "manifests", "k": 2})["results"]
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["metadata"]["document"], "a.txt")
        self.request("post", path, {"query": ""}, status=HTTPStatus.BAD_REQUEST)
        self.request("post", path, {"query": "x", "searchType": "nope"}, status=HTTPStatus.BAD_REQUEST)

    def test_status_snapshots_and_restore(self):
        self.mock_snapshots(self.service)
        hashed_id = self.vectorstore.hashed_id
        status = self.request("get", url(Names.status_by_hashed_id, hashed_id=hashed_id))
        self.assertEqual(status["status"], "ready")
        snapshot = self.request(
            "post", url(Names.snapshots_by_hashed_id, hashed_id=hashed_id), status=HTTPStatus.CREATED
        )
        listed = self.request("get", url(Names.snapshots_by_hashed_id, hashed_id=hashed_id))["snapshots"]
        self.assertEqual([s["name"] for s in listed], [snapshot["name"]])
        data = self.request("post", url(Names.restore_by_hashed_id, hashed_id=hashed_id, snapshot_id=snapshot["id"]))
        self.assertEqual(data["restored"], snapshot["name"])
        self.request(
            "post", url(Names.restore_by_hashed_id, hashed_id=hashed_id, snapshot_id=0), status=HTTPStatus.NOT_FOUND
        )

    def test_undeploy_and_deploy(self):
        hashed_id = self.vectorstore.hashed_id
        self.assertEqual(
            self.request("post", url(Names.undeploy_by_hashed_id, hashed_id=hashed_id))["status"], "stopped"
        )
        data = self.request("post", url(Names.deploy_by_hashed_id, hashed_id=hashed_id), status=HTTPStatus.ACCEPTED)
        self.assertEqual(data["status"], "ready")
