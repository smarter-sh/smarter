"""Test the dashboard views: :mod:`smarter.apps.llmhost.views`."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.llmhost.api.web.urls import LLMHostApiWebReverseNames as WebNames
from smarter.apps.llmhost.caching import (
    invalidate_all_cached_llmhost_computes_for_user_profile,
    invalidate_all_cached_llmhosts_for_user_profile,
)
from smarter.apps.llmhost.manifest.brokers.llmhost_compute import (
    compute_spec_to_django_orm,
)
from smarter.apps.llmhost.manifest.models.llmhost_compute.spec import (
    SAMLLMHostComputeSpec,
)
from smarter.apps.llmhost.models import LLMHost, LLMHostCompute
from smarter.apps.llmhost.urls import LLMHostReverseNames as Names
from smarter.lib import json
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.resource_views import (
    ResourceViewsTestMixin,
    assert_console_page,
    assert_no_resource,
    resource_detail_json,
)

from .base_classes import LLMHostTestBase


def url(name: str, **kwargs) -> str:
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs)


def web_url(name: str, **kwargs) -> str:
    return reverse(f"{WebNames.namespace}:{name}", kwargs=kwargs or None)


class TestLLMHostListViews(LLMHostTestBase):
    """Test the React list view's api: list, clone, rename and delete."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def post(self, path: str, status: int = HTTPStatus.OK) -> SmarterDictType:
        response = self.client.post(path)
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content)

    def test_web_api_paths(self):
        """Test that the LLMHost and LLMHostCompute list pages' endpoints are in the web console's api."""
        self.assertEqual(web_url(WebNames.listview_all), "/api/web/llmhost/listview/")
        self.assertEqual(web_url(WebNames.listview, ownership_filter="owned"), "/api/web/llmhost/listview/owned/")
        self.assertEqual(web_url(WebNames.clone, llmhost_id=1, new_name="x"), "/api/web/llmhost/clone/1/x/")
        self.assertEqual(web_url(WebNames.rename, llmhost_id=1, new_name="x"), "/api/web/llmhost/rename/1/x/")
        self.assertEqual(web_url(WebNames.delete, llmhost_id=1), "/api/web/llmhost/delete/1/")
        self.assertEqual(web_url(WebNames.compute_listview_all), "/api/web/llmhost/compute/listview/")
        self.assertEqual(
            web_url(WebNames.compute_listview, ownership_filter="owned"), "/api/web/llmhost/compute/listview/owned/"
        )
        self.assertEqual(
            web_url(WebNames.compute_clone, llmhost_compute_id=1, new_name="x"), "/api/web/llmhost/compute/clone/1/x/"
        )
        self.assertEqual(
            web_url(WebNames.compute_rename, llmhost_compute_id=1, new_name="x"),
            "/api/web/llmhost/compute/rename/1/x/",
        )
        self.assertEqual(web_url(WebNames.compute_delete, llmhost_compute_id=1), "/api/web/llmhost/compute/delete/1/")

    def test_list(self):
        llmhost = self.new_llmhost("test_views_list")
        data = self.post(web_url(WebNames.listview_all) + "?invalidate_cache=true")
        self.assertIn(llmhost.name, [item["name"] for item in data["objects"]])
        owned = self.post(web_url(WebNames.listview, ownership_filter="owned") + "?invalidate_cache=true")
        self.assertIn(llmhost.name, [item["name"] for item in owned["objects"]])

    def test_clone_rename_delete(self):
        """Test that the list view's actions find the LLMHost by its llmhost_id."""
        llmhost = self.new_llmhost("test_views_original")
        clone = self.post(web_url(WebNames.clone, llmhost_id=llmhost.pk, new_name="test_views_clone"))
        self.addCleanup(LLMHost.objects.filter(name="test_views_clone").delete)
        self.assertEqual(LLMHost.objects.get(pk=clone["id"]).spec, llmhost.spec)
        self.post(web_url(WebNames.rename, llmhost_id=clone["id"], new_name="test_views_renamed"))
        self.addCleanup(LLMHost.objects.filter(name="test_views_renamed").delete)
        self.assertEqual(LLMHost.objects.get(pk=clone["id"]).name, "test_views_renamed")
        self.post(web_url(WebNames.delete, llmhost_id=clone["id"]))
        self.assertFalse(LLMHost.objects.filter(pk=clone["id"]).exists())
        self.post(web_url(WebNames.delete, llmhost_id=clone["id"]), status=HTTPStatus.NOT_FOUND)


