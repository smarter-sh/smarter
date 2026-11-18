"""Test :mod:`smarter.lib.manifest.parsing`."""

import os
import tempfile

from smarter.lib import json
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.parsing import parse_manifest, read_manifest_file
from smarter.lib.unittest.base_classes import SmarterTestBase

YAML_MANIFEST = """
apiVersion: smarter.sh/v1
kind: Guardrail
metadata:
  name: test-guardrail
  description: A guardrail.
  version: 1.0.0
spec:
  config:
    provider: openai
"""

EXPECTED = {
    "apiVersion": "smarter.sh/v1",
    "kind": "Guardrail",
    "metadata": {"name": "test-guardrail", "description": "A guardrail.", "version": "1.0.0"},
    "spec": {"config": {"provider": "openai"}},
}


class TestParseManifest(SmarterTestBase):
    """Test :func:`parse_manifest`."""

    def test_yaml(self):
        """YAML text is parsed into a dict."""
        self.assertEqual(parse_manifest(YAML_MANIFEST), EXPECTED)

    def test_json(self):
        """JSON text is parsed into the same dict."""
        self.assertEqual(parse_manifest(json.dumps(EXPECTED)), EXPECTED)

    def test_dict(self):
        """A dict is returned as is."""
        self.assertIs(parse_manifest(EXPECTED), EXPECTED)

    def test_not_text(self):
        """Anything other than text or a dict is not a manifest."""
        with self.assertRaises(SAMValidationError) as context:
            parse_manifest(42)  # type: ignore[arg-type]
        self.assertIn("not a int", str(context.exception))

    def test_invalid_yaml(self):
        """Text that is not YAML is not a manifest."""
        with self.assertRaises(SAMValidationError) as context:
            parse_manifest("kind: [unclosed")
        self.assertIn("not valid YAML or JSON", str(context.exception))

    def test_not_an_object(self):
        """YAML that is not an object, e.g. a list or a plain string, is not a manifest."""
        for text in ("- a\n- b\n", "just a string", ""):
            with self.subTest(text=text):
                with self.assertRaises(SAMValidationError) as context:
                    parse_manifest(text)
                self.assertIn("must be a YAML object", str(context.exception))


class TestReadManifestFile(SmarterTestBase):
    """Test :func:`read_manifest_file`."""

    def test_read(self):
        """A manifest file is read and parsed into a dict."""
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as file:
            file.write(YAML_MANIFEST)
        try:
            self.assertEqual(read_manifest_file(file.name), EXPECTED)
        finally:
            os.remove(file.name)

    def test_missing_file(self):
        """A file that does not exist raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            read_manifest_file("/nonexistent/manifest.yaml")
