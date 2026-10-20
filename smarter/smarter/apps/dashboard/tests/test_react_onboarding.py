"""Test :mod:`smarter.apps.dashboard.templatetags.react_onboarding`, the onboarding state of each console page."""

from http import HTTPStatus

from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory
from waffle.testutils import override_switch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.models import (
    OnboardingHint,
    OnboardingHints,
    OnboardingOutcomes,
)
from smarter.apps.dashboard.templatetags import react_onboarding
from smarter.apps.dashboard.views.views.api import onboarding
from smarter.lib import json
from smarter.lib.django.waffle import SmarterWaffleSwitches

SWITCH = SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_ONBOARDING_HINTS


class TestReactOnboarding(TestAccountMixin):
    """Test the template tag, and the onboarding state and sidebar target on a console page."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.addCleanup(self.forget_hints)
        self.forget_hints()

    def forget_hints(self):
        OnboardingHint.objects.filter(user=self.non_admin_user).delete()
        onboarding.seen_onboarding_hints.invalidate(self.non_admin_user.id)

    def test_registered(self):
        self.assertIn("onboarding", react_onboarding.register.tags)

    def test_tag(self):
        """Test the state for a signed-in user, in camelCase, and for a request without one."""
        request = RequestFactory().get("/dashboard/")
        request.user = self.non_admin_user
        with override_switch(SWITCH, active=True):
            state = react_onboarding.onboarding({"request": request})
        self.assertTrue(state["enabled"])
        self.assertEqual(state["seen"], [])
        self.assertEqual(state["apiUrl"], "/dashboard/api/onboarding/seen/")
        request.user = AnonymousUser()
        with override_switch(SWITCH, active=True):
            self.assertFalse(react_onboarding.onboarding({"request": request})["enabled"])

    def test_console_pages_write_the_state_and_mark_the_sidebar_link(self):
        """Test that a console page holds the state as JSON, with the hints that the user has seen."""
        OnboardingHint.objects.create(
            user=self.non_admin_user, hint=OnboardingHints.SIDEBAR_LLMCLIENTS, outcome=OnboardingOutcomes.CLICKED
        )
        self.client.force_login(self.non_admin_user)
        with override_switch(SWITCH, active=True):
            response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = response.content.decode()
        self.assertIn('data-smarter-onboarding="sidebar-llmclients"', content)
        start = content.index('id="smarter-onboarding"')
        script = content[content.index(">", start) + 1 : content.index("</script>", start)]
        state = json.loads(script)
        self.assertTrue(state["enabled"])
        self.assertEqual(state["seen"], ["sidebar_llmclients"])
