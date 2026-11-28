"""
Tests of the egress proxy, egressProxy in values.yaml (ADR-038, phase 4, #1085).

The proxy is Smokescreen, which the app, the workers, Beat and the Jobs send their HTTP and HTTPS
requests through, and which logs each host they contact. These tests check that it is off by
default, and changes nothing then; that enabled, it holds nothing of the platform's, and its ACL
allows every host in report mode and refuses the unlisted ones in enforce mode; that the platform's
pods, and only they, send their requests through it; that they send the cluster's own services
around it, which it would refuse; and that the deploy action turns it on.

They render the chart with helm. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import re
import unittest

from chart_render import (
    APP_NAME,
    CHART_PATH,
    NAMESPACE,
    documents_of_kind,
    kind_and_name,
    needs_helm,
    render,
    service_type,
    workloads,
)

ACTION_PATH = CHART_PATH.parent.parent.parent / ".github" / "actions" / "deploy" / "action.yml"
WORKFLOW_PATH = CHART_PATH.parent.parent.parent / ".github" / "workflows" / "deploy.yml"

PROXY_NAME = f"{APP_NAME}-egress-proxy"
PROXY_URL = f"http://{PROXY_NAME}.{NAMESPACE}.svc.cluster.local:4750"

PROXIED_KINDS = ("api", "worker", "worker-infrastructure", "beat", "job-init", "job-migrate", "job-backup")
"""The kinds of pod whose requests go through the proxy."""

UNPROXIED_WORKLOADS = (f"{APP_NAME}-worker-tools", f"{APP_NAME}-worker-extensions", f"{APP_NAME}-bastion")
"""The workloads whose network policies are their own, and which don't use the proxy."""

PROXY_VARIABLES = ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy")

ENABLED = {
    "egressProxy": {"enabled": True},
    "workerTools": {"enabled": True},
    "env": {
        "SMARTER_PLATFORM_ROOT_DOMAIN": "example.com",
        "SMARTER_SUBSYSTEM_LOGGING_LOKI_URL": "http://smarter-loki:3100",
        "SMARTER_SUBSYSTEM_SQL_HOST": "mysql",
    },
}


def env_values(document: str, name: str) -> list[str]:
    """Every value that a rendered workload gives the variable ``name``, one per container that sets it."""
    pattern = rf"- name: {re.escape(name)}\n\s+value: \"([^\"]*)\""
    return re.findall(pattern, document)


def config_file(configmap: str, name: str) -> str:
    """The text of one file of the proxy's ConfigMap, e.g. acl.yaml, without its indentation."""
    data = configmap.split("\ndata:\n", 1)[1]
    match = re.search(rf"^  {re.escape(name)}: \|\n((?:    .*\n?)+)", data, re.MULTILINE)
    if match is None:
        raise AssertionError(f"the ConfigMap has no {name}")
    lines = [line[4:] for line in match.group(1).splitlines()]
    return "\n".join(lines)


@needs_helm
class TestEgressProxyDisabled(unittest.TestCase):
    """Off by default, the chart renders no proxy, and no pod's requests go through one."""

    @classmethod
    def setUpClass(cls):
        cls.documents = render({"workerTools": {"enabled": True}})

    def test_no_proxy_resources(self):
        """No document is the proxy's."""
        for document in self.documents:
            _, name = kind_and_name(document)
            self.assertNotEqual(name, PROXY_NAME)

    def test_no_proxy_environment(self):
        """No workload sets a proxy variable."""
        for name, document in workloads(self.documents).items():
            with self.subTest(workload=name):
                for variable in PROXY_VARIABLES + ("NO_PROXY", "no_proxy"):
                    self.assertEqual(env_values(document, variable), [])


