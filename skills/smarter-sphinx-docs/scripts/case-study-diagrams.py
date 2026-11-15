#!/usr/bin/env python3
"""
Draw the exhibits of the case studies, docs/source/_static/case-studies/*.svg.

Usage: case-study-diagrams.py [output folder]   (default: the folder above, from the repository root)

Each exhibit is one function, named after its file. Edit it, run the script, and render the result to check it:
rsvg-convert -w 1500 <svg> -o <scratchpad>/<name>.png. Most figures are Stackademy's, from its back office
(smarter-sh/stackademy), and the doodle's are from smarter.apps.doodle: keep them true when either changes.

Every exhibit has the look of the Smarter presentation deck: a dark gradient with an orange glow at the bottom left
and a purple one at the top right, Inter, a colored kicker over a short bold headline, translucent cards with tinted
icon chips, and amber curves with a dot at each end. The doodle artworks (doodle-*.svg) are not drawn here: they are
the platform's own, exported from its database.
"""

import os
import sys
from xml.sax.saxutils import escape

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "docs/source/_static/case-studies")

FONT = "Inter, 'Helvetica Neue', Lato, Arial, sans-serif"
MONO = "'JetBrains Mono', SFMono-Regular, Menlo, Consolas, monospace"

INK = "#FFFFFF"
INK2 = "#C9CAD3"
INK3 = "#8D8FA0"
LINE = "rgba(255,255,255,0.09)"
CARD = "#23252E"
SCREEN = "#14151B"
BLUE = "#4FA3FF"
PURPLE = "#A78BFA"
AMBER = "#F59E0B"
YELLOW = "#FFC50C"
GREEN = "#3DD68C"
RED = "#F87171"

# Line icons on a 24-unit grid, drawn in the chip's color.
ICONS = {
    "building": '<path d="M4 21V6l8-3 8 3v15M2.5 21h19M9 9h.01M15 9h.01M9 13h.01M15 13h.01M10 21v-4h4v4"/>',
    "brush": '<path d="M18.4 3.6a2 2 0 0 1 2.8 2.8L12 15.6 9.2 12.8z"/><path d="M9.2 12.8C6 12.8 4 15 4 20c4 0 6.8-1.6 8-4.4"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.8 2.8L16.5 9.5"/>',
    "coin": '<circle cx="12" cy="12" r="9"/><path d="M14.6 9.4c-.5-.9-1.4-1.4-2.6-1.4-1.4 0-2.5.8-2.5 2s1.1 1.7 2.5 2 2.5.8 2.5 2-1.1 2-2.5 2c-1.2 0-2.1-.5-2.6-1.4M12 6.5V8M12 16v1.5"/>',
    "database": '<ellipse cx="12" cy="5.5" rx="8" ry="2.5"/><path d="M4 5.5v13c0 1.4 3.6 2.5 8 2.5s8-1.1 8-2.5v-13M4 12c0 1.4 3.6 2.5 8 2.5s8-1.1 8-2.5"/>',
    "funnel": '<path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/>',
    "git": '<circle cx="6" cy="5.5" r="2.5"/><circle cx="6" cy="18.5" r="2.5"/><circle cx="18" cy="8" r="2.5"/><path d="M6 8v8M18 10.5c0 3.5-4 4.5-9.5 6"/>',
    "key": '<circle cx="8" cy="15" r="4.5"/><path d="M11.2 11.8L20 3M16 7l3 3M14 9l2 2"/>',
    "link": '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7.5a4 4 0 0 1 8 0V11"/>',
    "menu": '<path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01"/>',
    "network": '<circle cx="12" cy="5" r="2.5"/><circle cx="5" cy="19" r="2.5"/><circle cx="19" cy="19" r="2.5"/><path d="M12 7.5v4M12 11.5L6.7 17.1M12 11.5l5.3 5.6"/>',
    "plug": '<path d="M9 3v5M15 3v5M6 8h12v3.5a6 6 0 0 1-12 0zM12 17.5V21"/>',
    "server": '<rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01"/>',
    "shield": '<path d="M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    "smile": '<circle cx="12" cy="12" r="9"/><path d="M8 14c1 1.6 2.4 2.4 4 2.4s3-.8 4-2.4M9 9.5h.01M15 9.5h.01"/>',
    "sparkle": '<path d="M12 3l2.2 6.8L21 12l-6.8 2.2L12 21l-2.2-6.8L3 12l6.8-2.2z"/>',
    "table": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9.5h18M3 15h18M9.5 9.5V20"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
}


class Svg:
    """An SVG document, built one element at a time."""

    def __init__(self, width: int, height: int, title: str):
        self.width = width
        self.height = height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
            f'height="{height}" role="img" aria-label="{escape(title)}">',
            f"<title>{escape(title)}</title>",
        ]

    def add(self, element: str) -> None:
        self.parts.append(element)

    def save(self, name):
        self.parts.append("</svg>")
        path = os.path.join(OUT_DIR, f"{name}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.parts) + "\n")
        print(f"wrote {os.path.relpath(path, REPO_ROOT)}")


# ---------------------------------------------------------------------------------------------------------------
# The deck's parts
# ---------------------------------------------------------------------------------------------------------------
def canvas(width, height, title, kicker, kicker_color, headline, subtitle):
    """A new exhibit: the deck's background, then a kicker, a headline and a subtitle."""
    svg = Svg(width, height, title)
    svg.add(
        "<defs>"
        '<linearGradient id="dk-bg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#1A1C24"/><stop offset="1" stop-color="#24203A"/></linearGradient>'
        '<radialGradient id="dk-orange" cx="0.04" cy="1.12" r="0.62">'
        '<stop offset="0" stop-color="#EA580C" stop-opacity="0.32"/>'
        '<stop offset="0.55" stop-color="#EA580C" stop-opacity="0.08"/>'
        '<stop offset="1" stop-color="#EA580C" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="dk-purple" cx="0.98" cy="-0.06" r="0.5">'
        '<stop offset="0" stop-color="#7239EA" stop-opacity="0.3"/>'
        '<stop offset="1" stop-color="#7239EA" stop-opacity="0"/></radialGradient>'
        f'<marker id="dk-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{AMBER}"/></marker>'
        f'<marker id="dk-arrow-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{GREEN}"/></marker>'
        f'<marker id="dk-arrow-purple" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{PURPLE}"/></marker>'
        "</defs>"
    )
    for fill in ("url(#dk-bg)", "url(#dk-orange)", "url(#dk-purple)"):
        svg.add(f'<rect width="{width}" height="{height}" rx="24" fill="{fill}"/>')
    svg.add(f'<rect x="50" y="52" width="26" height="4" rx="2" fill="{kicker_color}"/>')
    text(svg, 88, 59, kicker, size=18, weight=600, fill=kicker_color)
    text(svg, 48, 116, headline, size=46, weight=700, spacing="-1.2")
    text(svg, 50, 154, subtitle, size=18, fill=INK2)
    return svg


def source(svg, s):
    text(svg, 50, svg.height - 22, s, size=13, fill=INK3)


def text(svg, x, y, s, size=16, weight=400, fill=INK, anchor="start", family=FONT, spacing=None, italic=False):
    letter = f' letter-spacing="{spacing}"' if spacing else ""
    style = ' font-style="italic"' if italic else ""
    svg.add(
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}"{letter}{style}>{escape(s)}</text>'
    )


def lines(svg, x, y, rows, size=15, leading=21, fill=INK2, family=FONT, anchor="start"):
    for i, row in enumerate(rows):
        text(svg, x, y + i * leading, row, size=size, fill=fill, family=family, anchor=anchor)


