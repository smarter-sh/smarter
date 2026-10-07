"""
Test :mod:`smarter.apps.mcpclient.models`.

.. note::

    **Experimental.** The MCPClient was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.db import IntegrityError, transaction

from smarter.apps.mcpclient.manifest.enum import (
    SAMMCPClientAuthType,
    SAMMCPClientTransport,
)
from smarter.apps.mcpclient.manifest.models.mcpclient.const import (
    DEFAULT_API_KEY_HEADER,
    DEFAULT_CACHE_TTL,
    DEFAULT_PRIORITY,
    DEFAULT_TIMEOUT,
)
from smarter.apps.mcpclient.models import (
    MCPAuthType,
    MCPClient,
    MCPConnectionStatus,
    MCPTransport,
)
from smarter.apps.mcpclient.serializers import MCPClientSerializer

from .base_classes import (
    MCPCLIENT_NAME,
    TOKEN_SECRET_NAME,
    TOKEN_VALUE,
    MCPClientTestBase,
)


class TestMCPClientModel(MCPClientTestBase):
    """Test the MCPClient model and its serializer."""

    def test_defaults(self):
        """Test the defaults of a new MCPClient."""
        mcpclient = MCPClient(name="defaults")
        self.assertEqual(mcpclient.transport, MCPTransport.HTTP)
        self.assertEqual(mcpclient.auth_type, MCPAuthType.NONE)
        self.assertEqual(mcpclient.api_key_header, DEFAULT_API_KEY_HEADER)
        self.assertEqual(mcpclient.timeout, DEFAULT_TIMEOUT)
        self.assertEqual(mcpclient.cache_ttl, DEFAULT_CACHE_TTL)
        self.assertEqual(mcpclient.priority, DEFAULT_PRIORITY)
        self.assertEqual(mcpclient.status, MCPConnectionStatus.UNCONFIGURED)
        self.assertTrue(mcpclient.is_active)
        self.assertTrue(mcpclient.include_instructions)

    def test_choices_match_the_manifest(self):
        """Test that the model's choices match the manifest's enums."""
        self.assertEqual(sorted(MCPTransport.values), sorted(SAMMCPClientTransport.all()))
        self.assertEqual(sorted(MCPAuthType.values), sorted(SAMMCPClientAuthType.all()))

    def test_unique_name_per_user_profile(self):
        """Test that a user may not have two MCPClients with the same name."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_mcpclient(MCPCLIENT_NAME)

    def test_same_name_for_another_user(self):
        """Test that another user may have an MCPClient with the same name."""
        other = self.new_mcpclient(MCPCLIENT_NAME, user_profile=self.non_admin_user_profile)
        self.assertNotEqual(other.pk, self.mcpclient.pk)

    def test_fingerprint(self):
        """Test that the fingerprint is stable, and changes with the connection fields only."""
        mcpclient = MCPClient.objects.get(pk=self.mcpclient.pk)
        fingerprint = mcpclient.fingerprint
        self.assertEqual(len(fingerprint), 16)
        self.assertEqual(mcpclient.fingerprint, fingerprint)
        mcpclient.description = "a new description"
        mcpclient.priority = 99
        self.assertEqual(mcpclient.fingerprint, fingerprint)
        mcpclient.headers = {"X-Other": "1"}
        self.assertNotEqual(mcpclient.fingerprint, fingerprint)

    def test_credentials(self):
        """Test credential_name, and that deleting the Secret clears credentials rather than deleting the MCPClient."""
        secret = self.token_secret.__class__.objects.create(
            user_profile=self.user_profile,
            name="test_mcpclient_disposable_token",
            encrypted_value=self.token_secret.__class__.encrypt(TOKEN_VALUE),
        )
        mcpclient = self.new_mcpclient(
            "test_mcpclient_credentials", auth_type=MCPAuthType.BEARER_TOKEN, credentials=secret
        )
        self.assertEqual(mcpclient.credential_name, "test_mcpclient_disposable_token")
        secret.delete()
        mcpclient.refresh_from_db()
        self.assertIsNone(mcpclient.credentials)
        self.assertIsNone(mcpclient.credential_name)

    def test_serializer(self):
        """Test that the serializer renders credentials as the Secret's name, never its value."""
        mcpclient = self.new_mcpclient(
            "test_mcpclient_serializer", auth_type=MCPAuthType.BEARER_TOKEN, credentials=self.token_secret
        )
        data = MCPClientSerializer(mcpclient).data
        self.assertEqual(data["credentials"], TOKEN_SECRET_NAME)
        self.assertEqual(data["endpointUrl"], mcpclient.endpoint_url)
        self.assertNotIn(TOKEN_VALUE, str(data))
