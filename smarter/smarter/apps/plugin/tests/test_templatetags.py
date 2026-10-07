# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.templatetags.react_plugin_list`.

The template tag returns the plugin-list React app's JS and CSS assets,
from its Vite-generated manifest.json. ./data/react-manifest.yaml is an
example manifest.json, which these tests install in a temporary STATIC_ROOT.
"""

import json
import os
import tempfile

from django.template import Context, Template
from django.test import override_settings

from smarter.apps.plugin.templatetags import react_plugin_list
from smarter.lib import logging
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import get_test_data

logger = logging.getLogger(__name__)

APP_NAME = "@smarter/plugin-list"


class TestReactPluginListTemplateTag(SmarterTestBase):
    """Test the plugin_list_react_assets template tag."""

    def setUp(self):
        super().setUp()
        self.static_root = tempfile.TemporaryDirectory()  # pylint: disable=R1732
        self.addCleanup(self.static_root.cleanup)
        manifest_dir = os.path.join(self.static_root.name, "react", APP_NAME)
        os.makedirs(manifest_dir)
        with open(os.path.join(manifest_dir, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(get_test_data("react-manifest.yaml"), f)

    def manager(self) -> SmarterReactTemplateTagManager:
        """Return a new manager, which reads the example manifest.json."""
        with override_settings(STATIC_ROOT=self.static_root.name):
            manager = SmarterReactTemplateTagManager(app_name=APP_NAME, templatetag_name=react_plugin_list.__name__)
            manager.reactapp_build_assets  # pylint: disable=W0104
        return manager

    def test_registered(self):
        """Test that the tag is registered in the template library."""
        self.assertIn("plugin_list_react_assets", react_plugin_list.register.tags)

    def test_manager(self):
        """Test that the module's manager belongs to the plugin-list React app."""
        manager = react_plugin_list.templatetag_manager
        self.assertIsInstance(manager, SmarterReactTemplateTagManager)
        self.assertEqual(manager.app_name, APP_NAME)
        self.assertEqual(manager.templatetag_name, react_plugin_list.__name__)

    def test_tag(self):
        """Test that the tag returns the manager's JS and CSS assets."""
        assets = react_plugin_list.plugin_list_react_assets()
        self.assertEqual(set(assets.keys()), {"js", "css"})
        self.assertIsInstance(assets["js"], list)
        self.assertIsInstance(assets["css"], list)
        self.assertEqual(assets, react_plugin_list.templatetag_manager.reactapp_build_assets)

    def test_build_assets(self):
        """Test that the example manifest's entry point, and every dependency, is collected."""
        assets = self.manager().reactapp_build_assets
        for file in ("assets/index.js", "assets/rolldown-runtime.js", "assets/xterm.js"):
            self.assertTrue(any(js.endswith(file) for js in assets["js"]), file)
        for file in ("assets/index-DvLY75bJ.css", "assets/xterm-TdnZ7DQy.css"):
            self.assertTrue(any(css.endswith(file) for css in assets["css"]), file)

    def test_template(self):
        """Test the tag in a template."""
        template = Template(
            "{% load react_plugin_list %}{% plugin_list_react_assets as assets %}{{ assets.js|length }}"
        )
        rendered = template.render(Context({}))
        self.assertEqual(rendered, str(len(react_plugin_list.plugin_list_react_assets()["js"])))
