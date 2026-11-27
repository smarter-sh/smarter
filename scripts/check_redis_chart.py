#!/usr/bin/env python3
"""
Start the Helm chart's Redis the way its pod starts it, and check its ACL users (``make redis-chart-check``).

The chart gives the tool worker its own Redis user, ``tools`` (ADR-030, rule 8), which the Redis subchart's start
script defines when Redis starts (``redis.master.preExecCmds`` in values.yaml). Neither docker-compose, which gives
Redis its users on the command line, nor ``helm template``, which starts nothing, runs that script. On 2026-11-27
a version of the chart that rendered correctly kept Redis from starting in prod: its ACL file was mounted where
runc couldn't create the mount. Then a fix was written to a config file that ended with a comment, which swallowed
the user. Only starting the real image showed either. This does that:

1. Render the chart's Redis with ``helm template``, from a copy of the chart, with its values.yaml.
2. Start the image that the chart pins, with the rendered start script and configuration, as the pod's container
   runs: user 1001, a read-only root filesystem, the same writable directories, the password files mounted where
   the pod mounts its Secrets, and the same environment.
3. Check that Redis starts, that ``default`` and ``tools`` exist, that ``tools`` may do what the tool worker needs
   and is refused the rest, and that Redis also starts without the tools Secret, with no user ``tools``.

It needs helm and docker, and the network to download the chart's dependencies and the image. It changes
nothing outside a temporary directory and its own two containers, which it removes. Run it from the
repository's root, before a change to the chart's Redis, or to Redis's image:

    python3 -I scripts/check_redis_chart.py
"""

import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
CHARTS_DIR = REPOSITORY_ROOT / "helm" / "charts"
CHART_NAME = "smarter"
SIBLING_CHARTS = ("slack-bot",)
"""Charts that the smarter chart depends on by a relative path, which are copied beside it."""

CHECK_VERSION = "0.0.0-check"
"""A valid chart version for the copy: Helm 4 refuses the placeholder in Chart.yaml, which the deploy replaces."""

SCRIPTS_TEMPLATE = "charts/redis/templates/scripts-configmap.yaml"
CONFIG_TEMPLATE = "charts/redis/templates/configmap.yaml"
STATEFULSET_TEMPLATE = "charts/redis/templates/master/application.yaml"

START_SCRIPT = "start-master.sh"
SCRIPTS_PATH = "/opt/bitnami/scripts/start-scripts"
CONFIG_PATH = "/opt/bitnami/redis/mounted-etc"
SECRETS_PATH = "/opt/bitnami/redis/secrets"
USERS_PATH = "/opt/bitnami/redis/users"
WRITABLE_PATHS = (
    "/opt/bitnami/redis/etc",
    "/tmp",
    "/data",
)  # nosec B108: paths in the container, as the pod mounts them
"""The paths that the pod mounts from an emptyDir or a volume: the only writable ones."""

RUN_AS = "1001:1001"
DEFAULT_PASSWORD = "DefaultCheckPassword1"
USER_PASSWORDS = {"tools": "ToolsCheckPassword1", "extensions": "ExtensionsCheckPassword1"}
"""The throwaway password of each worker's ACL user: the tool worker's, and the Extension worker's (issue #1077)."""
CONTAINER_PREFIX = "smarter-redis-chart-check"
READY_LINE = "Ready to accept connections"
READY_TIMEOUT_SECONDS = 60

ALLOWED_TO_TOOLS = (
    ("read its own queue", ("LLEN", "tools_celery_task_queue")),
    ("push to its own queue's keys", ("RPUSH", "tools_celery_task_queue.check", "x")),
    ("write a tool call's result", ("SET", "celery-task-meta-check", "x")),
)
"""What the tool worker's user must be allowed: a description, and the redis-cli arguments."""

