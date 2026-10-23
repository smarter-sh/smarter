"""Test the cached pages of the list apis, :mod:`smarter.lib.django.listview`."""

import copy
from http import HTTPStatus
from unittest.mock import patch

from django.db import connection, transaction
from django.db.models.signals import m2m_changed, post_save
from django.test import Client, RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from smarter.apps.account.models import UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.connection.models import ApiConnection
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.tests.base_classes import GUARDRAIL_DEFAULTS
from smarter.apps.guardrail.urls import GuardrailReverseNames
from smarter.apps.guardrail.views.listview.api import GuardrailListApiView
from smarter.common.conf import smarter_settings
from smarter.lib import json
from smarter.lib.django.listview import (
    LISTVIEW_CACHE_ALL,
    ListviewPageRequest,
    connect_listview_cache,
    invalidate_listview_cache,
    listview_cache_generation,
)
from smarter.lib.drf.views.listview.api import AuthTokenListApiView

TEST_KIND = "TestListviewKind"
"""A list that no app connects, so that only these tests change its generation."""


class TestListviewPageRequest(TestAccountMixin):
    """Test the request that a cached list page is serialized with."""

    def test_has_the_user_and_the_platform_host(self):
        """It has the user, and the platform's host and scheme, so that a file field's url is absolute."""
        request = ListviewPageRequest(self.user_profile.user)
        self.assertEqual(request.user, self.user_profile.user)
        self.assertEqual(
            request.build_absolute_uri("/media/provider/provider_logos/logo.png"),
            f"{smarter_settings.environment_url.rstrip('/')}/media/provider/provider_logos/logo.png",
        )


class TestListviewCacheGeneration(TestAccountMixin):
    """Test the generations that make a list's cached pages stale."""

    def test_stable_until_invalidated(self):
        """A generation stays the same until it is invalidated, and then changes."""
        generation = listview_cache_generation(TEST_KIND, None)
        self.assertEqual(listview_cache_generation(TEST_KIND, None), generation)
        listview_cache_generation.invalidate(TEST_KIND, None)
        self.assertNotEqual(listview_cache_generation(TEST_KIND, None), generation)

    def test_user_generation_is_separate(self):
        """Invalidating a user's generation of a list leaves the list's own generation alone."""
        generation = listview_cache_generation(TEST_KIND, None)
        user_generation = listview_cache_generation(TEST_KIND, self.user_profile.id)
        listview_cache_generation.invalidate(TEST_KIND, self.user_profile.id)
        self.assertEqual(listview_cache_generation(TEST_KIND, None), generation)
        self.assertNotEqual(listview_cache_generation(TEST_KIND, self.user_profile.id), user_generation)

    def test_invalidate_waits_for_the_commit(self):
        """Invalidate_listview_cache() changes the generation only once the transaction commits."""
        generation = listview_cache_generation(TEST_KIND, None)
        with transaction.atomic():
            invalidate_listview_cache(TEST_KIND)
            self.assertEqual(listview_cache_generation(TEST_KIND, None), generation)
        self.assertNotEqual(listview_cache_generation(TEST_KIND, None), generation)


