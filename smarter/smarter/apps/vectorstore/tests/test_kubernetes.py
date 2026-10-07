"""Test self-hosted Qdrant on Kubernetes: :mod:`smarter.apps.vectorstore.kubernetes`."""

import yaml

from smarter.apps.vectorstore.kubernetes import (
    API_KEY_ENV,
    DESTROY_KINDS,
    LABEL,
    STOP_KINDS,
    QdrantKubernetes,
    VectorstoreKubernetesError,
    unprivileged,
)

from .base_classes import VectorstoreTestBase


class TestQdrantKubernetes(VectorstoreTestBase):
    """Test the rendering, and the lifecycle, of a self-hosted Qdrant server's resources."""

    def qdrant(self, **spec_overrides) -> QdrantKubernetes:
        return QdrantKubernetes(self.new_vectorstore("test_k8s", **spec_overrides), kubernetes=self.kubernetes)  # type: ignore[arg-type]

    def test_render(self):
        """Test the Secret, Service and StatefulSet."""
        qdrant = self.qdrant(selfHosted={"storage": "5Gi", "storageClass": "gp3", "cpu": "250m", "memory": "512Mi"})
        secret, service, statefulset = qdrant.render("the-key")
        self.assertEqual([secret["kind"], service["kind"], statefulset["kind"]], ["Secret", "Service", "StatefulSet"])
        for resource in (secret, service, statefulset):
            self.assertEqual(resource["metadata"]["labels"][LABEL], qdrant.name)
        self.assertEqual(secret["stringData"]["api-key"], "the-key")
        self.assertEqual(service["spec"]["type"], "ClusterIP")
        pod = statefulset["spec"]["template"]["spec"]
        container = pod["containers"][0]
        self.assertTrue(container["image"].endswith("-unprivileged"))
        self.assertTrue(container["securityContext"]["runAsNonRoot"])
        self.assertEqual(container["resources"]["requests"], {"cpu": "250m", "memory": "512Mi"})
        env = {e["name"]: e for e in container["env"]}
        self.assertEqual(env[API_KEY_ENV]["valueFrom"]["secretKeyRef"]["name"], qdrant.name)
        claim = statefulset["spec"]["volumeClaimTemplates"][0]
        self.assertEqual(claim["spec"]["resources"]["requests"]["storage"], "5Gi")
        self.assertEqual(claim["spec"]["storageClassName"], "gp3")
        self.assertEqual(claim["metadata"]["labels"][LABEL], qdrant.name)
        self.assertTrue(qdrant.endpoint.startswith(f"http://{qdrant.name}."))

    def test_unprivileged(self):
        self.assertEqual(unprivileged("qdrant/qdrant:v1.19.1"), "qdrant/qdrant:v1.19.1-unprivileged")
        self.assertEqual(unprivileged("qdrant/qdrant:v1.19.1-unprivileged"), "qdrant/qdrant:v1.19.1-unprivileged")
        self.assertEqual(unprivileged("registry.example.com/qdrant:1"), "registry.example.com/qdrant:1")

    def test_apply_stop_destroy(self):
        """Test that apply sends the manifest, stop keeps the volume, and destroy deletes it."""
        qdrant = self.qdrant()
        qdrant.apply("the-key")
        kinds = [doc["kind"] for doc in yaml.safe_load_all(self.kubernetes.applied[0])]
        self.assertEqual(kinds, ["Secret", "Service", "StatefulSet"])
        qdrant.stop()
        qdrant.destroy()
        self.assertEqual(self.kubernetes.deleted, [(STOP_KINDS, qdrant.selector), (DESTROY_KINDS, qdrant.selector)])
        self.assertNotIn("persistentvolumeclaim", STOP_KINDS)
        self.assertEqual(qdrant.logs(), f"logs of {qdrant.selector}")

    def test_cluster_unavailable(self):
        """Test that nothing is attempted, and an error raised, when the cluster is unavailable."""
        qdrant = self.qdrant()
        self.kubernetes.ready = False
        with self.assertRaises(VectorstoreKubernetesError):
            qdrant.apply("the-key")
        with self.assertRaises(VectorstoreKubernetesError):
            qdrant.destroy()
        self.assertEqual(self.kubernetes.applied, [])

    def test_rejected(self):
        qdrant = self.qdrant()
        self.kubernetes.fail_apply = "admission webhook denied"
        with self.assertRaisesRegex(VectorstoreKubernetesError, "admission webhook denied"):
            qdrant.apply("the-key")

    def test_observe(self):
        """Test the observation of a missing, starting, crashing and ready server."""
        qdrant = self.qdrant()
        self.kubernetes.statefulset = None
        self.assertFalse(qdrant.observe().exists)
        self.kubernetes.statefulset = {"status": {"readyReplicas": 0}}
        self.assertEqual(qdrant.observe().message, "The Qdrant server is starting.")
        self.kubernetes.pods = [
            {
                "status": {
                    "containerStatuses": [
                        {"state": {"waiting": {"reason": "ImagePullBackOff", "message": "no such tag"}}}
                    ]
                }
            }
        ]
        observation = qdrant.observe()
        self.assertFalse(observation.ready)
        self.assertIn("ImagePullBackOff", observation.message)
        self.kubernetes.statefulset = {"status": {"readyReplicas": 1}}
        self.assertTrue(qdrant.observe().ready)
