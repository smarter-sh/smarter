"""
Tests of each kind of pod's environment Secret, <appName>-env-<pod> (ADR-038, phase 3, issue #1084), rendered by helm.

templates/secret-env.yaml renders one Secret per kind of pod, with smarter.podEnv in _helpers.tpl, which leaves out
every credential that files/credentials.json says the kind doesn't hold. These tests render the chart with
``helm template``, with a distinct value for every credential, and check what each Secret holds, which Secret each
workload reads, and which pods a changed credential rolls. A text match can't tell what a template filters.

The chart is rendered by chart_render.py. The Kubernetes Secrets that the chart reads from the cluster don't exist in
``helm template``, so every value comes from env.

They need helm, and are skipped without it, except on GitHub Actions, whose runners have it. Run them from the
repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import json
import re
import unittest

from chart_render import (
    APP_NAME,
    CHART_PATH,
    kind_and_name,
    needs_helm,
    render,
    service_type,
    workloads,
)

CREDENTIALS_PATH = CHART_PATH / "files" / "credentials.json"
SLACK_BOT_DEPLOYMENT_PATH = CHART_PATH.parent / "slack-bot" / "templates" / "deployment.yaml"

OWN_SECRETS = {
    "job-migrate": f"{APP_NAME}-env-migrate",
    "worker-tools": f"{APP_NAME}-env-tools",
    "worker-extensions": f"{APP_NAME}-env-extensions",
}
"""The kinds whose Secret has a name of its own; every other kind's is <appName>-env-<pod>."""

ENV_SECRET_PREFIX = f"{APP_NAME}-env"


def secret_name(pod: str) -> str:
    """The environment Secret of a kind of pod."""
    return OWN_SECRETS.get(pod, f"{APP_NAME}-env-{pod}")


def credential_values() -> dict[str, str]:
    """A distinct value for each credential in the map, e.g. ``test-SMARTER_SUBSYSTEM_SMTP_PASSWORD``."""
    holders = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
    values = {}
    for variable in holders:
        values[variable] = f"test-{variable}"
    return values


def render_env(env: dict[str, str]) -> list[str]:
    """Render the chart with these env values, and the Slack bot on."""
    return render({"env": env, "slackBot": {"enabled": True}})


def secrets(documents: list[str]) -> dict[str, dict[str, str]]:
    """Each rendered Secret's stringData, by the Secret's name."""
    retval = {}
    for document in documents:
        kind, name = kind_and_name(document)
        if kind != "Secret" or "stringData:" not in document:
            continue
        data = {}
        string_data = document.split("stringData:", 1)[1]
        for key, value in re.findall(r'^  ([A-Za-z0-9_]+): "(.*)"$', string_data, re.MULTILINE):
            data[key] = value
        retval[name] = data
    return retval


@needs_helm
class TestPodSecrets(unittest.TestCase):
    """Each kind of pod reads its own Secret, which holds only the credentials that its kind holds."""

    @classmethod
    def setUpClass(cls):
        cls.holders = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        cls.env = credential_values()
        cls.documents = render_env(cls.env)
        cls.secrets = secrets(cls.documents)
        cls.workloads = workloads(cls.documents)

    def test_each_secret_holds_only_its_kinds_credentials(self):
        """A credential is in a kind's Secret if, and only if, credentials.json names the kind."""
        pods = ("api", "worker", "worker-infrastructure", "beat", "bastion", "job-init", "job-backup", "job-migrate")
        for pod in pods:
            with self.subTest(pod=pod):
                data = self.secrets[secret_name(pod)]
                for variable, kinds in self.holders.items():
                    if pod in kinds:
                        self.assertEqual(data.get(variable), self.env[variable], variable)
                    else:
                        self.assertNotIn(variable, data)

    def test_examples(self):
        """What phase 0 found: Beat holds no SMTP or Django key; only three kinds hold the administrator's password."""
        beat = self.secrets[secret_name("beat")]
        self.assertNotIn("SMARTER_SUBSYSTEM_SMTP_PASSWORD", beat)
        self.assertNotIn("DJANGO_SECRET_KEY", beat)
        self.assertIn("SMARTER_SUBSYSTEM_SQL_PASSWORD", beat)
        root_password = "SMARTER_SUBSYSTEM_SQL_ROOT_PASSWORD"
        holding = sorted(name for name, data in self.secrets.items() if root_password in data)
        self.assertEqual(holding, [secret_name("bastion"), secret_name("job-backup"), secret_name("job-init")])

    def test_there_is_no_shared_secret(self):
        """The Secret that every pod used to read, <appName>-env, is gone."""
        self.assertNotIn(ENV_SECRET_PREFIX, self.secrets)

    def test_each_workload_reads_only_its_own_secret(self):
        """Every environment Secret that a workload reads, with envFrom or secretKeyRef, is its SERVICE_TYPE's."""
        checked = []
        for name, document in self.workloads.items():
            references = re.findall(r"(?:secretRef|secretKeyRef):\n\s+name: \"?([^\"\n]+)\"?", document)
            env_references = set()
            for reference in references:
                if reference.startswith(ENV_SECRET_PREFIX):
                    env_references.add(reference)
            if not env_references:
                continue
            pod = service_type(document)
            with self.subTest(workload=name):
                self.assertIsNotNone(pod)
                assert pod is not None
                self.assertEqual(env_references, {secret_name(pod)})
            checked.append(pod)
        for pod in ("api", "worker", "worker-infrastructure", "beat", "bastion", "job-init", "job-backup"):
            self.assertIn(pod, checked)

    def test_a_changed_credential_rolls_only_its_holders(self):
        """Each pod's checksum/env is its own Secret's: a new SMTP password rolls the api, not Celery Beat."""
        changed = dict(self.env)
        changed["SMARTER_SUBSYSTEM_SMTP_PASSWORD"] = "test-a-new-smtp-password"
        before = workloads(self.documents)
        after = workloads(render_env(changed))
        expected = {"smarter-api": True, "smarter-worker": True, "smarter-beat": False, "smarter-bastion": False}
        for name, rolls in expected.items():
            with self.subTest(workload=name):
                checksum_before = re.search(r"checksum/env: \"(\w+)\"", before[name]).group(1)
                checksum_after = re.search(r"checksum/env: \"(\w+)\"", after[name]).group(1)
                self.assertEqual(checksum_before != checksum_after, rolls)

    def test_the_slack_bot_has_only_its_tokens(self):
        """The Slack bot's Secret holds its two tokens, and no Smarter pod holds the app token."""
        bot = self.secrets[f"{APP_NAME}-env-slack-bot"]
        self.assertEqual(set(bot), {"SMARTER_SUBSYSTEM_SLACK_BOT_TOKEN", "SMARTER_SUBSYSTEM_SLACK_APP_TOKEN"})
        for name, data in self.secrets.items():
            if name == f"{APP_NAME}-env-slack-bot":
                continue
            with self.subTest(secret=name):
                self.assertNotIn("SMARTER_SUBSYSTEM_SLACK_APP_TOKEN", data)
        deployment = SLACK_BOT_DEPLOYMENT_PATH.read_text(encoding="utf-8")
        self.assertEqual(deployment.count('name: "{{ .Values.global.appName }}-env-slack-bot"'), 2)
        self.assertNotIn('name: "{{ .Values.global.appName }}-env"\n', deployment)


