"""Test the Infrastructure Resource web console: the list view, and its API."""

import json

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.infrastructure.models import InfrastructureResource
from smarter.apps.infrastructure.urls import InfrastructureReverseNames
from smarter.apps.infrastructure.views.listview import summary


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

    def test_list_api_limit(self):
        self.client.force_login(self.admin_user)
        for body, expected in (({"limit": 1}, 1), ({"limit": 0}, None), ({"limit": "x"}, None)):
            with self.subTest(body=body):
                response = self.client.post(
                    url(InfrastructureReverseNames.listview_api), data=json.dumps(body), content_type="application/json"
                )
                if expected is None:
                    self.assertGreaterEqual(len(response.json()["objects"]), 2)
                else:
                    self.assertEqual(len(response.json()["objects"]), expected)
        response = self.client.post(
            url(InfrastructureReverseNames.listview_api), data="not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)

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
