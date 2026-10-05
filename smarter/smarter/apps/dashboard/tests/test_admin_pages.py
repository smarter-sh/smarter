"""
Test that the admin console's pages render for each of the Smarter apps' models: the changelist, a change page, and the add page, for a superuser.

These run each ModelAdmin's list_display, list_filter, search, readonly field and form code.
"""

from http import HTTPStatus

from django.test import Client
from django.urls import NoReverseMatch, reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.admin import smarter_restricted_admin_site


class TestAdminPages(TestAccountMixin):
    """Test the admin pages of each model of the Smarter apps."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.admin_user)

    def admin_urls(self):
        """Yield the changelist, change and add urls of each Smarter model in the admin console."""
        site = smarter_restricted_admin_site
        for model, model_admin in site._registry.items():  # pylint: disable=protected-access
            if not model.__module__.startswith("smarter.apps."):
                continue
            info = (site.name, model._meta.app_label, model._meta.model_name)  # pylint: disable=protected-access
            try:
                yield model, "changelist", reverse("%s:%s_%s_changelist" % info)
                instance = model_admin.get_queryset(self.request()).order_by("-pk").first()
                if instance is not None:
                    yield model, "change", reverse("%s:%s_%s_change" % info, args=[instance.pk])
                yield model, "add", reverse("%s:%s_%s_add" % info)
            except NoReverseMatch:
                continue

    def request(self):
        from django.test import (
            RequestFactory,  # pylint: disable=import-outside-toplevel
        )

        request = RequestFactory().get("/admin/")
        request.user = self.admin_user
        return request

    def test_admin_pages(self):
        checked = 0
        for model, page, url in self.admin_urls():
            with self.subTest(model=model.__name__, page=page):
                response = self.client.get(url)
                self.assertIn(response.status_code, (HTTPStatus.OK, HTTPStatus.FORBIDDEN, HTTPStatus.FOUND), url)
                self.assertNotEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
                checked += 1
        self.assertGreater(checked, 10)

    def test_changelist_search(self):
        """Test each changelist's search, which runs its search_fields."""
        site = smarter_restricted_admin_site
        for model, model_admin in site._registry.items():  # pylint: disable=protected-access
            if not model.__module__.startswith("smarter.apps.") or not model_admin.search_fields:
                continue
            info = (site.name, model._meta.app_label, model._meta.model_name)  # pylint: disable=protected-access
            with self.subTest(model=model.__name__):
                response = self.client.get(reverse("%s:%s_%s_changelist" % info) + "?q=test")
                self.assertIn(response.status_code, (HTTPStatus.OK, HTTPStatus.FORBIDDEN, HTTPStatus.FOUND))
