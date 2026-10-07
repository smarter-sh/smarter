"""
A test mixin for the /api/v1/<resources>/ REST api that the vectorsearch and orchestrator apps repeat: a list view, a detail view by hashed id or by id, and the resource's default api view.

A subclass names the app's model, reverse names and url parameter, and creates the resource::

    class TestVectorsearchApi(ResourceApiTestMixin, ApiV1TestBase):
        model = Vectorsearch
        reverse_names = VectorsearchApiV1ReverseViews
        list_view = "vectorsearch_list_view"
        view_by_hashed_id = "vectorsearch_view_by_hashed_id"
        view_by_id = "vectorsearch_view_by_id"
        default_api_by_hashed_id = "default_vectorsearch_api_view_by_hashed_id"
        id_kwarg = "vectorsearch_id"

The requests authenticate with a session of the account's admin, who is a superuser.
test_list_with_api_key authenticates with the api key of ApiV1TestBase instead.
"""

from http import HTTPStatus

from django.db import models
from django.urls import reverse
from rest_framework.test import APIClient

from smarter.lib import json


class ResourceApiTestMixin:
    """Test the list, detail and default api views of a resource's /api/v1/ endpoints."""

    model: type[models.Model]
    reverse_names: type
    list_view: str
    view_by_hashed_id: str
    view_by_id: str
    default_api_by_hashed_id: str
    id_kwarg: str
    resource_name_prefix = "test_resource_api"

    @classmethod
    def create_resource(cls, name: str) -> models.Model:
        raise NotImplementedError

    def setUp(self):
        super().setUp()  # type: ignore[misc]
        self.api_client = APIClient()
        self.api_client.force_login(self.admin_user)  # type: ignore[attr-defined]
        self.addCleanup(self.api_client.logout)
        name = f"{self.resource_name_prefix}_{self.hash_suffix}"  # type: ignore[attr-defined]
        self.addCleanup(self.model.objects.filter(name__startswith=name).delete)  # type: ignore[attr-defined]
        self.resource = self.create_resource(name)

    def url(self, name: str, **kwargs) -> str:
        return reverse(f"{self.reverse_names.namespace}:{name}", kwargs=kwargs or None)

    def detail_urls(self) -> dict[str, str]:
        return {
            "by hashed id": self.url(self.view_by_hashed_id, hashed_id=self.resource.hashed_id),  # type: ignore[attr-defined]
            "by id": self.url(self.view_by_id, **{self.id_kwarg: self.resource.pk}),
        }

    def test_list(self):
        """Test that the list view returns the resource."""
        response = self.api_client.get(self.url(self.list_view))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])  # type: ignore[attr-defined]
        self.assertIn(self.resource.name, json.dumps(response.json()))  # type: ignore[attr-defined]

    def test_list_with_api_key(self):
        """Test that the list view accepts the api key of a superuser."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_key}")  # type: ignore[attr-defined]
        response = client.get(self.url(self.list_view))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])  # type: ignore[attr-defined]

    def test_list_anonymous(self):
        response = APIClient().get(self.url(self.list_view))
        self.assertIn(response.status_code, (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN))  # type: ignore[attr-defined]

    def test_get(self):
        """Test that the detail view returns the resource, by hashed id and by id."""
        for label, url in self.detail_urls().items():
            with self.subTest(url=label):  # type: ignore[attr-defined]
                response = self.api_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])  # type: ignore[attr-defined]
                self.assertEqual(response.json()["name"], self.resource.name)  # type: ignore[attr-defined]

    def test_get_not_found(self):
        response = self.api_client.get(self.url(self.view_by_hashed_id, hashed_id=self.model(id=999999999).hashed_id))  # type: ignore[attr-defined]
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)  # type: ignore[attr-defined]

    def test_post_invalid(self):
        """Test that a POST whose data is not the model's fields is refused."""
        response = self.api_client.post(self.url(self.list_view) + "0/", data={"no_such_field": 1}, format="json")
        self.assertIn(response.status_code, (HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND))  # type: ignore[attr-defined]

    def test_patch(self):
        """Test that a PATCH updates the resource's description."""
        url = self.detail_urls()["by hashed id"]
        response = self.api_client.patch(url, data={"description": "patched"}, format="json")
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:500])  # type: ignore[attr-defined]
        self.assertEqual(self.model.objects.get(pk=self.resource.pk).description, "patched")  # type: ignore[attr-defined]

    def test_delete(self):
        """Test that a DELETE deletes the resource."""
        response = self.api_client.delete(self.detail_urls()["by hashed id"])
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:500])  # type: ignore[attr-defined]
        self.assertFalse(self.model.objects.filter(pk=self.resource.pk).exists())  # type: ignore[attr-defined]

    def test_default_api_get_and_options(self):
        """Test that the default api refuses a GET, and answers an OPTIONS with its CORS headers."""
        url = self.url(self.default_api_by_hashed_id, hashed_id=self.resource.hashed_id)  # type: ignore[attr-defined]
        self.assertEqual(self.api_client.get(url).status_code, HTTPStatus.METHOD_NOT_ALLOWED)  # type: ignore[attr-defined]
        response = self.api_client.options(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)  # type: ignore[attr-defined]
        self.assertIn("POST", response["Access-Control-Allow-Methods"])  # type: ignore[attr-defined]
