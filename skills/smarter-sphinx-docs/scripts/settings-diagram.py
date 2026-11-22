#!/usr/bin/env python3
"""
Draw docs/source/_static/settings-data-flow.svg, the settings diagram of.

docs/source/smarter-platform/configuration.rst: how Smarter initializes its settings, from the
deployment's and the developer's sources to the values that Django runs with.

Usage: settings-diagram.py [output.svg]   (default: the file above, from the repository root)

The boxes are the calls to box() in the four column sections, and the arrows the calls to
arrow() after them. Edit those, run the script, and render the result to check it:
rsvg-convert -w 1875 <svg> -o <scratchpad>/settings.png.
"""

import os
import sys
from xml.sax.saxutils import escape

FONT = "Lato, 'Helvetica Neue', Arial, sans-serif"
W, H = 1250, 860
BLUE, BLUE_LIGHT, GREY, INK, MUTED, LINE = "#2980B9", "#DCEBF7", "#8C959F", "#24292F", "#57606A", "#D0D7DE"
out = []


def text(x, y, s, size=11.5, weight="normal", fill=INK, anchor="start", italic=False):
    style = ' font-style="italic"' if italic else ""
    out.append(
        f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
        f'fill="{fill}" text-anchor="{anchor}"{style}>{escape(s)}</text>'
    )


BOXES = {}


def box(key, x, y, w, title, lines, kind="plain", code=None):
    """A box with a title bar; ``code`` is a monospaced subtitle; returns its height."""
    h = 34 + (18 if code else 0) + 17 * len(lines) + 10
    fill, head, title_fill, body = {
        "plain": ("#FFFFFF", "#EAEEF2", INK, INK),
        "source": ("#FFFFFF", "#FFF1E5", "#8A4600", INK),
        "core": (BLUE, BLUE, "#FFFFFF", "#FFFFFF"),
        "django": ("#FFFFFF", "#E7F6EC", "#116329", INK),
    }[kind]
    out.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{LINE if kind != "core" else BLUE}"/>'
    )
    out.append(f'<path d="M{x},{y + 9} a9,9 0 0 1 9,-9 h{w - 18} a9,9 0 0 1 9,9 v17 h-{w} z" fill="{head}"/>')
    text(x + 12, y + 18, title, size=13, weight="bold", fill=title_fill)
    cy = y + 42
    if code:
        out.append(
            f'<text x="{x + 12}" y="{cy}" font-family="SFMono-Regular, Menlo, Consolas, monospace" font-size="10.5" '
            f'fill="{BLUE_LIGHT if kind == "core" else MUTED}">{escape(code)}</text>'
        )
        cy += 18
    for line in lines:
        text(x + 12, cy, line, fill=body)
        cy += 17
    BOXES[key] = (x, y, w, h)
    return h


def arrow(points, dashed=False, label=None, label_at=None):
    d = "M" + " L".join(f"{px},{py}" for px, py in points)
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    out.append(f'<path d="{d}" fill="none" stroke="{GREY}" stroke-width="1.6"{dash} marker-end="url(#head)"/>')
    if label:
        lx, ly = label_at
        text(lx, ly, label, size=10.5, fill=MUTED, anchor="middle", italic=True)


def right(k, dy=0):
    x, y, w, h = BOXES[k]
    return (x + w, y + h / 2 + dy)


def left(k, dy=0):
    x, y, w, h = BOXES[k]
    return (x - 2, y + h / 2 + dy)


def top(k, dx=0):
    x, y, w, h = BOXES[k]
    return (x + w / 2 + dx, y - 2)


def bottom(k, dx=0):
    x, y, w, h = BOXES[k]
    return (x + w / 2 + dx, y + h)


out.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
    'aria-labelledby="t d">'
)
out.append('<title id="t">How Smarter initializes its settings</title>')
out.append(
    '<desc id="d">Deployment sources (GitHub Actions secrets, the Kubernetes Secrets that '
    "smarter-infrastructure creates, and the Helm chart's values) and local sources (.env and "
    "user-settings/settings.yaml) become the process's environment variables, through the deploy "
    "action and the Helm release's env Secret, or Docker Compose. get_env reads them into "
    "settings_defaults, with the code constants of smarter.common.const, and smarter_settings validates "
    "them. Django's settings modules derive their settings from smarter_settings, then the user's own "
    "settings file and DJANGO_* variables supersede them. The startup logs, the initialize commands, and "
    "the web console read the result.</desc>"
)
out.append(
    f'<defs><marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{GREY}"/></marker></defs>'
)
out.append(f'<rect width="{W}" height="{H}" rx="14" fill="#F6F8FA"/>')
text(W / 2, 34, "How Smarter initializes its settings", size=20, weight="bold", anchor="middle")
text(
    W / 2,
    54,
    "from the sources a deployment or a developer controls, to the values that Django runs with",
    size=12,
    fill=MUTED,
    anchor="middle",
)

