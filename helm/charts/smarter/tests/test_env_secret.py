"""
Tests of the chart's env Secret, templates/secret-env.yaml, and of smarter.env, which builds it.

When the pods have an IAM role (serviceAccount.awsRoleArn), the deploy workflow sets
env.AWS_ACCESS_KEY_ID and env.AWS_SECRET_ACCESS_KEY to null, because a key in the pods'
environment would win over the role. values.yaml has no default for them, so the null reaches
the schema and the template. A schema that only allowed a string once failed a prod deploy at
helm upgrade. These tests check that both accept the null, and that the Secret leaves it out.

They need only the standard library. Run them from the repository's root:

    python -m unittest discover -s helm/charts/smarter/tests
"""

import json
import re
import unittest
from pathlib import Path

CHART_PATH = Path(__file__).resolve().parent.parent
SCHEMA_PATH = CHART_PATH / "values.schema.json"
VALUES_PATH = CHART_PATH / "values.yaml"
TEMPLATE_PATH = CHART_PATH / "templates" / "secret-env.yaml"

HELPERS_PATH = CHART_PATH / "templates" / "_helpers.tpl"
MARIADB_SECRET_PATH = CHART_PATH / "templates" / "secret-mariadb.yaml"
MIGRATE_JOB_PATH = CHART_PATH / "templates" / "job-migrate.yaml"
MIGRATE_SECRET_PATH = CHART_PATH / "templates" / "secret-env-migrate.yaml"

OPTIONAL_KEYS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")

DERIVED_KEYS = (
    "DJANGO_SETTINGS_MODULE",
    "SMARTER_SUBSYSTEM_K8S_NAMESPACE",
    "SMARTER_PLATFORM_S3_BUCKET",
)
"""The settings that smarter.env derives from the others, which values.yaml therefore doesn't set."""

INFRASTRUCTURE_SECRETS = (
    "mysql-smarter",
    "mysql-root",
    "smarter-admin",
    "smarter-django-secret-key",
    "aws-ses-config",
    "smarter-redis-password",
)
"""The Kubernetes Secrets that smarter-infrastructure creates in each environment's namespace."""


REPOSITORY_ROOT = CHART_PATH.parent.parent.parent
COMPOSE_PATHS = (REPOSITORY_ROOT / "docker-compose.yml", REPOSITORY_ROOT / "docker-compose.shard.yml")
CACHE_SETTINGS_PATH = REPOSITORY_ROOT / "smarter" / "smarter" / "common" / "conf" / "settings" / "cache.py"


def user_line(user: str) -> re.Pattern[str]:
    """
    Return the pattern of the line that redis.master.preExecCmds appends to master.conf for a Redis ACL user.

    :param user: The user, ``tools`` or ``extensions``.
    :returns: The pattern, whose group ``rules`` is the user's rules.
    """
    pattern = re.compile(rf'"user {user} on >\$\(< /opt/bitnami/redis/users/{user}\) (?P<rules>[^"]+)"')
    return pattern


def acl_rules(user: str) -> list[str]:
    """
    Return the Redis ACL rules of a worker's user, from values.yaml's redis.master.preExecCmds.

    :param user: The user, ``tools`` or ``extensions``.
    :returns: Its key patterns, channels and commands, one per rule.
    """
    values = VALUES_PATH.read_text(encoding="utf-8")
    match = user_line(user).search(values)
    if match is None:
        raise AssertionError(f"values.yaml's redis.master.preExecCmds don't define the user {user}")
    rules = match.group("rules").split()
    return rules


def tools_acl_rules() -> list[str]:
    """Return the tool worker's user's rules: :func:`acl_rules` of ``tools``."""
    return acl_rules("tools")


def local_password(constant: str) -> str:
    """
    Return one of the compose files' Redis passwords, from the settings' source, which these tests can't import.

    :param constant: The constant's name in cache.py, e.g. ``LOCAL_EXTENSION_WORKER_REDIS_PASSWORD``.
    :returns: The password.
    """
    text = CACHE_SETTINGS_PATH.read_text(encoding="utf-8")
    match = re.search(rf'^{constant} = "([^"]+)"$', text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"cache.py has no {constant}")
    return match.group(1)


