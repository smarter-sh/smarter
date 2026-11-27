#!/usr/bin/env python3
"""
Draw the diagrams of docs/source/adr/038-tool-isolation-and-egress.rst: phase 0's inventory.

Usage: adr-038-diagrams.py [output folder]   (default: docs/source/_static/adr-038, from the repository root)

- credentials.svg: which credentials each workload holds, from the one Secret that every pod but the tool
  worker reads, and which of them its code uses.
- cluster-writes.svg: who writes to the cluster and the cloud. The LLMClient hands its writes to the
  infrastructure worker; the LLMHost, LLMHostCompute and vectorstore brokers write from the app's request,
  which is why phase 3 can't move the Kubernetes Role to the infrastructure worker yet.
- egress.svg: the hosts that each process contacts: in the cluster, the fixed hosts (phase 4's allowlist),
  and the hosts that a manifest author chooses.

They describe phase 0's findings, from the code as of 0.48.8: keep them true when a workload's credentials,
calls or hosts change, or phase 0's log-only half corrects them. Edit the function, run the script, and render
each result to check it: rsvg-convert -w 1875 <svg> -o <scratchpad>/<name>.png.

It draws with the Diagram class of security-diagrams.py, loaded from beside this file, so that the diagrams
share one look and one copy of their drawing code. The matrix is drawn here: only credentials.svg has one.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "../../.."))
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "docs/source/_static/adr-038")


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
BLUE = security.BLUE
GREEN = security.GREEN
GREY = security.GREY
INK = security.INK
LINE = security.LINE
MUTED = security.MUTED
ORANGE = security.ORANGE
RED = security.RED

# ---------------------------------------------------------------------------------------------------------------
# credentials.svg
# ---------------------------------------------------------------------------------------------------------------
USED = "U"
"""Its code uses the credential."""
CHECK = "C"
"""It holds the credential only because a startup check requires it."""
HELD = "H"
"""It holds the credential, and its code never uses it."""
NONE = "-"
"""It doesn't hold the credential."""

WORKLOADS = [
    ("smarter-api", "the app"),
    ("smarter-worker", "default queue"),
    ("worker-infra…", "infrastructure"),
    ("smarter-beat", "the schedule"),
    ("worker-tools", "tool calls"),
    ("job-init", "initialize_platform"),
    ("job-migrate", "migrate"),
    ("mysql-backup", "CronJob"),
    ("bastion", "operators"),
]
"""The matrix's columns: each workload, and what it runs."""

SECRET_ROWS = [
    ("The database's password", "Django's DATABASES", "UUUH-UUH-"),
    ("DJANGO_SECRET_KEY", "require_django_secret_key()", "UCCC-CCC-"),
    ("The Fernet key", "decrypts Smarter Secrets", "UUUH-UHH-"),
    ("LLM providers' and services' keys", "copied into Smarter Secrets", "HHHH-UHH-"),
    ("The MariaDB root password", "a repository's SQL scripts", "HHHH-UHHU"),
    ("The backup account's password", "mysqldump", "HHHH-HHUU"),
    ("The administrator's password", "initialize_platform", "HHHH-UHH-"),
    ("The SMTP (SES) password", "every email", "UUHH-UHU-"),
    ("The social sign-in keys", "Google, GitHub, LinkedIn", "UHHH-HHH-"),
    ("The GitHub token", "skills, bug reports, indexing", "UUHH-UHH-"),
    ("The Slack bot's token", "email_job_log", "HHHH-UHU-"),
    ("Slack app token, DOCKERHUB_*", "read by no Python", "HHHH-HHH-"),
]
"""The rows read from secret-env.yaml: a label, where the code reads it, and one state for each workload."""

IDENTITY_ROWS = [
    ("The Kubernetes Role", "ServiceAccount smarter", "UCUH-UH--"),
    ("The IAM role (IRSA)", "ServiceAccount smarter", "UUUC-UC--"),
]
"""The rows of the shared ServiceAccount's identities."""

CELL_STYLE = {
    USED: ("dot", BLUE),
    CHECK: ("dot", ORANGE),
    HELD: ("ring", RED),
    NONE: ("dash", GREY),
}
"""How each state is drawn: a shape and its color."""


def draw_cell(d, cx, cy, state):
    """Draw one cell's mark, centered on (cx, cy)."""
    shape, color = CELL_STYLE[state]
    if shape == "dot":
        d.parts.append(f'<circle cx="{cx}" cy="{cy}" r="7.5" fill="{color}"/>')
    elif shape == "ring":
        d.parts.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="#FFFFFF" stroke="{color}" stroke-width="2.4"/>')
    else:
        d.parts.append(f'<rect x="{cx - 7}" y="{cy - 1}" width="14" height="2" fill="{color}"/>')


