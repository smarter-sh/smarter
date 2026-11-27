"""
Tests of the tool worker, workerTools in values.yaml (ADR-038).

The tool worker runs what tool calls run: requests and code that manifest authors, extension
authors and the LLM choose. These tests check that it gets none of the platform's credentials:
its environment is its own Secret, built from an allowlist of settings that aren't secret; its
ServiceAccount has no token; its pods are outside the platform's application-group, which the
network policies grant the database and the cluster; and its Celery worker sends no task events,
which would copy each call's credentials. They also check that it is off by default, and that
enabling it sends the app's tool calls to it.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import re
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
VALUES_PATH = CHART_PATH / "values.yaml"
HELPERS_PATH = CHART_PATH / "templates" / "_helpers.tpl"
DEPLOYMENT_PATH = CHART_PATH / "templates" / "deployment-worker-tools.yaml"
SECRET_PATH = CHART_PATH / "templates" / "secret-env-tools.yaml"
EXTENSIONS_DEPLOYMENT_PATH = CHART_PATH / "templates" / "deployment-worker-extensions.yaml"
EXTENSIONS_SECRET_PATH = CHART_PATH / "templates" / "secret-env-extensions.yaml"
SERVICE_ACCOUNT_PATH = CHART_PATH / "templates" / "serviceaccount.yaml"
ACTION_PATH = CHART_PATH.parent.parent.parent / ".github" / "actions" / "deploy" / "action.yml"

SECRET_WORDS = ("PASSWORD", "SECRET", "TOKEN", "API_KEY", "FERNET", "AWS_ACCESS", "SQL", "PAT", "SMTP", "ADMIN")
"""Words in the names of the settings that hold credentials, none of which the tool worker may have."""

REDIS_DEFAULT_USER_SETTINGS = ("DJANGO_CACHES", "DJANGO_CELERY_BROKER_URL", "SMARTER_SUBSYSTEM_REDIS_PASSWORD")
"""The settings that carry Redis's default user's password, which smarter.toolsEnv never copies (ADR-030, rule 8)."""


def template(name: str) -> str:
    """
    Return one template of _helpers.tpl.

    :param name: The template's name, e.g. smarter.toolsEnv.
    :returns: Its text, from its define to its end.
    """
    text = HELPERS_PATH.read_text(encoding="utf-8")
    start = text.index(f'{{{{- define "{name}" -}}}}')
    end = text.index("{{- end }}", start)
    return text[start:end]


def tools_env_keys() -> list[str]:
    """
    Return the settings that smarter.toolsEnv copies from smarter.env.

    :returns: The names in its allowlist.
    """
    match = re.search(r"\$keys := list\n((?:\s+\"[A-Z0-9_]+\"\n)+)", template("smarter.toolWorkerEnv"))
    if match is None:
        raise AssertionError("smarter.toolWorkerEnv has no $keys list")
    return re.findall(r'"([A-Z0-9_]+)"', match.group(1))


class TestToolWorker(unittest.TestCase):
    """The tool worker has none of the platform's credentials."""

    def test_allowlist_has_no_credential(self):
        """No setting that holds a credential is in the tool worker's environment."""
        keys = tools_env_keys()
        self.assertIn("SMARTER_APP_TOOLS_TASKS_CELERY_TASK_QUEUE", keys)
        for key in REDIS_DEFAULT_USER_SETTINGS:
            self.assertNotIn(key, keys)
        for key in keys:
            for word in SECRET_WORDS:
                self.assertNotIn(word, key, key)

    def test_environment_has_no_database(self):
        """The tool worker's environment says that it has no database, and keeps boto3 off the instance metadata."""
        helper = template("smarter.toolWorkerEnv")
        self.assertIn('set $env "SMARTER_DATABASE_UNAVAILABLE" "true"', helper)
        self.assertIn('set $env "AWS_EC2_METADATA_DISABLED" "true"', helper)
        self.assertIn('include "smarter.toolsEnv"', SECRET_PATH.read_text(encoding="utf-8"))

    def test_its_own_redis_user(self):
        """
        Its Redis credentials are the tools user's, from smarter-infrastructure's Secret, and the broker's url is built from them.

        Without the Secret they are left out, so the worker refuses to start, rather than run as the default user.
        """
        helper = template("smarter.toolWorkerEnv")
        self.assertIn('set $env "SMARTER_SUBSYSTEM_REDIS_USERNAME" $user', helper)
        self.assertIn('lookup "v1" "Secret" $root.Release.Namespace "smarter-redis-users"', helper)
        self.assertIn("{{- if hasKey $usersData $user -}}", helper)
        self.assertIn('set $env "SMARTER_SUBSYSTEM_REDIS_PASSWORD" $password', helper)
        self.assertIn('printf "redis://%s:%s@%s/0" $user (urlquery $password) $redis', helper)
        # @cache_results' own cache: the cache's database, as the same user, under its own key prefix.
        self.assertIn('printf "redis://%s:%s@%s/1" $user (urlquery $password) $redis', helper)
        self.assertIn('"KEY_PREFIX" (printf "%s_cache" $user)', helper)
        self.assertIn('set $env "CACHE_RESULTS_CACHE" (toJson $cache)', helper)
        tools = template("smarter.toolsEnv")
        self.assertIn('include "smarter.toolWorkerEnv" (dict "root" . "user" "tools" "queue" "")', tools)

    def test_deployment_takes_no_remote_control(self):
        """Mingle, gossip, heartbeats and remote control use keys that its Redis user can't reach."""
        text = DEPLOYMENT_PATH.read_text(encoding="utf-8")
        for flag in ("--without-mingle", "--without-gossip", "--without-heartbeat"):
            with self.subTest(flag=flag):
                self.assertIn(f'"{flag}"', text)
        # nor a liveness probe that pings it through remote control: it would always fail.
        probe = text.split("livenessProbe:", 1)[1].split("startupProbe:", 1)[0]
        self.assertNotIn("smarter.workers.liveness", probe)
        self.assertIn("pgrep -f 'celery.*worker'", probe)

    def test_deployment_reads_only_its_own_secret(self):
        """The Deployment reads its own Secret, not the platform's, and no other environment."""
        text = DEPLOYMENT_PATH.read_text(encoding="utf-8")
        self.assertIn('name: "{{ .Values.global.appName }}-env-tools"', text)
        self.assertNotIn('name: "{{ .Values.global.appName }}-env"\n', text)
        self.assertNotIn("worker.env", text)
        self.assertNotIn('include "smarter.waitForDatabase"', text)

    def test_deployment_has_no_token_and_its_own_group(self):
        """The pods have their own ServiceAccount, without a token, and are outside the platform's application-group."""
        text = DEPLOYMENT_PATH.read_text(encoding="utf-8")
        self.assertIn('serviceAccountName: "{{ $.Values.global.appName }}-tools"', text)
        self.assertIn("automountServiceAccountToken: false", text)
        self.assertNotIn('application-group: "{{ .Values.global.appName }}"\n', text)
        self.assertEqual(text.count('application-group: "{{ .Values.global.appName }}-tools"'), 2)
        accounts = SERVICE_ACCOUNT_PATH.read_text(encoding="utf-8")
        tools_account = accounts[accounts.index('name: "{{ .Values.global.appName }}-tools"') :]
        self.assertIn("automountServiceAccountToken: false", tools_account)
        self.assertNotIn("role-arn", tools_account)

    def test_worker_sends_no_task_events(self):
        """The Celery worker runs without -E, and on the tools queue."""
        command = re.search(r"command: (\[.*\])", DEPLOYMENT_PATH.read_text(encoding="utf-8"))
        assert command is not None
        self.assertNotIn('"-E"', command.group(1))
        self.assertIn("SMARTER_APP_TOOLS_TASKS_CELERY_TASK_QUEUE", command.group(1))

    def test_off_by_default_and_enabling_sends_tool_calls(self):
        """WorkerTools is off by default; enabled, it renders the worker and makes the app's runner remote."""
        values = VALUES_PATH.read_text(encoding="utf-8")
        self.assertRegex(values, r"\nworkerTools:\n  enabled: false\n")
        for path in (DEPLOYMENT_PATH, SECRET_PATH):
            self.assertIn(".enabled }}", path.read_text(encoding="utf-8"))
        self.assertIn('"SMARTER_APP_LLMTOOL_TOOL_RUNNER" | default "remote"', template("smarter.env"))

    def test_deploy_action_enables_it(self):
        """Smarter-sh's own deploy turns the tool worker on, from an input that defaults to true and can turn it off."""
        action = ACTION_PATH.read_text(encoding="utf-8")
        self.assertRegex(action, r"  tool-worker-enabled:\n(?:    .*\n)*?    default: \"true\"\n")
        self.assertIn("--set workerTools.enabled=${{ inputs.tool-worker-enabled == 'true' }}", action)

    def test_alloy_collects_its_logs(self):
        """Alloy's discovery selects the tool worker's pods, whose application-group is not the platform's."""
        values = VALUES_PATH.read_text(encoding="utf-8")
        self.assertIn("{{ .Values.global.appName }}-worker-tools,", values)
        # and the Extension worker's, in the same application-group (issue #1077).
        self.assertIn("{{ .Values.global.appName }}-worker-extensions,", values)


