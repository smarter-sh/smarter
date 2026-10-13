#!/usr/bin/env python3
"""Check a Smarter micro course design without building the Sphinx docs.

usage, from the repository root:
  python3 skills/smarter-course-design/scripts/check-course.py <slug> [<slug> ...]
  python3 skills/smarter-course-design/scripts/check-course.py --all

<slug> is the course's file name under
docs/source/smarter-instructors/example-courses/micro-courses/, e.g. docker.

Checks, for each course:

1. the files exist: <slug>.rst, and <slug>/ with bootcamp.rst, two-week.rst,
   four-week.rst, source-code.txt and further-study.txt;
2. each plan has the standard sections, includes source-code.txt and
   further-study.txt, and has the right number of graded assignments (3, 3, 4)
   and two capstones;
3. every rubric adds up: 20 points for an assignment, 100 for a capstone;
4. every https://github.com/smarter-sh/<repo>/(blob|tree)/main/<path> link
   names a file or folder on main (origin/main, else main) in the local clone
   of <repo>: this repository, or a sibling folder ../<repo>. A path that is
   only in the working tree is a warning: the link breaks until it is merged.
   Every commit link must name a commit in that clone. Run git fetch first;
5. the course is listed in micro-courses.rst (table and toctree).

:doc: links are checked by skills/smarter-sphinx-docs/scripts/check-docs.sh.
Exits 1 if anything fails.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
COURSES = ROOT / "docs/source/smarter-instructors/example-courses/micro-courses"
PLANS = {"bootcamp.rst": 3, "two-week.rst": 3, "four-week.rst": 4}
SECTIONS = [
    "At a Glance",
    "Learning Objectives",
    "Technical Prerequisites",
    "Schedule",
    "* in the Source Code",
    "Graded Assignments",
    "Capstone Projects",
    "Recommended Texts",
    "Further Study",
]
GITHUB = re.compile(r"https://github\.com/smarter-sh/([\w.-]+)/(blob|tree|commit)/([^\s>`]+)")

errors: list[str] = []
warnings: list[str] = []
unchecked: set[str] = set()


def fail(msg: str) -> None:
    errors.append(msg)
    print(f"FAIL  {msg}")


def git(local: Path, *args: str) -> bool:
    """Run a quiet git command in a clone, and return whether it succeeded."""
    return subprocess.run(["git", "-C", str(local), *args], capture_output=True).returncode == 0


def main_ref(local: Path) -> str:
    """Return origin/main if the clone has it, else main."""
    return "origin/main" if git(local, "rev-parse", "--verify", "-q", "origin/main") else "main"


def repo_dir(repo: str) -> Path | None:
    """Return the local clone of a smarter-sh repository, or None."""
    if repo == "smarter":
        return ROOT
    sibling = ROOT.parent / repo
    return sibling if (sibling / ".git").exists() else None


def subsections(text: str) -> list[tuple[str, str]]:
    """Split a page into (title, body) pairs at its ~~~ subsections."""
    parts = re.split(r"\n([^\n]+)\n~{3,}\n", "\n" + text)
    return list(zip(parts[1::2], parts[2::2]))


def rubric_points(body: str) -> list[int]:
    """Return the Pts column of the first rubric table in a subsection."""
    lines = body.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"\s+\* - Criterion\s*$", line):
            points = []
            for row in lines[i + 1 :]:
                if row and not row.startswith(" "):
                    break
                m = re.match(r"\s+- (\d+)\s*$", row)
                if m:
                    points.append(int(m.group(1)))
            return points
    return []


def check_plan(path: Path, assignments: int) -> None:
    text = path.read_text()
    name = path.relative_to(COURSES)
    for section in SECTIONS:
        pattern = re.escape(section).replace(r"\*", r"[\w ]+")
        if not re.search(rf"^{pattern}\n-{{3,}}$", text, re.M):
            fail(f"{name}: missing section '{section}'")
    for include in ("source-code.txt", "further-study.txt"):
        if f".. include:: {include}" not in text:
            fail(f"{name}: does not include {include}")
    subs = subsections(text)
    found = [t for t, _ in subs if re.match(r"Assignment \d+:", t)]
    capstones = [t for t, _ in subs if re.match(r"Capstone [AB]:", t)]
    if len(found) != assignments:
        fail(f"{name}: {len(found)} graded assignments, expected {assignments}")
    if len(capstones) != 2:
        fail(f"{name}: {len(capstones)} capstones, expected 2")
    for title, body in subs:
        expected = 20 if title.startswith("Assignment") else 100 if title.startswith("Capstone") else None
        if expected is None:
            continue
        total = sum(rubric_points(body))
        if total != expected:
            fail(f"{name}: '{title}' rubric totals {total}, expected {expected}")


def check_links(path: Path) -> None:
    name = path.relative_to(COURSES)
    for repo, kind, rest in GITHUB.findall(path.read_text()):
        local = repo_dir(repo)
        if local is None:
            unchecked.add(repo)
            continue
        if kind == "commit":
            sha = rest.split("#")[0]
            if not git(local, "cat-file", "-e", f"{sha}^{{commit}}"):
                fail(f"{name}: {repo} has no commit {sha}")
            continue
        branch, _, rel = rest.partition("/")
        rel = rel.split("#")[0].rstrip("/")
        if branch != "main":
            fail(f"{name}: link to branch '{branch}', use main: {repo}/{rest}")
        elif rel and not git(local, "cat-file", "-e", f"{main_ref(local)}:{rel}"):
            if (local / rel).exists():
                warnings.append(rel)
                print(f"WARN  {name}: {repo}/{rel} is not on main yet; the link breaks until it is merged")
            else:
                fail(f"{name}: {repo} has no {rel} on main")


def check_course(slug: str) -> None:
    overview = COURSES / f"{slug}.rst"
    folder = COURSES / slug
    for p in [overview, folder / "source-code.txt", folder / "further-study.txt"] + [folder / f for f in PLANS]:
        if not p.exists():
            fail(f"missing {p.relative_to(ROOT)}")
    if errors and not folder.exists():
        return
    for plan, n in PLANS.items():
        if (folder / plan).exists():
            check_plan(folder / plan, n)
    for p in [overview, *sorted(folder.glob("*"))]:
        if p.exists():
            check_links(p)
    index = (COURSES.parent / "micro-courses.rst").read_text()
    if f":doc:`micro-courses/{slug}`" not in index:
        fail(f"micro-courses.rst: no table row for {slug}")
    if not re.search(rf"^   micro-courses/{re.escape(slug)}$", index, re.M):
        fail(f"micro-courses.rst: {slug} is not in the toctree")


def main() -> int:
    if not COURSES.is_dir():
        print("Run this from the repository root.", file=sys.stderr)
        return 1
    args = sys.argv[1:]
    if args == ["--all"]:
        args = sorted(p.name for p in COURSES.iterdir() if p.is_dir())
    if not args:
        print(__doc__)
        return 1
    for slug in args:
        before = len(errors)
        check_course(slug)
        if len(errors) == before:
            print(f"ok    {slug}")
    for repo in sorted(unchecked):
        print(f"note  links to smarter-sh/{repo} not checked: clone it next to this repository")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
