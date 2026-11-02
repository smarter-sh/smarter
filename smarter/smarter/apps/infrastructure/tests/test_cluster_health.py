"""Test smarter.apps.infrastructure.cluster_health, and the cluster health of the base and in-memory providers."""

from smarter.apps.infrastructure.cluster_health import (
    AddonHealth,
    ClusterHealth,
    HealthIssue,
    version_key,
)
from smarter.apps.infrastructure.exceptions import InfrastructureNotReadyError

from .base import InfrastructureTestBase


class TestVersionKey(InfrastructureTestBase):
    """Test version_key()."""

    def test_versions_compare_by_their_numbers(self):
        self.assertEqual(version_key("v1.19.0-eksbuild.2"), (1, 19, 0, 2))
        self.assertLess(version_key("v1.9.0"), version_key("v1.19.0"), "as text, v1.9.0 would sort last")
        self.assertEqual(version_key("latest"), ())


class TestAddonHealth(InfrastructureTestBase):
    """Test AddonHealth.update_available."""

    def test_update_available(self):
        self.assertTrue(AddonHealth(name="coredns", version="v1.9.0", latest_version="v1.11.0").update_available)
        self.assertFalse(AddonHealth(name="coredns", version="v1.11.0", latest_version="v1.11.0").update_available)
        self.assertFalse(AddonHealth(name="coredns", version="v1.11.0").update_available, "the latest is unknown")


class TestProviderClusterHealth(InfrastructureTestBase):
    """Test CloudProvider.get_kubernetes_cluster_health(), with the in-memory provider."""

    def test_from_cluster_info(self):
        """Without a health of its own, a provider's health is built from its cluster info."""
        self.provider.cluster_info["health"] = {"issues": [{"code": "IamRoleNotFound", "message": "role"}, "junk"]}
        health = self.provider.get_kubernetes_cluster_health()
        self.assertEqual((health.status, health.version, health.platform_version), ("ACTIVE", "1.33", "memory"))
        self.assertEqual(health.issues, (HealthIssue(code="IamRoleNotFound", message="role"),))
        self.assertEqual(health.nodegroups, [])

    def test_configured(self):
        """A test's health is returned as a copy."""
        self.provider.cluster_health = ClusterHealth(name="test", addons=[AddonHealth(name="coredns")])
        health = self.provider.get_kubernetes_cluster_health()
        health.addons.clear()
        self.assertEqual(len(self.provider.get_kubernetes_cluster_health().addons), 1)

    def test_not_ready(self):
        self.provider.ready = False
        with self.assertRaises(InfrastructureNotReadyError):
            self.provider.get_kubernetes_cluster_health()
        self.provider.cluster_health = ClusterHealth(name="test")
        with self.assertRaises(InfrastructureNotReadyError):
            self.provider.get_kubernetes_cluster_health()
