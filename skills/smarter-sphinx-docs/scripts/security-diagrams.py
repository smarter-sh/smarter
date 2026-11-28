#!/usr/bin/env python3
"""
Draw the diagrams of docs/source/smarter-platform/system-administration/security/infrastructure.rst.

Usage: security-diagrams.py [output folder]   (default: docs/source/_static/security, from the repository root)

- network-traffic.svg: a request's path from the internet, through the Network Load Balancer and Traefik, to
  the platform's pods, and the pods' way out, in the VPC's public and private subnets.
- pod-network-policies.svg: the Calico network policies of the platform's namespace: default deny, and the
  traffic that each policy allows.
- aws-identity.svg: the IAM roles that the pods get through IRSA, what each may do, and the two IAM users
  that still have access keys.

Each diagram is one function, named after its file. They describe smarter-infrastructure
(aws/terraform/vpc, kubernetes, kubernetes_ingress and smarter) and the Helm chart: keep them true when
either changes. Edit a function, run the script, and render the result to check it:
rsvg-convert -w 1875 <svg> -o <scratchpad>/<name>.png. They have the look of settings-diagram.py.
"""

import os
import sys
from xml.sax.saxutils import escape

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "docs/source/_static/security")

FONT = "Lato, 'Helvetica Neue', Arial, sans-serif"
MONO = "SFMono-Regular, Menlo, Consolas, monospace"
BLUE = "#2980B9"
BLUE_LIGHT = "#DCEBF7"
GREY = "#8C959F"
INK = "#24292F"
MUTED = "#57606A"
LINE = "#D0D7DE"
GREEN = "#1A7F37"
RED = "#CF222E"
ORANGE = "#8A4600"

# box kinds: (fill, title bar, title color, body color, border)
KINDS = {
    "plain": ("#FFFFFF", "#EAEEF2", INK, INK, LINE),
    "outside": ("#FFFFFF", "#FFF1E5", ORANGE, INK, LINE),
    "core": (BLUE, BLUE, "#FFFFFF", "#FFFFFF", BLUE),
    "data": ("#FFFFFF", "#E7F6EC", "#116329", INK, LINE),
    "role": ("#FFFFFF", "#FBEFFF", "#6639BA", INK, LINE),
    "warn": ("#FFFFFF", "#FFEBE9", RED, INK, LINE),
}
# arrow kinds: (color, marker id)
ARROWS = {"grey": (GREY, "head"), "green": (GREEN, "head-green"), "red": (RED, "head-red"), "blue": (BLUE, "head-blue")}


