"""Test the dashboard's "Getting Started" api view, :mod:`smarter.apps.dashboard.views.views.api.getting_started`."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api.my_resources import get_llmclients
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.apps.llmclient.models import LLMClient
from smarter.lib import json

from ..const import namespace


class TestGettingStartedApiView(TestAccountMixin):
    """Test GettingStartedView, which lists the onboarding steps of the user."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.url = reverse(
            f"{namespace}:{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.getting_started}"
        )

    def steps(self, user) -> dict[str, dict]:
        self.client.force_login(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        return {step["name"]: step for step in json.loads(response.content)["steps"]}

    def test_steps(self):
        """Test that each step has its fields, and that only staff users have the API key step."""
        staff_steps = self.steps(self.admin_user)
        self.assertIn("Create an API key", staff_steps)
        for step in staff_steps.values():
            with self.subTest(step=step["name"]):
                self.assertIsInstance(step["done"], bool)
                self.assertTrue(step["description"])
                self.assertTrue(step["url"].startswith("/"))
        mortal_steps = self.steps(self.non_admin_user)
        self.assertNotIn("Create an API key", mortal_steps)
        self.assertIn("Create an LLM Client", mortal_steps)

    def test_steps_are_done(self):
        """Test that creating, then deploying, an LLM Client marks their steps done."""
        llmclient = LLMClient.objects.create(
            name=f"test_getting_started_{self.hash_suffix}", user_profile=self.non_admin_user_profile
        )
        self.addCleanup(llmclient.delete)
        get_llmclients(invalidate=True, user_profile=self.non_admin_user_profile)
        steps = self.steps(self.non_admin_user)
        self.assertTrue(steps["Create an LLM Client"]["done"])
        self.assertFalse(steps["Deploy an LLM Client"]["done"])
        LLMClient.objects.filter(pk=llmclient.pk).update(deployed=True)
        self.assertTrue(self.steps(self.non_admin_user)["Deploy an LLM Client"]["done"])

    def test_getting_started_anonymous(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
