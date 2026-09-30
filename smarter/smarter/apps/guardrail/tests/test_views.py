"""
Test the Guardrail dashboard views: the React list page, its api, the manifest detail page, and the urls.

.. note::

    **Experimental.** The Guardrail was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.guardrail.caching import (
    invalidate_all_cached_guardrails_for_user_profile,
)
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.urls import GuardrailReverseNames as Names
from smarter.lib import json

from .base_classes import GuardrailTestBase


def url(name: str, **kwargs) -> str:
    return reverse(f"{Names.namespace}:{name}", kwargs=kwargs or None)


class TestGuardrailViews(GuardrailTestBase):
    """Test the Guardrail dashboard views."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guardrail = cls.create_guardrail("test_views_guardrail")

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.addCleanup(self.client.logout)
        invalidate_all_cached_guardrails_for_user_profile(self.user_profile)

    def post(self, path: str, status: int = HTTPStatus.OK) -> dict:
        response = self.client.post(path)
        self.assertEqual(response.status_code, status, response.content)
        return json.loads(response.content)

    def test_listview(self):
        """Test the React list page, and that an anonymous user is redirected."""
        self.assertEqual(self.client.get(url(Names.listview)).status_code, HTTPStatus.OK)
        self.client.logout()
        self.assertEqual(self.client.get(url(Names.listview)).status_code, HTTPStatus.FOUND)

    def test_listview_api(self):
        """Test that the list api returns the user's Guardrails."""
        data = self.post(url(Names.listview_api_all))
        self.assertIn(self.guardrail.name, [item["name"] for item in data["objects"]])

    def test_clone_rename_delete(self):
        """Test the clone, rename and delete apis, which used the wrong url parameter name."""
        clone = self.post(url(Names.listview_api_clone, guardrail_id=self.guardrail.pk, new_name="test_views_clone"))
        self.addCleanup(Guardrail.objects.filter(name__startswith="test_views_clone").delete)
        clone_pk = Guardrail.objects.get(name="test_views_clone", user_profile=self.user_profile).pk
        self.assertEqual(clone["name"], "test_views_clone")
        renamed = self.post(url(Names.listview_api_rename, guardrail_id=clone_pk, new_name="test_views_clone_renamed"))
        self.assertEqual(renamed["name"], "test_views_clone_renamed")
        self.post(url(Names.listview_api_delete, guardrail_id=clone_pk))
        self.assertFalse(Guardrail.objects.filter(pk=clone_pk).exists())

    def test_detailview(self):
        """Test that the detail page renders the Guardrail's manifest, not a Provider's."""
        response = self.client.get(url(Names.detailview, hashed_id=self.guardrail.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.content.decode()
        self.assertIn(self.guardrail.name, content)
        self.assertIn("Guardrail", content)
        self.assertEqual(
            self.client.get(url(Names.detailview, hashed_id="not-a-hash")).status_code, HTTPStatus.NOT_FOUND
        )
