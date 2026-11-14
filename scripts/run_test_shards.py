#!/usr/bin/env python3
"""Run the Python test suite in several shards at once, each in a Docker stack of its own.

Usage::

    python3 -I scripts/run_test_shards.py                          # 8 shards, the whole suite
    python3 -I scripts/run_test_shards.py --shards 4
    python3 -I scripts/run_test_shards.py --labels smarter.apps.account smarter.apps.secret
    python3 -I scripts/run_test_shards.py --keep                   # leave the stacks running afterwards

``make test-sharded`` (``SHARDS=<n>``) runs it. CI splits the suite the same way, eight shards on eight runners
(``SMARTER_TEST_SHARD``, ``smarter.lib.unittest.runner``). Locally the shards can't share one stack: the tests
write real rows without rollback, sweep every test account in teardown, clear the shared Redis cache, and send
requests and Celery tasks to the one dev server and its workers. So each shard gets its own Compose project,
``smarter-shard-<n>``, from ``docker-compose.shard.yml``: MariaDB, Redis, the api and the two workers, with no
Celery Beat, whose scheduled tasks would change the rows of running tests.

Steps:

1. Dump the local database (``smarter-mariadb``: the ``smarter`` and ``stackademy`` databases and the
   users), so that every shard starts from the platform that ``initialize_platform`` set up, as the one-stack
   run does. The dev stack's MariaDB must be running; the rest of it may be stopped.
2. Start every shard's MariaDB and Redis, load the dump into each, then start its api and workers, and wait for
   each dev server.
3. Run ``SMARTER_TEST_SHARD=<n>/<shards> python manage.py test <labels>`` in every shard's api at once. Each
   shard's output goes to ``<out>/shard-<n>.log``.
4. Print each shard's result and every failing test, then stop and remove the stacks, unless ``--keep``.

It needs the ``smarter`` image (``make build``) and about 4 GB of Docker's memory per shard. It exits with 1
when a shard fails, or ends without a result, e.g. when Docker ran out of memory.
"""

import argparse
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPOSITORY_ROOT / "docker-compose.shard.yml"
DEFAULT_OUT = REPOSITORY_ROOT / ".test-shards"
DEV_MARIADB = "smarter-mariadb"
ROOT_PASSWORD = "smarter"
DATABASES = ["smarter", "stackademy"]
PROJECT_PREFIX = "smarter-shard-"
STORES = ["smarter-mariadb", "smarter-redis"]
APPLICATIONS = ["smarter-api", "smarter-worker", "smarter-worker-infrastructure"]
WORKDIR = "/home/smarter_user/smarter"
READY_TIMEOUT_SECONDS = 300
ANSI = re.compile(r"\x1b\[[0-9;]*m")


@dataclass
class ShardResult:
    """What a shard's log says about its run."""

    shard: int
    ran: int | None = None
    ok: bool = False
    summary: str = "no result"
    failures: list[str] = field(default_factory=list)


def project(shard: int) -> str:
    """The Compose project of a shard, e.g. smarter-shard-3."""
    return f"{PROJECT_PREFIX}{shard}"


def container(shard: int, service: str) -> str:
    """The name that Compose gives a shard's service's container, e.g. smarter-shard-3-smarter-api-1."""
    return f"{project(shard)}-{service}-1"


def compose(shard: int, *arguments: str) -> list[str]:
    """A docker compose command for a shard's project."""
    return ["docker", "compose", "-p", project(shard), "-f", str(COMPOSE_FILE), *arguments]


def test_command(shard: int, shards: int, labels: list[str]) -> list[str]:
    """The command that runs a shard's tests in its api container."""
    test = f"cd {WORKDIR} && python manage.py test {' '.join(labels)} --noinput"
    environment = f"SMARTER_TEST_SHARD={shard}/{shards}"
    return ["docker", "exec", "-e", environment, container(shard, "smarter-api"), "bash", "-c", test]