REFUSED_TO_BOTH = (
    ("push to the infrastructure queue", ("RPUSH", "infrastructure_celery_task_queue", "x")),
    ("push to the operational queue", ("RPUSH", "default_celery_task_queue", "x")),
    ("write kombu's routing set", ("SADD", "_kombu.binding.tools_celery_task_queue", "x")),
    ("read the shared unacked messages", ("HLEN", "unacked")),
    ("read a session", ("-n", "2", "EXISTS", ":1:django.contrib.sessions.cachecheck")),
    ("read RedBeat's schedule", ("EXISTS", "redbeat::schedule")),
    ("list the keys with SCAN", ("SCAN", "0")),
    ("list the keys with KEYS", ("KEYS", "*")),
    ("list the pub/sub channels", ("PUBSUB", "CHANNELS")),
)
"""What both workers' users must be refused with NOPERM: a description, and the redis-cli arguments."""

REFUSED_TO_TOOLS = REFUSED_TO_BOTH + (("read the Extensions queue", ("LLEN", "extensions_celery_task_queue")),)
"""What the tool worker's user must be refused, besides :data:`REFUSED_TO_BOTH`."""

ALLOWED_TO_EXTENSIONS = (
    ("read its own queue", ("LLEN", "extensions_celery_task_queue")),
    ("push to its own queue's keys", ("RPUSH", "extensions_celery_task_queue.check", "x")),
    ("write a tool call's result", ("SET", "celery-task-meta-check", "x")),
)
"""What the Extension worker's user must be allowed."""

REFUSED_TO_EXTENSIONS = REFUSED_TO_BOTH + (
    ("read the tools queue", ("LLEN", "tools_celery_task_queue")),
    ("read the tool worker's in-flight messages", ("HLEN", "tools_celery_task_queue.unacked")),
    (
        "write the robots.txt cache",
        ("-n", "1", "SET", "django6:1:smarter.apps.llmtool.plugin.websearch_fetch.robots_rules.check", "x"),
    ),
)
"""What the Extension worker's user must be refused: the tool worker's queue above all."""

USER_CHECKS = (
    ("tools", ALLOWED_TO_TOOLS, REFUSED_TO_TOOLS),
    ("extensions", ALLOWED_TO_EXTENSIONS, REFUSED_TO_EXTENSIONS),
)
"""Each worker's user, what it may do, and what it must be refused."""


def run(command: list[str], cwd: Path | None = None) -> str:
    """
    Run a command, and return its output.

    :param command: The command and its arguments.
    :param cwd: The directory to run it in.
    :returns: Its standard output.
    :raises RuntimeError: If it fails, with its error output.
    """
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{' '.join(command[:3])} failed:\n{completed.stderr.strip()}")
    return completed.stdout


def prepare_chart(work: Path) -> Path:
    """
    Copy the chart and its sibling charts into a directory, give it a valid version, and build its dependencies.

    :param work: The directory.
    :returns: The copy of the chart.
    """
    chart = work / CHART_NAME
    shutil.copytree(CHARTS_DIR / CHART_NAME, chart, ignore=shutil.ignore_patterns("charts"))
    for sibling in SIBLING_CHARTS:
        shutil.copytree(CHARTS_DIR / sibling, work / sibling)
    chart_yaml = chart / "Chart.yaml"
    text = chart_yaml.read_text(encoding="utf-8")
    text = re.sub(r"(?m)^version: .*$", f"version: {CHECK_VERSION}", text)
    chart_yaml.write_text(text, encoding="utf-8")
    run(["helm", "dependency", "build", "."], cwd=chart)
    return chart


def render(chart: Path, template: str) -> str:
    """
    Render one template of the chart.

    :param chart: The chart.
    :param template: The template's path in the chart, e.g. ``charts/redis/templates/configmap.yaml``.
    :returns: The rendered manifest.
    """
    manifest = run(["helm", "template", CHART_NAME, ".", "--namespace", "check", "--show-only", template], cwd=chart)
    return manifest


BLOCK_START = re.compile(r"^  (\S+): \|([-+]?)$")
"""The first line of a ConfigMap's value, as Helm writes it: ``  key: |`` or ``  key: |-``."""