def local_tool_worker_password() -> str:
    """
    Return LOCAL_TOOL_WORKER_REDIS_PASSWORD, from the settings' source, which these tests can't import.

    :returns: The password.
    """
    text = CACHE_SETTINGS_PATH.read_text(encoding="utf-8")
    match = re.search(r'^LOCAL_TOOL_WORKER_REDIS_PASSWORD = "([^"]+)"$', text, re.MULTILINE)
    if match is None:
        raise AssertionError("cache.py has no LOCAL_TOOL_WORKER_REDIS_PASSWORD")
    return match.group(1)


def compose_redis_command(text: str) -> list[str]:
    """
    Return the arguments of a docker-compose file's smarter-redis command.

    It is a list, not a string, because compose splits a string command like a shell, and stops at the
    ``>`` of the password. Prettier writes the list one argument per line.

    :param text: The docker-compose file.
    :returns: The command's arguments.
    """
    match = re.search(r"\n  smarter-redis:\n(?:    [^\n]*\n)*?    command:\s*\[(?P<arguments>[^\]]*)\]", text)
    if match is None:
        raise AssertionError("smarter-redis has no command list")
    arguments = re.findall(r'"([^"]*)"', match.group("arguments"))
    return arguments


def env_helper() -> str:
    """
    Return the smarter.env template of _helpers.tpl.

    :returns: Its text, from its define to its end.
    """
    text = HELPERS_PATH.read_text(encoding="utf-8")
    start = text.index('{{- define "smarter.env" -}}')
    end = text.index("{{- end }}", start)
    return text[start:end]


class TestOptionalAwsKeys(unittest.TestCase):
    """The AWS access keys can be left out of the pods' environment."""

    def test_schema_accepts_null(self):
        """The schema allows a string or null for each key."""
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        env_properties = schema["properties"]["env"]["properties"]
        for key in OPTIONAL_KEYS:
            with self.subTest(key=key):
                allowed = env_properties[key]["type"]
                self.assertIn("string", allowed)
                self.assertIn("null", allowed)

    def test_no_default_key(self):
        """Values.yaml sets no key, so a placeholder can never win over the IAM role."""
        text = VALUES_PATH.read_text(encoding="utf-8")
        for key in OPTIONAL_KEYS:
            with self.subTest(key=key):
                self.assertNotIn(f"\n  {key}:", text)

    def test_secret_leaves_out_null_values(self):
        """The env Secret skips a null value, rather than rendering an empty one."""
        self.assertIn('{{- $isNull := kindIs "invalid" $value -}}', env_helper())
        self.assertIn('include "smarter.env" . | fromYaml', TEMPLATE_PATH.read_text(encoding="utf-8"))


