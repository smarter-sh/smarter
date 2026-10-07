"""Test the Kubernetes resources of an LLMHost: :mod:`smarter.apps.llmhost.services.renderer`."""

from typing import Any

from smarter.apps.llmhost.const import MODELS_MOUNT_PATH, SHM_MOUNT_PATH
from smarter.apps.llmhost.manifest.models.llmhost.spec import SAMLLMHostSpec
from smarter.apps.llmhost.services.renderer import (
    RenderContext,
    dns_label,
    label_selector,
    render_resources,
    resource_name,
)
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

from .base_classes import spec_data

BASE_NAME = "llmhost-12-test-llmhost"


def context(
    hf_token: bool = True, api_key: bool = True, hostname: str = "llm.example.com", **overrides
) -> RenderContext:
    """A render context for the test manifest, with spec overrides."""
    return RenderContext(
        base_name=BASE_NAME,
        namespace="smarter-platform-test",
        spec=SAMLLMHostSpec(**spec_data(**overrides)),
        served_name="test_llmhost",
        account_number="1234-5678-9012",
        hostname=hostname,
        cluster_issuer="api.example.com",
        hf_token=hf_token,
        api_key=api_key,
    )


def by_kind(resources: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {resource["kind"]: resource for resource in resources}


class TestRenderer(SmarterTestBase):
    """Test render_resources() and its helpers."""

    def render(
        self, ctx: RenderContext = None, hf_token="hf_secret", api_key="api_secret"
    ) -> dict[str, dict[str, Any]]:
        return by_kind(render_resources(ctx or context(), hf_token=hf_token, api_key=api_key))

    def container(self, resources: dict[str, dict[str, Any]]) -> dict[str, Any]:
        return resources["Deployment"]["spec"]["template"]["spec"]["containers"][0]

    def test_names(self):
        """Test that resource names are DNS labels, unique by id, and short enough for pod names."""
        self.assertEqual(dns_label("Llama_3.1 8B__Instruct"), "llama-3-1-8b-instruct")
        self.assertEqual(resource_name(12, "test_llmhost"), BASE_NAME)
        long_name = resource_name(123456, "a_very_long_llmhost_name_that_goes_on_and_on_and_on")
        self.assertLessEqual(len(long_name), 50)
        self.assertFalse(long_name.endswith("-"))
        self.assertTrue(long_name.startswith("llmhost-123456-"))
        self.assertEqual(label_selector(BASE_NAME), f"smarter.sh/llmhost={BASE_NAME}")

    def test_resources(self):
        """Test that the resources are rendered in the order in which they are applied, all labeled and namespaced."""
        resources = render_resources(context(), hf_token="t", api_key="k")
        self.assertEqual(
            [r["kind"] for r in resources], ["PersistentVolumeClaim", "Secret", "Deployment", "Service", "Ingress"]
        )
        for resource in resources:
            with self.subTest(kind=resource["kind"]):
                self.assertEqual(resource["metadata"]["namespace"], "smarter-platform-test")
                self.assertEqual(resource["metadata"]["labels"]["smarter.sh/llmhost"], BASE_NAME)
                self.assertEqual(resource["metadata"]["labels"]["smarter.sh/account-number"], "1234-5678-9012")

    def test_volume_claim(self):
        """Test the model volume, and that an existing claim is mounted instead of created."""
        claim = self.render(context(storage={"size": "80Gi", "storageClass": "gp3"}))["PersistentVolumeClaim"]
        self.assertEqual(claim["metadata"]["name"], f"{BASE_NAME}-models")
        self.assertEqual(claim["spec"]["resources"]["requests"]["storage"], "80Gi")
        self.assertEqual(claim["spec"]["storageClassName"], "gp3")
        self.assertEqual(claim["spec"]["accessModes"], ["ReadWriteOnce"])
        resources = self.render(context(storage={"existingClaim": "shared-weights"}))
        self.assertNotIn("PersistentVolumeClaim", resources)
        volumes = resources["Deployment"]["spec"]["template"]["spec"]["volumes"]
        self.assertEqual(volumes[0]["persistentVolumeClaim"]["claimName"], "shared-weights")

    def test_secret(self):
        """Test that the token and API key are only in the Secret, and the container refers to them."""
        resources = self.render()
        self.assertEqual(resources["Secret"]["stringData"], {"HF_TOKEN": "hf_secret", "API_KEY": "api_secret"})
        deployment = json.dumps(resources["Deployment"])
        self.assertNotIn("hf_secret", deployment)
        self.assertNotIn("api_secret", deployment)
        env = {e["name"]: e for e in self.container(resources)["env"]}
        self.assertEqual(env["HF_TOKEN"]["valueFrom"]["secretKeyRef"], {"name": BASE_NAME, "key": "HF_TOKEN"})
        self.assertEqual(env["VLLM_API_KEY"]["valueFrom"]["secretKeyRef"], {"name": BASE_NAME, "key": "API_KEY"})

    def test_no_secret(self):
        """Test that there is no Secret, nor references to it, without a token or an API key."""
        resources = self.render(context(hf_token=False, api_key=False), hf_token=None, api_key=None)
        self.assertNotIn("Secret", resources)
        self.assertNotIn("secretKeyRef", json.dumps(resources["Deployment"]))

    def test_container(self):
        """Test the container's image, args, port, resources, mounts and probes."""
        container = self.container(self.render())
        self.assertEqual(container["name"], "engine")
        self.assertEqual(container["image"], "vllm/vllm-openai:latest")
        self.assertIn("meta-llama/Llama-3.1-8B-Instruct", container["args"])
        self.assertEqual(container["ports"][0]["containerPort"], 8000)
        self.assertEqual(container["resources"]["limits"], {"memory": "24Gi", "nvidia.com/gpu": 1})
        self.assertEqual(container["resources"]["requests"]["cpu"], "4")
        self.assertEqual([m["mountPath"] for m in container["volumeMounts"]], [MODELS_MOUNT_PATH, SHM_MOUNT_PATH])
        # 1800 seconds to start, checked every 10 seconds.
        self.assertEqual(container["startupProbe"]["failureThreshold"], 180)
        self.assertEqual(container["readinessProbe"]["httpGet"], {"path": "/health", "port": "http"})
        self.assertEqual(container["livenessProbe"]["httpGet"]["path"], "/health")
        self.assertNotIn("command", container)

    def test_default_resources(self):
        """Test the default cpu and memory requests."""
        container = self.container(self.render(context(resources={"cpu": None, "memory": None})))
        self.assertEqual(container["resources"]["requests"]["cpu"], "2")
        self.assertEqual(container["resources"]["limits"]["memory"], "8Gi")

    def test_scheduling(self):
        """Test the GPU toleration, the node selector, and the service account.

        Pods are not pinned to an instance type.
        """
        pod = self.render(context(resources={"nodeSelector": {"pool": "gpu"}, "serviceAccountName": "model-reader"}))[
            "Deployment"
        ]["spec"]["template"]["spec"]
        self.assertEqual(pod["nodeSelector"], {"pool": "gpu"})
        self.assertEqual(pod["tolerations"], [{"key": "nvidia.com/gpu", "operator": "Exists", "effect": "NoSchedule"}])
        self.assertEqual(pod["serviceAccountName"], "model-reader")
        self.assertEqual(pod["volumes"][1]["emptyDir"], {"medium": "Memory", "sizeLimit": "8Gi"})

    def test_cpu_scheduling(self):
        """Test that a CPU LLMHost requests no GPU, and tolerates no GPU taint."""
        resources = by_kind(
            render_resources(
                RenderContext(
                    base_name="llmhost-1-ollama",
                    namespace="ns",
                    spec=SAMLLMHostSpec(**spec_data("llmhost-ollama.yaml")),
                    served_name="ollama",
                    account_number="1",
                )
            )
        )
        pod = resources["Deployment"]["spec"]["template"]["spec"]
        self.assertNotIn("tolerations", pod)
        self.assertNotIn("nodeSelector", pod)
        self.assertNotIn("nvidia.com/gpu", pod["containers"][0]["resources"]["limits"])
        self.assertIn("exec", pod["containers"][0]["readinessProbe"])
        self.assertNotIn("Ingress", resources)
        self.assertNotIn("Secret", resources)

    def test_strategy(self):
        """Test that a ReadWriteOnce volume is replaced with Recreate, and a shared volume rolls."""
        self.assertEqual(self.render()["Deployment"]["spec"]["strategy"], {"type": "Recreate"})
        deployment = self.render(context(storage={"accessMode": "ReadWriteMany"}, scaling={"replicas": 2}))[
            "Deployment"
        ]
        self.assertEqual(deployment["spec"]["strategy"], {"type": "RollingUpdate"})
        self.assertEqual(deployment["spec"]["replicas"], 2)
        self.assertEqual(deployment["spec"]["selector"]["matchLabels"], {"smarter.sh/llmhost": BASE_NAME})

    def test_init_containers(self):
        """Test that a downloaded source adds its init container."""
        pod = self.render(context(model={"source": "s3", "repository": "s3://bucket/llama", "revision": None}))[
            "Deployment"
        ]["spec"]["template"]["spec"]
        self.assertEqual(pod["initContainers"][0]["name"], "download-model")
        self.assertNotIn("initContainers", self.render()["Deployment"]["spec"]["template"]["spec"])

    def test_service(self):
        """Test that the Service exposes the engine's port as port 80."""
        service = self.render()["Service"]
        self.assertEqual(service["spec"]["ports"][0]["port"], 80)
        self.assertEqual(service["spec"]["ports"][0]["targetPort"], "http")
        self.assertEqual(service["spec"]["selector"], {"smarter.sh/llmhost": BASE_NAME})

    def test_ingress(self):
        """Test the Ingress: the hostname, TLS with cert-manager, and the Service backend."""
        ingress = self.render()["Ingress"]
        self.assertEqual(ingress["spec"]["rules"][0]["host"], "llm.example.com")
        self.assertEqual(ingress["spec"]["tls"][0]["secretName"], f"{BASE_NAME}-tls")
        self.assertEqual(ingress["metadata"]["annotations"]["cert-manager.io/cluster-issuer"], "api.example.com")
        backend = ingress["spec"]["rules"][0]["http"]["paths"][0]["backend"]["service"]
        self.assertEqual(backend, {"name": BASE_NAME, "port": {"number": 80}})
        self.assertNotIn("Ingress", self.render(context(network={"ingress": False})))
        self.assertNotIn("Ingress", self.render(context(hostname=None)))

    def test_urls(self):
        """Test the endpoint inside the cluster, the health check URL, and the public URL."""
        ctx = context()
        self.assertEqual(ctx.endpoint, f"http://{BASE_NAME}.smarter-platform-test.svc.cluster.local/v1")
        self.assertEqual(ctx.health_check_url, f"http://{BASE_NAME}.smarter-platform-test.svc.cluster.local/health")
        self.assertEqual(ctx.public_url, "https://llm.example.com/v1")
        self.assertIsNone(context(network={"ingress": False}).public_url)
