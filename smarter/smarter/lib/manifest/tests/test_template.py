"""Test :mod:`smarter.lib.manifest.template`."""

from unittest.mock import patch

from smarter.lib.manifest import template
from smarter.lib.manifest.template import (
    manifest_template_values,
    render_manifest_template,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestManifestTemplate(SmarterTestBase):
    """Test the manifest templates' values, and their rendering."""

    def test_values(self):
        with patch.object(template, "smarter_settings") as settings:
            settings.environment_url = "https://alpha.platform.example.com/"
            settings.environment_platform_domain = "alpha.platform.example.com"
            self.assertEqual(
                manifest_template_values(),
                {
                    "environment_platform_scheme": "https",
                    "environment_platform_domain": "alpha.platform.example.com",
                },
            )
            self.assertEqual(
                render_manifest_template("url: ${environment_platform_scheme}://${environment_platform_domain}/x"),
                "url: https://alpha.platform.example.com/x",
            )

    def test_unknown_placeholder(self):
        with self.assertRaises(KeyError):
            render_manifest_template("url: ${no_such_value}")