def draw_rows(d, rows, top, label_x, first_column_x, column_width, row_height):
    """Draw a band of the matrix's rows, from ``top``, and return the y below its last row."""
    y = top
    for index, (label, where, states) in enumerate(rows):
        if index % 2 == 0:
            band_width = first_column_x + column_width * len(WORKLOADS) - label_x + 12
            d.parts.append(
                f'<rect x="{label_x - 12}" y="{y}" width="{band_width}" height="{row_height}" fill="#FFFFFF"/>'
            )
        d.text(label_x, y + 15, label, size=12, weight="bold")
        d.text(label_x, y + 29, where, size=10.5, fill=MUTED, family=security.MONO)
        for column, state in enumerate(states):
            cx = first_column_x + column_width * column + column_width / 2
            draw_cell(d, cx, y + row_height / 2, state)
        y += row_height
    return y


def credentials():
    """Which credentials each workload holds, and which its code uses."""
    d = Diagram(
        "credentials",
        1300,
        866,
        "Credentials by workload, today",
        "every pod but the tool worker reads one Secret, secret-env.yaml, and most hold far more than their code uses",
        "A matrix of the platform's credentials against its workloads: smarter-api, smarter-worker, "
        "smarter-worker-infrastructure, smarter-beat, smarter-worker-tools, the init Job, the migrate Job, the MariaDB "
        "backup CronJob and the bastion. A blue dot means the workload's code uses the credential; an orange dot means "
        "it holds the credential only because a startup check requires it; a red ring means it holds the credential "
        "and its code never uses it; a dash means it doesn't hold it. The LLM providers' and services' api keys are "
        "used only by the init Job, which copies them into Smarter Secrets; every other process reads them from the "
        "database, decrypted with the Fernet key. The MariaDB root password is used only by the init Job and the "
        "bastion, and the administrator's password only by the init Job. Every process with a database holds "
        "DJANGO_SECRET_KEY, because require_django_secret_key() refuses to start without it, though only the app "
        "signs anything. The app sends email, so it needs the SMTP password, and the infrastructure worker decrypts "
        "Smarter Secrets, so it needs the Fernet key. The app writes to the cluster and to EKS, so it needs the "
        "Kubernetes Role and the IAM role; the default worker holds the Role only for its startup check. The tool "
        "worker holds none of them: each tool call brings its own credential.",
    )
    label_x = 40
    first_column_x = 360
    column_width = 100
    row_height = 40
    matrix_right = first_column_x + column_width * len(WORKLOADS)

    # the column headings, with the tool worker's column marked as the target
    heading_y = 92
    tools_column = 4
    tools_x = first_column_x + column_width * tools_column
    d.parts.append(
        f'<rect x="{tools_x + 4}" y="{heading_y - 18}" width="{column_width - 8}" height="716" rx="8" '
        f'fill="#E7F6EC" stroke="{GREEN}" stroke-opacity="0.5"/>'
    )
    for column, (name, runs) in enumerate(WORKLOADS):
        cx = first_column_x + column_width * column + column_width / 2
        d.text(cx, heading_y, name, size=11.5, weight="bold", anchor="middle")
        d.text(cx, heading_y + 15, runs, size=10, fill=MUTED, anchor="middle", italic=True)
    d.parts.append(
        f'<rect x="{label_x - 12}" y="{heading_y + 26}" width="{matrix_right - label_x + 12}" height="1.5" fill="{LINE}"/>'
    )

    # the Secret's rows, then the ServiceAccount's
    y = heading_y + 40
    d.heading(label_x, y + 4, 300, "secret-env.yaml, read with envFrom")
    y = draw_rows(d, SECRET_ROWS, y + 18, label_x, first_column_x, column_width, row_height)
    y += 18
    d.heading(label_x, y + 4, 300, "The shared ServiceAccount's identities")
    y = draw_rows(d, IDENTITY_ROWS, y + 18, label_x, first_column_x, column_width, row_height)

    # the tool worker's own Secret, in its column
    d.text(tools_x + column_width / 2, y + 22, "its own Secret:", size=10, fill=GREEN, anchor="middle", italic=True)
    d.text(tools_x + column_width / 2, y + 36, "Redis only", size=10, fill=GREEN, anchor="middle", italic=True)

    # the legend, drawn here because its marks aren't arrows
    legend_y = 806
    d.parts.append(
        f'<rect x="28" y="{legend_y}" width="{1300 - 56}" height="40" rx="9" fill="#FFFFFF" stroke="{LINE}"/>'
    )
    entries = [
        (USED, "its code uses it"),
        (CHECK, "held only for a startup check"),
        (HELD, "held, and never used: phase 3 removes it"),
        (NONE, "not held"),
    ]
    x = 56
    for state, label in entries:
        draw_cell(d, x, legend_y + 20, state)
        d.text(x + 16, legend_y + 24, label, size=11, fill=MUTED)
        x += 40 + 6.1 * len(label) + 40
    d.save()


