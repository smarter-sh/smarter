---
name: smarter-git-commits
description: Use whenever the user asks you to "write a git commit" (or a commit message, or the git add) in the smarter-chat repo (@smarter.sh/ui-chat), or in ../smarter or a platform integration while working on it. Covers the never-execute rule, authorship, the multiple -m command format, conventional-commit types and scopes, and how thorough the body must be.
---

# Smarter Git Commits

## The rule: write, never execute

"Write a git commit", in any wording or tone, means **output the command as
text**. It never means run it.

- Never execute `git commit`, `git add`, `git reset`, `git restore --staged`,
  `git push`, `git stash`, or any other git command that writes. The user stages
  and commits themselves.
- Read-only git commands (`git status`, `git diff`, `git log`) are fine for
  working out what changed.
- Never run `npm publish` or `make release` either. Releases are CI's
  (`doc/adr/013-ci-cd.md`).
- Don't volunteer commit messages. Write one only when asked.

## Authorship

You are the author. Lawrence McDaniel is the co-author.

- `--author="Claude <noreply@anthropic.com>"`
- The last `-m` is `Co-authored-by: Lawrence McDaniel <lpm0073@gmail.com>`.

## Command format

Exactly one `git commit` command in one code block:

```console
git commit --author="Claude <noreply@anthropic.com>" \
  -m "<type>(<scope>): <subject>" \
  -m "<body paragraph>" \
  -m "<body paragraph or bullet list>" \
  -m "Co-authored-by: Lawrence McDaniel <lpm0073@gmail.com>"
```

- Use one `-m` per paragraph. git joins them with blank lines.
- No heredoc, no `-F`, and no `git add` in the same block.
- Avoid backticks, `$` and `!` inside the double-quoted messages. The shell
  would otherwise run or expand them. The user's shell is zsh, where a `!` in
  double quotes is history expansion: `"... !important ..."` aborts the whole
  command with `zsh: event not found: important`, and the commit isn't made.
  Reword instead (e.g. "important declarations"); escaping `!` with a backslash
  leaves the backslash in the message.
- When the user asks for the `git add` too, write it as a separate code block.
  List the paths explicitly. Leave out files that don't belong to the change
  (for example, untracked work for another task).

## Subject line

`<type>(<scope>): <subject>`, checked by commitlint
(`@commitlint/config-conventional` + `@commitlint/config-angular`) and read by
semantic-release (`release.config.cjs`) to version the release (`doc/adr/014-versioning.md`).

- **type:** `feat`, `fix`, `test`, `docs`, `refactor`, `perf`, `style`,
  `build`, `ci`, or `chore`.
  - `feat` is a user-visible capability (a prop, an embed option, an export), and `fix` is a bug fix. Both trigger a release, which is
    published to npm and reaches every site on `@0` through jsDelivr. `perf`
    is a patch release too. `docs`, `test`, `style`, `refactor`, `chore` and
    `ci` release nothing.
  - A change to the public api that breaks users (a renamed prop, option,
    cookie, class name or export: see `doc/adr/014-versioning.md`) needs a
    `BREAKING CHANGE:` paragraph, its own `-m`, which makes a major release.
    Don't write one without the user's agreement.
  - Use `chore` for data-only or housekeeping changes, such as example manifests
    or model defaults. Don't use `feat` for them.
  - Work that the user asked for as a list of bugs is `fix`, even when it adds a
    small capability along the way. Use `feat` only when the user framed the
    work as a new feature.
- **scope:** the area of the repository that the change centers on, in lower case:
  `chat` (the SmarterChat component), `console`, `docs-dialog`, `api`
  (`src/lib/api.ts`), `contract`, `messages`, `styles`, `embed`, `build`
  (`vite.config.ts`), `storybook`, `readme`, `tests`, `skills`, `adr`, `deps`,
  `ci`, ... You can omit it for changes that span the whole repository. In
  `../smarter`, the scope is the platform's Django app, as its own copy of
  this skill says.
- **subject:** imperative mood, lower case, no trailing period.
- **length:** the whole header, type and scope included, must be **72
  characters or fewer** (config-angular's `header-max-length`). This is a hard
  limit: the commitlint pre-commit hook rejects a 73-character header, and the
  user has to come back for a new command. Don't count by eye, because that has
  produced 73-character headers more than once. Measure it, and aim for 70 or
  fewer to leave a margin:

  ```console
  printf %s "refactor(account): run add_plugin_examples, create_stackademy at init" | wc -c
  ```

  If it's too long, shorten the subject, for example by naming the area
  instead of listing every command or file. Don't drop the scope just to save
  characters.

- `chore(release): ...` belongs to semantic-release. Never write it yourself.

## Body

Write the body for a reader with no context, such as a reviewer six months from
now. A terse four-bullet body has been rejected as "too brief".

- Start with the problem or motivation: what was wrong or missing, and how it
  showed up.
- Then go area by area, with a short heading paragraph per area (for example
  `Embed script (src/embed/options.ts):`), followed by one
  bullet per change. Each bullet says what changed and why, especially for
  non-obvious choices and alternatives that were rejected.
- Name files, classes, settings, and commands precisely.
- Cover the tests: what's new, and what they prove, with the counts you saw
  (e.g. "all 266 unit tests pass; check:dist passes"). Say what you didn't
  verify, e.g. a release workflow that hasn't run yet.
- End with the current status, such as known skips, pre-existing failures, or
  follow-ups.
- Use good grammar and plain sentences. Add links where they help.

## Before writing

1. Run `git status` and `git diff --stat` (and `git diff` on anything unclear),
   so the message describes the actual working tree, not your memory of it.
2. Ask, or check, which files belong to the commit, if that's ambiguous.
3. Measure the header with `wc -c`, as described in "Subject line", before you
   hand the command over.
4. Start the response with a one-line `Written for:` audience note, because a
   commit message is written for other readers.

See [references/canonical-git-commit.md](references/canonical-git-commit.md) for
a complete, real example. It is a commit of the platform, but the format is the
same here.

A change that spans several repositories (e.g. a contract field in
`../smarter`'s models, its use here, and its docs page in
`../smarter/docs/source/`) gets one commit command per repository. If the
change was made in the platform's workspace clone
(`../smarter/smarter/react/packages/smarter-chat`), say so: its commit is run
from that directory, never from `../smarter`.
