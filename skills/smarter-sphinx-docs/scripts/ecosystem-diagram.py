#!/usr/bin/env python3
"""
Draw docs/source/_static/smarter-ecosystem.svg, the ecosystem diagram at the top of.

docs/source/smarter-framework.rst.

Usage: ecosystem-diagram.py [output.svg]   (default: the file above, from the repository root)

The cards and their packages are the calls to card() near the end. Each package names
the registries it is published to, keys of REG. Edit those, run the script, and render
the result to check it: rsvg-convert -w 1500 <svg> -o <scratchpad>/eco.png.
"""

import os
import sys
from xml.sax.saxutils import escape

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "docs/source/_static/smarter-ecosystem.svg")
W, H = 1000, 668
FONT = "Lato, 'Helvetica Neue', Arial, sans-serif"
MONO = "SFMono-Regular, Menlo, Consolas, monospace"

REG = {  # registry: (label, color)
    "pypi": ("PyPI", "#2F6A9A"),
    "npm": ("npm", "#B8312F"),
    "brew": ("Homebrew", "#8A6100"),
    "apt": ("Ubuntu APT", "#B5400F"),
    "choco": ("Chocolatey", "#5E4130"),
    "docker": ("Docker Hub", "#1557C9"),
    "helm": ("Artifact Hub", "#2F6280"),
    "vsx": ("VS Code Marketplace", "#5C2D91"),
    "go": ("Go modules", "#00687D"),
    "gh": ("GitHub", "#24292F"),
}

parts = []


def add(s):
    parts.append(s)


def text(x, y, s, size=14, weight="normal", fill="#1F2328", anchor="start", family=FONT):
    add(
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>'
    )


def pill(x, y, key):
    label, color = REG[key]
    w = round(len(label) * 6.3 + 14)
    add(f'<rect x="{x}" y="{y}" width="{w}" height="18" rx="9" fill="{color}"/>')
    text(x + w / 2, y + 13, label, size=10.5, weight="bold", fill="#FFFFFF", anchor="middle")
    return x + w + 6


def card(x, y, w, h, title, items, mono=True):
    """Items: list of (name, note, [registries]); name in monospace."""
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#FFFFFF" stroke="#C9D1D9" stroke-width="1.2"/>')
    add(f'<rect x="{x}" y="{y}" width="{w}" height="34" rx="10" fill="#EAF2F9"/>')
    add(f'<rect x="{x}" y="{y + 24}" width="{w}" height="10" fill="#EAF2F9"/>')
    add(f'<line x1="{x}" y1="{y + 34}" x2="{x + w}" y2="{y + 34}" stroke="#C9D1D9" stroke-width="1"/>')
    text(x + 16, y + 22, title, size=14, weight="bold", fill="#1F5F8B")
    cy = y + 58
    for name, note, regs in items:
        if name.startswith("built on"):
            text(x + 16, cy, name, size=12.5, fill="#57606A")
        else:
            text(x + 16, cy, name, size=13.5 if mono else 14.5, weight="bold", family=MONO if mono else FONT)
        if note:
            text(x + 16 + len(name) * (8.2 if mono else 8.4) + 10, cy, note, size=12, fill="#57606A")
        px, py = x + 16, cy + 8
        for r in regs:
            if px + len(REG[r][0]) * 6.3 + 14 > x + w - 12:
                px, py = x + 16, py + 24
            px = pill(px, py, r)
        cy = py + 50 if regs else cy + 30


def arrow(x1, y1, x2, y2):
    add(
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#8C959F" stroke-width="1.6" '
        f'stroke-dasharray="5 4" marker-end="url(#head)"/>'
    )


add(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
    'aria-labelledby="t d">'
)
add('<title id="t">The Smarter ecosystem</title>')
add(
    '<desc id="d">The Smarter platform at the center, with the open-source packages around it and the '
    "registry each is published to: the smarter CLI and VS Code extension, the Python, Go and Node.js SDKs, "
    "the shared Python libraries smarter-types and cache-results, the npm chat and widget components, the "
    "website integrations, Smarter Extensions, and the platform's Docker image and Helm chart.</desc>"
)
add(
    '<defs><marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#8C959F"/></marker></defs>'
)
add(f'<rect width="{W}" height="{H}" rx="14" fill="#F6F8FA"/>')

# center: the platform
cx, cy, cw, ch = 360, 224, 280, 230
add(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="12" fill="#2980B9"/>')
text(cx + cw / 2, cy + 36, "Smarter Platform", size=20, weight="bold", fill="#FFFFFF", anchor="middle")
text(cx + cw / 2, cy + 60, "SAM manifests · REST API · OpenAPI", size=12.5, fill="#DCEBF7", anchor="middle")
add(f'<rect x="{cx + 18}" y="{cy + 80}" width="{cw - 36}" height="128" rx="8" fill="#FFFFFF" fill-opacity="0.97"/>')
text(cx + 34, cy + 104, "Deploy it", size=12, weight="bold", fill="#1F5F8B")
text(cx + 34, cy + 128, "Docker image", size=14, weight="bold")
pill(cx + 34, cy + 136, "docker")
text(cx + 34, cy + 176, "Helm chart", size=14, weight="bold")
pill(cx + 34, cy + 184, "helm")

# bottom
card(
    40,
    494,
    440,
    150,
    "Shared Python libraries",
    [
        ("smarter-types", None, ["pypi"]),
        ("cache-results", None, ["pypi"]),
    ],
)
card(
    520,
    494,
    440,
    150,
    "Smarter Extensions",
    [
        ("extensions-registry", "the signed index", ["gh"]),
        ("smarter-extension-*", "weather · calculator · dates", ["gh"]),
    ],
)
# middle left and right
card(
    40,
    224,
    280,
    230,
    "Command line and editor",
    [
        ("smarter", "the CLI", ["brew", "apt", "choco", "docker"]),
        ("smarter-manifest", None, ["vsx"]),
    ],
)
card(
    680,
    224,
    280,
    230,
    "SDKs",
    [
        ("smarter-api", "Python", ["pypi"]),
        ("smarter-golang", "Go", ["go"]),
        ("@smarter.sh/api", "Node.js", ["gh"]),
    ],
)
# top
card(
    40,
    24,
    440,
    160,
    "Chat and web components",
    [
        ("@smarter.sh/ui-chat", "React component, embed script", ["npm"]),
        ("@smarter.sh/ui-widgets", None, ["npm"]),
    ],
)
card(
    520,
    24,
    440,
    160,
    "Website integrations",
    [
        ("WordPress · Drupal · Shopify", None, []),
        ("Google Tag Manager", None, []),
        ("Docusaurus · MkDocs · Sphinx", None, []),
        ("built on the ui-chat embed script", None, []),
    ],
    mono=False,
)

# connectors to the platform
arrow(260, 184, 440, 222)
arrow(740, 184, 560, 222)
arrow(320, 339, 358, 339)
arrow(680, 339, 642, 339)
arrow(260, 494, 440, 456)
arrow(740, 494, 560, 456)
# integrations are built on the chat's embed script
arrow(520, 104, 482, 104)

add("</svg>")
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(parts) + "\n")