def parse_log(shard: int, text: str) -> ShardResult:
    """
    Read a shard's result from its test output.

    :param shard: The shard's number.
    :param text: Its output, with or without terminal colors.
    :returns: Its result: the number of tests it ran, whether they passed, the runner's summary line,
        e.g. ``FAILED (failures=1, skipped=3)``, and each failing test's ``FAIL:`` or ``ERROR:`` line.
    """
    result = ShardResult(shard=shard)
    plain = ANSI.sub("", text)
    for line in plain.splitlines():
        stripped = line.strip()
        ran = re.match(r"^Ran (\d+) tests? in ", stripped)
        if ran:
            result.ran = int(ran.group(1))
            continue
        if re.match(r"^(OK|FAILED)\b", stripped):
            result.summary = stripped
            result.ok = stripped.startswith("OK")
            continue
        if re.match(r"^(FAIL|ERROR): ", stripped) and stripped not in result.failures:
            result.failures.append(stripped)
    if result.ran is None:
        result.ok = False
    return result


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command, and fail with its output when it fails."""
    completed = subprocess.run(command, capture_output=True, text=True, check=False, **kwargs)
    if completed.returncode != 0:
        output = (completed.stdout + completed.stderr).strip()
        raise RuntimeError(f"{' '.join(command)} failed:\n{output}")
    return completed


def dump_database(out: Path) -> Path:
    """Dump the local database's Smarter databases and users into ``<out>/dump.sql``."""
    dump = out / "dump.sql"
    command = [
        "docker",
        "exec",
        DEV_MARIADB,
        "mariadb-dump",
        "-uroot",
        f"-p{ROOT_PASSWORD}",
        "--single-transaction",
        "--system=users",
        "--insert-ignore",
        "--databases",
        *DATABASES,
    ]
    with dump.open("w", encoding="utf-8") as file:
        completed = subprocess.run(command, stdout=file, stderr=subprocess.PIPE, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Couldn't dump {DEV_MARIADB}'s database. Is it running?\n{completed.stderr.strip()}")
    return dump


def wait_for(description: str, command: list[str]) -> None:
    """Run a command until it succeeds, for up to READY_TIMEOUT_SECONDS."""
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode == 0:
            return
        time.sleep(2)
    raise RuntimeError(f"{description} wasn't ready after {READY_TIMEOUT_SECONDS} seconds.")


def start_shard(shard: int, dump: Path) -> None:
    """Start a shard's stack with a copy of the local database, and wait for its dev server."""
    run(compose(shard, "up", "-d", *STORES))
    mariadb = container(shard, "smarter-mariadb")
    # the image's own check, over TCP: on its first start, the image runs a temporary server, on its socket
    # only, while it creates the database, then restarts. A ping on the socket would answer too early.
    ready = ["docker", "exec", mariadb, "healthcheck.sh", "--connect", "--innodb_initialized"]
    wait_for(f"{mariadb}'s MariaDB", ready)
    with dump.open("r", encoding="utf-8") as file:
        load = subprocess.run(
            ["docker", "exec", "-i", mariadb, "mariadb", "-uroot", f"-p{ROOT_PASSWORD}"],
            stdin=file,
            capture_output=True,
            text=True,
            check=False,
        )
    if load.returncode != 0:
        raise RuntimeError(f"Couldn't load the database into {mariadb}:\n{load.stderr.strip()}")
    run(["docker", "exec", mariadb, "mariadb", "-uroot", f"-p{ROOT_PASSWORD}", "-e", "FLUSH PRIVILEGES"])
    run(compose(shard, "up", "-d", *APPLICATIONS))
    api = container(shard, "smarter-api")
    # the dev server answers / with a redirect to the console's sign-in page once it is up.
    probe = (
        "import urllib.request, sys\n"
        "class NoRedirect(urllib.request.HTTPRedirectHandler):\n"
        "    def redirect_request(self, *args, **kwargs):\n"
        "        return None\n"
        "opener = urllib.request.build_opener(NoRedirect)\n"
        "try:\n"
        "    opener.open('http://localhost:9357/', timeout=5)\n"
        "except urllib.error.HTTPError as e:\n"
        "    sys.exit(0 if e.code == 302 else 1)\n"
        "except Exception:\n"
        "    sys.exit(1)\n"
    )
    wait_for(f"{api}'s dev server", ["docker", "exec", api, "python", "-c", probe])


def stop_shard(shard: int) -> None:
    """Stop and remove a shard's stack, and its network."""
    subprocess.run(compose(shard, "down", "--remove-orphans"), capture_output=True, check=False)


def run_shard(shard: int, shards: int, labels: list[str], out: Path) -> ShardResult:
    """Run a shard's tests, write its output to ``<out>/shard-<n>.log``, and read its result."""
    log = out / f"shard-{shard}.log"
    with log.open("w", encoding="utf-8") as file:
        subprocess.run(test_command(shard, shards, labels), stdout=file, stderr=subprocess.STDOUT, check=False)
    text = log.read_text(encoding="utf-8", errors="replace")
    return parse_log(shard, text)


def report(results: list[ShardResult], out: Path) -> bool:
    """Print each shard's result and the failing tests.

    Returns whether every shard passed.
    """
    print()
    for result in results:
        ran = "?" if result.ran is None else str(result.ran)
        print(f"shard {result.shard}: ran {ran} tests, {result.summary}   ({out / f'shard-{result.shard}.log'})")
    total = sum(result.ran or 0 for result in results)
    failures = [failure for result in results for failure in result.failures]
    passed = all(result.ok for result in results)
    print(f"\n{total} tests in {len(results)} shards: {'OK' if passed else 'FAILED'}")
    for failure in failures:
        print(f"  {failure}")
    return passed


def main(argv: list[str] | None = None) -> int:
    """Run the suite in shards.

    Returns the exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--shards", type=int, default=8, help="how many shards, each in its own stack (default 8)")
    parser.add_argument("--labels", nargs="+", default=["smarter"], help="what to test (default: smarter)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="where the logs go (default .test-shards/)")
    parser.add_argument("--keep", action="store_true", help="leave the stacks running afterwards")
    options = parser.parse_args(argv)
    if options.shards < 1:
        parser.error("--shards must be 1 or more")

    shards = list(range(1, options.shards + 1))
    out: Path = options.out
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        print(f"Dumping {DEV_MARIADB}'s database ...")
        dump = dump_database(out)
        print(f"Starting {len(shards)} stacks ...")
        with ThreadPoolExecutor(max_workers=len(shards)) as pool:
            list(pool.map(lambda shard: start_shard(shard, dump), shards))
        print(f"Running {len(shards)} shards of {' '.join(options.labels)}, logs in {out}/ ...")
        with ThreadPoolExecutor(max_workers=len(shards)) as pool:
            results = list(pool.map(lambda shard: run_shard(shard, options.shards, options.labels, out), shards))
    except RuntimeError as e:
        print(e, file=sys.stderr)
        results = None
    finally:
        if not options.keep:
            print("Stopping the stacks ...")
            with ThreadPoolExecutor(max_workers=len(shards)) as pool:
                list(pool.map(stop_shard, shards))

    if results is None:
        return 1
    passed = report(results, out)
    minutes = (time.monotonic() - started) / 60
    print(f"\nTook {minutes:.1f} minutes.")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
