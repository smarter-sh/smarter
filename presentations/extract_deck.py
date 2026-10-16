"""Extract the text of an archived slide deck into a JSON digest.

A deck's ``source/`` folder holds ``deck.json`` (title, slide order and
sections) and one ``slides/<id>.html`` per slide, each a single ``<section>``
whose last child is an ``<aside>`` of speaker notes. This script reads them,
together with the deck's hand-written ``meta.json`` (audience, presenter,
date, ...), and writes a digest of the deck's words with no layout markup.

Usage, from the repository root::

    python3 -I presentations/extract_deck.py \
        presentations/2026-11-executive/source \
        presentations/2026-11-executive/meta.json \
        presentations/2026-11-executive/the-smarter-project.json

It uses only the Python standard library.
"""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

BLOCKS = {"h1", "h2", "h3", "p", "li", "th", "td"}
"""The elements whose text becomes one block of the digest."""

VOID = {"br", "x-icon", "x-shape", "x-connector", "img", "hr"}
"""Elements that hold no text, and that the parser does not push onto its stack."""


class SlideParser(HTMLParser):
    """Collect the text blocks, tables and speaker notes of one slide, in reading order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.blocks = []
        self.cur = None
        self.notes = []
        self.in_aside = False
        self.rows = []
        self.row = None

    def _in_footer(self):
        """Return True inside the slide's pinned footer row (page number, deck name)."""
        return any(tag == "div" and "position:absolute" in style and "bottom:" in style for tag, style in self.stack)

    def handle_starttag(self, tag, attrs):
        """Open a block, a table row or the speaker notes."""
        style = (dict(attrs).get("style") or "").replace(" ", "")
        if tag == "br":
            if self.cur is not None:
                self.cur["text"] += "\n"
            return
        if tag in VOID:
            return
        self.stack.append((tag, style))
        if tag == "aside":
            self.in_aside = True
        elif tag == "tr":
            self.row = []
        elif tag in BLOCKS:
            self.cur = {
                "tag": tag,
                "style": style,
                "text": "",
                "footer": self._in_footer(),
            }

    def handle_endtag(self, tag):
        """Close the current block, table row, table or speaker notes."""
        if tag in VOID:
            return
        while self.stack:
            if self.stack.pop()[0] == tag:
                break
        if tag == "aside":
            self.in_aside = False
        elif tag == "tr":
            self.rows.append(self.row)
            self.row = None
        elif tag == "table":
            self.blocks.append({"tag": "table", "rows": self.rows, "footer": False})
            self.rows = []
        elif tag in BLOCKS and self.cur is not None and self.cur["tag"] == tag:
            if tag in ("th", "td"):
                self.row.append(clean(self.cur["text"]))
            else:
                self.blocks.append(self.cur)
            self.cur = None

    def handle_data(self, data):
        """Append text to the speaker notes or to the open block."""
        if self.in_aside:
            self.notes.append(data)
        elif self.cur is not None:
            self.cur["text"] += data


def clean(text, keep_lines=False):
    """Normalize whitespace.

    :param text: The raw text of a block.
    :param keep_lines: Keep line breaks and indentation, for code.
    :returns: The cleaned text.
    """
    if keep_lines:
        return "\n".join(line.rstrip() for line in text.strip("\n").split("\n"))
    return re.sub(r"\s+", " ", text).strip()


def is_eyebrow(block):
    """Return True for the small upper-case label above a slide's title."""
    return block["tag"] == "p" and "text-transform:uppercase" in block["style"]


def is_code(block):
    """Return True for a multi-line monospace block, such as a manifest or shell commands."""
    return "monospace" in block["style"] and "\n" in block["text"].strip("\n")


def slide_digest(html, footer_label):
    """Return the digest of one slide.

    :param html: The slide's ``<section>`` markup.
    :param footer_label: The deck name in the footer row, which is left out of the digest.
    :returns: A dict with ``eyebrow``, ``title``, ``body``, ``footnote`` and ``notes``.
    """
    parser = SlideParser()
    parser.feed(html)
    out = {"eyebrow": None, "title": None, "body": [], "footnote": None}
    for block in parser.blocks:
        if block["tag"] == "table":
            out["body"].append({"type": "table", "rows": block["rows"]})
            continue
        if block["footer"]:
            parts = [part.strip() for part in clean(block["text"]).split("·")]
            extra = [p for p in parts if p and p != footer_label and not p.isdigit()]
            if extra:
                out["footnote"] = " · ".join(extra)
            continue
        if out["eyebrow"] is None and out["title"] is None and is_eyebrow(block):
            out["eyebrow"] = clean(block["text"])
        elif out["title"] is None and block["tag"] in ("h1", "h2"):
            out["title"] = clean(block["text"])
        elif is_code(block):
            out["body"].append({"type": "code", "text": clean(block["text"], True)})
        else:
            kind = {"h3": "heading", "li": "bullet"}.get(block["tag"], "text")
            out["body"].append({"type": kind, "text": clean(block["text"])})
    out["notes"] = clean("".join(parser.notes))
    return out


def main(source, meta_path, out_path):
    """Write the JSON digest of the deck in ``source``.

    :param source: The deck's ``source/`` folder.
    :param meta_path: The deck's ``meta.json``. Its ``footer`` key names the deck in the footer row.
    :param out_path: Where to write the digest.
    """
    source = Path(source)
    deck = json.loads((source / "deck.json").read_text(encoding="utf-8"))
    meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    starts = {s["start"]: s["description"] for s in deck["sections"].values()}
    slides, section = [], None
    for number, slide_id in enumerate(deck["order"], start=1):
        section = starts.get(slide_id, section)
        html = (source / "slides" / f"{slide_id}.html").read_text(encoding="utf-8")
        slide = {"number": number, "id": slide_id, "section": section}
        digest = slide_digest(html, meta["footer"])
        slide.update({k: v for k, v in digest.items() if v not in (None, [], "")})
        slides.append(slide)
    result = {k: v for k, v in meta.items() if k != "footer"}
    result["title"] = deck["title"]
    result["sections"] = [{"description": s["description"], "starts_at": s["start"]} for s in deck["sections"].values()]
    result["slides"] = slides
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    Path(out_path).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:4])