COLS = [(28, 250), (336, 250), (644, 280), (984, 238)]
for (x, w), heading in zip(COLS, ["1 · Sources", "2 · Delivery", "3 · smarter_settings", "4 · Django settings"]):
    text(x, 86, heading, size=14, weight="bold", fill=BLUE)
    out.append(f'<rect x="{x}" y="92" width="{w}" height="2" fill="{BLUE}" fill-opacity="0.35"/>')

# --- 1 · Sources ------------------------------------------------------------------------------------
x, w = COLS[0]
text(x, 114, "Kubernetes: alpha, prod, …", size=11, weight="bold", fill=MUTED)
box(
    "gha",
    x,
    122,
    w,
    "GitHub Actions",
    ["repository secrets, e.g. OPENAI_API_KEY", "the deploy workflow's own env"],
    "source",
    code=".github/workflows/deploy.yml",
)
box(
    "k8s",
    x,
    222,
    w,
    "Kubernetes Secrets",
    ["mysql-smarter · mysql-root", "smarter-admin · aws-ses-config", "smarter-django-secret-key"],
    "source",
    code="Terraform: smarter-infrastructure",
)
box(
    "helm",
    x,
    340,
    w,
    "Helm chart values",
    ["env: SMARTER_* and DJANGO_* keys,", "defaults and SET-ME placeholders"],
    "source",
    code="helm/charts/smarter/values.yaml",
)
out.append(f'<rect x="{x}" y="452" width="{w}" height="1" fill="{LINE}"/>')
text(x, 474, "Local: make run, Docker Compose", size=11, weight="bold", fill=MUTED)
box(
    "dotenv",
    x,
    482,
    w,
    ".env",
    ["your own copy of .env.example;", "make adds a new Fernet key", "never committed"],
    "source",
    code="./.env",
)
box(
    "usersettings",
    x,
    600,
    w,
    "User settings file",
    ["your own Django settings, in YAML", "local development only"],
    "source",
    code="user-settings/settings.yaml",
)

# --- 2 · Delivery -----------------------------------------------------------------------------------
x, w = COLS[1]
box(
    "deploy",
    x,
    150,
    w,
    "Deploy action",
    [
        "reads the Kubernetes Secrets",
        "merges them with the GitHub secrets",
        "into the release's values",
        "runs helm upgrade",
    ],
    code=".github/actions/deploy",
)
box(
    "release",
    x,
    320,
    w,
    "Helm release",
    ["the Secret <appName>-env holds env;", "every pod reads it with envFrom:", "api, workers, beat, init and migrate"],
    code="templates/secret-env.yaml",
)
box(
    "compose",
    x,
    500,
    w,
    "Docker Compose",
    ["env_file: .env, in every container", "mounts user-settings/ read-only"],
    code="docker-compose.yml",
)

# --- 3 · smarter_settings ----------------------------------------------------------------------------
x, w = COLS[2]
box(
    "environ",
    x,
    112,
    w,
    "Environment variables",
    [
        "SMARTER_PLATFORM_* · SMARTER_APP_*",
        "SMARTER_SUBSYSTEM_* · DJANGO_*",
        "DJANGO_SETTINGS_MODULE",
        "the unprefixed names count too",
    ],
    code="os.environ",
)
box(
    "const",
    x + 118,
    262,
    w - 118,
    "Code constants",
    ["not configuration:", "port, admin account,", "paths, VERSION"],
    code="common.const",
)
box(
    "defaults",
    x,
    384,
    w,
    "Defaults",
    ["get_env(NAME): NAME, else SMARTER_NAME;", "else the literal default"],
    code="smarter.common.conf.defaults",
)
box(
    "settings",
    x,
    494,
    w,
    "smarter_settings",
    [
        "validated by Pydantic; a placeholder",
        "or an empty value is the default",
        "secrets are SecretStr, always masked",
        "platform_* · subsystem_* · app_*",
    ],
    "core",
    code="smarter.common.conf",
)

# --- 4 · Django settings -----------------------------------------------------------------------------
x, w = COLS[3]
box(
    "django",
    x,
    112,
    w,
    "Settings modules",
    [
        "① base.py",
        "② base_aws.py, on AWS only",
        "③ local · alpha · beta · next · prod",
        "derived from smarter_settings",
    ],
    "django",
    code="DJANGO_SETTINGS_MODULE",
)
box(
    "user",
    x,
    272,
    w,
    "apply_user_settings",
    ["④ user-settings/settings.yaml", "⑤ DJANGO_* variables", "each supersedes all before it"],
    "django",
    code="smarter.settings.user",
)
box(
    "runtime",
    x,
    408,
    w,
    "At startup, and after",
    [
        "the settings diagnostics, and",
        "every SMARTER_PLATFORM_* value",
        "each app: its SMARTER_APP_* values",
        "initialize_*: api keys become",
        "Smarter Secrets, Fernet-encrypted",
        "web console: session api, branding",
    ],
    code="logs · manage.py · web console",
)