class TestLLMHostComputeListViews(LLMHostTestBase):
    """Test the LLMHostCompute React list page, and its api: list, clone, rename and delete."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def post(self, path: str, status: int = HTTPStatus.OK) -> SmarterDictType:
        response = self.client.post(path)
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content)

    def own_compute(self, name: str) -> LLMHostCompute:
        """An LLMHostCompute of the test user, without a node group, deleted when the test ends."""
        spec = SAMLLMHostComputeSpec.model_validate(
            {
                "node": {"instanceType": "g6.2xlarge", "cpu": 8, "memoryGb": 32},
                "nodeGroup": {"maxNodes": 2},
                "cost": {"perHour": "1.0"},
            }
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
        data = self.post(web_url(WebNames.compute_listview_all) + "?invalidate_cache=true")
        self.assertIn(compute.name, [item["name"] for item in data["objects"]])
        for ownership_filter in ("owned", "shared", "all"):
            with self.subTest(ownership_filter=ownership_filter):
                self.post(web_url(WebNames.compute_listview, ownership_filter=ownership_filter))
        self.assertEqual(self.client.get(web_url(WebNames.compute_listview_all)).status_code, HTTPStatus.OK)

    def test_clone_rename_delete(self):
        """Test that the list view's actions find the LLMHostCompute by its llmhost_compute_id."""
        compute = self.own_compute("test_views_compute")
        clone_name = f"{compute.name}_clone"
        clone = self.post(web_url(WebNames.compute_clone, llmhost_compute_id=compute.pk, new_name=clone_name))
        clone_pk = LLMHostCompute.objects.get(name=clone_name, user_profile=self.user_profile).pk
        self.assertEqual(clone["name"], clone_name)
        renamed = f"{compute.name}_renamed"
        self.post(web_url(WebNames.compute_rename, llmhost_compute_id=clone_pk, new_name=renamed))
        self.assertEqual(LLMHostCompute.objects.get(pk=clone_pk).name, renamed)
        self.post(web_url(WebNames.compute_delete, llmhost_compute_id=clone_pk))
        self.assertFalse(LLMHostCompute.objects.filter(pk=clone_pk).exists())
        for name, kwargs in (
            (WebNames.compute_delete, {}),
            (WebNames.compute_rename, {"new_name": "x"}),
            (WebNames.compute_clone, {"new_name": "x"}),
        ):
            with self.subTest(view=name):
                self.post(web_url(name, llmhost_compute_id=999999999, **kwargs), status=HTTPStatus.NOT_FOUND)


class TestLLMHostDetailViews(LLMHostTestBase):
    """Test the LLMHost and LLMHostCompute manifest detail pages."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def test_llmhost_detail(self):
        """Test that the LLMHost's manifest page is the console's, whose resource api returns its manifest."""
        llmhost = self.new_llmhost("test_views_detail")
        detail = resource_detail_json(self, llmhost.record_locator)
        self.assertEqual(detail["kind"], "LLMHost")
        self.assertEqual(detail["name"], llmhost.name)
        self.assertIn(llmhost.name, detail["manifest"] or "")
        assert_console_page(self, url(Names.detailview, hashed_id=llmhost.hashed_id))

    def test_compute_detail(self):
        """Test that the LLMHostCompute's manifest page is the console's, whose resource api returns its manifest."""
        compute = TestLLMHostComputeListViews.own_compute(self, "test_views_compute_detail")
        detail = resource_detail_json(self, compute.record_locator)
        self.assertEqual(detail["kind"], "LLMHostCompute")
        self.assertEqual(detail["name"], compute.name)
        self.assertIn(compute.name, detail["manifest"] or "")
        assert_console_page(self, url(Names.compute_detailview, hashed_id=compute.hashed_id))

    def test_detail_not_found(self):
        """Test that the resource api has no LLMHost or LLMHostCompute for an invalid, or unknown, id."""
        for model in (LLMHost, LLMHostCompute):
            with self.subTest(model=model.__name__):
                unknown = model(id=999999999)
                prefix = unknown.record_locator.partition("-")[0]
                assert_no_resource(self, f"{prefix}-not-a-hashed-id")
                assert_no_resource(self, unknown.record_locator)


class TestLLMHostResourceViews(ResourceViewsTestMixin, LLMHostTestBase):
    """Test the LLMHost list page, list, clone, delete and rename apis, and detail page with the shared mixin."""

    model = LLMHost
    reverse_names = Names
    web_reverse_names = WebNames
    id_kwarg = "llmhost_id"
    invalidate_cache = staticmethod(invalidate_all_cached_llmhosts_for_user_profile)
    resource_name_prefix = "test_llmhost_views"

    @classmethod
    def create_resource(cls, name: str) -> LLMHost:
        return cls.create_llmhost(name)


class LLMHostComputeReverseNames:
    """The LLMHostCompute console page names, as ResourceViewsTestMixin names them."""

    namespace = Names.namespace
    listview = Names.compute_listview
    detailview = Names.compute_detailview


class LLMHostComputeApiWebReverseNames:
    """The LLMHostCompute web console api names, as ResourceViewsTestMixin names them."""

    namespace = WebNames.namespace
    listview = WebNames.compute_listview
    listview_all = WebNames.compute_listview_all
    clone = WebNames.compute_clone
    delete = WebNames.compute_delete
    rename = WebNames.compute_rename


class TestLLMHostComputeResourceViews(ResourceViewsTestMixin, LLMHostTestBase):
    """Test the LLMHostCompute list page, list, clone, delete and rename apis, and detail page with the shared mixin."""

    model = LLMHostCompute
    reverse_names = LLMHostComputeReverseNames
    web_reverse_names = LLMHostComputeApiWebReverseNames
    id_kwarg = "llmhost_compute_id"
    invalidate_cache = staticmethod(invalidate_all_cached_llmhost_computes_for_user_profile)
    resource_name_prefix = "test_compute_views"

    @classmethod
    def create_resource(cls, name: str) -> LLMHostCompute:
        """An LLMHostCompute without a node group."""
        spec = SAMLLMHostComputeSpec.model_validate(
            {
                "node": {"instanceType": "g6.2xlarge", "cpu": 8, "memoryGb": 32},
                "nodeGroup": {"maxNodes": 2},
                "cost": {"perHour": "1.0"},
            }
        )
        return LLMHostCompute.objects.create(
            name=name, user_profile=cls.user_profile, **compute_spec_to_django_orm(spec)
        )