RESTRICTED_WORKER_KEYS = {
    "AWS_EC2_METADATA_DISABLED",
    "CACHE_RESULTS_CACHE",
    "DJANGO_CELERY_BROKER_URL",
    "SERVICE_TYPE",
    "SMARTER_APP_EXTENSIONS_TASKS_CELERY_TASK_QUEUE",
    "SMARTER_APP_LLMTOOL_PLUGIN_MAX_DATA_RESULTS",
    "SMARTER_APP_TOOLS_TASKS_CELERY_TASK_QUEUE",
    "SMARTER_DATABASE_UNAVAILABLE",
    "SMARTER_DEBUG_MODE",
    "SMARTER_ENVIRONMENT",
    "SMARTER_LOG_LEVEL",
    "SMARTER_PLATFORM_INTERNAL_IP_PREFIXES",
    "SMARTER_PLATFORM_ROOT_DOMAIN",
    "SMARTER_PLATFORM_SHARED_RESOURCE_IDENTIFIER",
    "SMARTER_PLATFORM_SUBDOMAIN",
    "SMARTER_SUBSYSTEM_REDIS_PASSWORD",
    "SMARTER_SUBSYSTEM_REDIS_USERNAME",
}
"""What the tool worker's and the Extension worker's Secrets may hold: what they read, and no more."""


@needs_helm
class TestRestrictedWorkerSecrets(unittest.TestCase):
    """The tool worker's and the Extension worker's Secrets hold only what they read (ADR-038)."""

    def test_only_what_they_read(self):
        """No AWS region, cloud provider, Kubernetes namespace or settings module: they read none of them."""
        env = {
            "AWS_REGION": "ca-central-1",
            "SMARTER_PLATFORM_CLOUD_PROVIDER": "aws",
            "SMARTER_APP_TOOLS_TASKS_CELERY_TASK_QUEUE": "tools_celery_task_queue",
            "SMARTER_APP_EXTENSIONS_TASKS_CELERY_TASK_QUEUE": "extensions_celery_task_queue",
        }
        documents = render({"env": env, "workerTools": {"enabled": True}})
        rendered = secrets(documents)
        for name in (f"{APP_NAME}-env-tools", f"{APP_NAME}-env-extensions"):
            with self.subTest(secret=name):
                keys = set(rendered[name])
                self.assertLessEqual(keys, RESTRICTED_WORKER_KEYS | {"SMARTER_APP_TOOLS_WORKER_QUEUE"})
                for key in (
                    "AWS_REGION",
                    "DJANGO_SETTINGS_MODULE",
                    "SMARTER_PLATFORM_CLOUD_PROVIDER",
                    "SMARTER_SUBSYSTEM_K8S_NAMESPACE",
                ):
                    self.assertNotIn(key, keys)
                # both queues' names: the worker declares both, and the Extension worker checks the tool worker's.
                self.assertIn("SMARTER_APP_TOOLS_TASKS_CELERY_TASK_QUEUE", keys)
                self.assertIn("SMARTER_APP_EXTENSIONS_TASKS_CELERY_TASK_QUEUE", keys)


if __name__ == "__main__":
    unittest.main()
