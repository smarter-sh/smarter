---
name: smarter-sphinx-docs
description: Use when adding or editing Smarter's Sphinx documentation in docs/source (published to docs.smarter.sh), e.g. a page for a new SAM resource, its autodoc technical reference, or prose about a new feature. Covers page structure, headings, toctrees, autodoc pages, the evergreen-prose rule, and how to verify without running the 20-minute build.
---

# Smarter Sphinx Documentation

The docs live in `docs/source/` and are built by Sphinx with the Read the Docs
theme. They use autodoc, napoleon, `sphinx_autodoc_typehints`,
`sphinxcontrib_django`, `sphinxcontrib.autodoc_pydantic`, and `sphinx_design`
(see `docs/source/conf.py`). They're published to https://docs.smarter.sh.

## Don't build the docs to verify

A full build (`make sphinx-docs`) takes about **20 minutes**. Don't run it.
Verify instead:

```console
skills/smarter-sphinx-docs/scripts/check-docs.sh docs/source/smarter-resources/smarter-widget.rst docs/source/smarter-resources/widget/*.rst
```

[scripts/check-docs.sh](scripts/check-docs.sh) checks that:

- **Every `:doc:` target and toctree entry exists** as a `.rst` file, relative
  to the referring page (or absolute from `docs/source/` with a leading `/`).
- **Every autodoc target imports**, with Django set up, in the smarter-app
  container.

To check only the autodoc targets of every page on the host, without the
containers, run `python docs/source/lint.py` from the repository root, with the
virtual environment active. It sets up Django as `conf.py` does, and exits 1 if
any target fails to import.

Then read the page yourself to check that it's well-formed: heading underlines
at least as long as the title, a blank line after each directive, and code-block
content indented consistently.

The user builds the docs themselves.

## Where things go

| Content                                               | Location                                                                                                            |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| A resource kind (user guide plus technical reference) | `docs/source/smarter-resources/smarter-<kind>.rst`, listed in the toctree of `docs/source/smarter-resources.rst`    |
| Its autodoc pages                                     | `docs/source/smarter-resources/<app>/*.rst` (admin, api, models, serializers, tasks, views, `manifest/models`, ...) |
| Platform features (web console, deployment, ...)      | `docs/source/smarter-platform/`                                                                                     |
| Framework internals (brokers, manifests, CLI, API)    | `docs/source/smarter-framework/`                                                                                    |
| Architecture decisions                                | `docs/source/adr/`                                                                                                  |
| Example manifests served as files                     | `docs/source/example-manifests/`                                                                                    |

## Resource page structure

Copy `smarter-resources/smarter-guardrail.rst` (complete) or
`smarter-resources/smarter-custom-domain.rst` (compact):

```rst
Smarter <Kind>
==============

Overview
--------
What it is, who uses it, and why: plain language, for a reader new to Smarter.

How It Works
------------
The lifecycle, managed with the smarter CLI (console code-block) and the web console.

The Manifest
------------
A complete, valid yaml code-block, followed by notes on spec fields and the read-only status.

<Topic sections>
----------------
For example: Verification, Strategies, Built-in <Kinds>, Security Notes.

Technical Reference
-------------------

.. toctree::
   :maxdepth: 1

   <app>/models
   <app>/manifest
   ...
```

Headings: `=` for the page title, `-` for sections, then `~` and `^` below
that.

Autodoc pages are short:

```rst
Pydantic Models
================

.. automodule:: smarter.apps.guardrail.manifest.models.guardrail.spec
    :members:
    :undoc-members:
    :show-inheritance:
```

## Writing rules

- **Evergreen prose, no "what's new" sections.** Don't add "New in 0.18" or
  release-specific sections. Weave a new feature into the existing text where its
  topic belongs (security, teams, infrastructure, resources). Related features
  don't need to be presented together. The dashboard's What's New widget, not
  the docs, carries the release framing.
- Write for a reader new to Smarter, and perhaps new to Django. Define terms on
  first use, and link to the resource pages with `:doc:`.
- Manifests in docs must be valid: the field names and casing the Pydantic
  models accept (`domainName`, not `domain_name`).
- Use `double backticks` for literals, field names, and commands, and
  `.. code-block:: console | yaml | python` for examples.
- Keep the docs consistent with the code. When behavior changes, update the
  page in the same change.
- Python API documentation comes from docstrings. Fix a bad API page in the
  docstring, not the `.rst`. See `smarter-docstrings`.

See [references/canonical-sphinx-reference.md](references/canonical-sphinx-reference.md).