def data_section(manifest: str) -> list[str]:
    """
    Return the lines of a rendered ConfigMap after its ``data:`` line.

    :param manifest: The rendered ConfigMap.
    :returns: The lines, or none if it has no data.
    """
    lines = manifest.splitlines()
    if "data:" not in lines:
        return []
    start = lines.index("data:") + 1
    return lines[start:]


def store_value(data: dict[str, str], key: str | None, chomp: str, body: list[str]) -> None:
    """
    Store a ConfigMap's value, from its block scalar's lines, as the pod's file holds it.

    :param data: The values so far, to which this one is added.
    :param key: The value's key, or None before the first.
    :param chomp: The block scalar's chomping indicator: ``-`` for no final newline, else one.
    :param body: Its lines, without their indentation.
    """
    if key is None:
        return
    lines = list(body)
    while lines and lines[-1] == "":
        lines.pop()
    value = "\n".join(lines)
    if chomp != "-":
        value = value + "\n"
    data[key] = value


def configmap_data(manifest: str) -> dict[str, str]:
    """
    Return a rendered ConfigMap's data, each value exactly as the pod's file holds it.

    Helm writes each value as a literal block scalar, ``key: |`` or ``key: |-``, indented four spaces. ``|-`` means
    no newline at the end, which matters: Redis's config file ends that way.

    :param manifest: The rendered ConfigMap.
    :returns: Each key's value.
    """
    data: dict[str, str] = {}
    key = None
    chomp = ""
    body: list[str] = []
    for line in data_section(manifest):
        start = BLOCK_START.match(line)
        if start:
            store_value(data, key, chomp, body)
            key = start.group(1)
            chomp = start.group(2)
            body = []
        elif line.startswith("    ") or not line.strip():
            body.append(line[4:])
        else:
            break
    store_value(data, key, chomp, body)
    return data


def container_env(manifest: str) -> dict[str, str]:
    """
    Return the environment variables that a rendered StatefulSet's container sets by value.

    :param manifest: The rendered StatefulSet.
    :returns: Each variable's value.
    """
    env = {}
    for name, value in re.findall(r'- name: ([A-Z_]+)\n\s+value: "?([^"\n]*)"?', manifest):
        env[name] = value
    return env


def image_reference(manifest: str) -> str:
    """
    Return the image of a rendered StatefulSet's first container.

    :param manifest: The rendered StatefulSet.
    :returns: The image, e.g. ``registry-1.docker.io/bitnami/redis@sha256:...``.
    :raises ValueError: If it has none.
    """
    match = re.search(r"(?m)^\s+image: (\S+)$", manifest)
    if match is None:
        raise ValueError("the StatefulSet has no image")
    return match.group(1).strip('"')


def volume_mounts(manifest: str) -> list[tuple[str, str]]:
    """
    Return a rendered StatefulSet's volume mounts, as each volume's name and its mount path.

    :param manifest: The rendered StatefulSet.
    :returns: Each mount's volume name and path, in order, without a trailing slash.
    """
    mounts = []
    pattern = (
        r"-\s+(?:mountPath: (?P<path1>\S+)\s+name: (?P<name1>\S+)|name: (?P<name2>\S+)\s+mountPath: (?P<path2>\S+))"
    )
    for match in re.finditer(pattern, manifest):
        path = match.group("path1") or match.group("path2")
        name = match.group("name1") or match.group("name2")
        mounts.append((name.strip('"'), path.strip('"').rstrip("/")))
    return mounts


