---
name: blog.smarter.sh-release-announcement
description: Use when asked to write a release announcement, release notes post, or blog post for a Smarter version (e.g. "write the blog post for v0.16"), for blog.smarter.sh. Covers gathering the material from changelogs/CHANGELOG.md (latest/stable) or changelogs/CHANGELOG-vX.Y.md (older releases) and the full commit bodies, the post's structure (theme, summary table, one section per feature with a real manifest, fixes, upgrading, what's next), the writing style, public-repo hygiene, and what to check before handing it over.
---

# blog.smarter.sh Release Announcement

A release post on [blog.smarter.sh](https://blog.smarter.sh) tells developers
and platform operators what a Smarter release lets them do, and what they must
do to upgrade. It is a Markdown file the user pastes into the blog. It is not
part of the docs, and it is not committed to the repository.

[references/example-v0.16.md](references/example-v0.16.md) is a complete post
that the user accepted. Read it before writing, and match its structure and
tone.

## 1. Gather the material

The changelog alone is not enough. Its entries are one-line commit subjects.
The commit bodies explain what each feature is, why it exists, its security
rules, its limits and its upgrade steps, and that is what the post is made of.

1. Find the release's changelog. The latest/stable release is in
   `changelogs/CHANGELOG.md`. Older releases are archived as
   `changelogs/CHANGELOG-v0.XX.md` (e.g. `CHANGELOG-v0.19.md`), one file per
   minor version. Unless the user says otherwise,
   **everything in that file is part of the release**, including alpha and
   patch entries. The same commit often appears under several versions. Count
   it once.

2. Read the full commit bodies of every commit linked in the changelog. They are
   in `git log --format=%B <commit>`. The commit body is usually a few
   paragraphs, with a "Before using this" or migration paragraph at the end.
   The commit subject is usually a one-line summary of the feature, and is
   already in the changelog. When a commit has no body, read its diff
   (`git show <commit>`), and also check the `ci:` and `chore:` commits
   between the release tags (`git log --oneline vA..vB`), which the changelog
   leaves out but which often explain the change.

3. Print every linked commit's full message, once each, oldest first:

   ```bash
   # latest/stable
   skills/blog.smarter.sh-release-announcement/scripts/release-sources.sh changelogs/CHANGELOG.md
   # an older release
   skills/blog.smarter.sh-release-announcement/scripts/release-sources.sh changelogs/CHANGELOG-vX.Y.md
   ```

4. For each new resource kind, find its built-in or example manifests, usually
   in `smarter/smarter/apps/<app>/data/`, and use one of them, trimmed, in the
   post. Don't write a manifest from memory: field names change, and a wrong
   one in a post is a support ticket.
5. Find each feature's docs page under `docs/source/smarter-resources/` and
   link it as
   `https://docs.smarter.sh/en/latest/smarter-resources/<page>.html`.
6. If the user gives the previous release's post as a guide, fetch it. Keep
   its voice, and improve on it rather than copying it.

## 2. Structure

In this order:

1. **Title:** `# vX.Y Release: <the release's theme in a few words>`, then a
   date line.
2. **Theme, in one or two short paragraphs.** Say how this release differs
   from the last one, e.g. "v0.15 was about describing an AI application.
   v0.16 is about running one."
3. **A summary table** of the headline features: resource and what it does,
   one sentence each. Readers who stop here should still know what shipped.
4. **One `##` section per headline feature**, largest first. Each one:
   - opens with the problem it solves, in the reader's terms (idle GPUs that
     cost money, provider keys in every developer's hands, budgets that nothing
     enforced);
   - shows a real, trimmed manifest, and the `smarter apply` / `deploy`
     commands or SDK code a user would run;
   - lists its capabilities as short bullets with a bold lead-in;
   - has a `### Security` subsection if the commit describes security rules;
   - ends with `📖 [<Kind> documentation](<docs url>)`.
5. **Behavior changes users will notice** (e.g. delete now refuses while
   dependents exist) get their own short section. Don't put them in the list
   of fixes.
6. **Web console improvements**, then **Fixes and operations**: one bullet
   per change, saying what was wrong and what happens now.
7. **Upgrading:** new permissions, settings and environment variables,
   migration resets for anyone who ran the alphas, manual steps that the
   release does not do for you, and what `initialize_platform` now loads.
   Pull these from the commit bodies, which usually have a "Before using
   this" or migration paragraph.
8. **What's next**, then links to the changelog on GitHub
   (`https://github.com/smarter-sh/smarter/blob/main/changelogs/CHANGELOG.md`
   for latest/stable, `.../CHANGELOG-vX.Y.md` once it is archived),
   the docs and the repository.

Separate the major sections with `---`.

## 3. Style

- Write for developers who use or are evaluating Smarter, not for Smarter's
  own contributors. Leave out internal detail such as class names,
  serializers, Celery task names, ESLint counts by package, and refactors with
  no user-visible effect.
- Use plain words and short sentences. Prefer "Smarter adds a server, then
  removes it when it's empty" to marketing adjectives.
- Be specific: numbers (24 built-in models, 13 list pages, HTTP 402), names
  of providers and models, exact settings.
- Be honest about the past. "Earlier releases had budget models, but nothing
  enforced them" is more credible than pretending a feature is all new.
- Use headings, not bold lines, as section labels. The user's editor flags
  bold-as-heading (MD036) and lists without blank lines around them (MD032).
- No emoji except the 📖 docs link.

## 4. Public-repo hygiene

The post is published, and this skill lives in a public repository. Commit
bodies sometimes name production databases, namespaces, tenants or
hostnames. Never copy them into the post. Write `<your-smarter>` for the
host, and describe a manual step generically ("convert the column by hand")
instead of naming a customer's database.

## 5. Before handing it over

- Every manifest field in the post appears in a real manifest in the repo.
- Every claim traces to a commit body or the changelog. If you add something
  that doesn't, such as the "What's next" roadmap, which is usually a guess,
  tell the user so they can correct it.
- Every docs link's `.rst` file exists under `docs/source/`. You can't check
  that the published URL works, so say so.
- Save the post to `~/desktop/blog-vX.Y.md` (e.g. `~/desktop/blog-v0.17.md`),
  unless the user names another place. Never save it inside the repository
  or only in your scratchpad.
- In your reply, list what to review before publishing: guessed content,
  unverified links, anything you left out on purpose, and the exact date.
