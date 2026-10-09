"""Test the Infrastructure Resource web console: the list view, and its API."""

import json

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.infrastructure.models import InfrastructureResource
from smarter.apps.infrastructure.urls import InfrastructureReverseNames
from smarter.apps.infrastructure.views.listview import DEFAULT_PAGE_SIZE, summary


def url(name: str) -> str:
    return reverse(f"{InfrastructureReverseNames.namespace}:{name}")


class TestInfrastructureResourceConsole(TestAccountMixin):
    """Test that superusers, and only superusers, see the ledger of cloud resources."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        name = f"test-views-{self.hash_suffix}.example.com"
        self.zone = InfrastructureResource.record_created(
            provider="test",
            service="dns",
            resource_type="dns.zone",
            resource_name=name,
            resource_id="Z1",
            billable=True,
        )
        self.record = InfrastructureResource.record_created(
            provider="test", service="dns", resource_type="dns.record", resource_name=f"www.{name} A"
        )
        InfrastructureResource.record_destroyed(
            provider="test", service="dns", resource_type="dns.record", resource_name=f"www.{name} A"
        )
        self.addCleanup(InfrastructureResource.objects.filter(provider="test").delete)

    def tearDown(self):
        self.client.logout()
        super().tearDown()

    def test_list_view(self):
        """The list view renders the React app's root element, with the list API's URL."""
        self.client.force_login(self.admin_user)
        response = self.client.get(url(InfrastructureReverseNames.listview))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("smarter-infrastructure-resource-list-root", content)
        self.assertIn(url(InfrastructureReverseNames.listview_api), content)
        # the sidebar links to the page, for superusers.
        self.assertIn(f'href="{url(InfrastructureReverseNames.listview)}"', content)

    def test_list_view_is_for_superusers(self):
        self.client.force_login(self.non_admin_user)
        response = self.client.get(url(InfrastructureReverseNames.listview))
        self.assertEqual(response.status_code, 403)

    def test_list_api(self):
        """The list API returns the ledger, newest first, and its summary."""
        self.client.force_login(self.admin_user)
        response = self.client.post(
            url(InfrastructureReverseNames.listview_api), data="{}", content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["summary"], summary())
        ours = [o for o in data["objects"] if o["provider"] == "test"]
        self.assertEqual([o["resourceType"] for o in ours], ["dns.record", "dns.zone"])
        zone = ours[1]
        self.assertEqual((zone["resourceId"], zone["billable"], zone["status"]), ("Z1", True, "active"))
        self.assertEqual(ours[0]["status"], "destroyed")
        self.assertIsNotNone(ours[0]["destroyedAt"])

    def post(self, body) -> dict:
        response = self.client.post(
            url(InfrastructureReverseNames.listview_api),
            data=body if isinstance(body, str) else json.dumps(body),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_list_api_filters(self):
        """The list API filters the whole ledger, by status, billable, provider, type and text."""
        self.client.force_login(self.admin_user)
        mine = {"provider": "test"}
        cases = (
            ({}, ["dns.record", "dns.zone"]),
            ({"status": "active"}, ["dns.zone"]),
            ({"status": "destroyed"}, ["dns.record"]),
            ({"status": "all", "billableOnly": True}, ["dns.zone"]),
            ({"resourceType": "dns.record"}, ["dns.record"]),
            ({"text": "  WWW.  "}, ["dns.record"]),
            ({"text": "z1"}, ["dns.zone"]),
            ({"text": "nothing matches this"}, []),
        )
        for body, expected in cases:
            with self.subTest(body=body):
                data = self.post({**mine, **body})
                self.assertEqual([o["resourceType"] for o in data["objects"]], expected)
                self.assertEqual(data["pagination"]["count"], len(expected))
        self.assertEqual(self.post({"provider": "nobody"})["objects"], [])

    def test_list_api_choices(self):
        """The providers and types of the whole ledger, whatever the filters, for the dropdowns."""
        self.client.force_login(self.admin_user)
        data = self.post({"provider": "nobody"})
        self.assertIn("test", data["choices"]["providers"])
        self.assertIn("dns.zone", data["choices"]["resourceTypes"])
        self.assertEqual(data["choices"]["resourceTypes"], sorted(set(data["choices"]["resourceTypes"])))

    def test_list_api_pagination(self):
        self.client.force_login(self.admin_user)
        mine = {"provider": "test"}
        data = self.post({**mine, "pageSize": 1})
        self.assertEqual(data["pagination"], {"page": 1, "pageSize": 1, "numPages": 2, "count": 2})
        self.assertEqual(data["objects"][0]["resourceType"], "dns.record")
        data = self.post({**mine, "pageSize": 1, "page": 2})
        self.assertEqual(data["objects"][0]["resourceType"], "dns.zone")
        # a page past the last is the last.
        self.assertEqual(self.post({**mine, "pageSize": 1, "page": 99})["pagination"]["page"], 2)
        for body in ({"pageSize": 0}, {"pageSize": "x"}, {"pageSize": True}, {"pageSize": 10_000}, {"page": -1}):
            with self.subTest(body=body):
                pagination = self.post({**mine, **body})["pagination"]
                self.assertEqual((pagination["page"], pagination["pageSize"]), (1, DEFAULT_PAGE_SIZE))
        for body in ("not json", "[]"):
            with self.subTest(body=body):
                self.assertEqual(self.post(body)["pagination"]["page"], 1)

    def test_list_api_is_for_superusers(self):
        self.client.force_login(self.non_admin_user)
        response = self.client.post(url(InfrastructureReverseNames.listview_api))
        self.assertEqual(response.status_code, 403)
        self.assertIn("superusers", response.json()["error"])

    def test_summary(self):
        counts = summary()
        self.assertGreaterEqual(counts["total"], 2)
        self.assertGreaterEqual(counts["activeBillable"], 1)
        self.assertGreaterEqual(counts["destroyed"], 1)
        self.assertEqual(counts["total"], counts["active"] + counts["destroyed"])
