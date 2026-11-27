#!/usr/bin/env python3
"""
Draw the diagram of docs/source/adr/016-security.rst: the platform's security controls, layer by layer.

Usage: adr-016-diagrams.py [output folder]   (default: docs/source/_static/adr-016, from the repository root)

- controls.svg: six layers (the request, AI and tools, data and secrets, the pods, the network, the supply
  chain), each with its controls, and each control marked as in place, partial, or a known gap, with the ADR
  or page that owns it.

It describes the code as of 0.48.8: keep it true when a control is added, or a gap closes, e.g. a phase of
ADR-038 or a security rule of ADR-030. Edit CONTROLS, run the script, and render the result to check it:
rsvg-convert -w 1875 <svg> -o <scratchpad>/controls.png.

It draws with the Diagram class of security-diagrams.py, loaded from beside this file, so that the diagrams
share one look and one copy of their drawing code.
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "../../.."))
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "docs/source/_static/adr-016")


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
GREEN = security.GREEN
LINE = security.LINE
MUTED = security.MUTED
ORANGE = security.ORANGE
RED = security.RED

DONE = "done"
"""The control is in place."""
PARTIAL = "partial"
"""The control is in place, but doesn't yet do all it should."""
GAP = "gap"
"""A known weakness, with a plan."""

STATE_COLOR = {DONE: GREEN, PARTIAL: ORANGE, GAP: RED}
"""The color of each state's dot."""

CONTROLS = [
    (
        "1 · The request",
        "Django first: ADR-016",
        [
            (DONE, "TLS at Traefik, HSTS, X-Forwarded-Proto"),
            (DONE, "unknown hosts refused: SmarterSecurityMiddleware"),
            (DONE, "CORS and CSRF per deployed LLMClient"),
            (DONE, "Secure, HttpOnly, SameSite session cookie"),
            (DONE, "API keys stored as a digest; rate limits"),
            (DONE, "sensitive files and 404 scanners blocked"),
            (PARTIAL, "Content Security Policy: report-only"),
        ],
    ),
    (
        "2 · AI and tools",
        "ADR-038, the security pages",
        [
            (DONE, "guardrails on prompts and replies"),
            (DONE, "safe_http: public addresses only (SSRF)"),
            (DONE, "tool calls in a worker with no credentials"),
            (DONE, "the extension registry's index is signed"),
            (GAP, "an Extension stays loaded in its process"),
            (GAP, "MCP catalogs, custom endpoints: in the app"),
        ],
    ),
    (
        "3 · Data and secrets",
        "ADR-007, the security pages",
        [
            (DONE, "Smarter Secrets encrypted with Fernet"),
            (PARTIAL, "settings' credentials are SecretStr: no test"),
            (DONE, "no secret, credential or PII in a log"),
            (DONE, "backups and exports: private, encrypted S3"),
            (DONE, "Redis's password generated per environment"),
            (GAP, "volumes, Kubernetes Secrets: not encrypted"),
        ],
    ),
    (
        "4 · The pods",
        "the Helm chart, ADR-038",
        [
            (DONE, "non-root, read-only root, no capabilities"),
            (DONE, "seccomp RuntimeDefault, no escalation"),
            (DONE, "startup checks refuse an unsafe start"),
            (DONE, "the tool worker: no token, no IAM role"),
            (GAP, "one Secret, ServiceAccount, IAM role: phase 3"),
            (GAP, "the app writes to the cluster itself"),
        ],
    ),
    (
        "5 · The network and the queues",
        "Calico, ADR-030, ADR-038",
        [
            (DONE, "default deny; other namespaces kept out"),
            (DONE, "MariaDB and Redis: the platform's pods only"),
            (GAP, "egress open on 443: the proxy is phase 4"),
            (GAP, "any Redis client can queue any task"),
            (GAP, "no Redis ACL: sessions readable by all"),
        ],
    ),
    (
        "6 · The supply chain",
        "ADR-015, supply-chain.rst",
        [
            (DONE, "exact pins with hashes; 14-day cooldown"),
            (DONE, "pip-audit on every pull request"),
            (DONE, "signed image and chart; SBOM, provenance"),
            (DONE, "GitHub Actions pinned by SHA"),
            (DONE, "no long-lived AWS keys but SES's"),
            (PARTIAL, "a bad package still runs in every pod"),
        ],
    ),
]
"""Each layer: its heading, the ADRs or pages that own it, and its controls, each with a state."""


def draw_dot(d, cx, cy, state):
    """Draw a control's state, a filled dot, centered on (cx, cy)."""
    color = STATE_COLOR[state]
    d.parts.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{color}"/>')


def draw_layer(d, x, y, width, heading, owner, controls):
    """Draw one layer's panel: its heading, its owner, and a line per control.

    Return the panel's height.
    """
    row_height = 22
    height = 64 + row_height * len(controls)
    d.parts.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" fill="#FFFFFF" stroke="{LINE}"/>')
    d.text(x + 16, y + 26, heading, size=14, weight="bold", fill=security.BLUE)
    d.text(x + 16, y + 44, owner, size=10.5, fill=MUTED, italic=True)
    row_y = y + 68
    for state, label in controls:
        draw_dot(d, x + 24, row_y - 4, state)
        d.text(x + 38, row_y, label, size=11.5)
        row_y += row_height
    return height


def controls():
    """The platform's security controls, layer by layer, each marked as in place, partial, or a gap."""
    description_parts = []
    for heading, owner, items in CONTROLS:
        names = []
        for state, label in items:
            names.append(f"{label} ({state})")
        description_parts.append(f"{heading}, owned by {owner}: " + "; ".join(names) + ".")
    d = Diagram(
        "controls",
        1300,
        600,
        "Smarter's security controls, layer by layer",
        "what is in place, what is partial, and the known gaps, each owned by an ADR or a security page",
        "Six panels, one per layer, each listing its controls with a state: in place, partial, or a known gap. "
        + " ".join(description_parts),
    )
    column_width = 400
    gap = 22
    first_x = 28
    top = 84
    tallest_in_row = 0
    for index, (heading, owner, items) in enumerate(CONTROLS):
        column = index % 3
        if column == 0 and index > 0:
            top += tallest_in_row + gap
            tallest_in_row = 0
        x = first_x + column * (column_width + gap)
        height = draw_layer(d, x, top, column_width, heading, owner, items)
        tallest_in_row = max(tallest_in_row, height)

    legend_y = 538
    d.parts.append(f'<rect x="28" y="{legend_y}" width="1244" height="40" rx="9" fill="#FFFFFF" stroke="{LINE}"/>')
    x = 56
    for state, label in ((DONE, "in place"), (PARTIAL, "partial"), (GAP, "a known gap, with a plan in its ADR")):
        draw_dot(d, x, legend_y + 20, state)
        d.text(x + 14, legend_y + 24, label, size=11, fill=MUTED)
        x += 40 + 6.1 * len(label) + 40
    d.save()


if __name__ == "__main__":
    controls()