class TestConnectListviewCache(TestAccountMixin):
    """Test connect_listview_cache(), which invalidates a list when the models that it shows change."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connect_listview_cache(TEST_KIND, "connection.ConnectionBase")

    def test_subclasses_are_connected(self):
        """A multi-table child, e.g. ApiConnection, is connected too, since it sends post_save as itself."""
        dispatch_uid = f"smarter.lib.django.listview.{TEST_KIND}.connection.ApiConnection.post_save"
        lookup_keys = [lookup_key for lookup_key, *_ in post_save.receivers]
        self.assertTrue(any(key[0] == dispatch_uid for key in lookup_keys), dispatch_uid)

    def test_m2m_changed_invalidates_after_the_change(self):
        """M2m_changed invalidates the list on its post_ actions, not its pre_ ones, also for a subclass."""
        generation = listview_cache_generation(TEST_KIND, None)
        m2m_changed.send(sender=ApiConnection, instance=None, action="pre_add", reverse=False, model=None, pk_set=set())
        self.assertEqual(listview_cache_generation(TEST_KIND, None), generation)
        m2m_changed.send(
            sender=ApiConnection, instance=None, action="post_add", reverse=False, model=None, pk_set=set()
        )
        self.assertNotEqual(listview_cache_generation(TEST_KIND, None), generation)

    def test_profile_change_invalidates_every_list(self):
        """Saving a user profile invalidates every list, since it can change what any user sees."""
        generation = listview_cache_generation(LISTVIEW_CACHE_ALL, None)
        UserProfile.objects.get(pk=self.user_profile.pk).save()
        self.assertNotEqual(listview_cache_generation(LISTVIEW_CACHE_ALL, None), generation)


class TestSmarterListApiView(TestAccountMixin):
    """Test SmarterListApiView, with the Guardrail list api."""

    def setUp(self):
        super().setUp()
        self.guardrail = Guardrail.objects.create(
            name="test_listview_guardrail", user_profile=self.user_profile, **copy.deepcopy(GUARDRAIL_DEFAULTS)
        )
        self.addCleanup(Guardrail.objects.filter(pk=self.guardrail.pk).delete)
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def listed(self, ownership_filter: str = "owned", **params) -> dict:
        """Return the Guardrail list api's response, for the admin user."""
        url = reverse(
            f"{GuardrailReverseNames.namespace}:{GuardrailReverseNames.listview_api}",
            kwargs={"ownership_filter": ownership_filter},
        )
        if params:
            url += "?" + "&".join(f"{key}={value}" for key, value in params.items())
        response = self.client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        return json.loads(response.content)

    def names(self, data: dict) -> list[str]:
        """Return the names of a response's objects."""
        return [item["name"] for item in data["objects"]]

    def test_page_is_cached(self):
        """The second request for the same page is served from the cache, without building it."""
        with patch.object(GuardrailListApiView, "build_page", wraps=GuardrailListApiView.build_page) as build:
            first = self.listed()
            second = self.listed()
        self.assertEqual(build.call_count, 1)
        self.assertEqual(first, second)
        self.assertIn(self.guardrail.name, self.names(first))
        self.assertEqual(set(first), {"user", "admin", "objects", "pagination"})

    def test_every_page_is_cached_apart(self):
        """Each page, search and ordering is a page of its own in the cache."""
        with patch.object(GuardrailListApiView, "build_page", wraps=GuardrailListApiView.build_page) as build:
            self.listed()
            self.listed(search="no_such_guardrail")
            self.listed(ordering="-name")
        self.assertEqual(build.call_count, 3)

    def test_save_makes_the_page_stale(self):
        """Saving a resource that the list shows makes its cached pages stale."""
        self.listed()
        self.guardrail.description = "A description changed by test_save_makes_the_page_stale."
        self.guardrail.save()
        item = next(item for item in self.listed()["objects"] if item["name"] == self.guardrail.name)
        self.assertEqual(item["description"], self.guardrail.description)

    def test_delete_makes_the_page_stale(self):
        """Deleting a resource that the list shows makes its cached pages stale."""
        self.assertIn(self.guardrail.name, self.names(self.listed()))
        Guardrail.objects.filter(pk=self.guardrail.pk).delete()
        self.assertNotIn(self.guardrail.name, self.names(self.listed()))

    def test_invalidate_cache_rebuilds_the_page(self):
        """?invalidate_cache=true, the list's Refresh button, builds the user's page again."""
        self.listed()
        with patch.object(GuardrailListApiView, "build_page", wraps=GuardrailListApiView.build_page) as build:
            self.listed(invalidate_cache="true")
        self.assertEqual(build.call_count, 1)

    def test_update_is_not_seen_until_invalidated(self):
        """A QuerySet.update() sends no signal: the page is stale until the list is invalidated."""
        self.listed()
        Guardrail.objects.filter(pk=self.guardrail.pk).update(description="Changed by update().")
        item = next(item for item in self.listed()["objects"] if item["name"] == self.guardrail.name)
        self.assertNotEqual(item["description"], "Changed by update().")
        invalidate_listview_cache("Guardrail")
        item = next(item for item in self.listed()["objects"] if item["name"] == self.guardrail.name)
        self.assertEqual(item["description"], "Changed by update().")

    def test_pages_are_per_user(self):
        """A user never gets another user's cached page."""
        self.assertIn(self.guardrail.name, self.names(self.listed("owned")))
        self.client.force_login(self.non_admin_user)
        self.assertNotIn(self.guardrail.name, self.names(self.listed("owned")))

    def test_invalid_ownership_filter(self):
        """An unknown ownership filter is a bad request."""
        request = RequestFactory().post("/")
        request.user = self.admin_user
        view = GuardrailListApiView()
        view.setup(request)
        response = view.post(request, ownership_filter="everything")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_queryset_fetches_owner_and_tags(self):
        """The queryset joins the owner, and prefetches the tags of a model whose tags are a relation."""
        queryset = GuardrailListApiView.get_queryset(self.admin_user, "owned")
        self.assertIn("user_profile", queryset.query.select_related)
        self.assertIn("tags", queryset._prefetch_related_lookups)  # pylint: disable=W0212

    def test_queryset_without_tag_relation(self):
        """SmarterAuthToken's tags are a JSON list, which isn't prefetched."""
        queryset = AuthTokenListApiView.get_queryset(self.admin_user, "all")
        self.assertNotIn("tags", queryset._prefetch_related_lookups)  # pylint: disable=W0212

    def test_page_costs_few_queries(self):
        """A page of many resources costs a fixed number of queries, not a few per resource."""
        for i in range(5):
            guardrail = Guardrail.objects.create(
                name=f"test_listview_guardrail_{i}", user_profile=self.user_profile, **copy.deepcopy(GUARDRAIL_DEFAULTS)
            )
            self.addCleanup(Guardrail.objects.filter(pk=guardrail.pk).delete)
        with CaptureQueriesContext(connection) as few:
            self.listed(page_size="2", invalidate_cache="true")
        with CaptureQueriesContext(connection) as many:
            self.listed(page_size="6", invalidate_cache="true")
        # each owned guardrail still asks once whether an LLMClient uses it (see user_can_delete).
        self.assertLessEqual(len(many.captured_queries) - len(few.captured_queries), 4)
