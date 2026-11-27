#!/usr/bin/env python3
"""
Draw the diagrams of docs/source/adr/030-task-queues.rst: its inventory of the code, and its security.

Usage: adr-030-diagrams.py [output folder]   (default: docs/source/_static/adr-030, from the repository root)

- queues.svg: who sends tasks, the three queues in Redis, the worker that runs each, and the tasks that still
  wait by sleeping.
- redis-trust.svg: every pod that holds Redis's url, what Redis's three databases hold, and what code in the
  tool worker, which holds no credential but that url, can do with it.

They describe the code as of 0.48.8: keep them true when a task, a queue, a worker, a Beat entry or Redis's
access control changes. Edit the function, run the script, and render each result to check it:
rsvg-convert -w 1875 <svg> -o <scratchpad>/<name>.png.

It draws with the Diagram class of security-diagrams.py, loaded from beside this file, so that the diagrams
share one look and one copy of their drawing code.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "../../.."))
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "docs/source/_static/adr-030")


def load_security_diagrams():
    """Return the security-diagrams.py module, whose name isn't importable, writing to this script's folder."""
    path = os.path.join(HERE, "security-diagrams.py")
    spec = importlib.util.spec_from_file_location("security_diagrams", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    # it reads its output folder from sys.argv when it loads, so it is given ours.
    saved_argv = sys.argv
    sys.argv = [path, OUT_DIR]
    try:
        spec.loader.exec_module(module)
    finally:
        sys.argv = saved_argv
    return module


security = load_security_diagrams()
Diagram = security.Diagram
MUTED = security.MUTED
RED = security.RED


# ---------------------------------------------------------------------------------------------------------------
# queues.svg
# ---------------------------------------------------------------------------------------------------------------
def queues():
    """Who sends tasks, the three queues, the worker that runs each, and the waits that still sleep."""
    d = Diagram(
        "queues",
        1300,
        840,
        "Smarter's task queues, as built",
        "three queues in one Redis, one worker each; the queue a task runs in is routing, not a permission",
        "Three columns. The senders: the app, which queues tasks from its brokers, chats and signals; Celery Beat, "
        "whose 20 schedule entries name 14 operational tasks and 6 infrastructure tasks; the infrastructure tasks "
        "themselves, which check again later with apply_async and a countdown; and the init Job. The queues, all in "
        "Redis's database 0: default_celery_task_queue with 33 operational tasks, infrastructure_celery_task_queue "
        "with 22 infrastructure tasks, and tools_celery_task_queue with one task, run_tool_call, whose results the "
        "app waits for in the result backend, also in Redis. The workers: smarter-worker runs the default queue and "
        "smarter-worker-infrastructure the infrastructure queue; both register all 56 of the platform's tasks, so "
        "either would run any task that lands on its queue. smarter-worker-tools runs the tools queue, and registers "
        "only run_tool_call. Four infrastructure tasks still wait by sleeping, against the ADR's second rule: "
        "verify_certificate, up to nine and a half minutes, though nothing queues it; register_custom_domain and "
        "verify_custom_domain, up to ten minutes for a certificate's validation records and two and a quarter "
        "minutes for each record; and create_custom_domain_dns_record, two and a quarter minutes.",
    )

    # 1. the senders
    d.heading(28, 100, 330, "1 · Who sends tasks")
    d.box(
        "api",
        28,
        124,
        330,
        "smarter-api",
        ["brokers: deploy, delete, apply", "chats: history, charges, journal", "each tool call, when remote"],
        code="task.delay(), on_commit",
    )
    d.box(
        "beat",
        28,
        268,
        330,
        "smarter-beat",
        ["20 entries: 14 operational,", "6 infrastructure (each names its queue)"],
        code="RedBeat, its schedule in Redis",
    )
    d.box(
        "again",
        28,
        394,
        330,
        "The infrastructure tasks",
        ["a wait is a check, then a check later:", "deploy_default_api, verify_domain, …"],
        code="apply_async(countdown=…)",
    )
    d.box(
        "init",
        28,
        520,
        330,
        "job-init",
        ["initialize_platform: indexing,", "a repository's manifests"],
        code="index_repositories.delay()",
    )

    # 2. the queues
    d.heading(470, 100, 340, "2 · Redis, database 0")
    d.region(458, 116, 364, 520, "smarter-redis", note="one server, one password")
    d.box(
        "default",
        476,
        170,
        328,
        "Operational: 33 tasks",
        ["prompt history, charges, budgets,", "journal, indexing, data exports"],
        "data",
        code="default_celery_task_queue",
    )
    d.box(
        "infrastructure",
        476,
        296,
        328,
        "Infrastructure: 22 tasks",
        ["DNS, certificates, ingresses,", "LLMHosts, node groups, vectorstores"],
        "data",
        code="infrastructure_celery_task_queue",
    )
    d.box(
        "tools",
        476,
        422,
        328,
        "Tool calls: 1 task",
        ["run_tool_call: a resolved call,", "with its decrypted credentials"],
        "data",
        code="tools_celery_task_queue",
    )
    d.box(
        "results",
        476,
        548,
        328,
        "The result backend",
        ["run_tool_call's results only, 300 s"],
        "data",
        code="celery-task-meta-<task id>",
    )

    # 3. the workers
    d.heading(930, 100, 342, "3 · Who runs them")
    d.box(
        "worker",
        930,
        170,
        342,
        "smarter-worker",
        ["concurrency 5 · database, every credential", "registers all 56 platform tasks"],
        "core",
        code="-Q default_celery_task_queue",
    )
    d.box(
        "infra",
        930,
        296,
        342,
        "smarter-worker-infrastructure",
        ["concurrency 4 · the Kubernetes and IAM roles", "registers all 56 platform tasks"],
        "core",
        code="-Q infrastructure_celery_task_queue",
    )
    d.box(
        "toolworker",
        930,
        422,
        342,
        "smarter-worker-tools",
        ["no database, no credential, no token", "registers run_tool_call only"],
        "core",
        code="-Q tools_celery_task_queue",
    )

    # the senders' arrows, to the queues' left edges
    api_x, api_y = d.right("api")
    default_x, default_y = d.left("default")
    infrastructure_x, infrastructure_y = d.left("infrastructure")
    tools_x, tools_y = d.left("tools")
    d.arrow([(api_x, api_y - 20), (400, api_y - 20), (400, default_y), (default_x, default_y)], "blue")
    d.arrow(
        [(api_x, api_y), (412, api_y), (412, infrastructure_y - 14), (infrastructure_x, infrastructure_y - 14)], "blue"
    )
    d.arrow([(api_x, api_y + 20), (424, api_y + 20), (424, tools_y), (tools_x, tools_y)], "blue")
    beat_x, beat_y = d.right("beat")
    d.arrow([(beat_x, beat_y - 8), (436, beat_y - 8), (436, default_y + 18), (default_x, default_y + 18)], "blue")
    d.arrow(
        [(beat_x, beat_y + 8), (436, beat_y + 8), (436, infrastructure_y), (infrastructure_x, infrastructure_y)], "blue"
    )
    again_x, again_y = d.right("again")
    d.arrow(
        [(again_x, again_y), (448, again_y), (448, infrastructure_y + 14), (infrastructure_x, infrastructure_y + 14)],
        "blue",
    )
    init_x, init_y = d.right("init")
    d.arrow([(init_x, init_y), (388, init_y), (388, default_y + 30), (default_x, default_y + 30)], dashed=True)

    # the queues to their workers
    for queue_key, worker_key in (("default", "worker"), ("infrastructure", "infra"), ("tools", "toolworker")):
        queue_x, queue_y = d.right(queue_key)
        worker_x, worker_y = d.left(worker_key)
        d.arrow([(queue_x, queue_y), (worker_x, worker_y)], "green")

    # the tool worker's result, and the app's wait for it
    toolworker_x, toolworker_y, _toolworker_w, toolworker_h = d.boxes["toolworker"]
    results_x, results_y = d.right("results")
    d.arrow(
        [(toolworker_x + 60, toolworker_y + toolworker_h), (toolworker_x + 60, results_y), (results_x + 2, results_y)],
        "green",
        label="its result",
        label_at=(toolworker_x + 70, results_y - 8),
        label_anchor="start",
    )
    results_left_x, results_left_y = d.left("results")
    d.arrow(
        [(results_left_x, results_left_y), (376, results_left_y), (376, 150), (360, 150)],
        dashed=True,
        label="the app waits for it",
        label_at=(468, results_left_y + 18),
        label_anchor="end",
    )

    # the waits that still sleep
    d.box(
        "sleeps",
        28,
        660,
        1244,
        "Waits that still sleep in a task, against rule 2 (all on the infrastructure queue)",
        [
            "verify_certificate: wait_until_issued(), 20 checks 30 s apart, up to 9½ minutes. Nothing queues it.",
            "register_custom_domain, verify_custom_domain: create_validation_records(), 120 checks 5 s apart, up to "
            "10 minutes, then 2¼ minutes per record.",
            "create_custom_domain_dns_record: get_or_create_record(), 10 checks 15 s apart, up to 2¼ minutes.",
            "Each holds one of the infrastructure worker's 4 processes while it sleeps. deploy_default_api passes "
            "max_attempts=1, and complies.",
        ],
        "warn",
    )

    d.legend(
        784,
        [
            ("blue", False, "queues a task"),
            ("grey", True, "the init Job; the app waiting for a result"),
            ("green", False, "the worker takes it; its result"),
        ],
    )
    d.save()


# ---------------------------------------------------------------------------------------------------------------
# redis-trust.svg
# ---------------------------------------------------------------------------------------------------------------
REDIS_CLIENTS = [
    ("smarter-api", "sends every kind of task", "plain"),
    ("smarter-worker", "operational tasks", "plain"),
    ("worker-infrastructure", "the Kubernetes and IAM roles", "plain"),
    ("smarter-beat", "the schedule", "plain"),
    ("job-init, job-migrate", "initialize_platform", "plain"),
    ("smarter-worker-tools", "Extensions and tool calls", "warn"),
]
"""The pods that hold Redis's url: a name, what it runs, and its box's kind."""

TOOL_WORKER_REACH = [
    (
        "Push a task to the infrastructure queue",
        ["delete_default_api, destroy_llmhost, …:", "run with the Kubernetes and IAM roles"],
    ),
    ("Read the other pending tool calls", ["each with its decrypted credentials"]),
    ("Write a tool call's result first", ["the app hands a forged result to the LLM"]),
    ("Read the session keys, database 2", ["each is a valid sessionid cookie"]),
    ("Add an entry to RedBeat's schedule", ["a task that recurs, past every restart"]),
]
"""What code in the tool worker can do with Redis's url, by itself: a title and its lines."""


