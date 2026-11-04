"""Test :mod:`smarter.apps.doodle.templatetags.react_doodle`, and the sign-in page that shows the doodle."""

from http import HTTPStatus
from unittest.mock import patch

from django.test import Client
from waffle.testutils import override_switch

from smarter.apps.doodle.templatetags import react_doodle
from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.unittest.base_classes import SmarterTestBase

SWITCH = SmarterWaffleSwitches.ENABLE_DOODLE
MANAGER = "smarter.apps.doodle.templatetags.react_doodle.templatetag_manager"
ASSETS = ReactAppAssets(css=["assets/index.css"], js=["assets/index.js"])


class TestReactDoodle(SmarterTestBase):
    """The template tags, and the doodle on the sign-in page."""

    def page(self) -> str:
        """GET the sign-in page."""
        client = Client()
        with patch(f"{MANAGER}.reactapp_build_assets", ASSETS):
            response = client.get("/login/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        return response.content.decode()

    def test_registered(self):
        for tag in ["doodle_react_assets", "doodle_enabled", "doodle_api_url", "doodle_base_image_url"]:
            self.assertIn(tag, react_doodle.register.tags)

    def test_manager(self):
        manager = react_doodle.templatetag_manager
        self.assertIsInstance(manager, SmarterReactTemplateTagManager)
        self.assertEqual(manager.app_name, "@smarter/doodle")

    def test_tags(self):
        with patch(f"{MANAGER}.reactapp_build_assets", ASSETS):
            self.assertEqual(react_doodle.doodle_react_assets(), ASSETS)
        self.assertEqual(react_doodle.doodle_api_url(), "/api/v1/doodles/today/")
        self.assertEqual(react_doodle.doodle_base_image_url(), "/static/doodle/base.svg")
        with override_switch(SWITCH, active=True):
            self.assertTrue(react_doodle.doodle_enabled())
        with override_switch(SWITCH, active=False):
            self.assertFalse(react_doodle.doodle_enabled())

    def test_the_sign_in_page_shows_the_doodle(self):
        with override_switch(SWITCH, active=True):
            content = self.page()
        self.assertIn('id="smarter-doodle-root"', content)
        self.assertIn('smarter-doodle-api-url="/api/v1/doodles/today/"', content)
        self.assertIn("/static/react/%40smarter/doodle/assets/index.css", content)
        self.assertIn('src="/static/react/%40smarter/doodle/assets/index.js"', content)
        self.assertIn('src="/static/doodle/base.svg"', content)
        self.assertNotIn("auth-screens.png", content)

    def test_the_sign_in_page_shows_the_base_scene_while_the_switch_is_off(self):
        with override_switch(SWITCH, active=False):
            content = self.page()
        self.assertIn('id="smarter-doodle-root"', content)
        self.assertIn('src="/static/doodle/base.svg"', content)
        self.assertNotIn("smarter-doodle-api-url", content)
        self.assertNotIn("react/%40smarter/doodle/", content)