# ---------------------------------------------------------------------------------------------------------------
# cluster-writes.svg
# ---------------------------------------------------------------------------------------------------------------
def cluster_writes():
    """Who writes to the cluster and the cloud: through the infrastructure queue, or from the app's request."""
    d = Diagram(
        "cluster-writes",
        1300,
        910,
        "Who writes to the cluster and the cloud",
        "LLMClients go through the infrastructure worker; LLMHosts, their computes and vectorstores write from the app",
        "Two paths from the app to the Kubernetes api and the cloud's apis. The LLMClient broker hands its "
        "ingresses, DNS records and certificates to Celery tasks on the infrastructure queue, which "
        "smarter-worker-infrastructure runs with the Kubernetes Role and the IAM role for Route53 and ACM. Celery Beat "
        "schedules the inventory and the vectorstores' maintenance on the same queue. The LLMHost broker's deploy, "
        "undeploy and delete, and the vectorstore broker's apply and delete, call the Kubernetes api from the app's "
        "own request, and the LLMHostCompute broker's deploy and delete create, scale and delete its EKS node group "
        "from the app too. The app also reads the cluster: an LLMHost's observation and logs, a vectorstore's "
        "conditions and logs, the MCPServer's status tools, smarter status, and its startup check. So phase 3 can "
        "move the Kubernetes Role to the infrastructure worker only after those three brokers hand their writes to "
        "infrastructure tasks, as the LLMClient's broker does; the app's reads need a read-only Role either way.",
    )

    # 1. the app: its brokers, and its reads
    d.heading(28, 100, 330, "1 · The app, inside the request")
    d.region(18, 116, 350, 712, "smarter-api", note="the cli api and the web console's brokers")
    d.box(
        "llmclient",
        36,
        170,
        314,
        "LLMClient broker",
        ["ingresses, DNS records, certificates", "deploy, undeploy, custom domains"],
        code="deploy_default_api.delay() …",
    )
    d.box(
        "reads",
        36,
        300,
        314,
        "Status pages and tools",
        [
            "LLMHost, vectorstore: status, logs",
            "MCPServer status tools · smarter status",
            "startup check: check_kubernetes",
        ],
    )
    d.box(
        "llmhost",
        36,
        430,
        314,
        "LLMHost broker",
        ["deploy · undeploy · delete:", "Deployments, Services, Ingresses, Secrets"],
        "warn",
        code="LLMHostService.launch()",
    )
    d.box(
        "vectorstore",
        36,
        570,
        314,
        "Vectorstore broker",
        ["apply · delete: a StatefulSet,", "its Service, Secret and volume"],
        "warn",
        code="backend.provision()",
    )
    d.box(
        "compute",
        36,
        710,
        314,
        "LLMHostCompute broker",
        ["deploy · delete: its node group,", "created, scaled and deleted"],
        "warn",
        code="ComputeProvisioner.reconcile()",
    )

    # 2. the apis
    d.heading(470, 100, 340, "2 · The apis")
    d.box(
        "kubernetes",
        470,
        320,
        340,
        "The Kubernetes api",
        [
            "this namespace: the Role",
            "the cluster: a read-only ClusterRole",
            "Deployments, StatefulSets, Ingresses,",
            "Services, Secrets, volumes",
        ],
        "role",
        code="kubectl, as ServiceAccount smarter",
    )
    d.box(
        "dns",
        470,
        500,
        340,
        "Route53 and ACM",
        ["DNS records, hosted zones", "certificates and their validation"],
        "outside",
        code="boto3, the IAM role",
    )
    d.box(
        "eks",
        470,
        660,
        340,
        "EKS and Auto Scaling",
        ["managed node groups for LLMHosts", "the cluster's description"],
        "outside",
        code="boto3, the IAM role",
    )

    # 3. the queue and the worker
    d.heading(900, 100, 372, "3 · The infrastructure queue")
    d.box("beat", 900, 170, 372, "smarter-beat", ["the inventory, every 15 minutes", "the vectorstores' maintenance"])
    d.box(
        "queue",
        900,
        300,
        372,
        "Redis",
        ["one queue for every cloud and cluster write"],
        "data",
        code="infrastructure_celery_task_queue",
    )
    d.box(
        "infra",
        900,
        440,
        372,
        "smarter-worker-infrastructure",
        ["the Kubernetes Role", "the IAM role: Route53, ACM, EKS"],
        "core",
        code="celery -Q infrastructure_…",
    )

    # the LLMClient's path, over the apis, to the queue
    llmclient_x, llmclient_y = d.right("llmclient")
    queue_x, queue_y = d.left("queue")
    d.arrow(
        [(llmclient_x, llmclient_y), (860, llmclient_y), (860, queue_y), (queue_x, queue_y)],
        "blue",
        label="a task",
        label_at=(640, llmclient_y - 8),
    )
    d.arrow(
        [d.bottom("beat"), d.top("queue")], "blue", label="scheduled tasks", label_at=(1098, 288), label_anchor="start"
    )
    d.arrow(
        [d.bottom("queue"), d.top("infra")],
        "blue",
        label="the worker takes it",
        label_at=(1098, 428),
        label_anchor="start",
    )

    # the infrastructure worker's writes, to the apis' right edges
    infra_x, infra_y, _infra_w, _infra_h = d.boxes["infra"]
    kubernetes_x, kubernetes_y = d.right("kubernetes")
    dns_x, dns_y = d.right("dns")
    eks_x, eks_y = d.right("eks")
    d.arrow(
        [(infra_x, infra_y + 30), (850, infra_y + 30), (850, kubernetes_y), (kubernetes_x + 2, kubernetes_y)], "green"
    )
    d.arrow([(infra_x, infra_y + 55), (870, infra_y + 55), (870, dns_y), (dns_x + 2, dns_y)], "green")
    d.arrow([(infra_x, infra_y + 80), (885, infra_y + 80), (885, eks_y), (eks_x + 2, eks_y)], "green")

    # the app's reads, and its direct writes, to the apis' left edges
    kubernetes_left_x, kubernetes_left_y = d.left("kubernetes")
    reads_x, reads_y = d.right("reads")
    d.arrow([(reads_x, reads_y), (kubernetes_left_x, reads_y)], dashed=True, label="reads", label_at=(410, reads_y - 8))
    llmhost_x, llmhost_y = d.right("llmhost")
    d.arrow(
        [
            (llmhost_x, llmhost_y),
            (400, llmhost_y),
            (400, kubernetes_left_y + 20),
            (kubernetes_left_x, kubernetes_left_y + 20),
        ],
        "red",
    )
    vectorstore_x, vectorstore_y = d.right("vectorstore")
    d.arrow(
        [
            (vectorstore_x, vectorstore_y),
            (430, vectorstore_y),
            (430, kubernetes_left_y + 46),
            (kubernetes_left_x, kubernetes_left_y + 46),
        ],
        "red",
    )
    compute_x, compute_y = d.right("compute")
    eks_left_x, eks_left_y = d.left("eks")
    d.arrow([(compute_x, compute_y), (410, compute_y), (410, eks_left_y + 20), (eks_left_x, eks_left_y + 20)], "red")

    d.legend(
        850,
        [
            ("blue", False, "a task, through Redis"),
            ("green", False, "a write from the infrastructure worker"),
            ("red", False, "a write from the app's request: blocks phase 3"),
            ("grey", True, "a read"),
        ],
    )
    d.save()


