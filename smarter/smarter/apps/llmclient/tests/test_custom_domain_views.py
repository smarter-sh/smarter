"""
Test the CustomDomain dashboard views: the React list page, its list, clone, delete and rename api, and the manifest detail page.

See
:class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

from http import HTTPStatus

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.context_processors import sidebar_context
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientCustomDomain,
    LLMClientCustomDomainDNS,
)
from smarter.apps.llmclient.urls import LLMClientReverseNames
from smarter.lib.unittest.resource_views import ResourceViewsTestMixin


class CustomDomainReverseNames:
    """The CustomDomain view names, as ResourceViewsTestMixin names them."""

    namespace = LLMClientReverseNames.namespace
    listview = LLMClientReverseNames.custom_domain_listview
    listview_api = LLMClientReverseNames.custom_domain_listview_api
    listview_api_all = LLMClientReverseNames.custom_domain_listview_api_all
    listview_api_clone = LLMClientReverseNames.custom_domain_listview_api_clone
    listview_api_delete = LLMClientReverseNames.custom_domain_listview_api_delete
    listview_api_rename = LLMClientReverseNames.custom_domain_listview_api_rename
    detailview = LLMClientReverseNames.custom_domain_detailview


class TestCustomDomainViews(ResourceViewsTestMixin, TestAccountMixin):
    """Test the CustomDomain dashboard views."""

    model = LLMClientCustomDomain
    reverse_names = CustomDomainReverseNames
    id_kwarg = "custom_domain_id"
    resource_name_prefix = "test_custom_domain_views"

    @classmethod
    def create_resource(cls, name: str) -> LLMClientCustomDomain:
        return LLMClientCustomDomain.objects.create(
            name=name,
            user_profile=cls.user_profile,
            domain_name=f"{name.replace('_', '-')}.example.com",
        )

    def test_clone(self):
        super().test_clone()

    def test_delete(self):
        super().test_delete()

    def test_rename(self):
        super().test_rename()

    def test_list_page_root(self):
        """The page renders the React app's root, configured with the list api's url."""
        response = self.client.get(self.url("listview"))
        context = response.context["custom_domain_list"]
        self.assertEqual(context["root_id"], "smarter-custom-domain-list-root")
        self.assertEqual(context["custom_domain_list_api_url"], self.url("listview_api_all"))
        self.assertIn(f'smarter-custom-domain-list-api-url="{self.url("listview_api_all")}"', response.content.decode())

    def test_sidebar_links_to_the_list_page(self):
        self.assertEqual(sidebar_context()["sidebar"]["custom_domains"], self.url("listview"))

    def test_shared_with_the_account(self):
        """The admin's custom domain is shared with the account's other users."""
        self.client.force_login(self.non_admin_user)
        self.assertNotIn(self.resource.name, self.listed("owned"))
        self.assertIn(self.resource.name, self.listed("shared"))

    def test_list_api_reports_llmclient_and_dns_records(self):
        """A listed custom domain includes the llmclient that uses it, and its DNS records."""
        custom_domain = self.throwaway("in_use")
        LLMClientCustomDomainDNS.objects.create(
            custom_domain=custom_domain, record_name=custom_domain.domain_name, record_type="NS", record_value="ns-1"
        )
        llmclient = LLMClient.objects.create(name=f"{custom_domain.name}_llmclient", user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=llmclient.pk).delete)
        # update(), rather than save(), which sends llmclient signals.
        LLMClient.objects.filter(pk=llmclient.pk).update(custom_domain=custom_domain)

        objects = self.post(self.url("listview_api_all") + "?page_size=100")["objects"]
        listed = next(item for item in objects if item["name"] == custom_domain.name)
        self.assertEqual(listed["domainName"], custom_domain.domain_name)
        self.assertEqual(listed["llmclient"]["name"], llmclient.name)
        self.assertEqual(listed["dnsRecords"][0]["type"], "NS")
        self.assertIn(custom_domain.hashed_id, listed["manifestUrl"])
        self.assertFalse(listed["canDelete"])
        self.assertEqual(listed["verificationStatus"], "Not Verified")
        self.assertIsNone(listed["verifiedAt"])

        # an llmclient that uses it would be deleted with it, so it cannot be deleted.
        self.post(self.id_url("listview_api_delete", custom_domain.pk), status=HTTPStatus.BAD_REQUEST)
        self.assertTrue(LLMClientCustomDomain.objects.filter(pk=custom_domain.pk).exists())
        self.assertTrue(LLMClient.objects.filter(pk=llmclient.pk).exists())

    def test_can_delete(self):
        objects = self.post(self.url("listview_api_all") + "?page_size=100")["objects"]
        listed = next(item for item in objects if item["name"] == self.resource.name)
        self.assertTrue(listed["canDelete"])
