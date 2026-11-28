"""
Tests of each kind of pod's ServiceAccount and Kubernetes permissions (ADR-038, phase 3, issue #1084), rendered by helm.

templates/serviceaccount.yaml gives each kind of pod a ServiceAccount, <appName>-<pod>, and templates/rbac.yaml a
Role and a ClusterRole with only what its code does: the cluster writes in smarter-worker-infrastructure, reads
without Secrets in the app, whose web console terminal runs a shell with its token, and the init Job's ingress
retarget. These tests render the chart (chart_render.py) and check who reads which ServiceAccount, and what each
can do.

They need helm, and are skipped without it, except on GitHub Actions, whose runners have it. Run them from the
repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import re
import unittest

from chart_render import (
    APP_NAME,
    NAMESPACE,
    documents_of_kind,
    needs_helm,
    render,
    rules,
    service_type,
    workloads,
)

ROLE_ARN = "arn:aws:iam::000000000000:role/test-smarter-irsa"

WRITE_VERBS = {"create", "update", "patch", "delete", "deletecollection"}

OWN_SERVICE_ACCOUNTS = {
    "job-backup": f"{APP_NAME}-backup",
    "worker-tools": f"{APP_NAME}-tools",
    "worker-extensions": f"{APP_NAME}-tools",
}
"""The kinds whose ServiceAccount has a name of its own; every other kind's is <appName>-<pod>."""

WITHOUT_TOKEN = ("beat", "job-migrate", "job-backup", "bastion", "worker-tools", "worker-extensions")
"""The kinds that never call Kubernetes, and mount no ServiceAccount token."""


def service_account_name(pod: str) -> str:
    """The ServiceAccount of a kind of pod."""
    return OWN_SERVICE_ACCOUNTS.get(pod, f"{APP_NAME}-{pod}")


def granted(role: str) -> dict[str, set[str]]:
    """The verbs that a rendered Role grants, by resource."""
    retval: dict[str, set[str]] = {}
    for rule in rules(role):
        for resource in rule.get("resources", []):
            retval.setdefault(resource, set()).update(rule.get("verbs", []))
    return retval


