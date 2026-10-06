"""Test the web console views of vectorstores: the React list's api, and the detail view."""

from django.test import Client
from django.urls import reverse

from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.apps.vectorstore.urls import VectorstoreReverseNames as Names

from .base_classes import VectorstoreTestBase


def url(name: str, **kwargs) -> str:
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs or None)


class TestVectorstoreConsole(VectorstoreTestBase):
    """Test the list, clone, rename and delete apis, the list page, and the detail view."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def test_list_page(self):
        response = self.client.get(url(Names.listview))
        self.assertEqual(response.status_code, 200)
        self.assertIn("smarter-vectorstore-list-root", response.content.decode())

    def test_list_api(self):
        """Test that the list api returns the fields of the React app's Vectorstore type."""
        vectorstore = self.new_vectorstore("test_views_list")
        response = self.client.post(url(Names.listview_api, ownership_filter="owned") + "?invalidate_cache=true")
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

    def test_clone(self):
        """Test that a clone is a new, undeployed vectorstore with the same spec, and none of the original's state."""
        service = self.ready_service("test_views_clone")
        name = f"test_views_clone_copy_{self.hash_suffix}"
        response = self.client.post(url(Names.listview_api_clone, vectorstore_id=service.vectorstore.pk, new_name=name))
        self.assertEqual(response.status_code, 200, response.content)
        clone = VectorstoreMeta.objects.get(name=name)
        self.addCleanup(clone.delete)
        self.assertEqual(clone.status, "pending")
        self.assertEqual(
            (clone.index_name, clone.endpoint_url, clone.deployed_at, clone.api_key_secret), ("", "", None, None)
        )
        self.assertEqual(clone.spec["embeddings"], service.vectorstore.spec["embeddings"])
        conflict = self.client.post(url(Names.listview_api_clone, vectorstore_id=service.vectorstore.pk, new_name=name))
        self.assertEqual(conflict.status_code, 409)

    def test_rename(self):
        vectorstore = self.new_vectorstore("test_views_rename")
        kubernetes_name = vectorstore.kubernetes_name
        name = f"test_views_renamed_{self.hash_suffix}"
        response = self.client.post(url(Names.listview_api_rename, vectorstore_id=vectorstore.pk, new_name=name))
        self.assertEqual(response.status_code, 200, response.content)
        vectorstore.refresh_from_db()
        self.assertEqual((vectorstore.name, vectorstore.kubernetes_name), (name, kubernetes_name))

    def test_delete(self):
        """Test that delete destroys a deployed database, and refuses a protected one."""
        service = self.ready_service("test_views_delete")
        response = self.client.post(url(Names.listview_api_delete, vectorstore_id=service.vectorstore.pk))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(VectorstoreMeta.objects.filter(pk=service.vectorstore.pk).exists())
        self.assertIn("persistentvolumeclaim", self.kubernetes.deleted[-1][0])

        protected = self.new_vectorstore("test_views_protected")
        VectorstoreMeta.objects.filter(pk=protected.pk).update(deletion_protection=True)
        response = self.client.post(url(Names.listview_api_delete, vectorstore_id=protected.pk))
        self.assertEqual(response.status_code, 400)
        self.assertIn("deletionProtection", response.json()["error"])
        self.assertTrue(VectorstoreMeta.objects.filter(pk=protected.pk).exists())

    def test_detail_view(self):
        """Test that the detail view renders the vectorstore's manifest."""
        vectorstore = self.new_vectorstore("test_views_detail")
        response = self.client.get(url(Names.detailview, hashed_id=vectorstore.hashed_id))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(vectorstore.name, content)
        self.assertIn("vectorstoreStatus", content)

    def test_detail_view_shared_with_non_admin(self):
        """Test that a non-admin user sees the detail view of a vectorstore owned by the account's admin."""
        vectorstore = self.new_vectorstore("test_views_detail_shared")
        self.client.force_login(self.non_admin_user)
        response = self.client.get(url(Names.detailview, hashed_id=vectorstore.hashed_id))
        self.assertEqual(response.status_code, 200)
        self.assertIn(vectorstore.name, response.content.decode())

    def test_detail_view_unknown_id(self):
        """Test that a valid hashed id of a vectorstore that doesn't exist is not found, as is an invalid one."""
        response = self.client.get(url(Names.detailview, hashed_id=VectorstoreMeta(id=999999999).hashed_id))
        self.assertEqual(response.status_code, 404)
        response = self.client.get(url(Names.detailview, hashed_id="not-a-hash"))
        self.assertEqual(response.status_code, 404)