def nested_mounts(mounts: list[tuple[str, str]]) -> list[str]:
    """
    Name the mounts whose path is inside another mount's path.

    runc must create such a mount's target inside the other volume, which it can't do in a read-only volume
    such as a ConfigMap's or a Secret's: on 2026-11-27 the Redis subchart's ACL file, mounted inside its
    ConfigMap's directory, kept Redis from starting in prod ("not a directory"). docker run, which this script
    uses, doesn't reproduce that, so the rendered StatefulSet is checked instead.

    :param mounts: From :func:`volume_mounts`.
    :returns: Each nested mount, described with the mount it is inside.
    """
    nested = []
    for inner_name, inner_path in mounts:
        for outer_name, outer_path in mounts:
            if inner_path == outer_path:
                continue
            if inner_path.startswith(outer_path + "/"):
                nested.append(f"{inner_name} at {inner_path}, inside {outer_name} at {outer_path}")
    return nested


def write_pod_files(pod: Path, scripts: dict[str, str], config: dict[str, str], env: dict[str, str]) -> None:
    """
    Write the files that the pod mounts: the start scripts, the configuration, and the two Secrets.

    :param pod: The directory to write them in.
    :param scripts: The start scripts, from the scripts ConfigMap.
    :param config: The configuration files, from the configuration ConfigMap.
    :param env: The container's environment, which names the default password's file.
    """
    for directory in ("scripts", "config", "secrets", "users", "no-users"):
        (pod / directory).mkdir(parents=True)
    for name, text in scripts.items():
        path = pod / "scripts" / name
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)
    for name, text in config.items():
        (pod / "config" / name).write_text(text, encoding="utf-8")
    password_file = Path(env.get("REDIS_PASSWORD_FILE", f"{SECRETS_PATH}/redis-password")).name
    (pod / "secrets" / password_file).write_text(DEFAULT_PASSWORD, encoding="utf-8")
    for user, password in USER_PASSWORDS.items():
        (pod / "users" / user).write_text(password, encoding="utf-8")
    for path in pod.rglob("*"):
        mode = 0o755 if path.is_dir() or path.suffix == ".sh" else 0o644
        path.chmod(mode)


def start_redis(name: str, pod: Path, image: str, env: dict[str, str], users: str) -> None:
    """
    Start Redis's container as the pod runs it.

    :param name: The container's name.
    :param pod: The directory of the pod's files.
    :param image: The image.
    :param env: The container's environment.
    :param users: The directory of ``pod`` to mount as the tools Secret: ``users``, or ``no-users`` for none.
    """
    command = ["docker", "run", "-d", "--name", name, "--user", RUN_AS, "--read-only"]
    for path in WRITABLE_PATHS:
        command += ["--tmpfs", f"{path}:uid=1001"]
    for variable, value in env.items():
        command += ["-e", f"{variable}={value}"]
    mounts = (
        ("scripts", SCRIPTS_PATH),
        ("config", CONFIG_PATH),
        ("secrets", SECRETS_PATH),
        (users, USERS_PATH),
    )
    for source, target in mounts:
        command += ["-v", f"{pod / source}:{target}:ro"]
    command += ["--entrypoint", "/bin/bash", image, "-ec", f"{SCRIPTS_PATH}/{START_SCRIPT}"]
    run(command)


def wait_until_ready(name: str) -> bool:
    """
    Wait for Redis to accept connections.

    :param name: The container's name.
    :returns: True if it did within the timeout; False if it didn't, or its container stopped.
    """
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        logs = subprocess.run(["docker", "logs", name], capture_output=True, text=True, check=False)
        if READY_LINE in logs.stdout + logs.stderr:
            return True
        state = run(["docker", "inspect", "-f", "{{.State.Running}}", name]).strip()
        if state != "true":
            return False
        time.sleep(1)
    return False


def redis_cli(name: str, user: str, password: str, arguments: tuple[str, ...]) -> str:
    """
    Run redis-cli in the container as a user, and return its first line of output.

    :param name: The container's name.
    :param user: The ACL user.
    :param password: The user's password.
    :param arguments: The command, with its arguments.
    :returns: The first line of what it printed, its error included.
    """
    command = ["docker", "exec", name, "redis-cli", "--user", user, "--pass", password, "--no-auth-warning"]
    completed = subprocess.run(command + list(arguments), capture_output=True, text=True, check=False)
    output = (completed.stdout + completed.stderr).strip()
    first_line = output.splitlines()[0] if output else ""
    return first_line


