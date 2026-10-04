"""Test the dashboard views: :mod:`smarter.apps.llmhost.views`."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.llmhost.manifest.brokers.llmhost_compute import (
    compute_spec_to_django_orm,
)
from smarter.apps.llmhost.manifest.models.llmhost_compute.spec import (
    SAMLLMHostComputeSpec,
)
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute
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


class TestLLMHostComputeListViews(LLMHostTestBase):
    """Test the LLMHostCompute React list page, and its api: list, clone, rename and delete."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def post(self, path: str, status: int = HTTPStatus.OK) -> dict:
        response = self.client.post(path)
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content)

    def own_compute(self, name: str) -> LLMHostCompute:
        """An LLMHostCompute of the test user, without a node group, deleted when the test ends."""
        spec = SAMLLMHostComputeSpec(
            node={"instanceType": "g6.2xlarge", "cpu": 8, "memoryGb": 32},
            nodeGroup={"maxNodes": 2},
            cost={"perHour": "1.0"},
        )
        name = f"{name}_{self.hash_suffix}"
        self.addCleanup(LLMHostCompute.objects.filter(name__startswith=name).delete)
        return LLMHostCompute.objects.create(
            name=name, user_profile=self.user_profile, **compute_spec_to_django_orm(spec)
        )

    def test_list_page(self):
        self.assertEqual(self.client.get(url(Names.compute_listview)).status_code, HTTPStatus.OK)

    def test_list(self):
        compute = self.own_compute("test_views_compute_list")
        data = self.post(url(Names.compute_listview_api_all) + "?invalidate_cache=true")
        self.assertIn(compute.name, [item["name"] for item in data["objects"]])
        for ownership_filter in ("owned", "shared", "all"):
            with self.subTest(ownership_filter=ownership_filter):
                self.post(url(Names.compute_listview_api, ownership_filter=ownership_filter))
        self.assertEqual(self.client.get(url(Names.compute_listview_api_all)).status_code, HTTPStatus.OK)

    def test_clone_rename_delete(self):
        """Test that the list view's actions find the LLMHostCompute by its llmhost_compute_id."""
        compute = self.own_compute("test_views_compute")
        clone_name = f"{compute.name}_clone"
        clone = self.post(url(Names.compute_listview_api_clone, llmhost_compute_id=compute.pk, new_name=clone_name))
        clone_pk = LLMHostCompute.objects.get(name=clone_name, user_profile=self.user_profile).pk
        self.assertEqual(clone["name"], clone_name)
        renamed = f"{compute.name}_renamed"
        self.post(url(Names.compute_listview_api_rename, llmhost_compute_id=clone_pk, new_name=renamed))
        self.assertEqual(LLMHostCompute.objects.get(pk=clone_pk).name, renamed)
        self.post(url(Names.compute_listview_api_delete, llmhost_compute_id=clone_pk))
        self.assertFalse(LLMHostCompute.objects.filter(pk=clone_pk).exists())
        for name, kwargs in (
            (Names.compute_listview_api_delete, {}),
            (Names.compute_listview_api_rename, {"new_name": "x"}),
            (Names.compute_listview_api_clone, {"new_name": "x"}),
        ):
            with self.subTest(view=name):
                self.post(url(name, llmhost_compute_id=999999999, **kwargs), status=HTTPStatus.NOT_FOUND)


class TestLLMHostDetailViews(LLMHostTestBase):
    """Test the LLMHost and LLMHostCompute manifest detail pages."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def test_llmhost_detail(self):
        llmhost = self.new_llmhost("test_views_detail")
        response = self.client.get(url(Names.detailview, hashed_id=llmhost.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        self.assertIn(llmhost.name.encode(), response.content)

    def test_compute_detail(self):
        compute = TestLLMHostComputeListViews.own_compute(self, "test_views_compute_detail")
        response = self.client.get(url(Names.compute_detailview, hashed_id=compute.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        self.assertIn(compute.name.encode(), response.content)

    def test_detail_not_found(self):
        for name in (Names.detailview, Names.compute_detailview):
            with self.subTest(view=name):
                for hashed_id in ("not-a-hashed-id", LLMHost(id=999999999).hashed_id):
                    response = self.client.get(url(name, hashed_id=hashed_id))
                    self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