# --- arrows ------------------------------------------------------------------------------------------
gx, gy = right("gha")
dx, dy = left("deploy", -22)
arrow([(gx, gy), (gx + 22, gy), (gx + 22, dy), (dx, dy)])
kx, ky = right("k8s")
dx2, dy2 = left("deploy", 22)
arrow([(kx, ky), (kx + 22, ky), (kx + 22, dy2), (dx2, dy2)])
hx, hy = right("helm")
rx, ry = left("release")
arrow([(hx, hy), (hx + 22, hy), (hx + 22, ry), (rx, ry)])
arrow(
    [bottom("deploy"), top("release")],
    label="values JSON",
    label_at=(BOXES["deploy"][0] + 186, (BOXES["deploy"][1] + BOXES["deploy"][3] + BOXES["release"][1]) / 2 + 4),
)
ex, ey = right("dotenv")
cx, cy = left("compose", -10)
arrow([(ex, ey), (ex + 22, ey), (ex + 22, cy), (cx, cy)])
ux, uy = right("usersettings")
cx2, cy2 = left("compose", 14)
arrow([(ux, uy), (ux + 22, uy), (ux + 22, cy2), (cx2, cy2)], dashed=True)

ex3, ey3 = left("environ")
arrow([right("release", -18), (ex3 - 30, right("release", -18)[1]), (ex3 - 30, ey3 + 14), (ex3, ey3 + 14)])
text(right("release")[0] + 4, right("release", -18)[1] - 6, "envFrom", size=10.5, fill=MUTED, italic=True)
arrow([right("compose"), (ex3 - 14, right("compose")[1]), (ex3 - 14, ey3 + 32), (ex3, ey3 + 32)])
text(right("compose")[0] + 4, right("compose")[1] - 6, "env_file", size=10.5, fill=MUTED, italic=True)

envb = (BOXES["environ"][0] + 56, BOXES["environ"][1] + BOXES["environ"][3])
arrow([envb, (envb[0], BOXES["defaults"][1] - 2)])
arrow([bottom("const"), (bottom("const")[0], BOXES["defaults"][1] - 2)])
arrow([bottom("defaults"), top("settings")])

# DJANGO_SETTINGS_MODULE picks the module
arrow([right("environ", -20), left("django", -20)])
# DJANGO_* variables supersede
jx = right("environ")[0] + 20
arrow([right("environ", 26), (jx, right("environ", 26)[1]), (jx, left("user", -12)[1]), left("user", -12)], dashed=True)
text(jx - 4, left("user", -12)[1] - 6, "DJANGO_*", size=10.5, fill=MUTED, anchor="end", italic=True)
# smarter_settings feeds the settings modules and the runtime
sx, sy = right("settings", -30)
arrow([(sx, sy), (sx + 40, sy), (sx + 40, left("django", 30)[1]), left("django", 30)])
arrow([right("settings", 30), left("runtime", 60)])
# Django chain
arrow([bottom("django"), top("user")])
arrow([bottom("user"), top("runtime")])
# the user settings file, mounted locally
usb = bottom("usersettings")
rx_ = BOXES["user"][0] + BOXES["user"][2]
uy_ = right("user", 12)[1]
arrow([(usb[0], usb[1]), (usb[0], 752), (rx_ + 14, 752), (rx_ + 14, uy_), (rx_ + 2, uy_)], dashed=True)
text(
    620,
    746,
    "locally, user-settings/ is mounted into each container, where apply_user_settings reads it (④)",
    size=10.5,
    fill=MUTED,
    anchor="middle",
    italic=True,
)

# --- precedence and legend ---------------------------------------------------------------------------
out.append(f'<rect x="28" y="776" width="{W - 56}" height="64" rx="9" fill="#FFFFFF" stroke="{LINE}"/>')
text(44, 798, "Precedence, lowest to highest", size=12.5, weight="bold")
text(44, 818, "smarter_settings:  the literal default  →  SMARTER_NAME  →  NAME", size=11.5)
text(
    44,
    834,
    "Django:  ① base.py  →  ② base_aws.py  →  ③ the environment's module  →  ④ the user settings file  →  ⑤ DJANGO_* variables",
    size=11.5,
)
out.append(f'<path d="M{W - 250},806 h34" stroke="{GREY}" stroke-width="1.6" marker-end="url(#head)"/>')
text(W - 208, 810, "a value flows", size=11, fill=MUTED)
out.append(
    f'<path d="M{W - 250},828 h34" stroke="{GREY}" stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#head)"/>'
)
text(W - 208, 832, "a file, or an override", size=11, fill=MUTED)

out.append("</svg>")
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "docs/source/_static/settings-data-flow.svg")
with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