@needs_helm
class TestEgressProxy(unittest.TestCase):
    """Enabled, the proxy holds nothing, and the platform's pods, and only they, send their requests through it."""

    @classmethod
    def setUpClass(cls):
        cls.documents = render(ENABLED)
        cls.workloads = workloads(cls.documents)
        cls.deployment = cls.workloads[PROXY_NAME]
        cls.configmap = documents_of_kind(cls.documents, "ConfigMap")[PROXY_NAME]
        cls.service = documents_of_kind(cls.documents, "Service")[PROXY_NAME]

    def test_its_own_application_group(self):
        """Its pods are in <appName>-egress, whose network policies are their own."""
        for document in (self.deployment, self.service, self.configmap):
            self.assertIn(f'app.kubernetes.io/application-group: "{APP_NAME}-egress"', document)
        self.assertNotIn(f'app.kubernetes.io/application-group: "{APP_NAME}"\n', self.deployment)

    def test_holds_nothing(self):
        """No ServiceAccount token, no Secret, no environment."""
        self.assertIn("automountServiceAccountToken: false", self.deployment)
        self.assertNotIn("serviceAccountName", self.deployment)
        self.assertNotIn("envFrom", self.deployment)
        self.assertNotIn("secretKeyRef", self.deployment)
        self.assertNotRegex(self.deployment, r"\n\s+env:\n")

    def test_image_is_pinned(self):
        """Stripe's image, pinned by digest."""
        self.assertRegex(self.deployment, r'image: "ghcr\.io/stripe/smokescreen:v[0-9.]+@sha256:[0-9a-f]{64}"')

    def test_runs_unprivileged(self):
        """Non-root, read-only, every capability dropped."""
        self.assertIn("runAsNonRoot: true", self.deployment)
        self.assertIn("readOnlyRootFilesystem: true", self.deployment)
        self.assertIn("allowPrivilegeEscalation: false", self.deployment)

    def test_service_reaches_its_port(self):
        """The Service selects the proxy's pods on its port."""
        self.assertIn(f'app.kubernetes.io/name: "{PROXY_NAME}"', self.service)
        self.assertIn("port: 4750", self.service)
        self.assertIn("containerPort: 4750", self.deployment)

    def test_allows_a_missing_role(self):
        """The pods present no client certificate: without allow_missing_role, Smokescreen refuses every request."""
        config = config_file(self.configmap, "config.yaml")
        self.assertIn("allow_missing_role: true", config)
        self.assertIn("acl_file: /etc/smokescreen/acl.yaml", config)
        self.assertIn('"/etc/smokescreen/config.yaml"', self.deployment)
        self.assertIn("mountPath: /etc/smokescreen", self.deployment)

    def test_reports_by_default(self):
        """Stage 1: the default rule reports, and lists the seed hosts, the region's AWS endpoints and the account manager's api."""
        acl = config_file(self.configmap, "acl.yaml")
        self.assertIn("version: v1", acl)
        self.assertIn("action: report", acl)
        for host in (
            "api.openai.com",
            "raw.githubusercontent.com",
            "sts.us-east-1.amazonaws.com",
            "api.am.example.com",
        ):
            self.assertIn(f'- "{host}"', acl)

    def test_platform_pods_use_the_proxy(self):
        """Every container of each proxied kind sends its requests through the proxy."""
        checked = set()
        for name, document in self.workloads.items():
            kind = service_type(document)
            if kind not in PROXIED_KINDS:
                continue
            with self.subTest(workload=name):
                for variable in PROXY_VARIABLES:
                    values = env_values(document, variable)
                    self.assertNotEqual(values, [], variable)
                    self.assertEqual(set(values), {PROXY_URL}, variable)
            checked.add(kind)
        self.assertEqual(checked, set(PROXIED_KINDS))

    def test_backups_own_container_uses_the_proxy(self):
        """The backup's Debian container installs its tools with apt and curl, which read the lower case names."""
        backup = next(document for document in self.workloads.values() if service_type(document) == "job-backup")
        self.assertEqual(len(env_values(backup, "http_proxy")), 2)
        self.assertEqual(len(env_values(backup, "no_proxy")), 2)

    def test_other_pods_dont(self):
        """The tool worker, the Extension worker and the bastion keep their own egress."""
        for name in UNPROXIED_WORKLOADS:
            with self.subTest(workload=name):
                document = self.workloads[name]
                for variable in PROXY_VARIABLES + ("NO_PROXY", "no_proxy"):
                    self.assertEqual(env_values(document, variable), [])

    def test_cluster_services_go_around_it(self):
        """NO_PROXY names what Smokescreen would refuse: the cluster's services, its api, the metadata service and the VPC."""
        api = self.workloads[f"{APP_NAME}-api"]
        values = env_values(api, "NO_PROXY")
        self.assertEqual(len(values), 1)
        self.assertEqual(env_values(api, "no_proxy"), values)
        hosts = values[0].split(",")
        expected = (
            "localhost",
            ".svc",
            ".cluster.local",
            ".eks.amazonaws.com",
            "169.254.169.254",
            "10.0.0.0/8",
            "smarter-loki",
            "mysql",
            f"{APP_NAME}-api",
        )
        for host in expected:
            self.assertIn(host, hosts)
        self.assertEqual(len(hosts), len(set(hosts)))


@needs_helm
class TestEgressProxyValues(unittest.TestCase):
    """EgressProxy's values change the ACL and NO_PROXY."""

    @classmethod
    def setUpClass(cls):
        values = {
            "egressProxy": {
                "enabled": True,
                "action": "enforce",
                "allowedDomains": ["api.openai.com"],
                "noProxy": ["qdrant.internal"],
            },
            "env": {"AWS_REGION": "ca-central-1"},
        }
        cls.documents = render(values)
        cls.configmap = documents_of_kind(cls.documents, "ConfigMap")[PROXY_NAME]
        cls.api = workloads(cls.documents)[f"{APP_NAME}-api"]

    def test_enforce(self):
        """Stage 2: the default rule enforces its allowlist."""
        acl = config_file(self.configmap, "acl.yaml")
        self.assertIn("action: enforce", acl)
        self.assertIn('- "api.openai.com"', acl)
        self.assertNotIn('- "api.anthropic.com"', acl)

    def test_region(self):
        """The AWS endpoints are the region's."""
        acl = config_file(self.configmap, "acl.yaml")
        self.assertIn('- "sts.ca-central-1.amazonaws.com"', acl)
        self.assertNotIn("us-east-1", acl)

    def test_extra_no_proxy(self):
        """EgressProxy.noProxy adds to the chart's own."""
        hosts = env_values(self.api, "NO_PROXY")[0].split(",")
        self.assertIn("qdrant.internal", hosts)
        self.assertIn(".svc", hosts)


class TestDeployAction(unittest.TestCase):
    """The deploy action turns the proxy on from its input, which the deploy workflow reads from a repository variable."""

    def test_action_sets_the_value(self):
        """EgressProxy.enabled follows egress-proxy-enabled, which is off by default."""
        action = ACTION_PATH.read_text(encoding="utf-8")
        self.assertIn("--set egressProxy.enabled=${{ inputs.egress-proxy-enabled == 'true' }}", action)
        match = re.search(r"\n  egress-proxy-enabled:\n(?:    .*\n)+", action)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertIn('default: "false"', match.group(0))

    def test_workflow_reads_the_variable(self):
        """The deploy workflow passes the repository variable EGRESS_PROXY_ENABLED."""
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("egress-proxy-enabled: ${{ vars.EGRESS_PROXY_ENABLED == 'true' }}", workflow)


if __name__ == "__main__":
    unittest.main()
