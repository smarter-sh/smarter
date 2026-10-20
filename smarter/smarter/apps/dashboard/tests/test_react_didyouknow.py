"""Test :mod:`smarter.apps.dashboard.templatetags.react_didyouknow`, the Did you know? note below the web console's title."""

from http import HTTPStatus
from unittest.mock import patch

from django.template import Context, Template
from django.test import Client
from waffle.testutils import override_switch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.templatetags import react_didyouknow
from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

SWITCH = SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_DID_YOU_KNOW
MANAGER = "smarter.apps.dashboard.templatetags.react_didyouknow.templatetag_manager"
ASSETS = ReactAppAssets(css=["assets/index.css"], js=["assets/index.js"])


class TestReactDidYouKnow(TestAccountMixin):
    """Test the template tags, and the note in the title bar of a console page."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)

    def page(self) -> str:
        self.client.force_login(self.non_admin_user)
        with patch(f"{MANAGER}.reactapp_build_assets", ASSETS):
            response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        return response.content.decode()

    def test_registered(self):
        self.assertIn("didyouknow_react_assets", react_didyouknow.register.tags)
        self.assertIn("didyouknow_enabled", react_didyouknow.register.tags)

    def test_manager(self):
        manager = react_didyouknow.templatetag_manager
        self.assertIsInstance(manager, SmarterReactTemplateTagManager)
        self.assertEqual(manager.app_name, "@smarter/didyouknow")
        self.assertEqual(manager.templatetag_name, react_didyouknow.__name__)

    def test_assets(self):
        with patch(f"{MANAGER}.reactapp_build_assets", ASSETS):
            self.assertEqual(react_didyouknow.didyouknow_react_assets(), ASSETS)

    def test_enabled(self):
        with override_switch(SWITCH, active=True):
            self.assertTrue(react_didyouknow.didyouknow_enabled())
        with override_switch(SWITCH, active=False):
            self.assertFalse(react_didyouknow.didyouknow_enabled())

    def test_template(self):
        template = Template("{% load react_didyouknow %}{% didyouknow_enabled as on %}{{ on|yesno:'on,off' }}")
        with override_switch(SWITCH, active=False):
            self.assertEqual(template.render(Context()), "off")

    def test_console_pages_show_the_note_below_the_title(self):
        with override_switch(SWITCH, active=True):
            content = self.page()
        title = content.index('class="smarter-product-title"')
        root = content.index('id="smarter-didyouknow-root"')
        self.assertLess(title, root)
        self.assertIn("/static/react/%40smarter/didyouknow/assets/index.css", content)
        self.assertIn('src="/static/react/%40smarter/didyouknow/assets/index.js"', content)

    def test_console_pages_leave_it_out_while_the_switch_is_off(self):
        with override_switch(SWITCH, active=False):
            content = self.page()
        self.assertIn('class="smarter-product-title"', content)
        self.assertNotIn("smarter-didyouknow-root", content)
        self.assertNotIn("react/%40smarter/didyouknow/", content)
