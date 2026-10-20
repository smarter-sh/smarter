"""Test the onboarding hints' api view and state, :mod:`smarter.apps.dashboard.views.views.api.onboarding`, and their model."""

import re
from http import HTTPStatus
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import Client
from django.urls import reverse
from waffle.testutils import override_switch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.models import (
    OnboardingHint,
    OnboardingHints,
    OnboardingOutcomes,
)
from smarter.apps.dashboard.views.views.api import onboarding
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.lib import json
from smarter.lib.django.waffle import SmarterWaffleSwitches

from ..const import namespace

SWITCH = SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_ONBOARDING_HINTS
REACT_CONST = Path(settings.PROJECT_ROOT) / "react" / "packages" / "smarter-onboarding" / "src" / "lib" / "const.ts"


class TestOnboardingSeenView(TestAccountMixin):
    """Test OnboardingSeenView, which records what a user did with a hint, and the page's onboarding state."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.url = reverse(
            f"{namespace}:{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.onboarding_seen}"
        )
        self.addCleanup(self.forget_hints)
        self.forget_hints()

    def forget_hints(self):
        """Make the non-admin user a user who has seen no hint."""
        OnboardingHint.objects.filter(user=self.non_admin_user).delete()
        onboarding.seen_onboarding_hints.invalidate(self.non_admin_user.id)

    def post(self, body: object, status: int = HTTPStatus.OK) -> dict:
        self.client.force_login(self.non_admin_user)
        response = self.client.post(self.url, data=json.dumps(body), content_type="application/json")
        self.assertEqual(response.status_code, status, response.content[:300])
        return json.loads(response.content)

    def test_records_a_hint_once(self):
        """Test that the first outcome is kept, and that the response lists the seen hints in their order."""
        self.assertEqual(self.post({"hint": "workbench_tour", "outcome": "completed"}), {"seen": ["workbench_tour"]})
        data = self.post({"hint": "sidebar_llmclients", "outcome": "clicked"})
        self.assertEqual(data, {"seen": ["sidebar_llmclients", "workbench_tour"]})
        self.post({"hint": "sidebar_llmclients", "outcome": "dismissed"})
        hint = OnboardingHint.objects.get(user=self.non_admin_user, hint=OnboardingHints.SIDEBAR_LLMCLIENTS)
        self.assertEqual(hint.outcome, OnboardingOutcomes.CLICKED)
        self.assertEqual(str(hint), f"{self.non_admin_user}: sidebar_llmclients (clicked)")

    def test_invalid_body(self):
        """Test that an unknown hint or outcome, an extra key, or a body that isn't JSON is a 400 that records nothing."""
        for body in (
            {"hint": "a_future_hint", "outcome": "clicked"},
            {"hint": "workbench_tour", "outcome": "loved_it"},
            {"hint": "workbench_tour", "outcome": "clicked", "extra": True},
            {},
        ):
            with self.subTest(body=body):
                self.post(body, status=HTTPStatus.BAD_REQUEST)
        self.client.force_login(self.non_admin_user)
        response = self.client.post(self.url, data="not json", content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertFalse(OnboardingHint.objects.filter(user=self.non_admin_user).exists())

    def test_anonymous(self):
        self.assertEqual(self.client.post(self.url).status_code, HTTPStatus.FOUND)

    def test_unresolved_user(self):
        """Test that a user whom get_resolved_user() can't resolve is refused, rather than an error."""
        self.client.force_login(self.non_admin_user)
        with mock.patch.object(onboarding, "get_resolved_user", return_value=None):
            self.assertEqual(self.client.post(self.url).status_code, HTTPStatus.UNAUTHORIZED)

    def test_context(self):
        """Test the page's onboarding state, for a signed-in user, with the switch on and off, and for none."""
        with override_switch(SWITCH, active=True):
            context = onboarding.onboarding_context(self.non_admin_user, self.url)
        self.assertTrue(context.enabled)
        self.assertEqual(context.seen, [])
        self.assertEqual(context.api_url, self.url)
        self.post({"hint": "llmclient_weather", "outcome": "dismissed"})
        with override_switch(SWITCH, active=False):
            context = onboarding.onboarding_context(self.non_admin_user, self.url)
        self.assertFalse(context.enabled)
        self.assertEqual(context.seen, [OnboardingHints.LLMCLIENT_WEATHER])
        self.assertEqual(
            set(context.model_dump(by_alias=True)), {"enabled", "apiUrl", "seen", "csrfCookieName", "cookieDomain"}
        )
        with override_switch(SWITCH, active=True):
            context = onboarding.onboarding_context(AnonymousUser(), self.url)
        self.assertFalse(context.enabled)
        self.assertEqual(context.seen, [])

    def test_react_package_knows_the_same_hints_and_outcomes(self):
        """Test that @smarter/onboarding's OnboardingHints and OnboardingOutcomes are the model's choices."""
        source = REACT_CONST.read_text(encoding="utf-8")
        for name, choices in (("OnboardingHints", OnboardingHints), ("OnboardingOutcomes", OnboardingOutcomes)):
            with self.subTest(name=name):
                block = re.search(rf"export const {name} = \{{(.*?)\}} as const;", source, re.S)
                self.assertIsNotNone(block, f"{name} not found in {REACT_CONST}")
                values = set(re.findall(r':\s*"([a-z_]+)"', block.group(1)))  # type: ignore[union-attr]
                self.assertEqual(values, set(choices.values))
