#!/usr/bin/env python3
"""
Convert a blog.smarter.sh post from Markdown to WordPress block markup.

The published posts are stored as Gutenberg core blocks (heading, paragraph, list,
table, quote, separator) plus the SyntaxHighlighter plugin's code block, so a post
converted here edits in the block editor like the posts that were written there.
Only the Markdown that the release announcements use is supported: ATX headings,
paragraphs, ``-`` and ``1.`` lists (one level), pipe tables, ``>`` quotes, ``---``,
fenced code, ``![alt](url "caption")`` images on a line of their own, and inline
bold, italics, code and links.

Usage: md2wp.py post.md > post.html
"""

import html
import json
import re
import sys

FENCE = re.compile(r"^```\s*([\w+-]*)\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^(\s*)(?:[-*]|(\d+)\.)\s+(.*)$")
IMAGE = re.compile(r'^!\[([^\]]*)\]\((\S+?)(?:\s+"([^"]*)")?\)\s*$')


def inline(text: str) -> str:
    """Render one line's inline Markdown as HTML, with code spans left verbatim."""
    spans: list[str] = []

    def stash(match: re.Match) -> str:
        spans.append(f"<code>{html.escape(match.group(1), quote=False)}</code>")
        return f"\x00{len(spans) - 1}\x00"

    text = html.escape(re.sub(r"`([^`]+)`", stash, text), quote=False)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)\s]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)


def block(name: str, body: str, attrs: dict | None = None) -> str:
    """Wrap rendered HTML in a Gutenberg block comment."""
    opener = f"<!-- wp:{name} {json.dumps(attrs)} -->" if attrs else f"<!-- wp:{name} -->"
    return f"{opener}\n{body}\n<!-- /wp:{name} -->"


def paragraph(text: str) -> str:
    return block("paragraph", f"<p>{inline(text)}</p>")


def table(rows: list[str]) -> str:
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], [r for r in cells[1:] if not all(re.fullmatch(r":?-+:?", c) for c in r)]
    thead = "".join(f"<th>{inline(c)}</th>" for c in head)
    tbody = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
    figure = (
        '<figure class="wp-block-table"><table class="has-fixed-layout">'
        f"<thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></figure>"
    )
    return block("table", figure)


def image(alt: str, url: str, caption: str | None) -> str:
    """An image block, linked to the full-size file, with an optional caption."""
    src = html.escape(url)
    figcaption = f'<figcaption class="wp-element-caption">{inline(caption)}</figcaption>' if caption else ""
    figure = (
        f'<figure class="wp-block-image"><a href="{src}"><img src="{src}" alt="{html.escape(alt)}"/></a>'
        f"{figcaption}</figure>"
    )
    return block("image", figure, {"linkDestination": "media"})


def bullets(items: list[str], ordered: bool) -> str:
    tag = "ol" if ordered else "ul"
    lis = "\n\n".join(block("list-item", f"<li>{inline(i)}</li>") for i in items)
    return block("list", f'<{tag} class="wp-block-list">{lis}</{tag}>', {"ordered": True} if ordered else None)


def convert(markdown: str) -> str:
    lines = markdown.splitlines()
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        fence = FENCE.match(line)
        if fence:
            code = []
            i += 1
            while i < len(lines) and not FENCE.match(lines[i]):
                code.append(lines[i])
                i += 1
            i += 1
            # SyntaxHighlighter's brush names. An unknown one renders as plain, curly-quoted text.
            language = {
                "console": "bash",
                "sh": "bash",
                "shell": "bash",
                "zsh": "bash",
                "js": "jscript",
                "javascript": "jscript",
                "ts": "jscript",
                "typescript": "jscript",
                "json": "jscript",
                "toml": "plain",
                "ini": "plain",
                "text": "plain",
                "": "plain",
            }.get(fence.group(1), fence.group(1))
            pre = f'<pre class="wp-block-syntaxhighlighter-code">{html.escape(chr(10).join(code), quote=False)}</pre>'
            blocks.append(block("syntaxhighlighter/code", pre, {"language": language} if language else None))
            continue
        picture = IMAGE.match(line)
        if picture:
            blocks.append(image(*picture.groups()))
            i += 1
            continue
        heading = HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            body = f'<h{level} class="wp-block-heading">{inline(heading.group(2).strip())}</h{level}>'
            blocks.append(block("heading", body, {"level": level} if level != 2 else None))
            i += 1
            continue
        if re.fullmatch(r"\s*(-{3,}|\*{3,})\s*", line):
            blocks.append(block("separator", '<hr class="wp-block-separator has-alpha-channel-opacity"/>'))
            i += 1
            continue
        if line.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(lines[i])
                i += 1
            blocks.append(table(rows))
            continue
        if line.startswith(">"):
            quoted = []
            while i < len(lines) and lines[i].startswith(">"):
                quoted.append(lines[i][1:].strip())
                i += 1
            paras = [p.strip() for p in "\n".join(quoted).split("\n\n")]
            inner = "\n\n".join(paragraph(" ".join(p.split())) for p in paras if p)
            blocks.append(block("quote", f'<blockquote class="wp-block-quote">{inner}</blockquote>'))
            continue
        item = BULLET.match(line)
        if item:
            ordered = item.group(2) is not None
            items: list[str] = []
            while i < len(lines):
                item = BULLET.match(lines[i])
                if item:
                    items.append(item.group(3).strip())
                elif lines[i].startswith(("  ", "\t")) and lines[i].strip() and items:
                    items[-1] += " " + lines[i].strip()
                else:
                    break
                i += 1
            blocks.append(bullets(items, ordered))
            continue
        text = [line.strip()]
        i += 1
        while (
            i < len(lines)
            and lines[i].strip()
            and not (
                FENCE.match(lines[i])
                or IMAGE.match(lines[i])
                or HEADING.match(lines[i])
                or BULLET.match(lines[i])
                or lines[i].lstrip().startswith(("|", ">"))
            )
        ):
            text.append(lines[i].strip())
            i += 1
        blocks.append(paragraph(" ".join(text)))
    return "\n\n".join(blocks) + "\n"


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        sys.stdout.write(convert(f.read()))
