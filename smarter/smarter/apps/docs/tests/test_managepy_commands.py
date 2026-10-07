"""Test the docs app's generate_example_manifests management command."""

import os
from io import StringIO

import yaml
from django.core.management import call_command

from smarter.lib.unittest.base_classes import SmarterTestBase

OUTPUT_FOLDER = "/home/smarter_user/data/manifests/example_manifests"


class TestGenerateExampleManifests(SmarterTestBase):
    """Test that an example manifest of each kind is written as yaml."""

    def test_generate_example_manifests(self):
        """Test that the command writes an example manifest of each kind."""
        call_command("generate_example_manifests", stdout=StringIO(), stderr=StringIO())
        files = [name for name in os.listdir(OUTPUT_FOLDER) if name.endswith((".yaml", ".yml"))]
        self.assertTrue(files)
        for name in files:
            with self.subTest(file=name), open(os.path.join(OUTPUT_FOLDER, name), encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
                if isinstance(manifest, dict):
                    self.assertIn("kind", manifest)