# ---------------------------------------------------------------------------------------------------------------
# egress.svg
# ---------------------------------------------------------------------------------------------------------------
EGRESS_ROWS = [
    (
        "smarter-api",
        "the app",
        ["MariaDB · Redis · Loki", "the Kubernetes api", "LLMHosts · self-hosted vectorstores"],
        [
            "the LLM providers' apis · Pinecone",
            "Google, GitHub, LinkedIn sign-in",
            "api.github.com · raw.githubusercontent.com",
            "api.am.<root domain> · SES's SMTP",
            "AWS: STS, EKS, Auto Scaling",
        ],
        ["MCPClients' servers: the catalog", "vectorstores' ApiConnections", "LLMClients' and LLMHosts' endpoints"],
        "warn",
    ),
    (
        "smarter-worker",
        "default queue",
        ["MariaDB · Redis", "self-hosted vectorstores"],
        [
            "the LLM providers' apis · Pinecone",
            "GitHub · the blog: indexing",
            "smarter-sh.github.io: the registry",
            "SES's SMTP · AWS: STS, S3",
        ],
        [
            "MCPClients' servers: the catalog",
            "vectorstores' ApiConnections",
            "providers' website, terms, docs",
            "LLM prices' source pages",
        ],
        "warn",
    ),
    (
        "worker-infrastructure",
        "infrastructure queue",
        ["MariaDB · Redis", "the Kubernetes api"],
        ["AWS: Route53, ACM, EKS, STS", "public DNS: resolve_domain()"],
        ["none"],
        "plain",
    ),
    ("smarter-beat", "the schedule", ["Redis: RedBeat"], ["AWS: STS, the settings' check"], ["none"], "plain"),
    (
        "job-init",
        "initialize_platform",
        ["MariaDB · Redis", "the Kubernetes api"],
        [
            "GitHub: load_from_github's clones",
            "smarter-sh.github.io · the LLM providers",
            "SES's SMTP · Slack's api",
            "AWS: S3, Route53, STS",
        ],
        ["none found"],
        "plain",
    ),
    (
        "smarter-worker-tools",
        "tool calls",
        ["Redis", "MariaDB's port: SQL plugins"],
        ["none of its own"],
        ["every tool call: MCP servers, APIs,", "databases, searches, web pages,", "extensions' services"],
        "data",
    ),
]
"""Each process: its name, what it runs, its in-cluster hosts, its fixed hosts, the hosts that a manifest author.

chooses, and the kind of box that those take (warn: reached outside the tool worker).
"""


