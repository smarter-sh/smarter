"""
Tests of scripts/check_redis_chart.py's parsing of rendered manifests, and of its nested-mount check.

They need only the standard library, and run neither helm nor docker. Run them from the repository's root:

    python -m unittest discover -s scripts/tests -t scripts
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import check_redis_chart  # noqa: E402  pylint: disable=wrong-import-position

CONFIGMAP = """---
# Source: smarter/charts/redis/templates/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: smarter-redis-configuration
data:
  redis.conf: |-
    # User-supplied common configuration:
    appendonly yes

    save ""
    # End of common configuration
  master.conf: |-
    dir /data
    # End of master configuration
  start-master.sh: |
    #!/bin/bash
    exec redis-server
"""
"""A rendered ConfigMap, with Helm's ``|-`` (no final newline) and ``|`` (one) block scalars, and a blank line."""

STATEFULSET = """---
spec:
  template:
    spec:
      containers:
        - name: redis
          image: registry-1.docker.io/bitnami/redis@sha256:59078af5
          env:
            - name: REDIS_REPLICATION_MODE
              value: master
            - name: REDIS_PASSWORD_FILE
              value: "/opt/bitnami/redis/secrets/redis-password"
          volumeMounts:
            - name: start-scripts
              mountPath: /opt/bitnami/scripts/start-scripts
            - name: redis-password
              mountPath: /opt/bitnami/redis/secrets/
            - name: config
              mountPath: /opt/bitnami/redis/mounted-etc
            - name: empty-dir
              mountPath: /opt/bitnami/redis/etc/
              subPath: app-conf-dir
            - mountPath: /opt/bitnami/redis/users
              name: redis-users
"""
"""A rendered StatefulSet, with mounts written name-first and path-first, as Helm writes both."""

ACL_MOUNT = """            - name: redis-acl
              mountPath: /opt/bitnami/redis/mounted-etc/users.acl
              subPath: users.acl
"""
"""The mount of the Redis subchart's auth.acl, which kept Redis from starting in prod on 2026-11-27."""


class TestConfigmapData(unittest.TestCase):
    """Configmap_data() returns each file exactly as the pod's volume holds it."""

    def test_keeps_the_final_newline_as_helm_wrote_it(self):
        """``|-`` has no final newline, ``|`` has one: master.conf's missing newline once swallowed a line."""
        data = check_redis_chart.configmap_data(CONFIGMAP)
        self.assertEqual(data["master.conf"], "dir /data\n# End of master configuration")
        self.assertEqual(data["start-master.sh"], "#!/bin/bash\nexec redis-server\n")

    def test_keeps_blank_lines(self):
        data = check_redis_chart.configmap_data(CONFIGMAP)
        self.assertIn('appendonly yes\n\nsave ""', data["redis.conf"])

    def test_every_key(self):
        data = check_redis_chart.configmap_data(CONFIGMAP)
        self.assertEqual(sorted(data), ["master.conf", "redis.conf", "start-master.sh"])


class TestStatefulset(unittest.TestCase):
    """The environment, image and mounts read from a rendered StatefulSet."""

    def test_container_env(self):
        env = check_redis_chart.container_env(STATEFULSET)
        self.assertEqual(env["REDIS_REPLICATION_MODE"], "master")
        self.assertEqual(env["REDIS_PASSWORD_FILE"], "/opt/bitnami/redis/secrets/redis-password")

    def test_image_reference(self):
        image = check_redis_chart.image_reference(STATEFULSET)
        self.assertEqual(image, "registry-1.docker.io/bitnami/redis@sha256:59078af5")

    def test_volume_mounts_in_either_order(self):
        mounts = check_redis_chart.volume_mounts(STATEFULSET)
        self.assertIn(("redis-password", "/opt/bitnami/redis/secrets"), mounts)
        self.assertIn(("redis-users", "/opt/bitnami/redis/users"), mounts)
        self.assertEqual(len(mounts), 5)


class TestNestedMounts(unittest.TestCase):
    """A volume mounted inside another volume's mount is found: runc can't create it in a read-only volume."""

    def test_none_in_the_chart_as_it_is(self):
        mounts = check_redis_chart.volume_mounts(STATEFULSET)
        self.assertEqual(check_redis_chart.nested_mounts(mounts), [])

    def test_finds_the_acl_file_inside_the_configmap(self):
        manifest = STATEFULSET + ACL_MOUNT
        nested = check_redis_chart.nested_mounts(check_redis_chart.volume_mounts(manifest))
        self.assertEqual(
            nested,
            ["redis-acl at /opt/bitnami/redis/mounted-etc/users.acl, inside config at /opt/bitnami/redis/mounted-etc"],
        )

    def test_a_shared_prefix_is_not_nesting(self):
        """/opt/bitnami/redis/etc is not inside /opt/bitnami/redis/e, only beside it."""
        mounts = [("a", "/opt/bitnami/redis/e"), ("b", "/opt/bitnami/redis/etc")]
        self.assertEqual(check_redis_chart.nested_mounts(mounts), [])


class TestChecks(unittest.TestCase):
    """The lists of what the tool worker's user may and may not do."""

    def test_the_escalations_are_refused(self):
        refused = " ".join(description for description, _ in check_redis_chart.REFUSED_TO_TOOLS)
        for what in ("infrastructure queue", "routing set", "session", "RedBeat", "SCAN", "KEYS", "channels"):
            with self.subTest(what=what):
                self.assertIn(what, refused)

    def test_its_own_work_is_allowed(self):
        allowed = " ".join(description for description, _ in check_redis_chart.ALLOWED_TO_TOOLS)
        self.assertIn("its own queue", allowed)
        self.assertIn("result", allowed)


if __name__ == "__main__":
    unittest.main()
