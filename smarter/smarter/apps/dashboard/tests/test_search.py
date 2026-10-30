"""Test the dashboard's global search, :mod:`smarter.apps.dashboard.search` and its api view."""

import copy
from http import HTTPStatus
from unittest.mock import patch

from django.test import Client
from django.urls import reverse

from smarter.apps.account.models import Account
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.search import (
    MAX_RESULTS_PER_LIST,
    GlobalSearchResponse,
    global_search,
    list_url,
    parse_query,
    result_of,
)
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.tests.base_classes import GUARDRAIL_DEFAULTS
from smarter.lib import json
from smarter.lib.django.listview import listview_registry

from ..const import namespace


class TestParseQuery(TestAccountMixin):
    """Test how a query is understood."""

    def test_modes(self):
        """Text, a tag, an annotation requirement, and text that only looks like one."""
        cases = (
            ("  support ", ("text", "support", "")),
            ("tag: production", ("tag", "production", "")),
            ("TAG:production", ("tag", "production", "")),
            ("acme.com/crm-id", ("annotation", "acme.com/crm-id", "")),
            ("acme.com/crm-id=A 1", ("annotation", "acme.com/crm-id=A 1", "")),
            ("!acme.com/archived", ("annotation", "!acme.com/archived", "")),
            ("acme.com/crm-id!=A", ("annotation", "acme.com/crm-id!=A", "")),
            ("https://example.com/a", ("text", "https://example.com/a", "")),
            ("two words/here", ("text", "two words/here", "")),
        )
        for query, expected in cases:
            with self.subTest(query=query):
                self.assertEqual(parse_query(query), expected)

    def test_invalid_requirement(self):
        """Text with '=' or a leading '!' is a requirement, and an invalid one is an error."""
        mode, value, error = parse_query("Bad Key=x")
        self.assertEqual((mode, value), ("annotation", "Bad Key=x"))
        self.assertIn("Bad Key", error)


