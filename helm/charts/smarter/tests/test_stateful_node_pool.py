"""
Tests of how MariaDB, Redis and Loki are placed on the stateful node pool, in values.yaml.

smarter-infrastructure creates one on-demand node per environment, labeled and tainted
``smarter.sh/node-pool=stateful`` (aws/terraform/smarter/node-group-stateful.tf), so that a spot
reclaim no longer takes them down (issue #942). These tests check that:

- the toleration and node affinity are defined once, as YAML anchors, and that every one of the
  services uses them, so the pool's key and value live in one place;
- the affinity is preferred, not required, so the pods still start when the pool has no node;
- the services' memory requests fit on the pool's node (a t3.medium) together;
- their PodDisruptionBudgets let a node drain evict them, so that an upgrade of the node group
  proceeds on its own.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import re
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
VALUES_PATH = CHART_PATH / "values.yaml"

NODE_POOL_KEY = "smarter.sh/node-pool"
"""The label and taint key of the stateful node pool, as smarter-infrastructure sets it."""

NODE_POOL_VALUE = "stateful"
"""The label and taint value of the stateful node pool, as smarter-infrastructure sets it."""

STATEFUL_NODE_MEMORY_BUDGET_MI = 2560
"""
The memory, in MiB, that the stateful services may request together.

A t3.medium has about 3.4 GiB allocatable. The DaemonSets on every node (aws-node, kube-proxy, the
EBS CSI node, Calico) request a few hundred MiB of it. This budget leaves room for them.
"""

TOP_LEVEL_KEY_PATTERN = re.compile(r"^(\w+):", re.MULTILINE)
"""A key at the top level of values.yaml, e.g. ``mariadb:``."""

MEMORY_REQUEST_PATTERN = re.compile(
    r"^    resources:\n      requests:\n(?:        .*\n)*?        memory: \"?(\d+)(Mi|Gi)\"?$",
    re.MULTILINE,
)
"""The memory request of a component's resources, indented under e.g. mariadb.primary."""


def values_text() -> str:
    """
    Return values.yaml.

    :returns: Its text.
    """
    text = VALUES_PATH.read_text(encoding="utf-8")
    return text


def top_level_block(name: str) -> str:
    """
    Return one top-level block of values.yaml, e.g. ``mariadb``.

    :param name: The block's key.
    :returns: Its text, from its key up to the next top-level key.
    :raises AssertionError: If values.yaml has no such block.
    """
    text = values_text()
    start_match = re.search(rf"^{name}:\n", text, re.MULTILINE)
    if start_match is None:
        raise AssertionError(f"values.yaml has no {name} block")
    start = start_match.end()
    next_key_match = TOP_LEVEL_KEY_PATTERN.search(text, start)
    end = len(text)
    if next_key_match is not None:
        end = next_key_match.start()
    block = text[start:end]
    return block


def memory_request_mi(block: str) -> int:
    """
    Return the first memory request in a block of values.yaml, in MiB.

    :param block: The text of a top-level block.
    :returns: Its memory request, in MiB.
    :raises AssertionError: If the block has no memory request.
    """
    match = MEMORY_REQUEST_PATTERN.search(block)
    if match is None:
        raise AssertionError("the block has no resources.requests.memory")
    amount = int(match.group(1))
    unit = match.group(2)
    if unit == "Gi":
        amount = amount * 1024
    return amount


class TestStatefulNodePool(unittest.TestCase):
    """MariaDB, Redis and Loki prefer the stateful node pool, and fit on it."""

    def test_anchors_are_defined_once(self):
        """The toleration and affinity are written once, so the pool's key lives in one place."""
        text = values_text()
        self.assertEqual(text.count("&statefulNodePoolTolerations"), 1)
        self.assertEqual(text.count("&statefulNodePoolAffinity"), 1)

    def test_mariadb_defines_the_anchors(self):
        """MariaDB's primary carries the definitions, with the pool's key and value."""
        block = top_level_block("mariadb")
        self.assertIn("tolerations: &statefulNodePoolTolerations", block)
        self.assertIn("affinity: &statefulNodePoolAffinity", block)
        self.assertIn(f"key: {NODE_POOL_KEY}", block)
        self.assertIn(f"value: {NODE_POOL_VALUE}", block)
        self.assertIn("effect: NoSchedule", block)

    def test_redis_uses_the_anchors(self):
        """Redis's master references the same toleration and affinity."""
        block = top_level_block("redis")
        self.assertIn("tolerations: *statefulNodePoolTolerations", block)
        self.assertIn("affinity: *statefulNodePoolAffinity", block)

    def test_loki_uses_the_anchors(self):
        """Loki's single binary references the same toleration and affinity."""
        block = top_level_block("loki")
        self.assertIn("tolerations: *statefulNodePoolTolerations", block)
        self.assertIn("affinity: *statefulNodePoolAffinity", block)

    def test_affinity_is_preferred(self):
        """When the pool has no node, the pods run elsewhere rather than staying Pending."""
        block = top_level_block("mariadb")
        self.assertIn("preferredDuringSchedulingIgnoredDuringExecution", block)
        self.assertNotIn("requiredDuringSchedulingIgnoredDuringExecution", block)

    def test_memory_requests_fit_the_node(self):
        """The scheduler places pods by their requests, so together they must fit the node."""
        mariadb_mi = memory_request_mi(top_level_block("mariadb"))
        redis_mi = memory_request_mi(top_level_block("redis"))
        loki_mi = memory_request_mi(top_level_block("loki"))
        total_mi = mariadb_mi + redis_mi + loki_mi
        self.assertLessEqual(total_mi, STATEFUL_NODE_MEMORY_BUDGET_MI)

    def test_disruption_budgets_allow_a_drain(self):
        """A node group upgrade may evict MariaDB and Redis, instead of failing after 15 minutes."""
        for name in ("mariadb", "redis"):
            with self.subTest(name=name):
                block = top_level_block(name)
                self.assertRegex(block, r"(?m)^    pdb:\n(?:      .*\n)*?      maxUnavailable: 1$")
                self.assertNotRegex(block, r"(?m)^      minAvailable: 1$")


if __name__ == "__main__":
    unittest.main()