def acl_users(name: str) -> list[str]:
    """
    Return the names of Redis's ACL users.

    :param name: The container's name.
    :returns: The usernames.
    """
    output = run(["docker", "exec", name, "redis-cli", "-a", DEFAULT_PASSWORD, "--no-auth-warning", "ACL", "USERS"])
    return output.split()


def check(passed: bool, description: str, failures: list[str]) -> None:
    """
    Print a check's result, and remember a failure.

    :param passed: Whether it passed.
    :param description: What it checked.
    :param failures: The failures so far, to which a failure is added.
    """
    mark = "ok  " if passed else "FAIL"
    print(f"  {mark} {description}")
    if not passed:
        failures.append(description)


def check_with_tools(name: str, failures: list[str]) -> None:
    """
    Check Redis started with the users Secret: every user, and what each worker's user may and may not do.

    :param name: The container's name.
    :param failures: The failures so far.
    """
    users = acl_users(name)
    expected = ["default", *USER_PASSWORDS]
    check(sorted(users) == sorted(expected), f"the users are {', '.join(expected)} ({', '.join(users)})", failures)
    for user, allowed_checks, refused_checks in USER_CHECKS:
        password = USER_PASSWORDS[user]
        for description, arguments in allowed_checks:
            answer = redis_cli(name, user, password, arguments)
            allowed = not answer.startswith(("NOPERM", "AUTH failed", "NOAUTH", "WRONGPASS", "ERR"))
            check(allowed, f"{user} may {description}: {answer}", failures)
        for description, arguments in refused_checks:
            answer = redis_cli(name, user, password, arguments)
            check(answer.startswith("NOPERM"), f"{user} can't {description}: {answer}", failures)
    answer = redis_cli(name, "default", DEFAULT_PASSWORD, ("LLEN", "infrastructure_celery_task_queue"))
    check(answer.isdigit(), f"default may read the infrastructure queue: {answer}", failures)


def remove(name: str) -> None:
    """Remove a container, if it exists."""
    subprocess.run(["docker", "rm", "-f", name], capture_output=True, check=False)


def main() -> int:
    """
    Render the chart's Redis, start it twice, with and without the tools Secret, and check each.

    :returns: 0 if every check passed, 1 otherwise.
    """
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="redis-chart-check-") as directory:
        work = Path(directory)
        print("Rendering the chart's Redis ...")
        chart = prepare_chart(work)
        scripts = configmap_data(render(chart, SCRIPTS_TEMPLATE))
        config = configmap_data(render(chart, CONFIG_TEMPLATE))
        statefulset = render(chart, STATEFULSET_TEMPLATE)
        env = container_env(statefulset)
        image = image_reference(statefulset)
        nested = nested_mounts(volume_mounts(statefulset))
        check(not nested, "no volume is mounted inside another volume's mount", failures)
        for description in nested:
            print(f"       {description}")
        pod = work / "pod"
        write_pod_files(pod, scripts, config, env)
        runs = (("with the users Secret", "users"), ("without the users Secret", "no-users"))
        for label, users in runs:
            name = f"{CONTAINER_PREFIX}-{users}"
            remove(name)
            print(f"Starting {image} {label} ...")
            try:
                start_redis(name, pod, image, env, users)
                ready = wait_until_ready(name)
                check(ready, "Redis starts and accepts connections", failures)
                if not ready:
                    print(subprocess.run(["docker", "logs", name], capture_output=True, text=True).stderr[-2000:])
                    continue
                if users == "users":
                    check_with_tools(name, failures)
                else:
                    names = acl_users(name)
                    check(names == ["default"], f"the only user is default ({', '.join(names)})", failures)
            finally:
                remove(name)
    if failures:
        print(f"\n{len(failures)} check(s) failed.")
        return 1
    print("\nEvery check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
