#!/usr/bin/env python3
"""List every colon in a blog post's prose, and fail when there are too many.

A colon is a device for emphasis on blog.smarter.sh, used once or twice in a
post. This prints each one with its line number and kind, so each can be
rewritten as two sentences or a lead-in that ends with a period:

- ``join``: joins two clauses ("A QuerySet is lazy: it describes a query").
- ``lead-in``: ends a line, before a list or code ("Save this as app.py:").
- ``label``: labels a list item ("Hello, Smarter: connect and prompt").
- ``heading``: a heading ("Challenge 1: Expensive queries").
- ``table``: a table cell.

Image alt text counts, since screen readers read it aloud. Code blocks, inline
code, link targets, URLs and times (10:30) are skipped.
Works on the Markdown source of a post, or on its WordPress block markup
(``wp.py get <id> --raw <file>``).

usage::

    skills/blog.smarter.sh-blog-post/scripts/check-colons.py ~/desktop/blog-<slug>.md
    skills/blog.smarter.sh-blog-post/scripts/check-colons.py post.html --max 2

Exits 1 when the post has more than ``--max`` colons (default 2).
"""

import argparse
import html
import re
import sys


def markdown_lines(text: str):
    """Yield (line number, kind of block, prose) for each line of Markdown."""
    fence = False
    for number, line in enumerate(text.splitlines(), 1):
        if re.match(r"^\s*```", line):
            fence = not fence
            continue
        if fence:
            continue
        stripped = line.strip()
        if stripped.startswith("#"):
            kind = "heading"
        elif stripped.startswith("|"):
            kind = "table"
        elif re.match(r"^([-*]|\d+\.)\s", stripped):
            kind = "list"
        else:
            kind = "paragraph"
        yield number, kind, stripped


def block_markup_lines(text: str):
    """Yield (line number, kind of block, prose) for WordPress block markup."""
    text = re.sub(r"<!-- wp:syntaxhighlighter.*?<!-- /wp:syntaxhighlighter/code -->", "", text, flags=re.S)
    text = re.sub(r"<pre.*?</pre>", "", text, flags=re.S)
    text = re.sub(r"<code>.*?</code>", "`code`", text, flags=re.S)
    for number, line in enumerate(text.splitlines(), 1):
        if "<h" in line and re.search(r"<h[1-6]", line):
            kind = "heading"
        elif "<td" in line or "<th" in line:
            kind = "table"
        elif "<li" in line:
            kind = "list"
        else:
            kind = "paragraph"
        prose = html.unescape(re.sub(r"<[^>]+>", "", re.sub(r"<!--.*?-->", "", line))).strip()
        yield number, kind, prose
        for alt in re.findall(r'alt="([^"]*)"', line):
            yield number, "alt", html.unescape(alt)


def colons(kind: str, prose: str):
    """Return the kind of each prose colon in one line."""
    prose = re.sub(r"`[^`]*`", "`code`", prose)
    prose = re.sub(r"\]\([^)]*\)", "]", prose)
    prose = re.sub(r"https?://\S+", "URL", prose)
    prose = re.sub(r"\b\d{1,2}:\d{2}\b", "", prose)
    found = []
    for match in re.finditer(r":(?=\s|$)", prose):
        before, after = prose[: match.start()], prose[match.end() :].strip()
        if kind in ("heading", "table"):
            found.append(kind)
        elif not after:
            found.append("lead-in")
        elif kind == "list" and len(before.split()) <= 8 and ":" not in before:
            found.append("label")
        else:
            found.append("join")
    return found, prose


def main() -> int:
    """Print the post's colons and return 1 when there are more than --max."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("post", help="a Markdown post, or a post's block markup (.html)")
    parser.add_argument("--max", type=int, default=2, help="colons allowed in the post (default 2)")
    args = parser.parse_args()

    with open(args.post, encoding="utf-8") as file:
        text = file.read()
    lines = block_markup_lines(text) if args.post.endswith((".html", ".htm")) else markdown_lines(text)
    total = 0
    for number, kind, prose in lines:
        found, cleaned = colons(kind, prose)
        for colon_kind in found:
            total += 1
            print(f"{number:5d}  {colon_kind:8s} {cleaned[:160]}")
    print(f"\n{total} colons in prose (allowed: {args.max})")
    return 1 if total > args.max else 0


if __name__ == "__main__":
    sys.exit(main())
