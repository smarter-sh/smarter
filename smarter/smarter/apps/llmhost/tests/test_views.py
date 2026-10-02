"""Test the dashboard views: :mod:`smarter.apps.llmhost.views`."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.llmhost.models import LLMHost
from smarter.apps.llmhost.urls import LLMHostReverseNames as Names
from smarter.lib import json

from .base_classes import LLMHostTestBase


def url(name: str, **kwargs) -> str:
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs)


class TestLLMHostListViews(LLMHostTestBase):
    """Test the React list view's api: list, clone, rename and delete."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def post(self, path: str, status: int = HTTPStatus.OK) -> dict:
        response = self.client.post(path)
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content)

    def test_list(self):
        llmhost = self.new_llmhost("test_views_list")
        data = self.post(url(Names.listview_api_all) + "?invalidate_cache=true")
        self.assertIn(llmhost.name, [item["name"] for item in data["objects"]])
        owned = self.post(url(Names.listview_api, ownership_filter="owned") + "?invalidate_cache=true")
        self.assertIn(llmhost.name, [item["name"] for item in owned["objects"]])

    def test_clone_rename_delete(self):
        """Test that the list view's actions find the LLMHost by its llmhost_id."""
        llmhost = self.new_llmhost("test_views_original")
        clone = self.post(url(Names.listview_api_clone, llmhost_id=llmhost.pk, new_name="test_views_clone"))
        self.addCleanup(LLMHost.objects.filter(name="test_views_clone").delete)
        self.assertEqual(LLMHost.objects.get(pk=clone["id"]).spec, llmhost.spec)
        self.post(url(Names.listview_api_rename, llmhost_id=clone["id"], new_name="test_views_renamed"))
        self.addCleanup(LLMHost.objects.filter(name="test_views_renamed").delete)
        self.assertEqual(LLMHost.objects.get(pk=clone["id"]).name, "test_views_renamed")
        self.post(url(Names.listview_api_delete, llmhost_id=clone["id"]))
        self.assertFalse(LLMHost.objects.filter(pk=clone["id"]).exists())
        self.post(url(Names.listview_api_delete, llmhost_id=clone["id"]), status=HTTPStatus.NOT_FOUND)