if __name__ == "__main__":
    unittest.main()


class TestExtensionWorker(unittest.TestCase):
    """
    The Extension worker runs Extensions' calls apart from the tool worker, each in a process of its own (issue #1077).

    It is the tool worker in every other way: no database, no token, the same application-group.
    """

    def test_deployed_with_the_tool_worker(self):
        """It exists only with workerTools.enabled, and is sized by workerTools.extensions."""
        text = EXTENSIONS_DEPLOYMENT_PATH.read_text(encoding="utf-8")
        self.assertIn("{{- $extensions := $tools.extensions | default dict }}", text)
        self.assertIn("{{- if $tools.enabled }}", text)
        values = VALUES_PATH.read_text(encoding="utf-8")
        self.assertIn("\n  extensions:\n    replicaCount: 2\n", values)

    def test_a_process_per_call_on_its_own_queue(self):
        """It consumes the Extensions queue, with a fresh process per call, and no remote control."""
        text = EXTENSIONS_DEPLOYMENT_PATH.read_text(encoding="utf-8")
        self.assertIn(
            '"-Q", "{{ .Values.env.SMARTER_APP_EXTENSIONS_TASKS_CELERY_TASK_QUEUE | default "extensions_celery_task_queue" }}"',
            text,
        )
        self.assertIn('"-n", "extensions@%h", "--max-tasks-per-child=1"', text)
        for flag in ("--without-mingle", "--without-gossip", "--without-heartbeat"):
            with self.subTest(flag=flag):
                self.assertIn(f'"{flag}"', text)
        self.assertNotIn('"-E"', text)
        probe = text.split("livenessProbe:", 1)[1].split("startupProbe:", 1)[0]
        self.assertIn("pgrep -f 'celery.*worker'", probe)

    def test_isolated_like_the_tool_worker(self):
        """Its own Secret, the tool worker's ServiceAccount without a token, and the same application-group."""
        text = EXTENSIONS_DEPLOYMENT_PATH.read_text(encoding="utf-8")
        self.assertIn('name: "{{ .Values.global.appName }}-env-extensions"', text)
        self.assertNotIn('name: "{{ .Values.global.appName }}-env"\n', text)
        self.assertIn('serviceAccountName: "{{ $.Values.global.appName }}-tools"', text)
        self.assertIn("automountServiceAccountToken: false", text)
        self.assertIn('app.kubernetes.io/application-group: "{{ .Values.global.appName }}-tools"', text)
        self.assertNotIn('include "smarter.waitForDatabase"', text)

    def test_its_environment_is_the_extensions_users(self):
        """Its Secret is smarter.extensionsEnv: the Redis user extensions, on the Extensions queue."""
        secret = EXTENSIONS_SECRET_PATH.read_text(encoding="utf-8")
        self.assertIn('include "smarter.extensionsEnv"', secret)
        self.assertIn('-env-extensions"', secret)
        helper = template("smarter.extensionsEnv")
        self.assertIn('(dict "root" . "user" "extensions" "queue" $queue)', helper)
        self.assertIn('| default "extensions_celery_task_queue"', helper)
        shared = template("smarter.toolWorkerEnv")
        self.assertIn('set $env "SMARTER_APP_TOOLS_WORKER_QUEUE" .queue', shared)