class Diagram:
    """One SVG diagram, built one element at a time, with named boxes that arrows connect."""

    def __init__(self, name, width, height, title, subtitle, description):
        self.name = name
        self.width = width
        self.height = height
        self.boxes = {}
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
            f'height="{height}" role="img" aria-labelledby="t d">',
            f'<title id="t">{escape(title)}</title>',
            f'<desc id="d">{escape(description)}</desc>',
        ]
        markers = []
        for color, marker_id in ARROWS.values():
            markers.append(
                f'<marker id="{marker_id}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>'
            )
        self.parts.append("<defs>" + "".join(markers) + "</defs>")
        self.parts.append(f'<rect width="{width}" height="{height}" rx="14" fill="#F6F8FA"/>')
        self.text(width / 2, 34, title, size=20, weight="bold", anchor="middle")
        self.text(width / 2, 54, subtitle, size=12, fill=MUTED, anchor="middle")

    def text(self, x, y, s, size=11.5, weight="normal", fill=INK, anchor="start", italic=False, family=FONT):
        style = ' font-style="italic"' if italic else ""
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}"{style}>{escape(s)}</text>'
        )

    def heading(self, x, y, w, s):
        """A numbered column heading, underlined, as in the settings diagram."""
        self.text(x, y, s, size=14, weight="bold", fill=BLUE)
        self.parts.append(f'<rect x="{x}" y="{y + 6}" width="{w}" height="2" fill="{BLUE}" fill-opacity="0.35"/>')

    def region(self, x, y, w, h, label, note=None, dashed=True, fill="none"):
        """A boundary, such as the VPC, a subnet or a namespace, with its label at the top left."""
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{GREY}"'
            f' stroke-width="1.2"{dash}/>'
        )
        self.text(x + 12, y + 19, label, size=12, weight="bold", fill=MUTED)
        if note:
            self.text(x + 12, y + 35, note, size=10.5, fill=MUTED, italic=True)

    def box(self, key, x, y, w, title, lines=(), kind="plain", code=None):
        """A box with a title bar; ``code`` is a monospaced subtitle.

        Returns its height.
        """
        fill, head, title_fill, body, border = KINDS[kind]
        h = 34 + (18 if code else 0) + 17 * len(lines) + (10 if lines or code else -6)
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{border}"/>')
        self.parts.append(
            f'<path d="M{x},{y + 9} a9,9 0 0 1 9,-9 h{w - 18} a9,9 0 0 1 9,9 v17 h-{w} z" fill="{head}"/>'
        )
        self.text(x + 12, y + 18, title, size=13, weight="bold", fill=title_fill)
        cy = y + 42
        if code:
            self.text(x + 12, cy, code, size=10.5, fill=BLUE_LIGHT if kind == "core" else MUTED, family=MONO)
            cy += 18
        for line in lines:
            self.text(x + 12, cy, line, fill=body)
            cy += 17
        self.boxes[key] = (x, y, w, h)
        return h

    def arrow(self, points, kind="grey", dashed=False, label=None, label_at=None, label_anchor="middle"):
        color, marker_id = ARROWS[kind]
        d = "M" + " L".join(f"{px},{py}" for px, py in points)
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        self.parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.8"{dash} marker-end="url(#{marker_id})"/>'
        )
        if label:
            lx, ly = label_at
            self.text(
                lx, ly, label, size=10.5, fill=color if kind != "grey" else MUTED, anchor=label_anchor, italic=True
            )

    def cross(self, x, y):
        """A red cross on a denied path."""
        r = 7
        self.parts.append(
            f'<path d="M{x - r},{y - r} L{x + r},{y + r} M{x - r},{y + r} L{x + r},{y - r}" stroke="{RED}" '
            'stroke-width="2.6" stroke-linecap="round"/>'
        )

    def right(self, key, dy=0):
        x, y, w, h = self.boxes[key]
        return (x + w, y + h / 2 + dy)

    def left(self, key, dy=0):
        x, y, _w, h = self.boxes[key]
        return (x - 2, y + h / 2 + dy)

    def top(self, key, dx=0):
        x, y, w, _h = self.boxes[key]
        return (x + w / 2 + dx, y - 2)

    def bottom(self, key, dx=0):
        x, y, w, h = self.boxes[key]
        return (x + w / 2 + dx, y + h)

    def legend(self, y, entries):
        """A row of legend entries, each an arrow kind (or None for a region), dashed or not, and a label."""
        self.parts.append(
            f'<rect x="28" y="{y}" width="{self.width - 56}" height="40" rx="9" fill="#FFFFFF" stroke="{LINE}"/>'
        )
        x = 48
        for kind, dashed, label in entries:
            if kind is None:
                self.parts.append(
                    f'<rect x="{x}" y="{y + 12}" width="34" height="16" rx="4" fill="none" stroke="{GREY}" '
                    'stroke-dasharray="6 4"/>'
                )
            elif kind == "cross":
                self.cross(x + 17, y + 20)
            else:
                color, marker_id = ARROWS[kind]
                dash = ' stroke-dasharray="5 4"' if dashed else ""
                self.parts.append(
                    f'<path d="M{x},{y + 20} h34" stroke="{color}" stroke-width="1.8"{dash} '
                    f'marker-end="url(#{marker_id})"/>'
                )
            self.text(x + 44, y + 24, label, size=11, fill=MUTED)
            x += 54 + 6.1 * len(label) + 26

    def save(self):
        self.parts.append("</svg>")
        os.makedirs(OUT_DIR, exist_ok=True)
        path = os.path.join(OUT_DIR, f"{self.name}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.parts) + "\n")
        print(f"wrote {os.path.relpath(path, REPO_ROOT)}")


# ---------------------------------------------------------------------------------------------------------------
# network-traffic.svg
# ---------------------------------------------------------------------------------------------------------------
def network_traffic():
    """A request's path through the VPC, and the pods' way out."""
    d = Diagram(
        "network-traffic",
        1250,
        990,
        "How traffic reaches Smarter, and leaves it",
        "one load balancer in, one NAT gateway out; TLS ends at Traefik; Calico polices the traffic between pods",
        "Users and clients on the internet resolve each host name in Route53, which has one record per host and "
        "no wildcard, and connect to one AWS Network Load Balancer in the VPC's public subnets, on ports 80 and 443 "
        "only. The load balancer passes the TCP connection, with the proxy protocol, to Traefik in the private "
        "subnets, which terminates TLS with a cert-manager certificate from Let's Encrypt, redirects HTTP to HTTPS, "
        "sets HSTS and CORS, and forwards plain HTTP to the smarter-api pods on port 8000. Calico, on every node, "
        "enforces the platform namespace's network policies: default deny, so only the platform's pods reach MariaDB "
        "and Redis. The pods leave the VPC through a NAT gateway, to LLM providers, APIs and AWS's "
        "public endpoints, and reach S3 through a gateway endpoint that keeps that traffic inside AWS.",
    )

    # the internet
    d.heading(28, 96, 200, "The internet")
    d.box(
        "users",
        28,
        150,
        200,
        "Users and clients",
        ["the web console", "embedded Smarter Chat", "smarter CLI and the SDKs"],
        "outside",
        code="https://<host>",
    )
    d.box("route53", 28, 340, 200, "Route53", ["one record per host,", "no wildcard"], "outside", code="DNS")
    d.box(
        "letsencrypt",
        28,
        470,
        200,
        "Let's Encrypt",
        ["a certificate per host,", "by DNS-01 challenge"],
        "outside",
        code="ACME",
    )

    # the VPC and its subnets
    d.region(250, 86, 972, 680, "AWS VPC · 192.168.0.0/20")
    d.region(266, 124, 200, 626, "Public subnets", fill="#FFFFFF")
    d.region(
        482, 124, 724, 626, "Private subnets", note="the nodes, and the cluster's API: no public IP", fill="#FFFFFF"
    )

    d.box(
        "nlb",
        280,
        170,
        172,
        "Load balancer",
        ["ports 80 and 443 only", "passes TCP, with the", "proxy protocol"],
        code="AWS NLB",
    )
    d.box("nat", 280, 600, 172, "NAT gateway", ["the nodes' only way", "out to the internet"], code="egress")

    d.region(498, 170, 210, 250, "namespace traefik")
    d.box(
        "traefik",
        510,
        206,
        186,
        "Traefik",
        [
            "terminates TLS",
            "301: HTTP to HTTPS",
            "HSTS · CORS · access log",
            "forwards plain HTTP,",
            "with X-Forwarded-Proto",
        ],
        "core",
        code="ingress controller",
    )

    d.region(724, 170, 466, 400, "namespace smarter-platform-prod", note="Calico: default deny")
    d.box(
        "api",
        740,
        226,
        210,
        "smarter-api",
        ["rejects unknown hosts (400)", "rate limits · CSRF", "API keys · sessions"],
        "core",
        code="Django · :8000",
    )
    d.box(
        "workers",
        740,
        410,
        210,
        "Workers and beat",
        ["Celery tasks: LLM calls,", "DNS, certificates, email"],
        code="smarter-worker*",
    )
    d.box("mariadb", 968, 226, 206, "MariaDB", ["the platform's database"], "data", code=":3306")
    d.box("redis", 968, 350, 206, "Redis", ["sessions, cache, Celery"], "data", code=":6379")

    d.box("s3endpoint", 498, 600, 210, "S3 gateway endpoint", ["S3 and image pulls stay", "inside AWS's network"])
    d.box(
        "calico",
        1020,
        596,
        170,
        "Calico",
        ["enforces the network", "policies on every node"],
        "core",
        code="calico-system",
    )
    # Calico enforces the namespace's policies: an arrow to the namespace's bottom edge, at y=570
    d.arrow([d.top("calico"), (d.top("calico")[0], 572)], "blue", dashed=True)

    # outside the VPC, below
    d.box(
        "providers",
        266,
        810,
        300,
        "LLM providers, APIs, MCP servers",
        ["and AWS's public endpoints", "HTTPS, from the pods"],
        "outside",
        code="the internet",
    )
    d.box("s3", 598, 810, 260, "Amazon S3", ["the environment's buckets:", "static files, backups, exports"], "outside")

    # the request
    ux, uy = d.right("users")
    nx, ny = d.left("nlb")
    d.arrow([(ux, ny), (nx, ny)], "green", label="443 · 80", label_at=(254, ny - 8))
    tx, ty = d.left("traefik")
    d.arrow([d.right("nlb"), (470, d.right("nlb")[1]), (470, ty), (tx, ty)], "green")
    ax, ay = d.left("api")
    d.arrow([d.right("traefik", -30), (ax, d.right("traefik", -30)[1])], "green")

    # the platform's own traffic
    d.arrow([d.right("api", -14), d.left("mariadb", 0)[0:1] + (d.right("api", -14)[1],)])
    d.arrow([d.right("api", 18), (958, d.right("api", 18)[1]), (958, d.left("redis")[1]), d.left("redis")])
    d.arrow(
        [d.right("workers", -6), (962, d.right("workers", -6)[1]), (962, d.left("redis", 12)[1]), d.left("redis", 12)]
    )

    # DNS and certificates
    d.arrow(
        [d.bottom("users"), d.top("route53")],
        dashed=True,
        label="looks up the host",
        label_at=(134, 322),
        label_anchor="start",
    )
    lx, ly = d.right("letsencrypt")
    bx, by = d.bottom("traefik")
    d.arrow([(lx, ly), (bx, ly), (bx, by + 2)], dashed=True)
    d.text(bx - 8, ly - 8, "certificates, through cert-manager", size=10.5, fill=MUTED, anchor="end", italic=True)

    # the way out
    # from any of the namespace's pods: the region's bottom edge, at y=570
    d.arrow(
        [(1000, 570), (1000, 720), (472, 720), (472, d.right("nat")[1]), d.right("nat")],
        label="HTTPS out, from any pod",
        label_at=(760, 714),
    )
    d.arrow([(790, 570), (790, d.right("s3endpoint")[1]), (d.right("s3endpoint")[0] + 2, d.right("s3endpoint")[1])])
    d.arrow([d.bottom("nat"), (d.bottom("nat")[0], d.top("providers")[1])])
    d.arrow([d.bottom("s3endpoint"), (d.bottom("s3endpoint")[0], d.top("s3")[1])])

    d.legend(
        930,
        [
            ("green", False, "a request from the internet"),
            ("grey", False, "the platform's own traffic"),
            ("grey", True, "DNS and certificates"),
            ("blue", True, "Calico's network policies"),
            (None, False, "the VPC, a subnet or a namespace"),
        ],
    )
    d.save()


# ---------------------------------------------------------------------------------------------------------------
# pod-network-policies.svg
# ---------------------------------------------------------------------------------------------------------------
def pod_network_policies():
    """The Calico network policies of the platform's namespace."""
    d = Diagram(
        "pod-network-policies",
        1250,
        842,
        "Which pods may talk to which",
        "Calico enforces the namespace's network policies on every node: default deny, then only these paths",
        "In the platform's namespace, a default-deny policy blocks all ingress and egress. Traefik, in its own "
        "namespace, may reach the application's pods on port 8000 only. The application's pods (smarter-api, the "
        "Celery workers, beat, the init Job and the bastion) may reach each other, MariaDB on 3306, Redis on 6379, "
        "Loki on 3100 and 9095, DNS in kube-system on 53, and the internet on 443, 80, 587 and 3306. MariaDB and "
        "Redis accept connections only from the application's pods. A pod in another namespace, or one without the "
        "chart's labels, can reach nothing.",
    )

    d.box(
        "traefik",
        28,
        179,
        190,
        "Traefik",
        ["may reach the app's", "pods on :8000 only"],
        "outside",
        code="namespace traefik",
    )
    d.box(
        "stranger",
        28,
        620,
        190,
        "Any other pod",
        ["in another namespace, or", "without the chart's labels"],
        "warn",
        code="no policy allows it",
    )

    d.region(
        250,
        86,
        690,
        630,
        "namespace smarter-platform-prod",
        note="policy default-deny-all: no ingress, no egress, unless allowed below",
        fill="#FFFFFF",
    )
    d.region(272, 150, 340, 440, "application-group: smarter", note="may reach each other")
    pods = [
        ("api", "smarter-api", ["the app server, :8000"]),
        ("workers", "Celery workers", ["smarter-worker,", "smarter-worker-infrastructure"]),
        ("beat", "Celery beat", ["the scheduler"]),
        ("init", "Jobs", ["init, migrate, backup"]),
        ("bastion", "Bastion", ["kubectl exec only"]),
    ]
    y = 196
    for key, title, lines in pods:
        h = d.box(key, 292, y, 300, title, lines, "core" if key == "api" else "plain")
        y += h + 14

    d.box("mariadb", 700, 196, 220, "MariaDB", ["accepts only the", "application's pods"], "data", code=":3306")
    d.box("redis", 700, 330, 220, "Redis", ["accepts only the", "application's pods"], "data", code=":6379")
    d.box("loki", 700, 464, 220, "Loki", ["the pods' logs"], "data", code=":3100 · :9095")

    d.box("dns", 980, 196, 242, "DNS", ["CoreDNS"], "outside", code="namespace kube-system · :53")
    d.box(
        "internet",
        980,
        330,
        242,
        "The internet",
        [
            "443 · LLM providers, APIs, AWS",
            "80 · API plugins",
            "587 · SMTP to SES",
            "3306 · SQL plugins' databases",
        ],
        "outside",
        code="0.0.0.0/0",
    )

    # Traefik to the app, on 8000 only
    d.arrow([d.right("traefik"), d.left("api")], "green")

    # the application's pods to the data stores (from the group's right edge)
    gx = 612
    for key in ("mariadb", "redis", "loki"):
        _x, ty = d.left(key)
        d.arrow([(gx, ty), d.left(key)], "green")
    d.text(gx + 6, d.left("mariadb")[1] - 8, "3306", size=10.5, fill=GREEN, italic=True)
    d.text(gx + 6, d.left("redis")[1] - 8, "6379", size=10.5, fill=GREEN, italic=True)
    d.text(gx + 6, d.left("loki")[1] - 8, "3100 · 9095", size=10.5, fill=GREEN, italic=True)

    # and out of the namespace
    lane_y = 568
    d.arrow([(gx, lane_y), (950, lane_y), (950, d.left("dns")[1]), d.left("dns")], "green")
    d.arrow([(950, d.left("internet")[1]), d.left("internet")], "green")
    d.text(gx + 6, lane_y - 8, "egress: DNS, and the internet on these ports only", size=10.5, fill=GREEN, italic=True)

    # denied: from outside, into the application group
    sx, sy = d.right("stranger")
    d.arrow([(sx, sy), (442, sy), (442, 594)], "red", dashed=True)
    d.cross(330, sy)
    d.text(454, 640, "denied: the app's pods, MariaDB, Redis and Loki", size=10.5, fill=RED, italic=True)

    d.text(
        272,
        744,
        "The policies select pods by the labels that the Helm chart sets: app.kubernetes.io/application-group and "
        "app.kubernetes.io/name.",
        size=11.5,
        fill=MUTED,
    )
    d.text(272, 762, "A pod that you add without them can reach nothing.", size=11.5, fill=MUTED)
    d.legend(
        782,
        [
            ("green", False, "allowed, on the ports shown"),
            ("red", True, "denied by default"),
            ("cross", False, "no policy allows it"),
            (None, False, "a namespace, or a group of pods"),
        ],
    )
    d.save()


# ---------------------------------------------------------------------------------------------------------------
# aws-identity.svg
# ---------------------------------------------------------------------------------------------------------------
def aws_identity():
    """The pods' IAM roles, through IRSA, and the two IAM users with access keys."""
    d = Diagram(
        "aws-identity",
        1250,
        880,
        "Who may do what in AWS",
        "EKS gives each ServiceAccount short-lived credentials for its own IAM role; only email still uses a key",
        "The platform's pods (smarter-api, the Celery workers, beat, the init and migrate Jobs) each run as their own "
        "ServiceAccount, smarter-<pod>, which EKS's OIDC provider maps to the IAM role <namespace>-smarter-irsa, with "
        "short-lived "
        "credentials. That role may change Route53 records and hosted zones, request ACM certificates, read the "
        "cluster, create and change LLMHost node groups tagged with the environment, and use the environment's own S3 "
        "buckets. The nightly backup runs as smarter-backup, whose role <namespace>-smarter-backup-irsa may only write "
        "to backups/sql/ in the backup bucket. Two IAM users still have access keys: the deploy user, which the GitHub "
        "Actions Deploy workflow uses to push the image to ECR and run helm in the environment's namespace, and the "
        "SMTP user, whose SES SMTP password the pods read from the Kubernetes Secret aws-ses-config to send email.",
    )
    cols = [(28, 230), (290, 210), (532, 250), (814, 408)]
    for (x, w), heading in zip(cols, ["1 · Pods", "2 · runs as", "3 · which assumes", "4 · which may"]):
        d.heading(x, 92, w, heading)

    def row(keys_and_boxes, center):
        """Boxes side by side, each centered on the same line, so the arrows between them are level."""
        for key, x, w, title, lines, kind, code in keys_and_boxes:
            h = 34 + (18 if code else 0) + 17 * len(lines) + (10 if lines or code else -6)
            d.box(key, x, round(center - h / 2), w, title, lines, kind, code)

    row(
        [
            (
                "pods",
                28,
                230,
                "The platform's pods",
                ["smarter-api", "Celery workers and beat", "the init and migrate Jobs"],
                "core",
                None,
            ),
            (
                "sa",
                290,
                210,
                "smarter-<pod>",
                ["one per kind of pod,", "each annotated with the role"],
                "plain",
                "ServiceAccounts",
            ),
            ("role", 532, 250, "<namespace>-smarter-irsa", ["this environment only"], "role", "IAM role"),
            (
                "may",
                814,
                408,
                "AWS",
                [
                    "Route53: records and hosted zones, for deployed",
                    "LLMClients and custom domains",
                    "ACM: request and delete certificates",
                    "EKS: read the cluster; LLMHost node groups, only",
                    "with this environment's tag and name prefix",
                    "S3: this environment's static and exports buckets",
                ],
                "data",
                None,
            ),
        ],
        196,
    )
    d.box(
        "k8s",
        814,
        300,
        408,
        "Kubernetes (RBAC, not IAM)",
        [
            "a Role per kind of pod, in its own namespace:",
            "only the infrastructure worker writes, or reads Secrets;",
            "the app reads; cluster-wide: each kind's own reads",
        ],
        "data",
    )
    row(
        [
            ("backup", 28, 230, "The nightly backup", ["CronJob smarter-mysql-backup"], "core", None),
            ("sa_backup", 290, 210, "smarter-backup", ["its own ServiceAccount"], "plain", "ServiceAccount"),
            ("role_backup", 532, 250, "<namespace>-smarter-backup-irsa", ["write-only"], "role", "IAM role"),
            (
                "may_backup",
                814,
                408,
                "AWS",
                [
                    "S3: put and list under backups/sql/, in the private",
                    "backup bucket. It can't read or delete a backup.",
                ],
                "data",
                None,
            ),
        ],
        530,
    )

    for a, b in (
        ("pods", "sa"),
        ("sa", "role"),
        ("role", "may"),
        ("backup", "sa_backup"),
        ("sa_backup", "role_backup"),
        ("role_backup", "may_backup"),
    ):
        d.arrow([d.right(a), d.left(b)], "blue")
    # below the IAM role's box: Kubernetes permissions come from RBAC, not from the role
    sx, sy = d.bottom("sa")
    d.arrow([(sx, sy), (sx, 376), (800, 376), (800, d.left("k8s")[1]), d.left("k8s")], "blue", dashed=True)

    # how IRSA works
    d.parts.append(f'<rect x="290" y="392" width="492" height="62" rx="9" fill="#FFFFFF" stroke="{LINE}"/>')
    d.text(306, 414, "How a pod gets its credentials (IRSA)", size=12.5, weight="bold")
    d.text(306, 434, "EKS's OIDC provider signs the ServiceAccount's token; STS exchanges it for", size=11.5)
    d.text(
        306, 448, "credentials that expire within hours. A role trusts only the ServiceAccounts it names.", size=11.5
    )

    # the users with access keys
    d.parts.append(f'<rect x="28" y="606" width="{1250 - 56}" height="2" fill="{RED}" fill-opacity="0.3"/>')
    d.text(28, 634, "Still on access keys: two IAM users, each with one narrow job", size=14, weight="bold", fill=RED)
    d.text(
        28,
        654,
        "Their secret keys are in the Terraform state. Rotate a key by tainting its aws_iam_access_key and applying.",
        size=11.5,
        fill=MUTED,
    )
    row(
        [
            ("gha", 28, 230, "GitHub Actions", ["the Build and Deploy", "workflows"], "outside", "its secrets"),
            ("deploy_user", 290, 210, "<namespace>-deploy", ["one per environment"], "warn", "IAM user · access key"),
            (
                "deploy_may",
                532,
                690,
                "Deploys",
                [
                    "ECR: push and read this environment's image",
                    'EKS: helm and kubectl in this environment\'s namespace only  ·  SES: the "deployed" email',
                ],
                "data",
                None,
            ),
        ],
        716,
    )
    row(
        [
            (
                "smtp_pods",
                28,
                230,
                "The platform's pods",
                ["read the SMTP password from", "the Secret aws-ses-config"],
                "core",
                None,
            ),
            (
                "smtp_user",
                290,
                210,
                "<namespace>_smtp_user",
                ["its SES SMTP password"],
                "warn",
                "IAM user · access key",
            ),
            ("smtp_may", 532, 690, "Sends email", ["SES: SendRawEmail, and nothing else"], "data", None),
        ],
        820,
    )
    for a, b in (
        ("gha", "deploy_user"),
        ("deploy_user", "deploy_may"),
        ("smtp_pods", "smtp_user"),
        ("smtp_user", "smtp_may"),
    ):
        d.arrow([d.right(a), d.left(b)], "red")
    d.save()


if __name__ == "__main__":
    network_traffic()
    pod_network_policies()
    aws_identity()