@needs_helm
class TestRbac(unittest.TestCase):
    """Each kind of pod runs as its own ServiceAccount, whose Roles allow only what its code does."""

    @classmethod
    def setUpClass(cls):
        values = {"serviceAccount": {"awsRoleArn": ROLE_ARN, "createClusterRole": True}}
        cls.documents = render(values)
        cls.service_accounts = documents_of_kind(cls.documents, "ServiceAccount")
        cls.roles = documents_of_kind(cls.documents, "Role")
        cls.role_bindings = documents_of_kind(cls.documents, "RoleBinding")
        cls.cluster_roles = documents_of_kind(cls.documents, "ClusterRole")
        cls.cluster_role_bindings = documents_of_kind(cls.documents, "ClusterRoleBinding")
        cls.workloads = workloads(cls.documents)

    def test_each_workload_runs_as_its_own_service_account(self):
        """Every workload's ServiceAccount is its SERVICE_TYPE's, and only the kinds that call Kubernetes mount it."""
        checked = []
        for name, document in self.workloads.items():
            pod = service_type(document)
            if pod is None:
                continue
            with self.subTest(workload=name):
                account = re.search(r'serviceAccountName: "?([^"\n]+)"?', document)
                if pod == "bastion":
                    # the bastion runs as the namespace's default ServiceAccount, without its token.
                    self.assertIsNone(account)
                else:
                    self.assertIsNotNone(account)
                    assert account is not None
                    self.assertEqual(account.group(1), service_account_name(pod))
                    self.assertIn(service_account_name(pod), self.service_accounts)
                automount = re.search(r"automountServiceAccountToken: (true|false)", document)
                mounted = automount is None or automount.group(1) == "true"
                self.assertEqual(mounted, pod not in WITHOUT_TOKEN)
            checked.append(pod)
        for pod in ("api", "worker", "worker-infrastructure", "beat", "job-init", "job-migrate", "job-backup"):
            self.assertIn(pod, checked)

    def test_there_is_no_shared_service_account(self):
        """The ServiceAccount, Role and ClusterRole that every pod used to share are gone."""
        self.assertNotIn(APP_NAME, self.service_accounts)
        self.assertNotIn(APP_NAME, self.roles)
        self.assertNotIn(f"{APP_NAME}-{NAMESPACE}", self.cluster_roles)

    def test_every_platform_service_account_has_the_iam_role(self):
        """Until each gets its own IAM role (step 4), every platform ServiceAccount has the shared one."""
        for pod in ("api", "worker", "worker-infrastructure", "beat", "job-init", "job-migrate"):
            with self.subTest(pod=pod):
                account = self.service_accounts[service_account_name(pod)]
                self.assertIn(f'eks.amazonaws.com/role-arn: "{ROLE_ARN}"', account)

    def test_the_migrate_jobs_service_account_exists_before_the_job(self):
        """The migrate Job runs before the release's resources: its ServiceAccount is an earlier pre-upgrade hook."""
        account = self.service_accounts[service_account_name("job-migrate")]
        secret = documents_of_kind(self.documents, "Secret")[f"{APP_NAME}-env-migrate"]
        job = next(document for document in self.workloads.values() if service_type(document) == "job-migrate")

        def weight(document: str) -> int:
            match = re.search(r'"helm.sh/hook-weight": "(-?\d+)"', document)
            assert match is not None
            return int(match.group(1))

        for document in (account, secret, job):
            self.assertIn('"helm.sh/hook": pre-upgrade', document)
        self.assertLess(weight(account), weight(secret))
        self.assertLess(weight(secret), weight(job))

    def test_only_the_infrastructure_worker_writes(self):
        """Every write is the infrastructure worker's, but the init Job's ingress retarget; Secrets are its alone."""
        for name, role in self.roles.items():
            if name == f"{APP_NAME}-alloy":
                continue
            permissions = granted(role)
            with self.subTest(role=name):
                if name == f"{APP_NAME}-worker-infrastructure":
                    self.assertTrue(permissions["secrets"] & WRITE_VERBS)
                    continue
                self.assertNotIn("secrets", permissions)
                for resource, verbs in permissions.items():
                    writes = verbs & WRITE_VERBS
                    if name == f"{APP_NAME}-job-init" and resource == "ingresses":
                        self.assertEqual(writes, {"create", "patch"})
                        continue
                    self.assertEqual(writes, set(), resource)
        for name, role in self.cluster_roles.items():
            with self.subTest(cluster_role=name):
                for verbs in granted(role).values():
                    self.assertEqual(verbs & WRITE_VERBS, set())

    def test_the_apps_reads(self):
        """The app reads what its status pages, logs and the platform_status tool show, and nothing else."""
        permissions = granted(self.roles[f"{APP_NAME}-api"])
        expected = {
            "pods": {"get", "list"},
            "pods/log": {"get"},
            "events": {"get", "list"},
            "deployments": {"get", "list"},
            "statefulsets": {"get", "list"},
            "persistentvolumeclaims": {"get", "list"},
        }
        for resource, verbs in expected.items():
            with self.subTest(resource=resource):
                self.assertEqual(permissions[resource], verbs)
        # pod metrics, metrics.k8s.io's pods, share the name "pods": its rule is separate, and also read-only.
        self.assertEqual(set(permissions), set(expected))

    def test_each_binding_binds_its_own_service_account(self):
        """A Role or ClusterRole for a kind of pod is bound to that kind's ServiceAccount, and only to it."""
        bindings = {**self.role_bindings, **self.cluster_role_bindings}
        for name, binding in bindings.items():
            if name == f"{APP_NAME}-alloy":
                continue
            with self.subTest(binding=name):
                role = re.search(r"roleRef:\n(?:\s+.*\n)*?\s+name: \"?([^\"\n]+)\"?", binding)
                subjects = re.findall(r"- kind: ServiceAccount\n\s+name: \"?([^\"\n]+)\"?", binding)
                assert role is not None
                self.assertEqual(role.group(1), name)
                self.assertEqual(len(subjects), 1)
                pod = subjects[0].removeprefix(f"{APP_NAME}-")
                self.assertTrue(name.endswith(f"-{pod}"), (name, subjects))

    def test_the_cluster_wide_reads(self):
        """Each kind reads only its namespace, and the nodes and volumes that its code lists."""
        expected = {
            "api": {"namespaces", "nodes"},
            "worker": {"namespaces"},
            "worker-infrastructure": {"namespaces", "nodes", "persistentvolumes"},
            "job-init": {"namespaces", "nodes", "persistentvolumes"},
        }
        self.assertEqual(len(self.cluster_roles), len(expected))
        for pod, resources in expected.items():
            with self.subTest(pod=pod):
                role = self.cluster_roles[f"{APP_NAME}-{NAMESPACE}-{pod}"]
                self.assertEqual(set(granted(role)), resources)
                self.assertIn(f"- {NAMESPACE}", role, "the namespace rule names this namespace only")

    def test_without_cluster_roles(self):
        """With createClusterRole off, as smarter-sh's deploy has it, the chart creates nothing cluster-wide."""
        documents = render({"serviceAccount": {"createClusterRole": False}})
        self.assertEqual(documents_of_kind(documents, "ClusterRole", "ClusterRoleBinding"), {})


if __name__ == "__main__":
    unittest.main()