class TestGlobalSearch(TestAccountMixin):
    """Test global_search() with Guardrails, which the user owns and another account's user doesn't see."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tag = f"search_tag_{cls.hash_suffix}"
        cls.key = f"search-{cls.hash_suffix}.example.com/team"
        cls.guardrails = []
        for index in range(MAX_RESULTS_PER_LIST + 1):
            guardrail = Guardrail.objects.create(
                name=f"test_search_{cls.hash_suffix}_{index}",
                user_profile=cls.user_profile,
                **{**copy.deepcopy(GUARDRAIL_DEFAULTS), "description": f"Searchable guardrail {index}"},
            )
            guardrail.tags.add(cls.tag)
            guardrail.set_annotation(cls.key, "even" if index % 2 == 0 else "odd")
            cls.guardrails.append(guardrail)
        cls.other_user, cls.other_account, cls.other_profile = mortal_user_factory()

    @classmethod
    def tearDownClass(cls):
        Guardrail.objects.filter(pk__in=[guardrail.pk for guardrail in cls.guardrails]).delete()
        cls.other_profile.delete()
        cls.other_user.delete()
        Account.objects.filter(pk=cls.other_account.pk).delete()
        super().tearDownClass()

    def guardrails_group(self, response: GlobalSearchResponse):
        """The Guardrails group of a response, or None."""
        return next((group for group in response.groups if group.label == "Guardrails"), None)

    def test_text(self):
        """Text matches names and descriptions, a few results per list, with a link to the narrowed list."""
        response = global_search(self.admin_user, f"test_search_{self.hash_suffix}")
        group = self.guardrails_group(response)
        assert group is not None
        self.assertEqual((response.mode, group.count), ("text", MAX_RESULTS_PER_LIST + 1))
        self.assertEqual(len(group.results), MAX_RESULTS_PER_LIST)
        self.assertEqual(group.url, f"/guardrail/?search=test_search_{self.hash_suffix}")
        self.assertTrue(all(result.url.startswith("/guardrail/guardrails/") for result in group.results))
        self.assertEqual(response.count, sum(group.count for group in response.groups))

    def test_text_matches_a_tag(self):
        """Text that is a tag's name finds the resources with the tag."""
        group = self.guardrails_group(global_search(self.admin_user, self.tag))
        self.assertEqual(group.count if group else 0, MAX_RESULTS_PER_LIST + 1)

    def test_tag(self):
        """Tag:<name> finds the resources with the tag, and links to the list narrowed by it."""
        response = global_search(self.admin_user, f"tag:{self.tag}")
        group = self.guardrails_group(response)
        assert group is not None
        self.assertEqual((response.mode, group.count), ("tag", MAX_RESULTS_PER_LIST + 1))
        self.assertEqual(group.url, f"/guardrail/?tag={self.tag}")

    def test_annotation(self):
        """An annotation requirement finds the resources that match it."""
        response = global_search(self.admin_user, f"{self.key}=odd")
        group = self.guardrails_group(response)
        assert group is not None
        self.assertEqual((response.mode, group.count), ("annotation", (MAX_RESULTS_PER_LIST + 1) // 2))
        self.assertIn("annotation=", group.url)

    def test_another_account_finds_nothing(self):
        """A user of another account doesn't find the user's resources."""
        self.assertIsNone(self.guardrails_group(global_search(self.other_user, f"tag:{self.tag}")))

    def test_empty_and_invalid_queries(self):
        """An empty query searches nothing, and an invalid requirement is reported."""
        self.assertEqual(global_search(self.admin_user, "   ").groups, [])
        response = global_search(self.admin_user, "Bad Key=x")
        self.assertEqual(response.groups, [])
        self.assertIn("Bad Key", response.error)

    def test_a_failing_list_is_skipped(self):
        """One list's failure is logged, and doesn't hide the other lists' results."""
        entries = listview_registry()
        guardrails = next(entry for entry in entries if entry.label == "Guardrails")
        broken = next(entry for entry in entries if entry.label == "Secrets")
        with patch.object(broken.view_class, "get_queryset", side_effect=RuntimeError("broken")):
            response = global_search(self.admin_user, f"tag:{self.tag}", entries=(broken, guardrails))
        self.assertEqual([group.label for group in response.groups], ["Guardrails"])

    def test_result_of(self):
        """A result links to the serializer's manifest url, in either case, or else to its list."""
        self.assertEqual(result_of({"name": "a", "manifest_url": "/a/"}, "/list/").url, "/a/")
        self.assertEqual(result_of({"name": "a", "manifestUrl": "/b/"}, "/list/").url, "/b/")
        self.assertEqual(
            result_of({"name": "a", "description": None}, "/list/").model_dump(),
            {
                "name": "a",
                "description": "",
                "url": "/list/",
            },
        )
        entry = listview_registry()[0]
        self.assertEqual(list_url(entry, "annotation", "a/b=c"), f"{entry.page_url}?annotation=a%2Fb%3Dc")


class TestGlobalSearchView(TestAccountMixin):
    """Test GlobalSearchView, the api of the dashboard's search box."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)
        self.url = reverse(f"{namespace}:{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.global_search}")

    def test_post_and_get(self):
        """The query is read from a json body, or the query parameter of a GET, and answered camelCase."""
        response = self.client.post(self.url, data={"query": "tag:no_such_tag"}, content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        data = json.loads(response.content)
        self.assertEqual(set(data), {"query", "mode", "error", "count", "groups"})
        self.assertEqual((data["mode"], data["query"], data["groups"]), ("tag", "no_such_tag", []))
        response = self.client.get(self.url, {"query": "Bad Key=x"})
        self.assertIn("Bad Key", json.loads(response.content)["error"])

    def test_malformed_body(self):
        """A body that isn't a json object searches the query parameter instead."""
        response = self.client.post(f"{self.url}?query=tag:x", data="not json", content_type="application/json")
        self.assertEqual(json.loads(response.content)["query"], "x")
        response = self.client.post(self.url, data=["a list"], content_type="application/json")
        self.assertEqual(json.loads(response.content)["query"], "")

    def test_requires_login(self):
        """An anonymous request is refused."""
        self.client.logout()
        response = self.client.post(self.url, data={"query": "x"}, content_type="application/json")
        self.assertNotEqual(response.status_code, HTTPStatus.OK)
