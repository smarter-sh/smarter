#!/usr/bin/env python3
"""
Draw the exhibits of the Stackademy case studies, docs/source/_static/case-studies/*.svg.

Usage: case-study-diagrams.py [output folder]   (default: the folder above, from the repository root)

Each exhibit is one function, named after its file. Edit it, run the script, and render the result to check it:
rsvg-convert -w 1500 <svg> -o <scratchpad>/<name>.png. The figures are Stackademy's, from its back office
(smarter-sh/stackademy): keep them true when the data changes.
"""

import os
import sys
from xml.sax.saxutils import escape

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO_ROOT, "docs/source/_static/case-studies")

FONT = "Lato, 'Helvetica Neue', Arial, sans-serif"
MONO = "SFMono-Regular, Menlo, Consolas, monospace"

INK = "#1F2328"
MUTED = "#57606A"
LINE = "#C9D1D9"
HEAD = "#EAF2F9"
BLUE = "#1F5F8B"
GREEN = "#1A7F37"
GREEN_BG = "#DAFBE1"
RED = "#CF222E"
RED_BG = "#FFEBE9"
AMBER = "#9A6700"
AMBER_BG = "#FFF8C5"
GREY_BG = "#F6F8FA"
PURPLE = "#6639BA"
PURPLE_BG = "#FBEFFF"