class TestEnvironment(unittest.TestCase):
    """Smarter.env: the settings that the chart writes into the env Secret, without a deploy workflow."""

    def test_leaves_out_placeholders(self):
        """A SET-ME placeholder is left out, so the setting gets Smarter's default, not the placeholder's text."""
        self.assertIn('(hasPrefix "SET-ME" $value)', env_helper())

    def test_derives_the_deployment_values(self):
        """The values that a deploy workflow used to compute are derived, unless env sets them."""
        helper = env_helper()
        for key in DERIVED_KEYS:
            with self.subTest(key=key):
                self.assertIn(f'(get $env "{key}" | default', helper)
                self.assertNotIn(f"\n  {key}:", VALUES_PATH.read_text(encoding="utf-8"))

    def test_reads_the_infrastructure_secrets(self):
        """Every Kubernetes Secret that smarter-infrastructure creates is mapped to the settings it holds."""
        values = VALUES_PATH.read_text(encoding="utf-8")
        for secret_name in INFRASTRUCTURE_SECRETS:
            with self.subTest(secret=secret_name):
                self.assertIn(f"\n    {secret_name}:\n", values)
        self.assertIn('lookup "v1" "Secret" $.Release.Namespace $secretName', env_helper())

    def test_broker_url_uses_the_generated_redis_password(self):
        """
        The broker's url is built from Redis's password, read from smarter-infrastructure's Secret.

        It is built after the Secrets are read, and only when env doesn't set it. The password used to be
        values.yaml's public default, smarter (ADR-030, rule 5).
        """
        helper = env_helper()
        secrets_read_at = helper.index('lookup "v1" "Secret"')
        broker_built_at = helper.index('set $env "DJANGO_CELERY_BROKER_URL"')
        self.assertLess(secrets_read_at, broker_built_at)
        self.assertIn('get $env "SMARTER_SUBSYSTEM_REDIS_PASSWORD"', helper)
        self.assertIn('(not (hasKey $env "DJANGO_CELERY_BROKER_URL"))', helper)
        self.assertIn("urlquery $redisPassword", helper)
        self.assertNotIn(".Values.redis.auth.password", helper)
        self.assertNotIn("\n  DJANGO_CELERY_BROKER_URL:", VALUES_PATH.read_text(encoding="utf-8"))

    def test_redis_reads_the_generated_password(self):
        """The Redis subchart reads its password from the same Secret as the pods, and values.yaml has none."""
        values = VALUES_PATH.read_text(encoding="utf-8")
        self.assertIn('existingSecret: "smarter-redis-password"', values)
        self.assertIn('existingSecretPasswordKey: "REDIS_PASSWORD"', values)
        self.assertIn("      REDIS_PASSWORD: SMARTER_SUBSYSTEM_REDIS_PASSWORD\n", values)
        self.assertNotIn('password: "smarter"', values)

    def test_redis_defines_the_tools_user_at_start(self):
        """
        Redis's start script appends the user tools to master.conf, from smarter-infrastructure's Secret.

        Not the subchart's auth.acl, which mounts its ACL file as a subPath inside the ConfigMap's directory:
        runc couldn't create that mount on the cluster's nodes, and Redis never started (2026-11-27).
        """
        values = VALUES_PATH.read_text(encoding="utf-8")
        self.assertNotIn("\n    acl:\n", values)
        self.assertNotIn("userSecret", values)
        self.assertIn("          secretName: smarter-redis-users\n          optional: true\n", values)
        self.assertIn("        mountPath: /opt/bitnami/redis/users\n", values)
        self.assertNotIn("mountPath: /opt/bitnami/redis/mounted-etc/", values)
        self.assertIn("        if [[ -f /opt/bitnami/redis/users/tools ]]; then\n", values)
        # a newline first: the copy of master.conf ends with a comment and no newline.
        self.assertIn("printf '\\n%s\\n' \"user tools on >", values)
        self.assertIn('" >> /opt/bitnami/redis/etc/master.conf\n', values)
        rules = tools_acl_rules()
        self.assertEqual(rules[0], "~tools_celery_task_queue*", "the queue must be the tools queue")
        self.assertNotIn("~*", rules)
        self.assertNotIn("&*", rules)
        for command in ("-@dangerous", "-scan", "-pubsub", "-subscribe", "-psubscribe"):
            with self.subTest(command=command):
                self.assertIn(command, rules)

    def test_extensions_user_reaches_only_its_queue(self):
        """The Extension worker's user may use its own queue, never the tools queue."""
        values = VALUES_PATH.read_text(encoding="utf-8")
        self.assertIn("        if [[ -f /opt/bitnami/redis/users/extensions ]]; then\n", values)
        rules = acl_rules("extensions")
        self.assertEqual(rules[0], "~extensions_celery_task_queue*")
        self.assertFalse(any(rule.lstrip("%RW~").startswith("tools_celery_task_queue") for rule in rules))
        self.assertFalse(any("robots_rules" in rule for rule in rules))
        self.assertNotIn("~*", rules)
        for command in ("-@dangerous", "-scan", "-pubsub", "-subscribe", "-psubscribe"):
            with self.subTest(command=command):
                self.assertIn(command, rules)
        tools = acl_rules("tools")
        self.assertFalse(any(rule.lstrip("%RW~").startswith("extensions_celery_task_queue") for rule in tools))

    def test_each_user_has_its_own_cache_results_keys(self):
        """
        Each worker's user reads and writes its own @cache_results keys, <user>_cache:*, and no other cache keys.

        CACHE_RESULTS["CACHE"] in settings/base.py puts them there. The only key of the platform's cache that
        either user reaches is Extensions' archives, read-only: no rule names another key under django*.
        """
        for user, other in (("tools", "extensions"), ("extensions", "tools")):
            with self.subTest(user=user):
                rules = acl_rules(user)
                self.assertIn(f"~{user}_cache:*", rules)
                self.assertFalse(any(rule.lstrip("%RW~").startswith(f"{other}_cache") for rule in rules))
                platform_cache_rules = [rule for rule in rules if rule.lstrip("%RW~").startswith("django")]
                self.assertEqual(platform_cache_rules, ["%R~django*:1:smarter:extension:archive:*"])

    def test_compose_redis_has_the_charts_rules(self):
        """
        Docker-compose.yml's and docker-compose.shard.yml's Redis define the same user, so the tests check the chart's rules.

        The password is LOCAL_TOOL_WORKER_REDIS_PASSWORD, which the tests connect with.
        """
        password = local_tool_worker_password()
        arguments = ["redis-server", "--requirepass", "smarter", "--user", "tools", "on", f">{password}"]
        arguments.extend(acl_rules("tools"))
        arguments.extend(["--user", "extensions", "on", f">{local_password('LOCAL_EXTENSION_WORKER_REDIS_PASSWORD')}"])
        arguments.extend(acl_rules("extensions"))
        for path in COMPOSE_PATHS:
            with self.subTest(compose=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(compose_redis_command(text), arguments)
                self.assertIn("      - SMARTER_SUBSYSTEM_REDIS_USERNAME=tools\n", text)
                self.assertIn(f"      - SMARTER_SUBSYSTEM_REDIS_PASSWORD={password}\n", text)
                self.assertIn("--without-mingle --without-gossip --without-heartbeat", text)

    def test_mariadb_reads_the_platform_passwords(self):
        """MariaDB's Secret keeps the subchart's own name, so that its pod spec doesn't change."""
        values = VALUES_PATH.read_text(encoding="utf-8")
        self.assertIn('existingSecret: "{{ .Release.Name }}-mariadb"', values)
        template = MARIADB_SECRET_PATH.read_text(encoding="utf-8")
        self.assertIn('{{- $name := printf "%s-mariadb" .Release.Name }}', template)
        for key in ("mariadb-root-password", "mariadb-password", "mariadb-replication-password"):
            with self.subTest(key=key):
                self.assertIn(f"  {key}:", template)


class TestMigrateEnvironment(unittest.TestCase):
    """
    The pre-upgrade migrate Job runs with the new release's settings, not the previous release's.

    Helm applies secret-env.yaml only after the pre-upgrade hooks. v0.46.16 renamed SECRET_KEY to
    DJANGO_SECRET_KEY, and its migrate Job, which read secret-env.yaml's Secret, failed with
    "DJANGO_SECRET_KEY is not set" and stopped the deploy.
    """

    @staticmethod
    def hook_weight(template: str) -> int:
        """
        Return a hook template's helm.sh/hook-weight.

        :param template: The template's text.
        :returns: Its weight.
        """
        match = re.search(r'"helm\.sh/hook-weight": "(-?\d+)"', template)
        if match is None:
            raise AssertionError("the template has no hook weight")
        weight = int(match.group(1))
        return weight

    def test_job_reads_the_hook_secret(self):
        """The Job's envFrom names the hook Secret, not the release's env Secret."""
        job = MIGRATE_JOB_PATH.read_text(encoding="utf-8")
        self.assertIn('name: "{{ .Values.global.appName }}-env-migrate"', job)
        self.assertNotIn('name: "{{ .Values.global.appName }}-env"\n', job)

    def test_hook_secret_has_the_platform_settings(self):
        """The hook Secret is built by smarter.env, like the env Secret, so it has the new release's names."""
        secret = MIGRATE_SECRET_PATH.read_text(encoding="utf-8")
        self.assertIn('name: "{{ .Values.global.appName }}-env-migrate"', secret)
        self.assertIn('include "smarter.env" . | fromYaml', secret)

    def test_hook_secret_is_created_before_the_job(self):
        """Both are pre-upgrade hooks, and the Secret's lower weight makes Helm create it first."""
        secret = MIGRATE_SECRET_PATH.read_text(encoding="utf-8")
        job = MIGRATE_JOB_PATH.read_text(encoding="utf-8")
        for template in (secret, job):
            self.assertIn('"helm.sh/hook": pre-upgrade', template)
        self.assertLess(self.hook_weight(secret), self.hook_weight(job))

    def test_hook_secret_is_replaced_on_each_upgrade(self):
        """A failed upgrade's copy is replaced by the next upgrade's, and a passing upgrade deletes it."""
        secret = MIGRATE_SECRET_PATH.read_text(encoding="utf-8")
        self.assertIn('"helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded', secret)


if __name__ == "__main__":
    unittest.main()
