"""Test :class:`smarter.lib.django.templatetags.smarter_react_templatetag_manager.SmarterReactTemplateTagManager`."""

import os
import tempfile

from django.test import override_settings

from smarter.common.exceptions import SmarterValueError
from smarter.lib import json
from smarter.lib.django.templatetags.smarter_react_contract import (
    ReactAppAssets,
    ViteManifest,
)
from smarter.lib.django.templatetags.smarter_react_templatetag_manager import (
    SmarterReactTemplateTagManager,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

APP = "@smarter/test-app"

#: A Vite manifest.json: the entry imports a chunk, which imports another, and a circular import.
MANIFEST = {
    "index.html": {
        "file": "assets/index.js",
        "isEntry": True,
        "imports": ["_vendor.js", "_shared.js"],
        "css": ["assets/index.css"],
    },
    "_vendor.js": {"file": "assets/vendor.js", "imports": ["_shared.js"], "css": ["assets/vendor.css"]},
    "_shared.js": {"file": "assets/shared.js", "imports": ["index.html"]},
    "_custom": {"buildTime": "2026-10-12T01:09:47.988Z", "version": "0.3.0", "buildEnv": "production"},
}


class TestSmarterReactTemplateTagManager(SmarterTestBase):
    """Test loading a React app's Vite manifest.json, and collecting its assets in dependency order."""

    def setUp(self):
        super().setUp()
        self.static_root = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.static_root.cleanup)
        self.app_dir = os.path.join(self.static_root.name, "react", APP)
        os.makedirs(self.app_dir)
        settings = override_settings(STATIC_ROOT=self.static_root.name)
        settings.enable()
        self.addCleanup(settings.disable)

    def write_manifest(self, content: str):
        with open(os.path.join(self.app_dir, "manifest.json"), "w", encoding="utf-8") as f:
            f.write(content)

    def test_assets(self):
        self.write_manifest(json.dumps(MANIFEST))
        manager = SmarterReactTemplateTagManager(app_name=APP, templatetag_name="test_tag")
        self.assertEqual(manager.entry_key, "index.html")
        self.assertIsInstance(manager.manifest, ViteManifest)
        self.assertEqual(manager.manifest.build_info.version, "0.3.0")
        assets = manager.reactapp_build_assets
        self.assertIsInstance(assets, ReactAppAssets)
        self.assertEqual(assets.js, ["assets/index.js", "assets/vendor.js", "assets/shared.js"])
        self.assertEqual(assets.css, ["assets/index.css", "assets/vendor.css"])
        self.assertIs(manager.reactapp_build_assets, assets)

    def test_missing_manifest(self):
        """Test that an app without a manifest.json has no entry and no assets."""
        manager = SmarterReactTemplateTagManager(app_name=APP, templatetag_name="test_tag")
        self.assertIsNone(manager.entry_key)
        self.assertIsNone(manager.manifest)
        self.assertEqual(manager.reactapp_build_assets, ReactAppAssets(js=[], css=[]))

    def test_invalid_manifests(self):
        """Test that a manifest.json that isn't JSON, or isn't a Vite manifest, is treated as missing."""
        for content in ("not json", json.dumps(["a", "list"]), json.dumps({"index.html": {"isEntry": True}})):
            with self.subTest(content=content):
                self.write_manifest(content)
                manager = SmarterReactTemplateTagManager(app_name=APP, templatetag_name="test_tag")
                self.assertIsNone(manager.manifest)
                self.assertEqual(manager.reactapp_build_assets, ReactAppAssets())

    def test_manifest_without_entry(self):
        self.write_manifest(json.dumps({"_vendor.js": {"file": "assets/vendor.js"}}))
        with self.assertRaises(SmarterValueError):
            SmarterReactTemplateTagManager(app_name=APP, templatetag_name="test_tag")