def redis_trust():
    """Who holds Redis's url, what Redis holds, and what code in the tool worker can do with the url."""
    d = Diagram(
        "redis-trust",
        1300,
        800,
        "Every pod holds Redis's url, and Redis can't tell them apart",
        "one password for every client, generated per environment, and no access control list",
        "Three columns. The pods that hold Redis's url: the app, both workers, beat, the Jobs and the tool worker, "
        "which holds no other credential. Redis itself, with one password, which smarter-infrastructure generates for "
        "each environment, and no access control list, so every client may run "
        "every command on every database: database 0 holds the three task queues, the tool calls' results and "
        "RedBeat's schedule; database 1 the cache, with Extensions' archives and cached tool results; database 2 the "
        "users' sessions. Calico's network policies are what keeps other pods out. The last column is what code "
        "in the tool worker, such as an Extension, can do with the url alone: push a task to the infrastructure "
        "queue, which smarter-worker-infrastructure runs with the Kubernetes Role and the IAM role; read the other "
        "pending tool calls in its queue, with their decrypted credentials; write a tool call's result before the "
        "worker that took it does, so the app hands a forged result to the LLM; read the session keys, each of "
        "which is a valid session cookie; and add an entry to RedBeat's schedule, which recurs after every restart. "
        "An Extension's archive can't be swapped: the worker checks its sha256 against the call.",
    )

    # 1. the clients
    d.heading(28, 100, 300, "1 · Who holds Redis's url")
    y = 124
    for index, (name, runs, kind) in enumerate(REDIS_CLIENTS):
        height = d.box(f"client{index}", 28, y, 300, name, [runs], kind)
        y += height + 22

    # 2. Redis
    d.heading(410, 100, 400, "2 · Redis: one password, no ACL")
    d.region(398, 116, 424, 560, "smarter-redis", note="one password, smarter-redis-password, for every client")
    d.box(
        "db0",
        416,
        172,
        388,
        "Database 0: the broker",
        [
            "default, infrastructure and tools queues",
            "run_tool_call's arguments and results",
            "RedBeat's schedule and lock",
        ],
        "data",
        code="CELERY_BROKER_URL …/0",
    )
    d.box(
        "db1",
        416,
        330,
        388,
        "Database 1: the cache",
        ["cached objects and tool results", "Extensions' archives, by sha256"],
        "data",
        code="CACHES['default'] …/1",
    )
    d.box(
        "db2",
        416,
        470,
        388,
        "Database 2: sessions",
        ["every signed-in user's session,", "keyed by its cookie's value"],
        "data",
        code="CACHES['sessions'] …/2",
    )
    d.text(416, 640, "Calico keeps other namespaces' pods out.", size=11, fill=MUTED, italic=True)
    d.text(416, 656, "Nothing inside keeps one client from another.", size=11, fill=MUTED, italic=True)

    # every client's arrow to Redis's region
    for index in range(len(REDIS_CLIENTS)):
        client_x, client_y = d.right(f"client{index}")
        kind = "red" if REDIS_CLIENTS[index][2] == "warn" else "grey"
        d.arrow([(client_x, client_y), (396, client_y)], kind)

    # 3. what the tool worker can do
    d.heading(900, 100, 372, "3 · What code in the tool worker can do")
    y = 124
    for index, (title, lines) in enumerate(TOOL_WORKER_REACH):
        height = d.box(f"reach{index}", 900, y, 372, title, lines, "warn")
        y += height + 18
    d.box("archive", 900, y, 372, "Swap an Extension's archive: no", ["the worker checks its sha256"], "data")

    # the tool worker's path through Redis to the last column
    tool_index = len(REDIS_CLIENTS) - 1
    tool_x, tool_y, tool_w, tool_h = d.boxes[f"client{tool_index}"]
    d.arrow(
        [(tool_x + tool_w / 2, tool_y + tool_h), (tool_x + tool_w / 2, 712), (860, 712), (860, 140), (898, 140)],
        "red",
        label="with the url alone",
        label_at=(640, 704),
    )

    d.legend(
        740,
        [
            ("grey", False, "holds the url, with every other credential"),
            ("red", False, "holds the url, and nothing else"),
        ],
    )
    d.text(760, 764, "red boxes: open today · green: closed", size=11, fill=RED)
    d.save()


if __name__ == "__main__":
    queues()
    redis_trust()
