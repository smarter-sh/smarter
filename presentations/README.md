# Presentations

The slide decks that present The Smarter Project to people outside the
project, kept as the record of how Smarter describes itself to each audience.

| Folder                                          | Deck                      | Audience                                                                                         | Length                |
| ----------------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------ | --------------------- |
| [2026-11-executive](2026-11-executive/)         | The Smarter Project       | Senior decision makers in large organizations and educational institutions, mostly non-technical | 17 slides, 30 minutes |
| [2026-11-it-leadership](2026-11-it-leadership/) | Smarter for IT Leadership | IT leadership: the CIO and the heads of custom programming, infrastructure and technical support | 16 slides, 30 minutes |

Both decks were written in November 2026 and are presented by Lawrence McDaniel.

## What each folder holds

- **`<deck>.json`**, the digest: the deck's words with no layout. Every slide
  has its number, id, section, eyebrow (the small label above the title),
  title, body blocks and speaker notes. Body blocks have a `type` of
  `heading`, `text`, `bullet`, `code` or `table`. Read this file to see what
  the deck says, or use it as the source for a new deck, page or post.
- **`meta.json`**: who the deck is for, its purpose, presenter, date and
  length. Written by hand, and merged into the digest.
- **`source/`**: the deck itself. `deck.json` holds its title, slide order,
  sections and typefaces, and `slides/<id>.html` holds one slide, with its
  speaker notes in the closing `<aside>`. The slides use a small, inline-styled
  HTML subset on a 1920×1080 canvas, so they can be republished as a deck and
  exported to PowerPoint, Keynote or PDF without being redrawn.

## Regenerating a digest

After a change to a deck's `source/` or `meta.json`, regenerate its digest from
the repository root:

```console
python3 -I presentations/extract_deck.py \
  presentations/2026-11-executive/source \
  presentations/2026-11-executive/meta.json \
  presentations/2026-11-executive/the-smarter-project.json
```

The script uses only the Python standard library.

## Adding a deck

Make a folder named `<yyyy-mm>-<audience>`, put the deck's files in
`source/`, write its `meta.json`, generate its digest, and add a row to the
table above.
