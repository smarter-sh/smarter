"""
Tests of each kind of pod's environment Secret, <appName>-env-<pod> (ADR-038, phase 3, issue #1084), rendered by helm.

templates/secret-env.yaml renders one Secret per kind of pod, with smarter.podEnv in _helpers.tpl, which leaves out
every credential that files/credentials.json says the kind doesn't hold. These tests render the chart with
``helm template``, with a distinct value for every credential, and check what each Secret holds, which Secret each
workload reads, and which pods a changed credential rolls. A text match can't tell what a template filters.

The chart is rendered from a copy without its subcharts (Chart.yaml's dependencies), which ``helm template`` would
otherwise have to download, and with a valid version in place of the placeholder that the release sets. The
Kubernetes Secrets that the chart reads from the cluster don't exist in ``helm template``, so every value comes from
env.

They need helm, and are skipped without it, except on GitHub Actions, whose runners have it. Run them from the
repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = CHART_PATH / "files" / "credentials.json"
SLACK_BOT_DEPLOYMENT_PATH = CHART_PATH.parent / "slack-bot" / "templates" / "deployment.yaml"
APP_NAME = "smarter"
HELM = shutil.which("helm")

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


def render(env: dict[str, str]) -> list[str]:
    """
    Render the chart with these env values, and the Slack bot on.

    :param env: Values of env, by variable.
    :returns: The rendered documents.
    """
    with tempfile.TemporaryDirectory() as folder:
        chart = Path(folder) / "smarter"
        shutil.copytree(CHART_PATH, chart, ignore=shutil.ignore_patterns("charts", "tests", "__pycache__", "*.lock"))
        chart_yaml = (chart / "Chart.yaml").read_text(encoding="utf-8")
        chart_yaml = re.sub(r"^(version|appVersion): .*$", r"\1: 0.0.1", chart_yaml, flags=re.MULTILINE)
        chart_yaml = chart_yaml[: chart_yaml.index("dependencies:")]
        (chart / "Chart.yaml").write_text(chart_yaml, encoding="utf-8")
        # JSON is YAML: a values file without quoting rules to get wrong.
        values = {"env": env, "slackBot": {"enabled": True}}
        values_path = Path(folder) / "values.json"
        values_path.write_text(json.dumps(values), encoding="utf-8")
        command = [HELM, "template", APP_NAME, str(chart), "--namespace", "smarter-test", "-f", str(values_path)]
        completed = subprocess.run(command, capture_output=True, text=True, check=False)  # nosec B603
    if completed.returncode != 0:
        raise AssertionError(f"helm template failed:\n{completed.stderr}")
    return completed.stdout.split("\n---\n")


def kind_and_name(document: str) -> tuple[str, str]:
    """A rendered document's kind and name, its metadata's name wherever it is in the block, or empty strings."""
    kind = re.search(r"^kind: (\w+)$", document, re.MULTILINE)
    if kind is None or "\nmetadata:\n" not in document:
        return "", ""
    metadata = document.split("\nmetadata:\n", 1)[1]
    for line in metadata.splitlines():
        if not line.startswith(" "):
            break
        name = re.match(r'^  name: "?([^"\n]+?)"?$', line)
        if name is not None:
            return kind.group(1), name.group(1)
    return "", ""


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


def workloads(documents: list[str]) -> dict[str, str]:
    """Each rendered Deployment, Job and CronJob, by name."""
    retval = {}
    for document in documents:
        kind, name = kind_and_name(document)
        if kind in ("Deployment", "Job", "CronJob"):
            retval[name] = document
    return retval


@unittest.skipUnless(HELM or os.environ.get("GITHUB_ACTIONS"), "helm isn't installed")
class TestPodSecrets(unittest.TestCase):
    """Each kind of pod reads its own Secret, which holds only the credentials that its kind holds."""

    @classmethod
    def setUpClass(cls):
        if HELM is None:
            raise AssertionError("helm isn't installed, and GitHub Actions' runners have it.")
        cls.holders = json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        cls.env = credential_values()
        cls.documents = render(cls.env)
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
            service_types = set(re.findall(r"- name: SERVICE_TYPE\n\s+value: \"?([a-z-]+)\"?", document))
            with self.subTest(workload=name):
                self.assertEqual(len(service_types), 1, service_types)
                pod = service_types.pop()
                self.assertEqual(env_references, {secret_name(pod)})
            checked.append(pod)
        for pod in ("api", "worker", "worker-infrastructure", "beat", "bastion", "job-init", "job-backup"):
            self.assertIn(pod, checked)

    def test_a_changed_credential_rolls_only_its_holders(self):
        """Each pod's checksum/env is its own Secret's: a new SMTP password rolls the api, not Celery Beat."""
        changed = dict(self.env)
        changed["SMARTER_SUBSYSTEM_SMTP_PASSWORD"] = "test-a-new-smtp-password"
        before = workloads(self.documents)
        after = workloads(render(changed))
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


if __name__ == "__main__":
    unittest.main()
