"""Test the Proxy manifest's Pydantic models, :mod:`smarter.apps.proxy.manifest.models.proxy`."""

import os
import unittest

from pydantic import ValidationError

from smarter.apps.proxy.builtins import builtin_manifest_files
from smarter.apps.proxy.manifest.models.proxy.const import MANIFEST_KIND
from smarter.apps.proxy.manifest.models.proxy.metadata import SAMProxyMetadata
from smarter.apps.proxy.manifest.models.proxy.model import SAMProxy
from smarter.apps.proxy.manifest.models.proxy.spec import SAMProxySpec, SAMProxySpecAuth
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader

from .base_classes import get_data_path, get_test_data

INVALID = (SAMValidationError, ValidationError)


def spec(**changes) -> dict:
    """The test manifest's spec, with changes.

    A None value removes the field.
    """
    retval = get_test_data("proxy.yaml")["spec"]
    for key, value in changes.items():
        if value is None:
            retval.pop(key, None)
        else:
            retval[key] = value
    return retval


class TestSAMProxySpec(unittest.TestCase):
    """Test the validation of Proxy.spec."""

    def test_valid(self):
        model = SAMProxySpec(**spec())
        self.assertEqual(model.provider, "test_proxy_provider")
        self.assertEqual(model.apiKey, "test_proxy_api_key")
        self.assertEqual(model.headers, {"OpenAI-Beta": "assistants=v2"})
        self.assertEqual(model.allowedPaths, ["chat/completions", "embeddings", "models", "models/*"])

    def test_defaults(self):
        """Test that only the provider is required."""
        model = SAMProxySpec(provider="openai")
        self.assertIsNone(model.apiKey)
        self.assertIsNone(model.baseUrl)
        self.assertEqual((model.auth.header, model.auth.scheme), ("Authorization", "Bearer"))
        self.assertEqual((model.headers, model.allowedPaths, model.timeout, model.isActive), ({}, [], 120, True))

    def test_unknown_field(self):
        """Test that unknown fields are refused, to catch typos."""
        with self.assertRaises(INVALID):
            SAMProxySpec(**spec(allowedPath=["x"]))
        with self.assertRaises(INVALID):
            SAMProxySpec(**spec(auth={"header": "x-api-key", "schema": ""}))

    def test_provider(self):
        with self.assertRaises(INVALID):
            SAMProxySpec(**spec(provider=None))
        for name in ("", "open ai", "openai/../x"):
            with self.subTest(name=name), self.assertRaises(INVALID):
                SAMProxySpec(**spec(provider=name))

    def test_api_key(self):
        """Test that apiKey is a Secret's name, and that an API key itself is refused."""
        self.assertIsNone(SAMProxySpec(**spec(apiKey=None)).apiKey)
        with self.assertRaises(INVALID):
            SAMProxySpec(**spec(apiKey="sk-proj abc.def"))

    def test_base_url(self):
        self.assertEqual(SAMProxySpec(**spec(baseUrl="https://api.x.com/v1")).baseUrl, "https://api.x.com/v1/")
        self.assertEqual(
            SAMProxySpec(**spec(baseUrl="http://localhost:11434/v1/")).baseUrl, "http://localhost:11434/v1/"
        )
        for url in (
            "ftp://api.x.com/",
            "api.x.com/v1/",
            "https://user:pass@api.x.com/",
            "https://api.x.com/v1/?key=abc",
            "https://api.x.com/v1/#x",
        ):
            with self.subTest(url=url), self.assertRaises(INVALID):
                SAMProxySpec(**spec(baseUrl=url))

    def test_auth(self):
        auth = SAMProxySpecAuth(header="x-api-key", scheme="")
        self.assertEqual((auth.header, auth.scheme), ("x-api-key", ""))
        self.assertEqual(SAMProxySpecAuth(header="x-api-key", scheme=None).scheme, "")
        for header in ("Host", "Content-Length", "Cookie", "Connection", "bad header", "x:y"):
            with self.subTest(header=header), self.assertRaises(INVALID):
                SAMProxySpecAuth(header=header)
        with self.assertRaises(INVALID):
            SAMProxySpecAuth(scheme="Bearer token")

    def test_headers(self):
        """Test that headers may not set credentials, hop-by-hop headers, or line breaks."""
        self.assertEqual(
            SAMProxySpec(**spec(headers={"anthropic-version": "2023-06-01"})).headers["anthropic-version"], "2023-06-01"
        )
        for headers in (
            {"Authorization": "Bearer x"},
            {"x-api-key": "x"},
            {"Host": "evil.example.com"},
            {"Cookie": "x"},
            {"Transfer-Encoding": "chunked"},
            {"X-Forwarded-For": "1.2.3.4"},
            {"bad header": "x"},
            {"x-ok": "a\r\nInjected: b"},
        ):
            with self.subTest(headers=headers), self.assertRaises(INVALID):
                SAMProxySpec(**spec(headers=headers))

    def test_allowed_paths(self):
        model = SAMProxySpec(**spec(allowedPaths=["/v1/messages/", "models/*:generateContent"]))
        self.assertEqual(model.allowedPaths, ["v1/messages", "models/*:generateContent"])
        for pattern in ("", "../files", "a b", "https://x/"):
            with self.subTest(pattern=pattern), self.assertRaises(INVALID):
                SAMProxySpec(**spec(allowedPaths=[pattern]))

    def test_timeout(self):
        for timeout in (0, 601, -1):
            with self.subTest(timeout=timeout), self.assertRaises(INVALID):
                SAMProxySpec(**spec(timeout=timeout))


class TestSAMProxy(unittest.TestCase):
    """Test the Proxy manifest, and the built-in manifests."""

    def test_test_manifest(self):
        loader = SAMLoader(file_path=get_data_path("proxy.yaml"))
        model = SAMProxy(
            apiVersion=loader.manifest_api_version,
            kind=loader.manifest_kind,
            metadata=SAMProxyMetadata(**loader.manifest_metadata),
            spec=SAMProxySpec(**loader.manifest_spec),
        )
        self.assertEqual(model.kind, MANIFEST_KIND)
        self.assertEqual(MANIFEST_KIND, "Proxy")
        self.assertIsNone(model.status)

    def test_builtin_manifests(self):
        """Test that every built-in manifest is valid, restricts its paths, and names a Secret."""
        files = builtin_manifest_files()
        self.assertGreaterEqual(len(files), 9)
        names = set()
        for filename in files:
            with self.subTest(manifest=os.path.basename(filename)):
                loader = SAMLoader(file_path=filename)
                self.assertEqual(loader.manifest_kind, MANIFEST_KIND)
                metadata = SAMProxyMetadata(**loader.manifest_metadata)
                model = SAMProxySpec(**loader.manifest_spec)
                self.assertTrue(model.allowedPaths, "a built-in Proxy must restrict its paths.")
                self.assertTrue(model.apiKey)
                self.assertTrue(model.baseUrl and model.baseUrl.startswith("https://"))
                self.assertIn({"smarter.sh/proxy/builtin": "true"}, metadata.annotations)
                names.add(metadata.name)
        self.assertEqual(len(names), len(files), "built-in Proxy names must be unique.")
        self.assertTrue({"openai", "anthropic", "googleai", "mistral"} <= names)
