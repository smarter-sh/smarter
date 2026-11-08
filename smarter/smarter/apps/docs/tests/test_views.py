"""Test the docs pages: :mod:`smarter.apps.docs.views.views`."""

from http import HTTPStatus

from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.docs.urls import DocsReverseNames
from smarter.apps.docs.views.views import is_sam_kind
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.resource_views import assert_console_page

DOCS = DocsReverseNames.namespace


def kind_url(name: str, kind: str) -> str:
    """The url of a kind's docs page, e.g. ``/docs/manifest/llmclient/``."""
    # smarter.lib.django.shortcuts.reverse takes kwargs only with one joined name.
    return reverse(f"{DOCS}:{name}", kwargs={"kind": kind})


class TestDocsViews(TestAccountMixin):
    """Test that the docs pages are the console's, for anyone, and that a kind's pages exist for SAM kinds only."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.non_admin_user)

    def test_landing_pages(self):
        """The example manifests and the JSON Schemas are the console's pages, signed in or not."""
        for name in (DocsReverseNames.example_manifests, DocsReverseNames.json_schemas):
            with self.subTest(name=name):
                self.client.force_login(self.non_admin_user)
                assert_console_page(self, reverse(DOCS, name))

    def test_every_kind(self):
        """Every kind's example manifest and JSON Schema page is the console's, for a visitor too."""
        self.client.logout()
        for kind in SAMKinds.all():
            for name in (DocsReverseNames.example_manifest, DocsReverseNames.json_schema):
                with self.subTest(kind=kind, name=name):
                    response = self.client.get(kind_url(name, kind.lower()))
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_a_kind_page_is_the_console(self):
        """A kind's pages are the console's, signed in or not."""
        assert_console_page(self, kind_url(DocsReverseNames.example_manifest, "llmclient"))
        self.client.force_login(self.non_admin_user)
        assert_console_page(self, kind_url(DocsReverseNames.json_schema, "llmclient"))

    def test_unknown_kind_is_not_found(self):
        """A kind that doesn't exist is a 404, not the console's page."""
        for name in (DocsReverseNames.example_manifest, DocsReverseNames.json_schema):
            with self.subTest(name=name):
                response = self.client.get(kind_url(name, "nosuchkind"))
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_is_sam_kind(self):
        """A url's kind matches a SAM kind in any case."""
        self.assertTrue(is_sam_kind("llmclient"))
        self.assertTrue(is_sam_kind("LLMClient"))
        self.assertTrue(is_sam_kind("SmarterAuthToken"))
        self.assertFalse(is_sam_kind(""))
        self.assertFalse(is_sam_kind("llmclients"))