class Svg:
    """An SVG document, built one element at a time."""

    def __init__(self, width: int, height: int, title: str):
        self.width = width
        self.height = height
        self.parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
            f'height="{height}" role="img" aria-label="{escape(title)}">',
            f"<title>{escape(title)}</title>",
            "<defs>"
            f'<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker>'
            f'<marker id="arrow-red" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker>'
            f'<marker id="arrow-green" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{GREEN}"/></marker>'
            "</defs>",
            f'<rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>',
        ]

    def add(self, element: str) -> None:
        self.parts.append(element)

    def text(self, x, y, s, size=13, weight="normal", fill=INK, anchor="start", family=FONT, italic=False):
        style = ' font-style="italic"' if italic else ""
        self.add(
            f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}"{style}>{escape(s)}</text>'
        )

    def lines(self, x, y, rows, size=12.5, leading=17, fill=INK, anchor="start", weight="normal", family=FONT):
        for i, row in enumerate(rows):
            self.text(x, y + i * leading, row, size=size, fill=fill, anchor=anchor, weight=weight, family=family)

    def rect(self, x, y, w, h, fill="#FFFFFF", stroke=LINE, rx=8, width=1.2, dash=False):
        dashed = ' stroke-dasharray="6 4"' if dash else ""
        self.add(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{width}"{dashed}/>'
        )

    def card(
        self, x, y, w, h, title, rows=(), title_fill=BLUE, head=HEAD, fill="#FFFFFF", stroke=LINE, mono_rows=False
    ):
        """A box with a shaded title bar and rows of text below it."""
        self.rect(x, y, w, h, fill=fill, stroke=stroke)
        self.add(f'<path d="M{x},{y + 30} v-22 a8,8 0 0 1 8,-8 h{w - 16} a8,8 0 0 1 8,8 v22 z" fill="{head}"/>')
        self.add(f'<line x1="{x}" y1="{y + 30}" x2="{x + w}" y2="{y + 30}" stroke="{stroke}" stroke-width="1"/>')
        self.text(x + 12, y + 20, title, size=13.5, weight="bold", fill=title_fill)
        self.lines(x + 12, y + 50, rows, size=12, family=MONO if mono_rows else FONT)

    def arrow(self, x1, y1, x2, y2, color=MUTED, dash=False, width=1.6, label=None, label_dy=-6, marker="arrow"):
        dashed = ' stroke-dasharray="6 4"' if dash else ""
        self.add(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"{dashed} '
            f'marker-end="url(#{marker})"/>'
        )
        if label:
            self.text((x1 + x2) / 2, (y1 + y2) / 2 + label_dy, label, size=11, fill=MUTED, anchor="middle")

    def path(self, d, color=MUTED, width=1.6, dash=False, marker="arrow", fill="none"):
        dashed = ' stroke-dasharray="6 4"' if dash else ""
        end = f' marker-end="url(#{marker})"' if marker else ""
        self.add(f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{width}"{dashed}{end}/>')

    def pill(self, x, y, label, fill, color="#FFFFFF", size=10.5):
        w = round(len(label) * size * 0.58 + 14)
        self.rect(x, y, w, 18, fill=fill, stroke=fill, rx=9, width=1)
        self.text(x + w / 2, y + 13, label, size=size, weight="bold", fill=color, anchor="middle")
        return x + w + 6

    def heading(self, title, subtitle=None):
        self.text(24, 34, title, size=18, weight="bold", fill=INK)
        if subtitle:
            self.text(24, 56, subtitle, size=12.5, fill=MUTED)

    def source(self, s):
        self.text(24, self.height - 14, s, size=10.5, fill=MUTED, italic=True)

    def save(self, name):
        self.parts.append("</svg>")
        path = os.path.join(OUT_DIR, f"{name}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.parts) + "\n")
        print(f"wrote {os.path.relpath(path, REPO_ROOT)}")


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
    svg = Svg(1080, 540, "Exhibit: Stackademy's accounts, people and assistants")
    svg.heading(
        "Stackademy's accounts, people and assistants",
        "Each department is an account under the company. Administrators manage one account; the Head of IT administers every one.",
    )
    svg.card(400, 76, 280, 52, "Smarter platform (root)", [], head=GREY_BG, title_fill=MUTED)
    svg.text(412, 118, "3141-5926-5359 · shares with every account", size=11, fill=MUTED)
    svg.arrow(540, 128, 540, 156)
    svg.card(
        330,
        158,
        420,
        100,
        "Stackademy Corp · 2718-2818-0000",
        [
            "Vera Jaramillo, CEO · administrator; member of every department",
            "Odette Hartigan, CFO · member",
            "Atlas, the Board Pack · quarterly board pack orchestration",
        ],
    )
    svg.pill(612, 162, "members only", "#57606A", size=9.5)
    xs = [24, 234, 444, 654, 864]
    for (name, number, admin, member, assistant, shares), x in zip(DEPARTMENTS, xs):
        svg.path(f"M540,258 V300 H{x + 96} V326", marker="arrow")
        fill = PURPLE_BG if shares else "#FFFFFF"
        svg.card(x, 328, 192, 176, name, [], fill=fill, head=PURPLE_BG if shares else HEAD)
        svg.text(x + 12, 376, number, size=11.5, family=MONO, fill=MUTED)
        svg.lines(x + 12, 396, [admin.split(", ")[0], admin.split(", ")[1] + " · admin"], size=11.5)
        if member:
            svg.lines(x + 12, 434, [member.split(", ")[0] + " · member"], size=11.5)
        label = "shares with all of Stackademy" if shares else "members only"
        svg.pill(x + 12, 446, label, PURPLE if shares else "#57606A", size=9)
        svg.text(
            x + 12,
            488,
            f"Assistant: {assistant}" if assistant != "PII guardrail" else "Shares: PII guardrail",
            size=11.5,
            fill=BLUE,
            weight="bold",
        )
    svg.source("Source: smarter-sh/stackademy, org/accounts/ and org/users/. All people are fictional.")
    svg.save("org-chart")


def sharing():
    svg = Svg(1000, 430, "Exhibit: what a member of Stackademy HR may read")
    svg.heading(
        "What a member of Stackademy HR may read",
        "A member reads an account's resources if their own account is that account, or descends from its share scope.",
    )
    nodes = {
        "root": (390, 80, "Smarter platform", "share scope: itself, the root", True),
        "corp": (390, 170, "Stackademy Corp", "share scope: itself, its members", False),
        "it": (90, 270, "Stackademy IT", "share scope: Stackademy Corp", True),
        "hr": (390, 270, "Stackademy HR", "share scope: itself", True),
        "acct": (690, 270, "Stackademy Accounting", "share scope: itself", False),
    }
    for key, (x, y, title, note, readable) in nodes.items():
        fill = GREEN_BG if readable else GREY_BG
        stroke = GREEN if readable else LINE
        svg.rect(x, y, 230, 62, fill=fill, stroke=stroke, width=1.6 if readable else 1.2)
        svg.text(x + 14, y + 26, title, size=14, weight="bold", fill=GREEN if readable else MUTED)
        svg.text(x + 14, y + 46, note, size=11.5, fill=MUTED)
    svg.arrow(505, 142, 505, 168)
    svg.path("M505,232 V252 H205 V268")
    svg.arrow(505, 232, 505, 268)
    svg.path("M505,252 H805 V268")
    svg.pill(632, 92, "readable: shares with everyone", GREEN, size=9.5)
    svg.pill(110, 340, "readable: shares with Corp's subtree", GREEN, size=9.5)
    svg.pill(410, 340, "readable: their own account", GREEN, size=9.5)
    svg.pill(710, 340, "not readable: shares with no one", RED, size=9.5)
    svg.pill(632, 182, "not readable: its members only", RED, size=9.5)
    svg.lines(
        24,
        386,
        [
            "So Harper, HR's assistant, can use IT's PII guardrail and the platform's built-in resources, but not Accounting's "
            "connection, and Accounting can't use HR's.",
        ],
        size=12.5,
    )
    svg.source("Source: ADR-036, smarter.apps.account.hierarchy.readable_account_ids().")
    svg.save("sharing")


def org_as_code():
    svg = Svg(1080, 470, "Exhibit: the organization, declared in a git repository")
    svg.heading(
        "The organization, declared in a git repository",
        "One repository holds the accounts, the people and every department's resources. owners.yaml says who applies each folder.",
    )
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
    svg.card(24, 78, 370, 352, "smarter-sh/stackademy")
    for i, (path, note) in enumerate(listing):
        y = 132 + i * 26
        indent = 22 if path.startswith("  ") else 0
        svg.text(38 + indent, y, path.strip(), size=12, family=MONO)
        svg.text(236, y, note, size=12, fill=MUTED)
    svg.card(
        440,
        176,
        196,
        138,
        "load_from_github",
        [
            "run by initialize_platform:",
            "applies every manifest,",
            "in dependency order,",
            "as its folder's owner,",
            "in its owner's account",
        ],
    )
    svg.arrow(396, 236, 438, 236)
    rows = [
        ("departments/hr/", "Avery Ivanova", "Stackademy HR"),
        ("departments/hr/connections/", "Tomas Hartigan", "Stackademy HR"),
        ("departments/accounting/", "Odette Hartigan", "Stackademy Accounting"),
        ("departments/it/", "Tomas Hartigan", "Stackademy IT"),
        ("departments/executive/", "Vera Jaramillo", "Stackademy Corp"),
        ("org/accounts/, org/users/", "the platform admin", "creates the organization"),
    ]
    svg.text(676, 92, "Folder", size=12, weight="bold", fill=MUTED)
    svg.text(898, 92, "Applied as · in", size=12, weight="bold", fill=MUTED)
    for i, (folder, owner, account) in enumerate(rows):
        y = 104 + i * 54
        svg.rect(666, y, 398, 44, fill=GREY_BG if i % 2 else "#FFFFFF")
        svg.text(676, y + 27, folder, size=11.5, family=MONO)
        svg.text(898, y + 18, owner, size=12, weight="bold")
        svg.text(898, y + 35, account, size=11.5, fill=MUTED)
        svg.path(f"M638,245 C652,245 652,{y + 22} 664,{y + 22}", width=1.2)
    svg.source(
        "Source: smarter-sh/stackademy; smarter.apps.account.repository_owners. owners.yaml is generated from the back office."
    )
    svg.save("org-as-code")


# ---------------------------------------------------------------------------------------------------------------
# Department assistants
# ---------------------------------------------------------------------------------------------------------------
def access_path():
    svg = Svg(1080, 370, "Exhibit: how HR's assistant reaches HR's records, and nothing else")
    svg.heading(
        "How HR's assistant reaches HR's records, and nothing else",
        "Every link in the chain lives in Stackademy HR's account, where only HR's members may use it.",
    )
    svg.rect(16, 74, 1048, 172, fill="#FFFFFF", stroke=BLUE, dash=True)
    svg.pill(28, 82, "Account: Stackademy HR · members only", BLUE, size=10)
    boxes = [
        ("Harper", ["LLMClient", "the HR assistant", "owner: HR Director"]),
        ("3 SqlPlugins", ["headcount", "employee record", "requisitions"]),
        ("SqlConnection", ["stackademy_hr_db", "+ Secret: its password", "owner: Head of IT"]),
        ("Database user", ["stackademy_hr", "read-only, SELECT", "on HR's tables only"]),
        ("Tables", ["departments, employees", "compensation, PTO", "job requisitions"]),
    ]
    x = 34
    for i, (title, rows) in enumerate(boxes):
        svg.card(x, 118, 182, 110, title, rows, fill=GREY_BG if i == 4 else "#FFFFFF")
        if i < 4:
            svg.arrow(x + 184, 173, x + 206, 173)
        x += 206
    svg.card(
        34,
        268,
        300,
        64,
        "PII guardrail · Stackademy IT",
        ["shared with all of Stackademy, read by Harper"],
        head=PURPLE_BG,
    )
    svg.arrow(184, 268, 184, 230, color=PURPLE, marker="arrow")
    svg.card(
        372,
        268,
        330,
        64,
        "Budget · stackademy_hr_ai",
        ["$150 a month, $1,800 in all; blocks when spent"],
        head=AMBER_BG,
    )
    svg.path("M537,268 V256 H110 V230", color=AMBER, dash=True, marker=None)
    svg.path("M537,256 H330 V230", color=AMBER, dash=True, marker=None)
    svg.card(
        740, 268, 324, 64, "The database's own grants", ["Accounting's user is refused compensation"], head=GREEN_BG
    )
    svg.source("Source: smarter-sh/stackademy, departments/hr/ and scripts/backoffice-grants.txt.")
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
    svg = Svg(1060, 500, "Exhibit: what each department's database user may read")
    svg.heading(
        "What each department's database user may read",
        "Table-level grants, generated with the data and checked on every load: only HR's user reads compensation.",
    )
    x0, y0, cw, rh = 230, 110, 112, 44
    for j, col in enumerate(ACCESS_COLUMNS):
        svg.text(x0 + j * cw + cw / 2, y0 - 12, col, size=12.5, weight="bold", fill=MUTED, anchor="middle")
    for i, (user, cells) in enumerate(ACCESS_ROWS):
        y = y0 + i * rh
        svg.text(24, y + 27, user, size=12.5, family=MONO)
        for j, cell in enumerate(cells):
            fill = {"full": GREEN, "part": "#8CD49A", "": GREY_BG}[cell]
            svg.rect(x0 + j * cw + 4, y + 6, cw - 8, rh - 12, fill=fill, stroke="#FFFFFF", rx=5)
            if cell:
                svg.text(
                    x0 + j * cw + cw / 2,
                    y + 27,
                    "all" if cell == "full" else "some",
                    size=11,
                    fill="#FFFFFF" if cell == "full" else INK,
                    anchor="middle",
                    weight="bold",
                )
    svg.rect(x0 + 2 * cw + 1, y0 - 2, cw - 2, rh * 6 + 4, fill="none", stroke=RED, width=2)
    svg.text(
        x0 + 2 * cw + cw / 2, y0 + rh * 6 + 22, "salaries: HR only", size=11.5, fill=RED, anchor="middle", weight="bold"
    )
    svg.lines(
        24,
        444,
        [
            "Catalogue: courses, cohorts, modules, lessons. Directory: departments, employees. HR records: compensation, time off, requisitions.",
            "Admissions: students, enrollments, payments, contracts. Finance: ledger, budgets, invoices. Production: assets, tasks. Board views: totals only.",
        ],
        size=11.5,
        fill=MUTED,
    )
    svg.source("Source: smarter-sh/stackademy, GRANTS in scripts/generate_backoffice.py.")
    svg.save("access-matrix")


# ---------------------------------------------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------------------------------------------
def board_pack_run():
    svg = Svg(1080, 540, "Exhibit: a run of the quarterly board pack")
    svg.heading(
        "A run of the quarterly board pack",
        "Four departments answer independently, each from its own records and on its own budget; Atlas writes the page.",
    )
    svg.card(24, 196, 170, 100, "Vera Jaramillo", ["CEO, starts a run:", "Prepare the board pack", "for Q4 2025."])
    svg.arrow(196, 246, 226, 246, label="POST")
    svg.card(
        228,
        176,
        200,
        140,
        "Orchestrator",
        ["stackademy_quarterly_", "board_pack", "strategy: parallel", "Stackademy Corp"],
        head=PURPLE_BG,
    )
    svg.text(240, 334, "checks: the runner may use", size=11, fill=RED)
    svg.text(240, 349, "every harness, or 403", size=11, fill=RED)
    lanes = [
        ("Harper", "Stackademy HR", "stackademy_hr", "headcount, hiring"),
        ("Ledger", "Stackademy Accounting", "stackademy_accounting", "results, budgets, invoices"),
        ("Reel", "Course Content", "stackademy_content", "courses in production"),
        ("Ada", "Admissions", "stackademy_admissions", "enrollments, contracts"),
    ]
    for i, (name, account, user, subject) in enumerate(lanes):
        y = 82 + i * 98
        svg.path(f"M430,246 C470,246 470,{y + 40} 506,{y + 40}")
        svg.rect(508, y, 300, 82, fill="#FFFFFF")
        svg.text(522, y + 24, f"{name} · {account}", size=13, weight="bold", fill=BLUE)
        svg.text(522, y + 44, f"reads as {user}", size=11.5, family=MONO, fill=MUTED)
        svg.text(522, y + 64, subject, size=11.5)
        svg.path(f"M810,{y + 40} C850,{y + 40} 850,246 878,246")
    svg.card(
        880,
        176,
        180,
        140,
        "Atlas",
        ["summarizer", "Stackademy Corp", "views of totals", "checks the figures"],
        head=GREEN_BG,
    )
    svg.arrow(970, 318, 970, 366)
    svg.rect(880, 368, 180, 56, fill=GREEN_BG, stroke=GREEN)
    svg.text(970, 392, "The board pack", size=13.5, weight="bold", fill=GREEN, anchor="middle")
    svg.text(970, 410, "one page, about 30 s", size=11.5, fill=MUTED, anchor="middle")
    svg.lines(
        24,
        488,
        [
            "Each step is an ordinary prompt of its LLMClient, run as that LLMClient's owner: its tools, guardrail and budget apply.",
            "The CFO, who isn't a member of HR, is refused: an orchestrator is never a way into an account its runner doesn't belong to.",
        ],
        size=12,
        fill=MUTED,
    )
    svg.source(
        "Source: ADR-037; smarter.apps.orchestrator.runtime; departments/executive/orchestrators/ in smarter-sh/stackademy."
    )
    svg.save("board-pack-run")


def strategies():
    svg = Svg(1080, 400, "Exhibit: the four orchestration strategies that Smarter runs")
    svg.heading(
        "The four orchestration strategies that Smarter runs",
        "A summarizer, when there is one, answers last after any of them. Voting and debate are declared, but not yet run.",
    )

    def node(x, y, label, fill="#FFFFFF", stroke=LINE, w=74):
        svg.rect(x, y, w, 30, fill=fill, stroke=stroke, rx=15)
        svg.text(x + w / 2, y + 20, label, size=11.5, anchor="middle", weight="bold")

    panels = [
        ("Sequential", "each sees the answers before it"),
        ("Parallel", "each sees only the objective"),
        ("Router", "a router picks one assistant"),
        ("Supervisor", "a planner asks, one at a time"),
    ]
    for k, (title, note) in enumerate(panels):
        x = 24 + k * 264
        svg.rect(x, 76, 248, 290, fill=GREY_BG)
        svg.text(x + 14, 100, title, size=14, weight="bold", fill=BLUE)
        svg.text(x + 14, 118, note, size=11.5, fill=MUTED)
    # sequential
    x = 24
    for i, label in enumerate(["A", "B", "C"]):
        node(x + 87, 140 + i * 56, label)
        if i < 2:
            svg.arrow(x + 124, 170 + i * 56, x + 124, 194 + i * 56)
    svg.arrow(x + 124, 282, x + 124, 300)
    node(x + 77, 302, "summary", fill=GREEN_BG, stroke=GREEN, w=94)
    # parallel
    x = 288
    node(x + 87, 140, "objective", fill=PURPLE_BG, stroke=PURPLE, w=74)
    for i, label in enumerate(["A", "B", "C"]):
        nx = x + 20 + i * 74
        node(nx, 222, label, w=60)
        svg.arrow(x + 124, 170, nx + 30, 220)
        svg.arrow(nx + 30, 252, x + 124, 300)
    node(x + 77, 302, "summary", fill=GREEN_BG, stroke=GREEN, w=94)
    # router
    x = 552
    node(x + 87, 140, "router", fill=PURPLE_BG, stroke=PURPLE)
    for i, label in enumerate(["A", "B", "C"]):
        nx = x + 20 + i * 74
        node(nx, 222, label, fill=GREEN_BG if label == "B" else "#FFFFFF", stroke=GREEN if label == "B" else LINE, w=60)
    svg.arrow(x + 124, 170, x + 124, 220, color=GREEN, marker="arrow-green")
    svg.path(f"M{x + 110},170 L{x + 55},218", dash=True, marker=None)
    svg.path(f"M{x + 138},170 L{x + 193},218", dash=True, marker=None)
    svg.text(x + 124, 290, '{"harness": "B"}', size=11, family=MONO, fill=MUTED, anchor="middle")
    # supervisor
    x = 816
    node(x + 87, 140, "planner", fill=PURPLE_BG, stroke=PURPLE)
    node(x + 20, 236, "A")
    node(x + 154, 236, "B")
    svg.path(f"M{x + 100},170 C{x + 70},190 {x + 60},210 {x + 57},234", marker="arrow")
    svg.path(f"M{x + 40},236 C{x + 40},200 {x + 70},180 {x + 87},160", dash=True, marker="arrow")
    svg.path(f"M{x + 148},170 C{x + 178},190 {x + 190},210 {x + 191},234", marker="arrow")
    svg.text(x + 124, 300, '{"next": "A", "message": ...}', size=10.5, family=MONO, fill=MUTED, anchor="middle")
    svg.text(x + 124, 318, '{"done": true, "result": ...}', size=10.5, family=MONO, fill=MUTED, anchor="middle")
    svg.source("Source: ADR-037, items 7 and 8; smarter.apps.orchestrator.runtime, STRATEGY_RUNNERS.")
    svg.save("strategies")


# ---------------------------------------------------------------------------------------------------------------
# Accuracy
# ---------------------------------------------------------------------------------------------------------------
QUARTERS = [
    # quarter, revenue, expenses, net (database-computed, fiscal 2025)
    ("Q1", 885864.11, 978630.16, -92766.05),
    ("Q2", 1264186.17, 1029137.84, 235048.33),
    ("Q3", 1170382.42, 1054216.79, 116165.63),
    ("Q4", 1081466.17, 1091474.24, -10008.07),
]


def money(value):
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"


def quarterly_results():
    svg = Svg(1000, 494, "Exhibit: Stackademy's results by quarter, fiscal 2025")
    svg.heading(
        "Stackademy's results by quarter, fiscal 2025",
        "Revenue and expenses as the database totals them. The faint cap on Q4 is the $4,620 that an early view wrongly counted.",
    )
    x0, y0, plot_h, top = 110, 400, 300, 1300000.0
    for tick in (0, 250000, 500000, 750000, 1000000, 1250000):
        y = y0 - tick / top * plot_h
        svg.add(f'<line x1="{x0 - 6}" y1="{y}" x2="{960}" y2="{y}" stroke="#EAEEF2" stroke-width="1"/>')
        svg.text(x0 - 12, y + 4, f"${tick / 1000000:.2f}M" if tick else "$0", size=11, fill=MUTED, anchor="end")
    for i, (quarter, revenue, expenses, net) in enumerate(QUARTERS):
        gx = x0 + 30 + i * 210
        for k, (value, color) in enumerate(((revenue, BLUE), (expenses, "#8C959F"))):
            h = value / top * plot_h
            svg.add(f'<rect x="{gx + k * 62}" y="{y0 - h}" width="56" height="{h}" fill="{color}" rx="3"/>')
            svg.text(gx + k * 62 + 28, y0 - h - 8, f"${value / 1000:,.0f}k", size=11, fill=INK, anchor="middle")
        if quarter == "Q4":
            extra = 4620 / top * plot_h
            h = revenue / top * plot_h
            svg.add(
                f'<rect x="{gx}" y="{y0 - h - extra - 1}" width="56" height="{max(extra, 3)}" fill="{RED}" opacity="0.55"/>'
            )
            svg.text(gx - 8, y0 - h + 14, "+$4,620 counted", size=10.5, fill=RED, anchor="end")
            svg.text(gx - 8, y0 - h + 28, "in error, now fixed", size=10.5, fill=RED, anchor="end")
        svg.text(gx + 59, y0 + 22, quarter, size=13, weight="bold", anchor="middle")
        svg.text(
            gx + 59,
            y0 + 40,
            f"net {money(net)}",
            size=11.5,
            fill=GREEN if net > 0 else RED,
            anchor="middle",
            weight="bold",
        )
    svg.rect(740, 70, 14, 14, fill=BLUE, stroke=BLUE, rx=2)
    svg.text(760, 82, "Revenue", size=12)
    svg.rect(840, 70, 14, 14, fill="#8C959F", stroke="#8C959F", rx=2)
    svg.text(860, 82, "Expenses", size=12)
    svg.source(
        "Source: Stackademy's back office, board_income_statement, fiscal 2025. Fictional data, generated with a fixed seed."
    )
    svg.save("quarterly-results")


ERRORS = [
    (
        "Arithmetic by the model",
        "Atlas added Q2's expense accounts itself",
        "$1,033,137.84 for $1,029,137.84 · off by $4,000",
        "The database totals every figure; the prompt forbids adding up",
    ),
    (
        "A truncated result",
        "The budget tool returned at most 25 rows, so a quarter was cut short",
        "Admissions over budget by $20,548.92, not $21,659.57",
        "Totals per department computed in SQL, one row each",
    ),
    (
        "A period boundary",
        "Views grouped by quarter without the year: Dec. 2024 prepaid tuition counted as Q4 2025",
        "Q4 revenue $1,086,086.17, not $1,081,466.17 · +$4,620",
        "Fiscal-year filter, a reconciliation check on load, a regression test",
    ),
    (
        "A confident correction",
        "The summarizer trusted the flawed view over the department's right figure",
        "Every Q4 board pack overstated net income by $4,620",
        "One set of totals, from one source, reconciled to the ledger",
    ),
]


def errors_and_controls():
    svg = Svg(1080, 520, "Exhibit: four errors, and the control that now prevents each")
    svg.heading(
        "Four errors, and the control that now prevents each",
        "Each was found by comparing an assistant's figure with the database, before any reached a real reader.",
    )
    cols = [(24, 210, "Kind of error"), (242, 330, "What happened"), (580, 230, "Effect"), (818, 240, "Control")]
    for x, w, title in cols:
        svg.text(x + 8, 92, title, size=12.5, weight="bold", fill=MUTED)
    for i, (kind, what, effect, control) in enumerate(ERRORS):
        y = 104 + i * 98
        svg.rect(24, y, 1032, 88, fill=GREY_BG if i % 2 else "#FFFFFF")
        svg.text(32, y + 30, kind, size=13, weight="bold", fill=RED)
        wrap(svg, 250, y + 26, what, 44)
        wrap(svg, 588, y + 26, effect, 30, fill=RED)
        svg.arrow(800, y + 44, 814, y + 44, color=GREEN, marker="arrow-green")
        wrap(svg, 826, y + 26, control, 31, fill=GREEN, weight="bold")
    svg.source(
        "Source: the Stackademy back office's verification, November 2026; smarter-sh/stackademy commit history."
    )
    svg.save("errors-and-controls")


def wrap(svg, x, y, s, width, fill=INK, weight="normal", size=12):
    words = s.split()
    rows, row = [], ""
    for word in words:
        if len(row) + len(word) + 1 > width and row:
            rows.append(row)
            row = word
        else:
            row = f"{row} {word}".strip()
    rows.append(row)
    svg.lines(x, y, rows, size=size, fill=fill, weight=weight)


# ---------------------------------------------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------------------------------------------
ADMIN_ROWS = [
    ("Platform superuser", ["every account", "every account"]),
    ("Staff user", ["every account, member or not", "only accounts they belong to"]),
    ("Account administrator", ["no such role", "their one account"]),
    ("Customer admin made superuser", ["every customer's account", "demoted: their own accounts"]),
    ("Api key for another user", ["any user, any account", "users of their own account"]),
]


def admin_rule():
    svg = Svg(1060, 430, "Exhibit: who may administer an account, before and after the review")
    svg.heading(
        "Who may administer an account, before and after the review",
        "One rule, user_administers_account(), now decides it for every broker, api key and console control.",
    )
    svg.text(32, 96, "Role or path", size=12.5, weight="bold", fill=MUTED)
    svg.text(380, 96, "Before", size=12.5, weight="bold", fill=RED)
    svg.text(720, 96, "After", size=12.5, weight="bold", fill=GREEN)
    for i, (role, (before, after)) in enumerate(ADMIN_ROWS):
        y = 108 + i * 56
        svg.rect(24, y, 1012, 48, fill=GREY_BG if i % 2 else "#FFFFFF")
        svg.text(36, y + 29, role, size=13, weight="bold")
        unchanged = before == after
        before_bg, before_ink = (GREY_BG, MUTED) if unchanged else (RED_BG, RED)
        after_bg, after_ink = (GREY_BG, MUTED) if unchanged else (GREEN_BG, GREEN)
        svg.rect(372, y + 9, 320, 30, fill=before_bg, stroke=before_bg, rx=6)
        svg.text(384, y + 29, before, size=12.5, fill=before_ink)
        svg.rect(712, y + 9, 316, 30, fill=after_bg, stroke=after_bg, rx=6)
        svg.text(724, y + 29, after + (" (unchanged)" if unchanged else ""), size=12.5, fill=after_ink)
    svg.lines(
        24,
        398,
        [
            "Before the review, a staff user of any customer account could add anyone, themselves included, to any other account as its administrator."
        ],
        size=12,
        fill=MUTED,
    )
    svg.source(
        "Source: ADR-036 item 10; smarter.apps.account.models.user_profile.user_administers_account(); migration 0017."
    )
    svg.save("admin-rule")


SEVERITY = {
    "Critical": (RED, "#FFFFFF"),
    "High": (RED_BG, RED),
    "Medium": (AMBER_BG, AMBER),
    "Low": (GREY_BG, MUTED),
}

# (area, [(id, severity, label, in a release?)]); keep in step with the register in governance-review.rst.
FINDINGS = [
    (
        "Who administers what",
        [
            ("F1", "Critical", "Staff administered every account", False),
            ("F2", "High", "Customer admins made superusers", True),
            ("F3", "High", "Api keys for other accounts' users", True),
            ("F4", "Medium", "Platform admin added to new accounts", None),
        ],
    ),
    (
        "Where resources resolve",
        [
            ("F5", "Low", "Manifests applied in any account", None),
            ("F6", "Low", "Plugins found via the admin's profile", None),
            ("F7", "Low", "Guardrails resolved by applier", None),
        ],
    ),
    (
        "Credentials in logs",
        [
            ("F8", "Medium", "Session keys, usernames in server log", True),
            ("F9", "Medium", "CSRF token in the browser's log", True),
        ],
    ),
    (
        "Reliability and hygiene",
        [
            ("F10", "Low", "Stale caches of roles, default account", None),
            ("F11", "Low", "Manifest pages answered 500", None),
            ("F12", "Low", "Tests left 9 superusers behind", None),
        ],
    ),
]


def findings_register():
    svg = Svg(1080, 470, "Exhibit: the review's twelve findings, by area and severity")
    svg.heading(
        "The review's twelve findings, by area and severity",
        "Each was fixed in the release that found it. A solid marker means the flaw was in an earlier release.",
    )
    for col, (area, findings) in enumerate(FINDINGS):
        x = 24 + col * 262
        svg.rect(x, 76, 248, 34, fill=HEAD, stroke=LINE, rx=6)
        svg.text(x + 124, 98, area, size=13, weight="bold", fill=BLUE, anchor="middle")
        for row, (fid, severity, label, released) in enumerate(findings):
            y = 122 + row * 70
            svg.rect(x, y, 248, 60, fill="#FFFFFF", stroke=LINE, rx=6)
            fill, ink = SEVERITY[severity]
            svg.pill(x + 10, y + 9, f"{fid} · {severity}", fill, color=ink, size=10)
            if released is not None:
                marker_fill = INK if released else "#FFFFFF"
                svg.add(
                    f'<circle cx="{x + 232}" cy="{y + 18}" r="6" fill="{marker_fill}" stroke="{INK}" stroke-width="1.4"/>'
                )
            svg.text(x + 12, y + 47, label, size=12)
    svg.add(f'<circle cx="34" cy="420" r="6" fill="{INK}" stroke="{INK}" stroke-width="1.4"/>')
    svg.text(46, 424, "in an earlier release", size=11.5, fill=MUTED)
    svg.add(f'<circle cx="196" cy="420" r="6" fill="#FFFFFF" stroke="{INK}" stroke-width="1.4"/>')
    svg.text(208, 424, "found before any release", size=11.5, fill=MUTED)
    svg.text(380, 424, "No marker: surfaced by loading the organization.", size=11.5, fill=MUTED)
    svg.source("Source: the commits of Smarter 0.46.0 that each finding cites; smarter-console 1.1.12.")
    svg.save("findings-register")


# ---------------------------------------------------------------------------------------------------------------
# Release incident
# ---------------------------------------------------------------------------------------------------------------
def release_pipeline():
    svg = Svg(1080, 470, "Exhibit: the release of 0.46.0, and where it stopped")
    svg.heading(
        "The release of 0.46.0, and where it stopped",
        "The release job published the version, then failed in its last step; everything that ships it was skipped.",
    )
    steps = [
        ("Merge #1005", "to main", GREEN_BG, GREEN),
        ("Analyze", "commits → 0.46.0", GREEN_BG, GREEN),
        ("Tag v0.46.0", "and changelog commit", GREEN_BG, GREEN),
        ("GitHub release", "published", GREEN_BG, GREEN),
        ("Success step", "#1003 is not an issue", RED_BG, RED),
    ]
    for i, (title, note, fill, stroke) in enumerate(steps):
        x = 24 + i * 210
        svg.rect(x, 90, 186, 70, fill=fill, stroke=stroke, width=1.6)
        svg.text(x + 93, 118, title, size=13.5, weight="bold", fill=stroke, anchor="middle")
        svg.text(x + 93, 140, note, size=11.5, fill=MUTED, anchor="middle")
        if i < 4:
            svg.arrow(x + 188, 125, x + 208, 125)
    svg.text(24, 196, "release job: failed", size=12.5, weight="bold", fill=RED)
    skipped = [
        ("Docker image", "never built"),
        ("Helm chart", "never published"),
        ("Deploy to prod", "never ran"),
        ("Notify", "never sent"),
    ]
    for i, (title, note) in enumerate(skipped):
        x = 24 + i * 210
        svg.rect(x, 210, 186, 60, fill=GREY_BG, stroke=LINE, dash=True)
        svg.text(x + 93, 236, title, size=13, weight="bold", fill=MUTED, anchor="middle")
        svg.text(x + 93, 256, note, size=11.5, fill=MUTED, anchor="middle")
    svg.path("M942,162 C942,240 860,240 846,240", color=RED, marker="arrow-red")
    svg.text(
        24,
        312,
        "Re-runs 2 and 3: main is ahead of the run (it has the release commit), so nothing is released and everything is skipped again.",
        size=12.5,
    )
    svg.rect(24, 330, 1032, 104, fill=GREEN_BG, stroke=GREEN)
    svg.text(40, 356, "Recovery and fix", size=13.5, weight="bold", fill=GREEN)
    svg.lines(
        40,
        378,
        [
            "Recovery: start Build by hand with tag v0.46.0, which builds the image and chart of the release that already exists.",
            "Fix: run semantic-release 25, whose GitHub plugin skips references that resolve to no issue. Proven on the next",
            "release, 0.46.0-alpha.18, whose success step completed.",
        ],
        size=12.5,
    )
    svg.source("Source: GitHub Actions run 43651270572 of smarter-sh/smarter; .github/workflows/build.yml.")
    svg.save("release-pipeline")


EXHIBITS = [
    org_chart,
    sharing,
    org_as_code,
    access_path,
    access_matrix,
    board_pack_run,
    strategies,
    quarterly_results,
    errors_and_controls,
    admin_rule,
    findings_register,
    release_pipeline,
]

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    for exhibit in EXHIBITS:
        exhibit()
