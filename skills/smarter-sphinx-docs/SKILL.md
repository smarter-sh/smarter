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
The docs are built and published only from the `main` branch, so a local build
is never part of the work, however fast it gets. Verify instead:

```console
skills/smarter-sphinx-docs/scripts/check-docs.sh docs/source/smarter-resources/smarter-widget.rst docs/source/smarter-resources/widget/*.rst
```

[scripts/check-docs.sh](scripts/check-docs.sh) checks that:

- **Every `:doc:` target and toctree entry exists** as a `.rst` file, relative
  to the referring page (or absolute from `docs/source/` with a leading `/`).
- **Every `literalinclude` and `include` target exists.** The script makes the
  same shallow clone of smarter-sh/example-manifests into
  `docs/source/_example-manifests/` that `conf.py` makes at build time, when
  it's missing, so those includes resolve.
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
| A platform example manifest, shown on a page          | `.. literalinclude:: /_example-manifests/<folder>/<file>.yaml`, from the clone of smarter-sh/example-manifests      |

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
that. Every page must be in a toctree, or Sphinx warns.

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
- **Every example must be true.** Check it against the code and its tests,
  or run it. Manifests must use the field names and casing the Pydantic
  models accept (`domainName`, not `domain_name`).
- **Example manifests are not in this repository.** They live in
  [smarter-sh/example-manifests](https://github.com/smarter-sh/example-manifests)
  (one folder per kind). Show one with
  `.. literalinclude:: /_example-manifests/<folder>/<file>.yaml` (Sphinx's
  source-root-absolute form, which also works in docstrings), followed by a
  link to it: ``From `<folder>/<file>.yaml <https://github.com/smarter-sh/example-manifests/blob/main/<folder>/<file>.yaml>`__ in the :doc:`example manifests repository </smarter-framework/smarter-manifests/example-manifests>`.``
  `conf.py` clones the repository into `docs/source/_example-manifests/`
  (git-ignored). Never include from an app's `data/` folder: there is none.
- Use `double backticks` for literals, field names, and commands, and
  `.. code-block:: console | yaml | python` for examples.
- Keep the docs consistent with the code. When behavior changes, update the
  page in the same change.
- Python API documentation comes from docstrings. Fix a bad API page in the
  docstring, not the `.rst`. See `smarter-docstrings`.

## ADRs

One decision each, in Michael Nygard's format, in `docs/source/adr/NNN-<slug>.rst`
and `adr.rst`'s toctree. Read `adr/000-intro.rst` first.

- **Sections, in order:** Status, Context, Decision, Alternatives Considered,
  Consequences (**Positive:** and **Negative:** lists), Related ADRs.
- **State the rule and the forces behind it**, not how the code came to be.
  Keep them brief: a few sentences per section.
- **Related ADRs** use `:doc:` (`` - :doc:`ADR-001: Django <001-django>` ``), not
  Markdown links, which render as literal text.
- **Never rewrite a decision.** Add an ADR that supersedes it, and set the old
  one's Status to `Superseded by ADR-NNN`.

## Publishing and the site's AWS resources (`terraform/docs/`)

`make sphinx-publish` uploads `docs/build/html` to the `docs.smarter.sh`
bucket and invalidates the CloudFront distribution. The user publishes;
publish yourself only when asked.

The site's resources were made by hand in the AWS console, then adopted into
Terraform in `terraform/docs/` with `import` blocks (`imports.tf`): the ACM
certificate and its validation record, the bucket (ACLs enabled, because
`make sphinx-publish` uploads with `--acl public-read`), its encryption and
policy (only the distribution may read it, through an OAC), the CloudFront
distribution, its `docs-smarter-sh-redirect` function (`redirect.js`, which
redirects the old `/en/latest/...` urls to the root), and the CNAME record. The
configuration describes them as they are, so adopting them changes nothing.
After that first apply, change them only in Terraform.

```console
make terraform-init    # once: the S3 backend (state key smarter/docs/terraform.tfstate)
make terraform-plan    # writes terraform/docs/tfplan: read it before applying
make terraform-apply   # applies exactly that plan
```

Run `terraform -chdir=terraform/docs fmt` and `validate` after editing, and
apply only a plan the user has seen: these are live resources in a shared
account and DNS zone.

### Rules for these stacks

These are what went wrong before, in this and other smarter-sh repositories.

- **Plain `terraform` must work.** `cd terraform/docs && terraform plan` with
  only `AWS_PROFILE` set must not prompt for anything. Terraform signs in as
  the profile's account; never add a required variable that only `make` can
  fill (an `aws_account_id` with no default made a bare `terraform apply`
  stop at a prompt). The account id is needed only for the state bucket's
  name, at `make terraform-init`. An account guard, if any, is an optional
  variable (`default = null`, and
  `allowed_account_ids = var.aws_account_id == null ? null : [var.aws_account_id]`).
- **Read account-wide singletons, never create them.** GitHub's OIDC
  provider (`token.actions.githubusercontent.com`, one per account), the
  `smarter.sh` hosted zone and the state bucket are shared by every
  repository's stack. A stack reads them with a `data` source. Creating one
  fails with `EntityAlreadyExists` (409) in an account that has it, and a
  stack that owns one breaks every other repository when it is destroyed.
  To hand off one that a stack already owns, switch to the `data` source and
  add a `removed { from = ... lifecycle { destroy = false } }` block; the plan
  must say "will no longer be managed by Terraform, but will not be
  destroyed".
- **Look in AWS before writing a stack.** Check with read-only `aws` calls
  whether the resources already exist, as they did here. Adopt them with
  `import` blocks and a configuration that describes them as they are, until
  the plan shows imports and no change to anything live, and no destroys.
  Compute import ids from `data` sources (e.g. a certificate's ARN from
  `data "aws_acm_certificate"`) so that no account id is written into this
  public repository.
- **Plan before you hand it over.** After any change, run `terraform plan`
  yourself with the user's profile (it only reads) and read it: a stack that
  validates can still fail at apply. Never leave a stale `tfplan` behind.
- **When the user's apply fails, fix the stack.** Don't explain why it was
  run "wrong" or offer workarounds; the stack is what must work.

See [references/canonical-sphinx-reference.md](references/canonical-sphinx-reference.md).