def egress():
    """The hosts that each process contacts: in the cluster, fixed, and chosen by a manifest author."""
    d = Diagram(
        "egress",
        1300,
        918,
        "Which hosts each process contacts",
        "the fixed hosts are the seed of phase 4's allowlist; the hosts a manifest author chooses decide its open questions",
        "For each process, three lanes: the services in the cluster that it reaches, the fixed hosts on the internet "
        "that it reaches, which are the seed of phase 4's allowlist, and the hosts that a manifest author chooses. "
        "The app reaches MariaDB, Redis, Loki, the Kubernetes api, the LLMHosts and the self-hosted vectorstores; the "
        "LLM providers' apis, Pinecone, the social sign-in providers, GitHub, the account manager's api, SES's SMTP "
        "endpoint and AWS's STS, EKS and Auto Scaling; and, chosen by a manifest author, the MCPClients' servers, "
        "whose catalogs it lists, the vectorstores' ApiConnections, and the LLMClients' and LLMHosts' custom "
        "endpoints. The default worker reaches the LLM providers, Pinecone, GitHub and the blog, the extension "
        "registry, SES and S3; and, chosen by a manifest author, the MCPClients' servers, the vectorstores' "
        "ApiConnections, the providers' pages and the LLM prices' source pages. The infrastructure worker reaches "
        "Route53, ACM, EKS, STS and public DNS; beat only Redis and STS; the init Job GitHub, the extension registry, the "
        "LLM providers, SES, Slack and AWS. The tool worker reaches only Redis and MariaDB's port in the cluster, and "
        "every host that a tool call chooses on the internet: that is its purpose. Every host that a manifest author "
        "chooses outside the tool worker must be moved behind it or added to the allowlist before phase 4 enforces.",
    )
    name_x = 28
    name_width = 200
    lane_x = [252, 560, 948]
    lane_width = [284, 364, 324]
    d.heading(lane_x[0], 100, lane_width[0], "1 · In the cluster")
    d.heading(lane_x[1], 100, lane_width[1], "2 · Fixed hosts: the allowlist")
    d.heading(lane_x[2], 100, lane_width[2], "3 · Chosen by a manifest author")

    y = 130
    for index, (name, runs, cluster, fixed, chosen, chosen_kind) in enumerate(EGRESS_ROWS):
        name_kind = "core" if name == "smarter-worker-tools" else "plain"
        heights = [
            d.box(f"name{index}", name_x, y, name_width, name, [runs], name_kind),
            d.box(f"cluster{index}", lane_x[0], y, lane_width[0], "In the cluster", cluster, "data"),
            d.box(f"fixed{index}", lane_x[1], y, lane_width[1], "Fixed hosts", fixed, "outside"),
            d.box(f"chosen{index}", lane_x[2], y, lane_width[2], "Chosen hosts", chosen, chosen_kind),
        ]
        name_right_x, name_right_y = d.right(f"name{index}")
        d.arrow([(name_right_x, name_right_y), (lane_x[0] - 4, name_right_y)])
        y += max(heights) + 22

    d.legend(
        850,
        [
            ("grey", False, "the process reaches each host in its row"),
        ],
    )
    # the box kinds, explained beside the arrow
    d.text(560, 874, "red: a chosen host outside the tool worker, which phase 4 must move or allow", size=11, fill=RED)
    d.save()


if __name__ == "__main__":
    credentials()
    cluster_writes()
    egress()
