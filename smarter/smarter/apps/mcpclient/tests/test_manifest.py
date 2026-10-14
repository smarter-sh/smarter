"""
Test the MCPClient Pydantic manifest: :mod:`smarter.apps.mcpclient.manifest.models.mcpclient`.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import copy
import glob
import os
from urllib.parse import urlparse

from pydantic import ValidationError

from smarter.apps.llmtool.plugin.safe_http import is_loopback_host
from smarter.apps.mcpclient.const import DATA_PATH
from smarter.apps.mcpclient.manifest.models.mcpclient.const import (
    DEFAULT_API_KEY_HEADER,
    DEFAULT_CACHE_TTL,
    DEFAULT_TIMEOUT,
    MAX_HEADERS,
    MAX_TIMEOUT,
)
from smarter.apps.mcpclient.manifest.models.mcpclient.model import SAMMCPClient
from smarter.apps.mcpclient.manifest.models.mcpclient.spec import (
    SAMMCPClientSpecConfig,
)
from smarter.apps.mcpclient.utils import MCPClientExamples, manifest_template_values
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import get_test_data

EXAMPLES_PATH = os.path.join(DATA_PATH, "mcpclients")
URL = "https://mcp.example.com/mcp"


class TestMCPClientManifest(SmarterTestBase):
    """Test SAMMCPClient and SAMMCPClientSpecConfig."""

    def config(self, **fields) -> SAMMCPClientSpecConfig:
        """Return a spec.config, with endpointUrl and any other fields."""
        return SAMMCPClientSpecConfig(**{"endpointUrl": URL, **fields})

    def assertInvalid(self, **fields):
        """Assert that a spec.config with these fields is rejected."""
        with self.assertRaises((SAMValidationError, ValidationError, ValueError)):
            self.config(**fields)

    def test_example_manifests(self):
        """Test that every example manifest and manifest template in data/mcpclients is valid."""
        examples = MCPClientExamples()
        self.assertEqual(
            examples.count(),
            len(
                glob.glob(os.path.join(EXAMPLES_PATH, "*.yaml")) + glob.glob(os.path.join(EXAMPLES_PATH, "*.yaml.tpl"))
            ),
        )
        self.assertGreaterEqual(examples.count(), 28)
        names = []
        for example in examples:
            with self.subTest(filename=example.filename):
                manifest = SAMMCPClient(**example.to_json())
                config = manifest.spec.config
                self.assertIn(config.transport, ("http", "sse"))
                hostname = urlparse(config.endpointUrl).hostname
                self.assertTrue(
                    config.endpointUrl.startswith("https://")
                    or (config.endpointUrl.startswith("http://") and is_loopback_host(hostname))
                )
                if config.authType != "none":
                    self.assertTrue(config.credentials)
                names.append(manifest.metadata.name)
        self.assertEqual(len(names), len(set(names)))

    def test_example_manifest_templates(self):
        """The smarter_project_* templates are filled in with this platform's scheme and domain."""
        values = manifest_template_values()
        templates = [example for example in MCPClientExamples() if example.is_template]
        self.assertEqual(len(templates), 10)
        for example in templates:
            with self.subTest(filename=example.filename):
                self.assertTrue(example.name.startswith("smarter_project"))
                endpoint_url = example.to_json()["spec"]["config"]["endpointUrl"]
                self.assertTrue(
                    endpoint_url.startswith(
                        f"{values['environment_platform_scheme']}://{values['environment_platform_domain']}"
                        "/api/v1/mcp/smarter-project/"
                    )
                )
                self.assertNotIn("$", example.to_yaml())

    def test_test_manifest(self):
        """Test the test manifest."""
        manifest = SAMMCPClient(**get_test_data("mcpclient.yaml"))
        self.assertEqual(manifest.metadata.name, "test_mcpclient")
        self.assertEqual(manifest.spec.config.headers, {"X-Client-Id": "smarter-tests"})

    def test_defaults(self):
        """Test the defaults of spec.config."""
        config = self.config()
        self.assertEqual(config.transport, "http")
        self.assertEqual(config.authType, "none")
        self.assertIsNone(config.credentials)
        self.assertEqual(config.apiKeyHeader, DEFAULT_API_KEY_HEADER)
        self.assertEqual(config.timeout, DEFAULT_TIMEOUT)
        self.assertEqual(config.cacheTtl, DEFAULT_CACHE_TTL)
        self.assertEqual(config.headers, {})
        self.assertEqual(config.allowedTools, [])
        self.assertEqual(config.allowedResources, [])
        self.assertTrue(config.includeInstructions)
        self.assertTrue(config.isActive)

    def test_transport(self):
        """Test that http and sse are accepted, case insensitively, and stdio is rejected."""
        self.assertEqual(self.config(transport="SSE").transport, "sse")
        self.assertInvalid(transport="stdio")
        self.assertInvalid(transport="websocket")

    def test_endpoint_url(self):
        """Test that the endpoint must be https, or http for localhost, may name a port, and has no credentials or fragment."""
        self.assertEqual(
            self.config(endpointUrl="https://mcp.example.com/mcp?x=1").endpointUrl, "https://mcp.example.com/mcp?x=1"
        )
        self.assertEqual(
            self.config(endpointUrl="https://mcp.example.com:443/mcp").endpointUrl, "https://mcp.example.com:443/mcp"
        )
        self.assertEqual(
            self.config(endpointUrl="https://localhost:9357/api/v1/mcp/").endpointUrl,
            "https://localhost:9357/api/v1/mcp/",
        )
        for url in (
            "http://localhost:9357/api/v1/mcp/",
            "http://api.localhost:9357/mcp",
            "http://127.0.0.1:8000/mcp",
            "http://[::1]:8000/mcp",
        ):
            with self.subTest(url=url):
                self.assertEqual(self.config(endpointUrl=url).endpointUrl, url)
        self.assertInvalid(endpointUrl="http://mcp.example.com/mcp")
        self.assertInvalid(endpointUrl="http://localhost.example.com/mcp")
        self.assertInvalid(endpointUrl="https://mcp.example.com:99999/mcp")
        self.assertInvalid(endpointUrl="https://user:password@mcp.example.com/mcp")
        self.assertInvalid(endpointUrl="https://mcp.example.com/mcp#fragment")
        self.assertInvalid(endpointUrl="not a url")

    def test_headers(self):
        """Test that custom headers are validated, and credential and transport headers are reserved."""
        self.assertEqual(self.config(headers={"X-Toolsets": "repos"}).headers, {"X-Toolsets": "repos"})
        for name in ("Authorization", "authorization", "Cookie", "Host", "Mcp-Session-Id", "Content-Type"):
            with self.subTest(name=name):
                self.assertInvalid(headers={name: "value"})
        self.assertInvalid(headers={"Bad Header": "value"})
        self.assertInvalid(headers={"X-Ok": "line one\r\nInjected: header"})
        self.assertInvalid(headers={f"X-Header-{i}": "v" for i in range(MAX_HEADERS + 1)})

    def test_timeout_and_cache_ttl(self):
        """Test the bounds of timeout and cacheTtl."""
        self.assertEqual(self.config(timeout=MAX_TIMEOUT).timeout, MAX_TIMEOUT)
        self.assertEqual(self.config(cacheTtl=0).cacheTtl, 0)
        self.assertInvalid(timeout=0)
        self.assertInvalid(timeout=MAX_TIMEOUT + 1)
        self.assertInvalid(cacheTtl=-1)

    def test_credentials(self):
        """Test that credentials are required unless authType is none, and forbidden if it is."""
        for auth_type in ("api_key", "bearer_token", "oauth2"):
            with self.subTest(auth_type=auth_type):
                self.assertEqual(self.config(authType=auth_type, credentials="a_secret").credentials, "a_secret")
                self.assertInvalid(authType=auth_type)
        self.assertInvalid(authType="none", credentials="a_secret")
        self.assertInvalid(authType="basic", credentials="a_secret")

    def test_api_key_header(self):
        """Test that the api key header must be a valid, unreserved header name."""
        config = self.config(authType="api_key", credentials="a_secret", apiKeyHeader="CONTEXT7_API_KEY")
        self.assertEqual(config.apiKeyHeader, "CONTEXT7_API_KEY")
        self.assertInvalid(authType="api_key", credentials="a_secret", apiKeyHeader="Cookie")
        self.assertInvalid(authType="api_key", credentials="a_secret", apiKeyHeader="bad header")

    def test_patterns(self):
        """Test that allowedTools and allowedResources are deduplicated, and must not contain empty strings."""
        config = self.config(allowedTools=["search_*", " search_* ", "get_issue"])
        self.assertEqual(config.allowedTools, ["search_*", "get_issue"])
        self.assertInvalid(allowedTools=[""])
        self.assertInvalid(allowedResources=["  "])

    def test_immutable(self):
        """Test that the manifest is immutable."""
        manifest = SAMMCPClient(**get_test_data("mcpclient.yaml"))
        with self.assertRaises(ValidationError):
            manifest.spec.config.timeout = 1

    def test_status_is_optional(self):
        """Test that a manifest may omit its status."""
        data = copy.deepcopy(get_test_data("mcpclient.yaml"))
        data.pop("status", None)
        self.assertIsNone(SAMMCPClient(**data).status)
