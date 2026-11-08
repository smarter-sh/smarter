"""Test the web console views of vectorstores: the React list's api, the list page, and the manifest page, which loads.

the vectorstore from the dashboard's resource api.
"""

from django.test import Client
from django.urls import reverse

from smarter.apps.vectorstore.api.web.urls import (
    VectorstoreApiWebReverseNames as WebNames,
)
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.apps.vectorstore.urls import VectorstoreReverseNames as Names
from smarter.lib.unittest.resource_views import (
    assert_console_page,
    assert_no_resource,
    resource_detail_json,
)

from .base_classes import VectorstoreTestBase


def url(name: str, **kwargs) -> str:
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs or None)


def web_url(name: str, **kwargs) -> str:
    return reverse(f"{WebNames.namespace}:{name}", kwargs=kwargs or None)


class TestVectorstoreConsole(VectorstoreTestBase):
    """Test the list, clone, rename and delete apis, the list page, and the detail view."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def test_list_page(self):
        """Test that the list page is the single-page console's."""
        assert_console_page(self, url(Names.listview))

    def test_web_api_paths(self):
        """Test that the list page's endpoints are in the web console's api."""
        self.assertEqual(web_url(WebNames.listview_all), "/api/web/vectorstore/listview/")
        self.assertEqual(web_url(WebNames.listview, ownership_filter="owned"), "/api/web/vectorstore/listview/owned/")
        self.assertEqual(web_url(WebNames.clone, vectorstore_id=1, new_name="x"), "/api/web/vectorstore/clone/1/x/")
        self.assertEqual(web_url(WebNames.rename, vectorstore_id=1, new_name="x"), "/api/web/vectorstore/rename/1/x/")
        self.assertEqual(web_url(WebNames.delete, vectorstore_id=1), "/api/web/vectorstore/delete/1/")

    def test_list_api(self):
        """Test that the list api returns the fields of the React app's Vectorstore type."""
        vectorstore = self.new_vectorstore("test_views_list")
        response = self.client.post(web_url(WebNames.listview, ownership_filter="owned") + "?invalidate_cache=true")
        self.assertEqual(response.status_code, 200)
        (item,) = (o for o in response.json()["objects"] if o["name"] == vectorstore.name)
        for key in (
            "backend",
            "hosting",
            "status",
            "statusMessage",
            "vectorCount",
            "documentCount",
            "snapshotCount",
            "embeddingsProvider",
            "embeddingsModel",
            "deletionProtection",
            "manifestUrl",
            "spec",
            "apiKeySecret",
        ):
            self.assertIn(key, item)
        self.assertEqual(item["embeddingsProvider"], self.provider.name)

    def test_list_api_sorts(self):
        """Test that the list api sorts by the database and the number of vectors, in either direction."""
        first = self.new_vectorstore("test_views_sort_a")
        second = self.new_vectorstore("test_views_sort_b")
        VectorstoreMeta.objects.filter(pk=first.pk).update(vector_count=5)
        VectorstoreMeta.objects.filter(pk=second.pk).update(vector_count=10)
        expected = [first.name, second.name]
        list_url = web_url(WebNames.listview, ownership_filter="owned") + "?invalidate_cache=true&page_size=100"
        for ordering, names in (("vectorCount", expected), ("-vectorCount", list(reversed(expected)))):
            data = self.client.post(f"{list_url}&ordering={ordering}").json()
            self.assertEqual(data["pagination"]["ordering"], ordering)
            self.assertEqual([o["name"] for o in data["objects"] if o["name"] in expected], names)
        data = self.client.post(f"{list_url}&ordering=-database").json()
        self.assertEqual(data["pagination"]["ordering"], "-database")
        self.assertIn("database", data["pagination"]["sortFields"])

    def test_clone(self):
        """Test that a clone is a new, undeployed vectorstore with the same spec, and none of the original's state."""
        service = self.ready_service("test_views_clone")
        name = f"test_views_clone_copy_{self.hash_suffix}"
        response = self.client.post(web_url(WebNames.clone, vectorstore_id=service.vectorstore.pk, new_name=name))
        self.assertEqual(response.status_code, 200, response.content)
        clone = VectorstoreMeta.objects.get(name=name)
        self.addCleanup(clone.delete)
        self.assertEqual(clone.status, "pending")
        self.assertEqual(
            (clone.index_name, clone.endpoint_url, clone.deployed_at, clone.api_key_secret), ("", "", None, None)
        )
        self.assertEqual(clone.spec["embeddings"], service.vectorstore.spec["embeddings"])
        conflict = self.client.post(web_url(WebNames.clone, vectorstore_id=service.vectorstore.pk, new_name=name))
        self.assertEqual(conflict.status_code, 409)

    def test_rename(self):
        vectorstore = self.new_vectorstore("test_views_rename")
        kubernetes_name = vectorstore.kubernetes_name
        name = f"test_views_renamed_{self.hash_suffix}"
        response = self.client.post(web_url(WebNames.rename, vectorstore_id=vectorstore.pk, new_name=name))
        self.assertEqual(response.status_code, 200, response.content)
        vectorstore.refresh_from_db()
        self.assertEqual((vectorstore.name, vectorstore.kubernetes_name), (name, kubernetes_name))

    def test_delete(self):
        """Test that delete destroys a deployed database, and refuses a protected one."""
        service = self.ready_service("test_views_delete")
        response = self.client.post(web_url(WebNames.delete, vectorstore_id=service.vectorstore.pk))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(VectorstoreMeta.objects.filter(pk=service.vectorstore.pk).exists())
        self.assertIn("persistentvolumeclaim", self.kubernetes.deleted[-1][0])

        protected = self.new_vectorstore("test_views_protected")
        VectorstoreMeta.objects.filter(pk=protected.pk).update(deletion_protection=True)
        response = self.client.post(web_url(WebNames.delete, vectorstore_id=protected.pk))
        self.assertEqual(response.status_code, 400)
        self.assertIn("deletionProtection", response.json()["error"])
        self.assertTrue(VectorstoreMeta.objects.filter(pk=protected.pk).exists())

    def test_detail_view(self):
        """Test that the manifest page is the console's, whose resource api returns the vectorstore's manifest."""
        vectorstore = self.new_vectorstore("test_views_detail")
        detail = resource_detail_json(self, vectorstore.record_locator)
        self.assertEqual(detail["kind"], "Vectorstore")
        self.assertEqual(detail["name"], vectorstore.name)
        self.assertIn(vectorstore.name, detail["manifest"] or "")
        self.assertIn("vectorstoreStatus", detail["manifest"] or "")
        assert_console_page(self, url(Names.detailview, hashed_id=vectorstore.hashed_id))

    def test_detail_view_shared_with_non_admin(self):
        """Test that a non-admin user may read a vectorstore owned by the account's admin from the resource api."""
        vectorstore = self.new_vectorstore("test_views_detail_shared")
        self.client.force_login(self.non_admin_user)
        detail = resource_detail_json(self, vectorstore.record_locator)
        self.assertIn(vectorstore.name, detail["manifest"] or "")

    def test_detail_view_unknown_id(self):
        """Test that the resource api has no vectorstore for a valid hashed id of one that doesn't exist, or an invalid one."""
        assert_no_resource(self, VectorstoreMeta(id=999999999).record_locator)
        assert_no_resource(self, "vectorstoremeta-not-a-hash")