def spans(svg, x, y, parts, size=15, anchor="start"):
    """One line of text in several styles: parts are (text, weight, color, gap before it)."""
    inner = ""
    for s, weight, fill, gap in parts:
        inner += f'<tspan dx="{gap}" font-weight="{weight}" fill="{fill}">{escape(s)}</tspan>'
    svg.add(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" text-anchor="{anchor}">{inner}</text>')


def card(svg, x, y, w, h, accent=None, tint=None, dim=False):
    """A translucent card, with a colored bar on its left edge, or tinted and outlined in a color."""
    opacity = ' opacity="0.55"' if dim else ""
    if tint:
        svg.add(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{tint}" fill-opacity="0.08" '
            f'stroke="{tint}" stroke-opacity="0.55" stroke-width="1.2"{opacity}/>'
        )
    else:
        svg.add(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{CARD}" fill-opacity="0.82" '
            f'stroke="{LINE}" stroke-width="1"{opacity}/>'
        )
    if accent:
        svg.add(f'<rect x="{x}" y="{y + 18}" width="4" height="{h - 36}" rx="2" fill="{accent}"/>')


def chip(svg, x, y, icon, color):
    svg.add(f'<rect x="{x}" y="{y}" width="52" height="52" rx="14" fill="{color}" fill-opacity="0.18"/>')
    svg.add(
        f'<g transform="translate({x + 13},{y + 13}) scale(1.0833)" fill="none" stroke="{color}" stroke-width="2.2" '
        f'stroke-linecap="round" stroke-linejoin="round">{ICONS[icon]}</g>'
    )


def pill(svg, x, y, label, color, align="right", size=12.5):
    """A rounded label, tinted in its color; x is its right edge, or its left edge with align="left"."""
    w = round(len(label) * size * 0.57 + 22)
    if align == "right":
        x = x - w
    svg.add(f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="12" fill="{color}" fill-opacity="0.16"/>')
    text(svg, x + w / 2, y + 16.5, label, size=size, weight=600, fill=color, anchor="middle")
    return w


def curve(svg, x1, y1, x2, y2, color=AMBER, dash=False, vertical=False, dots=True):
    """An S-curve from (x1, y1) to (x2, y2), leaving and arriving level (or upright), with a dot at each end."""
    if x1 == x2 or y1 == y2:
        d = f"M{x1},{y1} L{x2},{y2}"
    elif vertical:
        mid = (y1 + y2) / 2
        d = f"M{x1},{y1} C{x1},{mid} {x2},{mid} {x2},{y2}"
    else:
        mid = (x1 + x2) / 2
        d = f"M{x1},{y1} C{mid},{y1} {mid},{y2} {x2},{y2}"
    dashed = ' stroke-dasharray="7 6"' if dash else ""
    svg.add(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.4" stroke-opacity="0.85"{dashed}/>')
    if dots:
        dot = YELLOW if color == AMBER else color
        svg.add(f'<circle cx="{x1}" cy="{y1}" r="5" fill="{dot}"/>')
        svg.add(f'<circle cx="{x2}" cy="{y2}" r="5" fill="{dot}"/>')


def arrow(svg, d, color=AMBER, dash=False):
    """A path with an arrowhead, for the small graphs where direction is the point."""
    dashed = ' stroke-dasharray="6 5"' if dash else ""
    marker = {GREEN: "dk-arrow-green", PURPLE: "dk-arrow-purple"}.get(color, "dk-arrow")
    svg.add(
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.2" stroke-opacity="0.9"{dashed} '
        f'marker-end="url(#{marker})"/>'
    )


# ---------------------------------------------------------------------------------------------------------------
# Stackademy, the company: its accounts and people
# ---------------------------------------------------------------------------------------------------------------
DEPARTMENTS = [
    # (name, account number, admin, member, assistant, shares)
    ("Stackademy IT", "2718-2818-0001", "Tomas Hartigan, Head of IT", None, "PII guardrail", "all of Stackademy"),
    ("Stackademy HR", "2718-2818-0002", "Avery Ivanova, HR Director", "Quinn Sandoval, HR Partner", "Harper", None),
    (
        "Stackademy Accounting",
        "2718-2818-0003",
        "Odette Hartigan, CFO",
        "Kofi Sandoval, Accountant",
        "Ledger",
        None,
    ),
    (
        "Course Content",
        "2718-2818-0004",
        "Odette Eriksen, Head of Content",
        "Tomas Underhill, Designer",
        "Reel",
        None,
    ),
    ("Admissions", "2718-2818-0005", "Dmitri Dumont, Director", "Wren Dumont, Advisor", "Ada", None),
]


def org_chart():
    svg = canvas(
        1200,
        810,
        "Exhibit: Stackademy's accounts, people and assistants",
        "Stackademy at a glance",
        AMBER,
        "Five departments. One company. One platform.",
        "Each department is an account under the company. Administrators manage one; the Head of IT manages every one.",
    )
    # the platform, and the company
    card(svg, 390, 196, 420, 80)
    chip(svg, 404, 210, "server", INK3)
    text(svg, 472, 230, "Smarter platform (root)", size=19, weight=700, fill=INK2)
    text(svg, 472, 255, "3141-5926-5359 · shares with every account", size=14, fill=INK3)
    curve(svg, 600, 276, 600, 310)
    card(svg, 300, 310, 600, 156)
    chip(svg, 320, 332, "building", AMBER)
    text(svg, 390, 352, "Stackademy Corp", size=21, weight=700, fill=AMBER)
    text(svg, 390, 376, "2718-2818-0000", size=13.5, fill=INK3, family=MONO)
    pill(svg, 880, 330, "members only", INK3)
    lines(
        svg,
        390,
        404,
        [
            "Vera Jaramillo, CEO · administrator; member of every department",
            "Odette Hartigan, CFO · member",
            "Atlas, the Board Pack · quarterly board pack orchestration",
        ],
        size=15,
    )
    # the departments
    for i, (name, number, admin, member, assistant, shares) in enumerate(DEPARTMENTS):
        x = 50 + i * 222
        y = 530
        curve(svg, 600, 466, x + 106, y, vertical=True)
        card(svg, x, y, 212, 222, accent=PURPLE if shares else BLUE)
        text(svg, x + 20, y + 36, name, size=15.5, weight=700)
        text(svg, x + 20, y + 58, number, size=13, fill=INK3, family=MONO)
        admin_name, admin_title = admin.split(", ")
        text(svg, x + 20, y + 90, admin_name, size=15, weight=600)
        text(svg, x + 20, y + 110, f"{admin_title} · admin", size=14, fill=INK2)
        if member:
            text(svg, x + 20, y + 136, f"{member.split(', ')[0]} · member", size=14, fill=INK2)
        if shares:
            pill(svg, x + 20, y + 150, "shares with Stackademy", PURPLE, align="left", size=12)
            text(svg, x + 20, y + 200, "Shares: PII guardrail", size=15, weight=700, fill=PURPLE)
        else:
            pill(svg, x + 20, y + 150, "members only", INK3, align="left", size=12)
            text(svg, x + 20, y + 200, f"Assistant: {assistant}", size=15, weight=700, fill=GREEN)
    source(svg, "Source: smarter-sh/stackademy, org/accounts/ and org/users/. All people are fictional.")
    svg.save("org-chart")


def sharing():
    svg = canvas(
        1200,
        740,
        "Exhibit: what a member of Stackademy HR may read",
        "Organizing for AI",
        BLUE,
        "What HR can read, and what it can't.",
        "A member reads an account's resources if their own account is that account, or descends from its share scope.",
    )
    nodes = [
        # (x, y, title, scope, readable, verdict)
        (435, 196, "Smarter platform", "share scope: itself, the root", True, "Readable: shares with everyone"),
        (435, 336, "Stackademy Corp", "share scope: itself, its members", False, "Not readable: its members only"),
        (50, 486, "Stackademy IT", "share scope: Stackademy Corp", True, "Readable: shares with Corp's subtree"),
        (435, 486, "Stackademy HR", "share scope: itself", True, "Readable: their own account"),
        (820, 486, "Stackademy Accounting", "share scope: itself", False, "Not readable: shares with no one"),
    ]
    curve(svg, 600, 300, 600, 336)
    for child_x in (215, 600, 985):
        curve(svg, 600, 440, child_x, 486, vertical=True)
    for x, y, title, scope, readable, verdict in nodes:
        color = GREEN if readable else RED
        card(svg, x, y, 330, 104, accent=color, dim=not readable)
        chip(svg, x + 20, y + 26, "check" if readable else "lock", color)
        text(svg, x + 88, y + 38, title, size=18, weight=700, fill=INK if readable else INK2)
        text(svg, x + 88, y + 62, scope, size=14, fill=INK3)
        text(svg, x + 88, y + 86, verdict, size=13.5, weight=600, fill=color)
    pill(svg, 600 - 64, 597, "Harper's account", AMBER, align="left")
    card(svg, 50, 628, 1100, 70, accent=AMBER)
    lines(
        svg,
        78,
        657,
        [
            "So Harper, HR's assistant, can use IT's PII guardrail and the platform's built-in resources, but not",
            "Accounting's connection, and Accounting can't use HR's.",
        ],
        size=16,
        leading=22,
    )
    source(svg, "Source: ADR-036, smarter.apps.account.hierarchy.readable_account_ids().")
    svg.save("sharing")


def org_as_code():
    svg = canvas(
        1200,
        700,
        "Exhibit: the organization, declared in a git repository",
        "Organizing for AI",
        BLUE,
        "The whole organization is one git repository.",
        "It holds the accounts, the people and every department's resources. owners.yaml says who applies each folder.",
    )
    # the repository, as a code window
    x = 50
    y = 200
    svg.add(f'<rect x="{x}" y="{y}" width="405" height="430" rx="18" fill="{SCREEN}" stroke="{LINE}"/>')
    for i in range(3):
        svg.add(f'<circle cx="{x + 24 + i * 18}" cy="{y + 24}" r="5.5" fill="#4A4D59"/>')
    text(svg, x + 90, y + 29, "smarter-sh/stackademy", size=14, fill=INK3, family=MONO)
    svg.add(f'<line x1="{x}" y1="{y + 48}" x2="{x + 405}" y2="{y + 48}" stroke="{LINE}"/>')
    listing = [
        ("org/accounts/", "6 Account manifests"),
        ("org/users/", "10 User manifests"),
        ("owners.yaml", "folder → owner, account"),
        ("secrets/", "the demo password"),
        ("departments/it/", "PII guardrail"),
        ("departments/hr/", "assistant, plugins"),
        ("  connections/", "database credentials"),
        ("departments/accounting/", "content/, admissions/"),
        ("departments/executive/", "Board Pack, orchestrator"),
        ("budgets/", "one per department"),
        ("scripts/", "the database, generated"),
    ]
    for i, (path, note) in enumerate(listing):
        row_y = y + 84 + i * 31
        indent = 20 if path.startswith("  ") else 0
        color = AMBER if path == "owners.yaml" else BLUE
        text(svg, x + 22 + indent, row_y, path.strip(), size=14, fill=color, family=MONO)
        text(svg, x + 232, row_y, note, size=13.5, fill=INK3)
    # the loader
    curve(svg, 455, 415, 495, 415)
    card(svg, 495, 320, 240, 190)
    chip(svg, 515, 338, "git", AMBER)
    text(svg, 515, 418, "load_from_github", size=15.5, weight=700, fill=AMBER, family=MONO)
    lines(
        svg,
        515,
        444,
        [
            "run by initialize_platform:",
            "applies every manifest,",
            "in dependency order",
        ],
        size=14,
        leading=19,
    )
    # who applies each folder
    rows = [
        ("departments/hr/", "Avery Ivanova", "Stackademy HR"),
        ("departments/hr/connections/", "Tomas Hartigan", "Stackademy HR"),
        ("departments/accounting/", "Odette Hartigan", "Stackademy Accounting"),
        ("departments/it/", "Tomas Hartigan", "Stackademy IT"),
        ("departments/executive/", "Vera Jaramillo", "Stackademy Corp"),
        ("org/accounts/, org/users/", "the platform admin", "creates the organization"),
    ]
    text(svg, 782, 188, "Applied as its folder's owner, in its owner's account", size=14, weight=600, fill=INK3)
    for i, (folder, owner, account) in enumerate(rows):
        row_y = 204 + i * 72
        card(svg, 780, row_y, 370, 62, accent=AMBER)
        text(svg, 800, row_y + 26, folder, size=13.5, fill=INK, family=MONO)
        text(svg, 800, row_y + 49, owner, size=15, weight=700, fill=INK)
        text(svg, 1132, row_y + 49, account, size=14, fill=INK3, anchor="end")
        curve(svg, 735, 415, 780, row_y + 31)
    source(
        svg,
        "Source: smarter-sh/stackademy; smarter.apps.account.repository_owners. owners.yaml is generated from the back office.",
    )
    svg.save("org-as-code")


# ---------------------------------------------------------------------------------------------------------------
# Department assistants
# ---------------------------------------------------------------------------------------------------------------
def access_path():
    svg = canvas(
        1200,
        690,
        "Exhibit: how HR's assistant reaches HR's records, and nothing else",
        "Confidential by construction",
        GREEN,
        "Every link to HR's records lives in HR's account.",
        "Harper reaches HR's records, and nothing else: only HR's members may use any link in the chain.",
    )
    svg.add(
        f'<rect x="50" y="196" width="1100" height="270" rx="22" fill="{BLUE}" fill-opacity="0.04" '
        f'stroke="{BLUE}" stroke-opacity="0.5" stroke-width="1.4" stroke-dasharray="8 6"/>'
    )
    pill(svg, 72, 212, "Account: Stackademy HR · members only", BLUE, align="left", size=13)
    chain = [
        ("sparkle", PURPLE, "Harper", ["LLMClient", "the HR assistant", "owner: HR Director"]),
        ("plug", PURPLE, "3 SqlPlugins", ["headcount", "employee record", "requisitions"]),
        ("link", PURPLE, "SqlConnection", ["stackademy_hr_db", "+ Secret: its password", "owner: Head of IT"]),
        ("key", BLUE, "Database user", ["stackademy_hr", "read-only, SELECT", "on HR's tables only"]),
        ("table", BLUE, "Tables", ["departments, employees", "compensation, PTO", "job requisitions"]),
    ]
    tops = []
    for i, (icon, color, title, rows) in enumerate(chain):
        x = 72 + i * 216
        y = 256
        card(svg, x, y, 192, 188)
        chip(svg, x + 18, y + 18, icon, color)
        text(svg, x + 18, y + 102, title, size=18, weight=700, fill=color)
        lines(svg, x + 18, y + 128, rows, size=14, leading=21)
        if i > 0:
            curve(svg, x - 24, y + 44, x, y + 44)
        tops.append(x + 96)
    # what reaches into the chain from outside it
    below = [
        (72, "shield", PURPLE, "PII guardrail · Stackademy IT", ["Shared with all of Stackademy,", "read by Harper"]),
        (430, "coin", AMBER, "Budget · stackademy_hr_ai", ["$150 a month, $1,800 in all;", "blocks when spent"]),
        (798, "database", GREEN, "The database's own grants", ["Accounting's user is refused", "compensation"]),
    ]
    for x, icon, color, title, rows in below:
        card(svg, x, 506, 330, 116, accent=color)
        chip(svg, x + 22, 526, icon, color)
        text(svg, x + 90, 548, title, size=16, weight=700, fill=color)
        lines(svg, x + 90, 574, rows, size=14.5, leading=21)
    curve(svg, 237, 506, tops[0], 444, color=PURPLE, vertical=True)
    curve(svg, 565, 506, tops[0], 444, dash=True, vertical=True)
    curve(svg, 625, 506, tops[1], 444, dash=True, vertical=True)
    curve(svg, 963, 506, tops[3], 444, color=GREEN, dash=True, vertical=True)
    source(svg, "Source: smarter-sh/stackademy, departments/hr/ and scripts/backoffice-grants.txt.")
    svg.save("access-path")


ACCESS_COLUMNS = ["Catalogue", "Directory", "HR records", "Admissions", "Finance", "Production", "Board views"]
ACCESS_ROWS = [
    # user, then one of "full", "part" or "" per column
    ("stackademy_catalog", ["full", "", "", "", "", "", ""]),
    ("stackademy_hr", ["", "full", "full", "", "", "", ""]),
    ("stackademy_admissions", ["part", "", "", "full", "", "", ""]),
    ("stackademy_accounting", ["part", "full", "", "part", "full", "", ""]),
    ("stackademy_content", ["part", "full", "", "", "part", "full", ""]),
    ("stackademy_executive", ["", "", "", "", "", "", "full"]),
]


def access_matrix():
    svg = canvas(
        1200,
        790,
        "Exhibit: what each department's database user may read",
        "Confidential by construction",
        GREEN,
        "Only HR's database user can read salaries.",
        "Table-level grants, generated with the data and checked on every load: only HR's user reads compensation.",
    )
    x0 = 320
    y0 = 254
    cw = 118
    rh = 56
    hr_x = x0 + 2 * cw
    svg.add(
        f'<rect x="{hr_x - 2}" y="{y0 - 50}" width="{cw + 4}" height="{rh * 6 + 60}" rx="16" fill="{RED}" '
        f'fill-opacity="0.06" stroke="{RED}" stroke-opacity="0.8" stroke-width="2"/>'
    )
    for j, column in enumerate(ACCESS_COLUMNS):
        color = RED if j == 2 else INK2
        text(svg, x0 + j * cw + cw / 2, y0 - 18, column, size=14.5, weight=700, fill=color, anchor="middle")
    for i, (user, cells) in enumerate(ACCESS_ROWS):
        y = y0 + i * rh
        text(svg, 50, y + 34, user, size=15, family=MONO)
        for j, cell in enumerate(cells):
            x = x0 + j * cw
            if cell == "full":
                fill = f'fill="{GREEN}" fill-opacity="0.85"'
            elif cell == "part":
                fill = f'fill="{GREEN}" fill-opacity="0.2"'
            else:
                fill = 'fill="#FFFFFF" fill-opacity="0.045"'
            svg.add(f'<rect x="{x + 6}" y="{y + 8}" width="{cw - 12}" height="{rh - 16}" rx="10" {fill}/>')
            if cell == "full":
                text(svg, x + cw / 2, y + 33, "all", size=14, weight=700, fill="#0F1015", anchor="middle")
            if cell == "part":
                text(svg, x + cw / 2, y + 33, "some", size=14, weight=700, fill=GREEN, anchor="middle")
    label_w = round(len("salaries: HR only") * 13 * 0.57 + 22)
    pill(svg, hr_x + cw / 2 - label_w / 2, y0 + rh * 6 + 22, "salaries: HR only", RED, align="left", size=13)
    card(svg, 50, 652, 1100, 80)
    lines(
        svg,
        74,
        684,
        [
            "Catalogue: courses, cohorts, modules, lessons. Directory: departments, employees. HR records: compensation, "
            "time off, requisitions.",
            "Admissions: students, enrollments, payments, contracts. Finance: ledger, budgets, invoices. Production: "
            "assets, tasks. Board views: totals only.",
        ],
        size=13.5,
        leading=22,
        fill=INK3,
    )
    source(svg, "Source: smarter-sh/stackademy, GRANTS in scripts/generate_backoffice.py.")
    svg.save("access-matrix")


# ---------------------------------------------------------------------------------------------------------------
# Ask Stanley: the public course advisor
# ---------------------------------------------------------------------------------------------------------------
STANLEY_ROWS = [
    # (course_code, course_name, cost, prerequisite), as the plugin's query returns them for description = AI
    ("CS210", "Artificial Intelligence", "700.00", "CS107 Algorithms"),
    ("CS316", "AI for Robotics", "850.00", "CS301 Machine Learning"),
    ("CS319", "AI in Healthcare", "800.00", "CS301 Machine Learning"),
    ("CS405", "AI Capstone Project", "1000.00", "CS301 Machine Learning"),
]


def stanley_architecture():
    svg = canvas(
        1200,
        860,
        "Exhibit: how Stanley is wired to the AI model and to Stackademy's database",
        "Ask Stanley",
        GREEN,
        "Stanley's facts come from the database.",
        "The AI model writes the sentences. Every course, price and prerequisite in them is a row of the courses table.",
    )
    # the prospective student, on any web site that may embed Stanley's chat
    card(svg, 50, 236, 240, 196)
    chip(svg, 70, 256, "user", AMBER)
    text(svg, 70, 334, "Prospective student", size=18, weight=700, fill=AMBER)
    lines(svg, 70, 360, ["any hour, any country", "Smarter Chat, on a page", "in allowedOrigins"], size=14.5)

    # the Smarter platform, and Stanley's five resources
    svg.add(
        f'<rect x="330" y="196" width="530" height="520" rx="22" fill="{BLUE}" fill-opacity="0.04" '
        f'stroke="{BLUE}" stroke-opacity="0.5" stroke-width="1.4" stroke-dasharray="8 6"/>'
    )
    pill(svg, 352, 212, "Smarter platform · five manifests, no code", BLUE, align="left", size=13)
    resources = [
        # (y, icon, color, title, name, description)
        (252, "smile", BLUE, "Stanley", "LLMClient · stackademy_sql", "Instructions: use the tool, don't guess"),
        (392, "plug", GREEN, "One tool", "SqlPlugin · stackademy_sql", "A reviewed SELECT over courses; 2 values"),
        (532, "link", GREEN, "The connection", "SqlConnection · stackademy_catalog_db", "+ Secret: the password"),
    ]
    for y, icon, color, title, name, description in resources:
        card(svg, 360, y, 480, 108, accent=color)
        chip(svg, 382, y + 28, icon, color)
        text(svg, 452, y + 36, title, size=19, weight=700, fill=color)
        text(svg, 452, y + 61, name, size=13.5, fill=INK3, family=MONO)
        text(svg, 452, y + 86, description, size=15.5, fill=INK2)
    curve(svg, 600, 360, 600, 392, color=GREEN)
    curve(svg, 600, 500, 600, 532, color=GREEN)
    # the budget, around Stanley and his tool
    card(svg, 360, 660, 480, 40, tint=AMBER)
    text(
        svg,
        600,
        686,
        "Budget stackademy_project · $2,500 a month, then a hard stop",
        size=14.5,
        weight=600,
        fill=AMBER,
        anchor="middle",
    )

    # the student talks only to Stanley
    curve(svg, 290, 334, 360, 306)

    # the AI model: words, not facts
    card(svg, 910, 236, 240, 196, accent=PURPLE)
    chip(svg, 932, 256, "sparkle", PURPLE)
    text(svg, 932, 334, "AI model", size=18, weight=700, fill=PURPLE)
    text(svg, 932, 358, "openai · gpt-6-luna", size=13.5, fill=INK3, family=MONO)
    lines(svg, 932, 384, ["Chooses the tool's values,", "writes the answer"], size=14.5)
    curve(svg, 840, 290, 910, 290, color=PURPLE)
    curve(svg, 840, 322, 910, 322, color=PURPLE)
    text(svg, 885, 282, "ask", size=12, weight=600, fill=INK3, anchor="middle")
    text(svg, 885, 342, "tool call", size=12, weight=600, fill=INK3, anchor="middle")
    pill(svg, 1150, 444, "never sees the database", PURPLE, size=12)

    # the database: the facts
    card(svg, 910, 486, 240, 230, tint=GREEN)
    chip(svg, 930, 504, "database", GREEN)
    text(svg, 994, 526, "MariaDB", size=18, weight=700, fill=GREEN)
    text(svg, 994, 548, "stackademy", size=13.5, fill=INK3, family=MONO)
    text(svg, 930, 588, "as stackademy_catalog:", size=13.5, fill=INK3, family=MONO)
    text(svg, 930, 612, "courses", size=15, weight=700, fill=GREEN, family=MONO)
    text(svg, 1012, 612, "← the query", size=14, fill=GREEN)
    text(svg, 930, 634, "cohorts, modules, lessons", size=13.5, fill=INK2)
    text(svg, 930, 664, "21 other tables refused:", size=13.5, weight=600, fill=RED)
    text(svg, 930, 685, "students, employees, pay ...", size=13.5, fill=INK3)
    curve(svg, 840, 586, 910, 586, color=GREEN)
    text(svg, 885, 576, "SELECT", size=11.5, weight=600, fill=GREEN, family=MONO, anchor="middle")
    curve(svg, 840, 614, 910, 614, color=GREEN)
    text(svg, 885, 634, "rows", size=12, weight=600, fill=GREEN, anchor="middle")

    card(svg, 50, 740, 1100, 70, accent=GREEN)
    lines(
        svg,
        78,
        769,
        [
            "Smarter, not the model, runs the query: it binds the model's values as parameters, connects as a read-only user,",
            "and hands the rows back. Change a price in courses, and Stanley's next answer has it. There is no copy to update.",
        ],
        size=15,
        leading=22,
    )
    source(svg, "Source: smarter-sh/stackademy, llm-clients/, plugins/sql/, connections/sql/ and budgets/.")
    svg.save("stanley-architecture")


def stanley_tool_call():
    svg = canvas(
        1200,
        1010,
        "Exhibit: one question to Stanley, from the chat to the database and back",
        "Ask Stanley",
        GREEN,
        "One question, one query, one answer.",
        "The model asks for the tool; Smarter runs the query. Green is data from the database.",
    )
    lanes = [
        # (x, icon, color, title, subtitle)
        (150, "user", AMBER, "Student", "Smarter Chat"),
        (470, "smile", BLUE, "Stanley", "LLMClient, on Smarter"),
        (790, "sparkle", PURPLE, "AI model", "gpt-6-luna"),
        (1060, "database", GREEN, "MariaDB", "stackademy"),
    ]
    for x, icon, color, title, subtitle in lanes:
        svg.add(
            f'<line x1="{x}" y1="270" x2="{x}" y2="856" stroke="#FFFFFF" stroke-opacity="0.16" '
            f'stroke-width="1.5" stroke-dasharray="4 6"/>'
        )
        card(svg, x - 115, 196, 230, 74)
        chip(svg, x - 101, 207, icon, color)
        text(svg, x - 36, 228, title, size=17, weight=700, fill=color)
        text(svg, x - 36, 251, subtitle, size=13.5, fill=INK3)
    x_of = {lane[3]: lane[0] for lane in lanes}

    def message(n, y, start, end, label, color=AMBER):
        x1 = x_of[start]
        x2 = x_of[end]
        step = 12 if x2 > x1 else -12
        arrow(svg, f"M{x1 + step},{y} L{x2 - step},{y}", color=color)
        mid = (x1 + x2) / 2
        w = round(len(label) * 14.5 * 0.53)
        svg.add(f'<circle cx="{mid - w / 2 - 18}" cy="{y - 15}" r="11" fill="{color}" fill-opacity="0.2"/>')
        text(svg, mid - w / 2 - 18, y - 10, str(n), size=12.5, weight=700, fill=color, anchor="middle")
        text(svg, mid - w / 2, y - 10, label, size=14.5, fill=INK if color != GREEN else GREEN)

    message(1, 322, "Student", "Stanley", "“Do you offer any courses on AI?”")
    message(2, 378, "Stanley", "AI model", "the question + the tool, described", color=PURPLE)
    message(3, 434, "AI model", "Stanley", "tool call: description = AI", color=PURPLE)
    message(4, 490, "Stanley", "MariaDB", "the reviewed query, AI bound as a parameter", color=GREEN)
    message(5, 546, "MariaDB", "Stanley", "4 rows of the courses table", color=GREEN)

    # the rows, as the database returned them
    x = 500
    y = 566
    svg.add(
        f'<rect x="{x}" y="{y}" width="640" height="150" rx="16" fill="{SCREEN}" stroke="{GREEN}" '
        f'stroke-opacity="0.55" stroke-width="1.2"/>'
    )
    columns = [0, 74, 290, 380]
    for header, dx in zip(["code", "course_name", "cost", "prerequisite"], columns):
        text(svg, x + 22 + dx, y + 30, header, size=13, fill=INK3, family=MONO)
    for i, row in enumerate(STANLEY_ROWS):
        for value, dx in zip(row, columns):
            text(svg, x + 22 + dx, y + 58 + i * 24, value, size=13.5, fill=GREEN, family=MONO)

    message(6, 762, "Stanley", "AI model", "the 4 rows", color=GREEN)
    message(7, 818, "AI model", "Stanley", "an answer, written from the rows", color=PURPLE)
    message(8, 874, "Stanley", "Student", "the answer, in seconds")

    card(svg, 50, 900, 1100, 70, accent=AMBER)
    spans(
        svg,
        78,
        929,
        [
            ("Stanley:", 700, AMBER, 0),
            ("“Yes, four. Start with CS210 Artificial Intelligence, $700, after CS107 Algorithms.", 400, INK, 8),
        ],
        size=15.5,
    )
    text(
        svg,
        78,
        953,
        "CS316, CS319 and CS405 follow CS301 Machine Learning, from $800 to $1,000.” (illustrative wording)",
        size=15.5,
        fill=INK,
    )
    source(svg, "Source: plugins/sql/stackademy-sql.yaml in smarter-sh/stackademy; the rows are its query's, for AI.")
    svg.save("stanley-tool-call")


# ---------------------------------------------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------------------------------------------
def board_pack_run():
    svg = canvas(
        1200,
        800,
        "Exhibit: a run of the quarterly board pack",
        "The board pack",
        PURPLE,
        "Four departments answer. Atlas writes the page.",
        "Each department answers independently, from its own records and on its own budget.",
    )
    center = 405
    # the CEO starts a run
    card(svg, 50, center - 92, 210, 184)
    chip(svg, 70, center - 72, "user", AMBER)
    text(svg, 70, center + 8, "Vera Jaramillo", size=17, weight=700, fill=AMBER)
    text(svg, 70, center + 32, "CEO, starts a run:", size=14, fill=INK3)
    lines(svg, 70, center + 54, ["Prepare the board pack", "for Q4 2025."], size=14, leading=19, fill=INK2)
    curve(svg, 260, center, 310, center)
    text(svg, 285, center - 12, "POST", size=11.5, weight=600, fill=INK3, family=MONO, anchor="middle")
    # the orchestrator
    card(svg, 310, center - 100, 230, 200)
    chip(svg, 330, center - 80, "network", PURPLE)
    text(svg, 330, center + 2, "Orchestrator", size=18, weight=700, fill=PURPLE)
    lines(svg, 330, center + 26, ["stackademy_quarterly_", "board_pack"], size=13, leading=18, fill=INK3, family=MONO)
    lines(svg, 330, center + 68, ["strategy: parallel", "Stackademy Corp"], size=14, leading=19)
    lines(
        svg, 314, center + 130, ["checks: the runner may use", "every harness, or 403"], size=13.5, leading=19, fill=RED
    )
    # the four departments
    lanes = [
        ("Harper", "Stackademy HR", "stackademy_hr", "headcount, hiring"),
        ("Ledger", "Stackademy Accounting", "stackademy_accounting", "results, budgets, invoices"),
        ("Reel", "Course Content", "stackademy_content", "courses in production"),
        ("Ada", "Admissions", "stackademy_admissions", "enrollments, contracts"),
    ]
    for i, (name, account, user, subject) in enumerate(lanes):
        y = 200 + i * 106
        mid = y + 46
        curve(svg, 540, center, 590, mid)
        card(svg, 590, y, 300, 92, accent=BLUE)
        spans(svg, 612, y + 30, [(name, 700, BLUE, 0), ("·", 400, INK3, 8), (account, 400, INK2, 8)], size=15.5)
        text(svg, 612, y + 54, f"reads as {user}", size=13, fill=INK3, family=MONO)
        text(svg, 612, y + 77, subject, size=14.5, fill=INK2)
        curve(svg, 890, mid, 950, center - 10)
    # Atlas, and the page it writes
    card(svg, 950, center - 105, 200, 190)
    chip(svg, 970, center - 85, "sparkle", GREEN)
    text(svg, 970, center - 6, "Atlas", size=18, weight=700, fill=GREEN)
    lines(
        svg,
        970,
        center + 18,
        ["summarizer", "Stackademy Corp", "views of totals", "checks the figures"],
        size=14,
        leading=19,
    )
    curve(svg, 1050, center + 85, 1050, center + 125, color=GREEN)
    card(svg, 950, center + 125, 200, 80, tint=GREEN)
    text(svg, 1050, center + 159, "The board pack", size=17, weight=700, fill=GREEN, anchor="middle")
    text(svg, 1050, center + 183, "one page, about 30 s", size=14, fill=INK2, anchor="middle")
    card(svg, 50, 646, 1100, 80, accent=PURPLE)
    lines(
        svg,
        78,
        678,
        [
            "Each step is an ordinary prompt of its LLMClient, run as that LLMClient's owner: its tools, guardrail and budget apply.",
            "The CFO, who isn't a member of HR, is refused: an orchestrator is never a way into an account its runner doesn't belong to.",
        ],
        size=15,
        leading=23,
    )
    source(
        svg,
        "Source: ADR-037; smarter.apps.orchestrator.runtime; departments/executive/orchestrators/ in smarter-sh/stackademy.",
    )
    svg.save("board-pack-run")


def strategies():
    svg = canvas(
        1200,
        630,
        "Exhibit: the four orchestration strategies that Smarter runs",
        "The board pack",
        PURPLE,
        "Four ways to run a team of assistants.",
        "A summarizer, when there is one, answers last after any of them. Voting and debate are declared, but not yet run.",
    )

    def node(cx, y, label, color=None, w=76):
        x = cx - w / 2
        if color:
            svg.add(
                f'<rect x="{x}" y="{y}" width="{w}" height="34" rx="17" fill="{color}" fill-opacity="0.18" '
                f'stroke="{color}" stroke-opacity="0.7" stroke-width="1.4"/>'
            )
        else:
            svg.add(
                f'<rect x="{x}" y="{y}" width="{w}" height="34" rx="17" fill="#FFFFFF" fill-opacity="0.06" '
                f'stroke="#FFFFFF" stroke-opacity="0.22" stroke-width="1.2"/>'
            )
        text(svg, cx, y + 22, label, size=14, weight=700, fill=color or INK, anchor="middle")

    panels = [
        ("Sequential", "each sees the answers before it"),
        ("Parallel", "each sees only the objective"),
        ("Router", "a router picks one assistant"),
        ("Supervisor", "a planner asks, one at a time"),
    ]
    top = 196
    for k, (title, note) in enumerate(panels):
        x = 50 + k * 280
        card(svg, x, top, 260, 370)
        text(svg, x + 24, top + 42, title, size=20, weight=700, fill=PURPLE)
        text(svg, x + 24, top + 66, note, size=14, fill=INK3)
    # sequential
    cx = 50 + 130
    for i, label in enumerate(["A", "B", "C"]):
        node(cx, top + 100 + i * 62, label)
        arrow(svg, f"M{cx},{top + 136 + i * 62} L{cx},{top + 158 + i * 62}")
    node(cx, top + 286, "summary", color=GREEN, w=110)
    # parallel
    cx = 330 + 130
    node(cx, top + 100, "objective", color=PURPLE, w=104)
    for i, label in enumerate(["A", "B", "C"]):
        nx = cx + (i - 1) * 78
        node(nx, top + 190, label, w=62)
        arrow(svg, f"M{cx + (i - 1) * 18},{top + 136} L{nx},{top + 186}")
        arrow(svg, f"M{nx},{top + 226} L{cx + (i - 1) * 22},{top + 282}")
    node(cx, top + 286, "summary", color=GREEN, w=110)
    # router
    cx = 610 + 130
    node(cx, top + 100, "router", color=PURPLE, w=90)
    for i, label in enumerate(["A", "B", "C"]):
        nx = cx + (i - 1) * 78
        node(nx, top + 190, label, color=GREEN if label == "B" else None, w=62)
    arrow(svg, f"M{cx},{top + 136} L{cx},{top + 186}", color=GREEN)
    svg.add(
        f'<path d="M{cx - 14},{top + 136} L{cx - 70},{top + 188} M{cx + 14},{top + 136} L{cx + 70},{top + 188}" '
        f'stroke="{INK3}" stroke-width="1.6" stroke-dasharray="5 5" fill="none"/>'
    )
    text(svg, cx, top + 290, '{"harness": "B"}', size=13.5, fill=INK3, family=MONO, anchor="middle")
    # supervisor
    cx = 890 + 130
    node(cx, top + 100, "planner", color=PURPLE, w=96)
    node(cx - 72, top + 214, "A")
    node(cx + 72, top + 214, "B")
    arrow(svg, f"M{cx - 20},{top + 136} C{cx - 50},{top + 160} {cx - 64},{top + 180} {cx - 66},{top + 210}")
    arrow(svg, f"M{cx - 90},{top + 212} C{cx - 92},{top + 170} {cx - 72},{top + 132} {cx - 50},{top + 122}", dash=True)
    arrow(svg, f"M{cx + 20},{top + 136} C{cx + 50},{top + 160} {cx + 64},{top + 180} {cx + 66},{top + 210}")
    text(svg, cx, top + 296, '{"next": "A", "message": ...}', size=12, fill=INK3, family=MONO, anchor="middle")
    text(svg, cx, top + 318, '{"done": true, "result": ...}', size=12, fill=INK3, family=MONO, anchor="middle")
    source(svg, "Source: ADR-037, items 7 and 8; smarter.apps.orchestrator.runtime, STRATEGY_RUNNERS.")
    svg.save("strategies")


# ---------------------------------------------------------------------------------------------------------------
# Shadow AI: the departments' own AI projects, brought behind Smarter
# ---------------------------------------------------------------------------------------------------------------
def shadow_ai_responses():
    svg = canvas(
        1200,
        560,
        "Exhibit: three ways to respond to the AI projects that departments have already built",
        "Shadow AI",
        AMBER,
        "Three ways to respond.",
        "People already build with AI. Stackademy chose the third way: make the easy path the governed one.",
    )
    options = [
        # (icon, color, title, what happens, at Stackademy, chosen)
        (
            "menu",
            INK3,
            "1  Ignore it",
            ["Everyone keeps building alone.", "Nothing is shared, and no one", "sees it."],
            ["The AI invoice grows $288 a", "month; data leaves unseen."],
            False,
        ),
        (
            "lock",
            RED,
            "2  Ban it",
            ["Some people stop. Others go", "around the rule. The business", "slows down."],
            ["Month-end, the nightly emails and", "the screener stop; the rest hide."],
            False,
        ),
        (
            "shield",
            GREEN,
            "3  Enable it",
            ["One place to build and run AI,", "under the company's rules, with", "nothing rewritten on day one."],
            ["A Proxy per project at once;", "the leaky ones rebuilt next."],
            True,
        ),
    ]
    for k, (icon, color, title, happens, here, chosen) in enumerate(options):
        x = 50 + k * 370
        if chosen:
            card(svg, x, 196, 360, 300, tint=GREEN)
        else:
            card(svg, x, 196, 360, 300, accent=color)
        chip(svg, x + 26, 220, icon, color)
        text(svg, x + 94, 254, title, size=22, weight=700, fill=color if color != INK3 else INK)
        lines(svg, x + 28, 312, happens, size=16, leading=23, fill=INK2)
        text(svg, x + 28, 404, "At Stackademy", size=13, weight=600, fill=INK3)
        lines(svg, x + 28, 430, here, size=15, leading=21, fill=color if chosen else INK2)
        if chosen:
            pill(svg, x + 336, 226, "chosen", GREEN)
    source(svg, "Source: the Smarter presentation deck; account 5300 and ap_invoices in smarter-sh/stackademy.")
    svg.save("shadow-ai-responses")


def shadow_ai_proxy():
    svg = canvas(
        1200,
        900,
        "Exhibit: phase 1, every legacy AI project calls its AI provider through a Smarter Proxy",
        "Shadow AI · phase 1",
        AMBER,
        "Two lines changed. Every call goes through Smarter.",
        "Each project keeps its code and its provider's SDK; only its base URL and its API key change.",
    )
    # before: the projects called the providers directly
    card(svg, 50, 186, 1100, 74, accent=RED)
    spans(
        svg,
        78,
        216,
        [("Before", 700, RED, 0), ("seven projects called three providers directly, with provider keys", 400, INK, 10)],
        size=16,
    )
    text(
        svg,
        78,
        242,
        "in scripts, notebooks, a spreadsheet and a CI variable, and one invoice a month, charged to IT.",
        size=16,
        fill=INK2,
    )

    # the projects, each with its own Smarter API key
    projects = [
        ("Month-end commentary", "Accounting", "openai"),
        ("Résumé screener", "HR", "openai"),
        ("Enrollment follow-up", "Admissions", "anthropic"),
        ("Lesson reviewer", "Course Content", "googleai"),
        ("Helpdesk bot + 2 more", "IT, HR, Admissions", "openai"),
    ]
    top = 300
    pitch = 96
    for i, (name, department, _provider) in enumerate(projects):
        y = top + i * pitch
        card(svg, 50, y, 270, 80)
        chip(svg, 64, y + 14, "user", AMBER)
        text(svg, 128, y + 36, name, size=15.5, weight=700, fill=INK)
        text(svg, 128, y + 59, department, size=13.5, fill=INK3)
        curve(svg, 320, y + 40, 392, y + 40)
    text(svg, 386, top - 24, "Smarter API key", size=12, weight=600, fill=AMBER, anchor="end")

    # the Smarter platform
    svg.add(
        f'<rect x="392" y="{top - 14}" width="476" height="{5 * pitch + 10}" rx="22" fill="{BLUE}" '
        f'fill-opacity="0.04" stroke="{BLUE}" stroke-opacity="0.5" stroke-width="1.4" stroke-dasharray="8 6"/>'
    )
    pill(svg, 414, top + 2, "Smarter · a Proxy per project, in its department's account", BLUE, align="left", size=13)
    steps = [
        ("key", AMBER, "Smarter API key", "one per project; revocable; last used"),
        ("funnel", BLUE, "Proxy", "allowedPaths, e.g. chat/completions"),
        ("coin", AMBER, "Budget", "the department's; 402 at the limit"),
        ("lock", GREEN, "Secret", "the provider's key, which never leaves"),
        ("table", PURPLE, "Charges", "tokens by project, person and model"),
    ]
    for i, (icon, color, title, note) in enumerate(steps):
        y = top + 40 + i * 86
        card(svg, 414, y, 432, 74, accent=color)
        chip(svg, 432, y + 11, icon, color)
        text(svg, 500, y + 32, title, size=16.5, weight=700, fill=color)
        text(svg, 500, y + 55, note, size=14, fill=INK2)

    # the providers
    providers = [
        ("OpenAI", "openai SDK"),
        ("Anthropic", "anthropic SDK"),
        ("Google Gemini", "google-genai SDK"),
    ]
    for i, (name, host) in enumerate(providers):
        y = top + 50 + i * 150
        card(svg, 930, y, 220, 100, accent=PURPLE)
        chip(svg, 948, y + 24, "sparkle", PURPLE)
        text(svg, 1012, y + 46, name, size=16.5, weight=700, fill=PURPLE)
        text(svg, 1012, y + 70, host, size=12, fill=INK3, family=MONO)
        curve(svg, 868, top + 180 + (i - 1) * 40, 930, y + 50, color=PURPLE)
    text(svg, 1150, top + 30, "+ the provider's key", size=12, weight=600, fill=PURPLE, anchor="end")

    card(svg, 50, 790, 1100, 70, accent=AMBER)
    lines(
        svg,
        78,
        819,
        [
            "Nothing stops working, and from the first call each project has an owner, a key, a budget and its own charges.",
            "The Proxy forwards prompts as they are, so a project that sends private data still does, until phase 2.",
        ],
        size=15,
        leading=22,
    )
    source(svg, "Source: smarter.apps.proxy and docs/source/smarter-resources/smarter-proxy.rst.")
    svg.save("shadow-ai-proxy")


def shadow_ai_tools():
    svg = canvas(
        1200,
        800,
        "Exhibit: phase 2, the month-end commentary sends the model three totals instead of the general ledger",
        "Shadow AI · phase 2",
        GREEN,
        "Send the rows, not the table.",
        "The month-end commentary, before and after. The same question; about 90,000 tokens, then about a thousand.",
    )
    # before
    card(svg, 50, 196, 540, 470, accent=RED)
    text(svg, 78, 236, "Before: paste the ledger", size=20, weight=700, fill=RED)
    text(svg, 78, 262, "a notebook, through its Proxy", size=14, fill=INK3)
    svg.add(
        f'<rect x="78" y="286" width="484" height="210" rx="14" fill="{SCREEN}" stroke="{RED}" '
        f'stroke-opacity="0.45" stroke-width="1.2"/>'
    )
    text(svg, 98, 314, "prompt", size=13, fill=INK3, family=MONO)
    text(svg, 98, 342, "Write the month-end commentary.", size=14, fill=INK, family=MONO)
    text(svg, 98, 368, "line_id,entry_date,gl_account,…", size=14, fill=RED, family=MONO)
    text(svg, 98, 392, "1,2024-12-11,1000,…,750.00,0.00", size=14, fill=RED, family=MONO)
    text(svg, 98, 416, "2,2024-12-11,4000,…,0.00,750.00", size=14, fill=RED, family=MONO)
    text(svg, 98, 440, "… 2,502 lines of gl_entries", size=14, fill=RED, family=MONO)
    text(svg, 98, 474, "≈ 88,000 tokens, every run", size=14, weight=700, fill=RED, family=MONO)
    lines(
        svg,
        78,
        534,
        [
            "The whole ledger goes to the AI provider,",
            "whatever the question. The cost grows with the",
            "table, not with the answer.",
        ],
        size=15.5,
        leading=23,
        fill=INK2,
    )
    pill(svg, 562, 626, "leaves the company", RED)

    # after
    card(svg, 610, 196, 540, 470, tint=GREEN)
    text(svg, 638, 236, "After: ask Ledger", size=20, weight=700, fill=GREEN)
    text(svg, 638, 262, "Accounting's LLMClient, with SqlPlugins", size=14, fill=INK3)
    flow = [
        ("sparkle", PURPLE, "The model asks for a tool", "stackademy_accounting_results · Q4 2025"),
        ("database", GREEN, "Smarter runs the reviewed query", "as Accounting's read-only database user"),
        ("table", GREEN, "Three totals come back", "revenue · expenses · net_income"),
    ]
    for i, (icon, color, title, note) in enumerate(flow):
        y = 290 + i * 98
        card(svg, 638, y, 484, 80)
        chip(svg, 654, y + 14, icon, color)
        text(svg, 720, y + 35, title, size=16, weight=700, fill=color)
        text(svg, 720, y + 59, note, size=12.5, fill=INK2, family=MONO)
        if i < 2:
            curve(svg, 880, y + 80, 880, y + 98, color=GREEN, dots=False)
    lines(
        svg,
        638,
        606,
        ["The ledger stays in the database. Ledger's guardrail,", "budget and chat history apply to every question."],
        size=15.5,
        leading=23,
        fill=INK2,
    )

    card(svg, 50, 690, 1100, 70, accent=GREEN)
    lines(
        svg,
        78,
        719,
        [
            "The same pattern rebuilt the others: HR's requisitions instead of every salary; one student's enrollments and the",
            "catalogue's API instead of 320 students' records; a read-only GitHub MCPClient instead of whole course folders.",
        ],
        size=15,
        leading=22,
    )
    source(svg, "Source: departments/accounting/plugins/ and scripts/backoffice.sql in smarter-sh/stackademy.")
    svg.save("shadow-ai-tools")


# ---------------------------------------------------------------------------------------------------------------
# The Smarter Doodle (a case of the Smarter Project itself, not Stackademy)
# ---------------------------------------------------------------------------------------------------------------
def artwork(path, x, y, w):
    """A doodle's artwork, nested at (x, y), w wide, from its file in docs/source/_static/case-studies/."""
    with open(path, encoding="utf-8") as f:
        svg_text = f.read()
    start = svg_text.index(">", svg_text.index("<svg")) + 1
    end = svg_text.rindex("</svg>")
    inner = svg_text[start:end]
    inner = inner.replace(inner[inner.index("<title>") : inner.index("</title>") + len("</title>")], "")
    # no trailing whitespace, which the pre-commit hooks would strip from the exhibit
    stripped = [line.rstrip() for line in inner.split("\n")]
    inner = "\n".join(line for line in stripped if line)
    h = round(w * 340 / 520)
    return f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 520 340">{inner}</svg>'


def doodle_pipeline():
    svg = canvas(
        1200,
        1010,
        "Exhibit: how a day's doodle is chosen and drawn",
        "The Smarter Doodle",
        AMBER,
        "Code sets the menu. AI makes the call.",
        "Python plans, gathers and checks. Smarter AI resources choose, judge and draw. A person approves new art.",
    )
    left = 50
    right = 610
    card_w = 490
    card_h = 104
    top = 236

    # the two lanes
    for x, y, label, sub, color in (
        (left, 210, "Python and Django", "smarter.apps.doodle", BLUE),
        (right, 374, "Smarter AI resources", "YAML manifests", PURPLE),
    ):
        text(svg, x + 2, y, label, size=15, weight=700, fill=color, spacing="1.4")
        text(svg, x + card_w, y, sub, size=14, fill=INK3, anchor="end", family=MONO)

    steps = [
        # (lane x, y, icon, title, code name, description, refuses)
        (
            left,
            0,
            "calendar",
            "Planner",
            "Celery Beat, every 6 hours",
            "7 days ahead, 12 regions, 19 reviewed themes",
            False,
        ),
        (left, 124, "menu", "Candidates", "editor_request()", "Each region's menu: catalog, holidays, trends", False),
        (
            right,
            150,
            "sparkle",
            "Doodle Editor",
            "smarter_doodle_editor · LLMClient",
            "Picks one item per region, and says why",
            False,
        ),
        (left, 248, "shield", "Checks", "check_decision()", "On the menu? Blocked words, caption, link", True),
        (
            right,
            278,
            "smile",
            "Tone judge",
            "upbeat_occasion_input · Guardrail",
            "A small LLM: is it plainly cheerful?",
            True,
        ),
        (
            right,
            402,
            "brush",
            "Doodle Artist",
            "smarter_doodle_artist · LLMClient",
            "Draws the decorations, in flat SVG shapes",
            False,
        ),
        (left, 432, "funnel", "Sanitizer", "sanitize_svg()", "Allowlist: no scripts, links or url()", True),
    ]
    mids = []
    for i, (x, dy, icon, title, name, description, refuses) in enumerate(steps):
        y = top + dy
        color = BLUE if x == left else PURPLE
        card(svg, x, y, card_w, card_h)
        chip(svg, x + 20, y + 26, icon, color)
        text(svg, x + 90, y + 36, f"{i + 1}  {title}", size=21, weight=700, fill=color)
        text(svg, x + 90, y + 61, name, size=13.5, fill=INK3, family=MONO)
        text(svg, x + 90, y + 86, description, size=16, fill=INK2)
        if refuses:
            pill(svg, x + card_w - 16, y + 18, "can refuse", RED)
        mids.append((x, y))

    # the curves between consecutive steps: across the lanes, or down within one
    for (x1, y1), (x2, y2) in zip(mids, mids[1:]):
        if x1 == x2:
            cx = x1 + card_w / 2
            curve(svg, cx, y1 + card_h, cx, y2)
        elif x1 == left:
            curve(svg, left + card_w, y1 + card_h / 2, right, y2 + card_h / 2)
        else:
            curve(svg, right, y1 + card_h / 2, left + card_w, y2 + card_h / 2)

    # the last row: a person approves, and the sign-in page shows it
    last = top + 564
    last_h = 128
    card(svg, left, last, card_w, last_h)
    chip(svg, left + 20, last + 26, "user", AMBER)
    text(svg, left + 90, last + 36, "8  Superuser", size=21, weight=700, fill=AMBER)
    text(svg, left + 90, last + 61, "Django admin · Preview the week", size=13.5, fill=INK3, family=MONO)
    text(svg, left + 90, last + 86, "Approves new drawings, or rejects them", size=16, fill=INK2)
    text(svg, left + 90, last + 109, "Reviewed catalog art needs no one.", size=16, fill=INK2)
    _, sanitizer_y = mids[-1]
    curve(svg, left + card_w / 2, sanitizer_y + card_h, left + card_w / 2, last)

    card(svg, right, last, card_w, last_h, tint=GREEN)
    text(svg, right + 24, last + 36, "Sign-in page", size=21, weight=700, fill=GREEN)
    text(svg, right + 24, last + 61, "/api/v1/doodles/today/", size=13.5, fill=INK3, family=MONO)
    text(svg, right + 24, last + 86, "Each region's doodle,", size=16, fill=INK2)
    text(svg, right + 24, last + 109, "from local midnight", size=16, fill=INK2)
    artwork_path = os.path.join(REPO_ROOT, "docs/source/_static/case-studies/doodle-culture-day.svg")
    svg.add(artwork(artwork_path, right + card_w - 16 - 172, last + 14, 172))
    curve(svg, left + card_w, last + last_h / 2, right, last + last_h / 2, color=GREEN)

    # the short path: a catalog theme or the default needs no new art
    _, editor_y = mids[2]
    lane = right + card_w + 36
    entry = last + 30
    svg.add(
        f'<path d="M{right + card_w},{editor_y + card_h / 2} C{lane},{editor_y + card_h / 2} {lane},{editor_y + card_h / 2} '
        f'{lane},{editor_y + card_h / 2 + 30} L{lane},{entry - 30} C{lane},{entry} {lane},{entry} {right + card_w},{entry}" '
        f'fill="none" stroke="{GREEN}" stroke-width="2.4" stroke-opacity="0.85" stroke-dasharray="7 6"/>'
    )
    svg.add(f'<circle cx="{right + card_w}" cy="{editor_y + card_h / 2}" r="5" fill="{GREEN}"/>')
    svg.add(f'<circle cx="{right + card_w}" cy="{entry}" r="5" fill="{GREEN}"/>')
    label_y = (editor_y + entry) / 2
    svg.add(
        f'<text transform="translate({lane + 22},{label_y}) rotate(90)" font-family="{FONT}" font-size="14" '
        f'font-weight="600" fill="{GREEN}" text-anchor="middle">catalog or default: shown at once</text>'
    )

    # fail safe, in the space above the right lane
    card(svg, right, top - 26, card_w, 136, accent=RED)
    text(svg, right + 28, top + 8, "Fail safe", size=21, weight=700, fill=RED)
    text(svg, right + 28, top + 36, "Any refusal or failure, at any step, keeps", size=16, fill=INK2)
    text(svg, right + 28, top + 59, "the doodle that the calendar planned. Nothing", size=16, fill=INK2)
    text(svg, right + 28, top + 82, "worse than the plain scene can reach the page.", size=16, fill=INK2)
    source(
        svg,
        "Source: smarter.apps.doodle; smarter/ in smarter-sh/example-manifests. The sign-in page shows Japan's Culture Day.",
    )
    svg.save("doodle-pipeline")


EXHIBITS = [
    org_chart,
    sharing,
    org_as_code,
    access_path,
    access_matrix,
    stanley_architecture,
    stanley_tool_call,
    board_pack_run,
    strategies,
    shadow_ai_responses,
    shadow_ai_proxy,
    shadow_ai_tools,
    doodle_pipeline,
]

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for exhibit in EXHIBITS:
        exhibit()
