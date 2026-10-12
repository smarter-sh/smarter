"""Test :mod:`smarter.lib.django.templatetags.smarter_react_contract`."""

from pydantic import ValidationError

from smarter.lib.django.templatetags.smarter_react_contract import (
    ReactAppAssets,
    ReactAppBuildInfo,
    ViteManifest,
    ViteManifestChunk,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

#: A Vite manifest.json, with a field that Vite doesn't document, and Smarter's build information.
MANIFEST = {
    "index.html": {
        "file": "assets/index.js",
        "name": "index",
        "src": "index.html",
        "isEntry": True,
        "imports": ["_vendor.js", "_missing.js"],
        "dynamicImports": ["_lazy.js"],
        "css": ["assets/index.css"],
    },
    "_vendor.js": {"file": "assets/vendor.js", "imports": ["index.html"], "css": ["assets/vendor.css"]},
    "_lazy.js": {"file": "assets/lazy.js", "isDynamicEntry": True, "css": ["assets/lazy.css"]},
    "logo.svg": {"file": "assets/logo.svg", "names": ["logo.svg"], "integrity": "sha384-abc"},
    "_custom": {"buildTime": "2026-10-12T01:09:47.988000Z", "version": "0.3.0", "buildEnv": "production"},
}


class TestViteManifest(SmarterTestBase):
    """Test the Pydantic model of a Vite-generated manifest.json."""

    def test_chunk_fields(self):
        """Test that camelCase fields are read by alias, and that undocumented fields are kept."""
        manifest = ViteManifest.model_validate(MANIFEST)
        entry = manifest.chunks["index.html"]
        self.assertIsInstance(entry, ViteManifestChunk)
        self.assertTrue(entry.is_entry)
        self.assertEqual(entry.dynamic_imports, ["_lazy.js"])
        self.assertTrue(manifest.chunks["_lazy.js"].is_dynamic_entry)
        logo = manifest.chunks["logo.svg"]
        self.assertFalse(logo.is_entry)
        self.assertEqual(logo.imports, [])
        self.assertEqual(logo.model_extra, {"integrity": "sha384-abc"})
        self.assertNotIn("_custom", manifest.chunks)
        self.assertEqual(manifest.model_dump(mode="json", by_alias=True, exclude_defaults=True), MANIFEST)

    def test_build_info(self):
        """Test that the _custom entry is read as build information, and that a manifest may omit it."""
        build_info = ViteManifest.model_validate(MANIFEST).build_info
        self.assertIsInstance(build_info, ReactAppBuildInfo)
        self.assertEqual(build_info.version, "0.3.0")
        self.assertEqual(build_info.build_env, "production")
        self.assertEqual(build_info.build_time.year, 2026)
        manifest = ViteManifest.model_validate({"index.html": {"file": "assets/index.js", "isEntry": True}})
        self.assertIsNone(manifest.build_info)
        self.assertNotIn("_custom", manifest.model_dump())
        with self.assertRaises(ValidationError):
            ViteManifest.model_validate({**MANIFEST, "_custom": {"version": "0.3.0"}})

    def test_keyword_arguments(self):
        manifest = ViteManifest(chunks={"index.html": ViteManifestChunk(file="assets/index.js", is_entry=True)})
        self.assertEqual(manifest.entry_key(), "index.html")
        self.assertIsNone(manifest.build_info)

    def test_chunk_requires_file(self):
        with self.assertRaises(ValidationError):
            ViteManifestChunk.model_validate({"isEntry": True})

    def test_bool(self):
        self.assertTrue(ViteManifest.model_validate(MANIFEST))
        self.assertFalse(ViteManifest.model_validate({}))

    def test_entry_key(self):
        self.assertEqual(ViteManifest.model_validate(MANIFEST).entry_key(), "index.html")
        self.assertIsNone(ViteManifest.model_validate({"_vendor.js": {"file": "assets/vendor.js"}}).entry_key())

    def test_collect_assets(self):
        """Test that static imports are collected once each, and that unknown keys and dynamic imports are skipped."""
        manifest = ViteManifest.model_validate(MANIFEST)
        self.assertEqual(manifest.collect_assets("index.html", "js"), ["assets/index.js", "assets/vendor.js"])
        self.assertEqual(manifest.collect_assets("index.html", "css"), ["assets/index.css", "assets/vendor.css"])
        self.assertEqual(manifest.collect_assets("_missing.js", "js"), [])


class TestReactAppAssets(SmarterTestBase):
    """Test the Pydantic model of a React app's assets."""

    def test_defaults(self):
        self.assertEqual(ReactAppAssets().model_dump(), {"js": [], "css": []})

    def test_forbids_extra_fields(self):
        with self.assertRaises(ValidationError):
            ReactAppAssets.model_validate({"js": [], "css": [], "html": []})
