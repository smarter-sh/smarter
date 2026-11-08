"""Test the auth token web console pages, :mod:`smarter.lib.drf.views.detailview` and :mod:`smarter.lib.drf.views.listview.view`."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.drf.const import namespace
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.urls import AuthTokenReverseNames
from smarter.lib.unittest.resource_views import (
    assert_console_page,
    assert_no_resource,
    resource_detail_json,
)


class TestAuthTokenViews(TestAccountMixin):
    """Test the auth token detail and list pages."""

    def setUp(self):
        super().setUp()
        self.token, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=self.user_profile, name="test_drf_views_token", user=self.admin_user, description="test"
        )
        self.addCleanup(SmarterAuthToken.objects.filter(pk=self.token.pk).delete)
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)

    def test_detail_view(self):
        """Test that the manifest page is the console's, whose resource api returns the token's manifest."""
        self.assertEqual(self.token.record_locator, f"smarterauthtoken-{self.token.key_id}")
        detail = resource_detail_json(self, self.token.record_locator)
        self.assertEqual(detail["kind"], "SmarterAuthToken")
        self.assertEqual(detail["name"], self.token.name)
        self.assertIn(self.token.name, detail["manifest"] or "")
        assert_no_resource(self, "smarterauthtoken-not-a-key-id")
        url = reverse(f"{namespace}:{AuthTokenReverseNames.detailview}", kwargs={"authtoken_id": self.token.key_id})
        assert_console_page(self, url)

    def test_list_view(self):
        """Test that the list page renders."""
        response = self.client.get(reverse(f"{namespace}:{AuthTokenReverseNames.listview}"))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
