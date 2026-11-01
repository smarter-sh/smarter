---
name: smarter-pull-requests
description: Use when asked to create, open, write or update a GitHub pull request in the Smarter repository, e.g. "create a PR for these commits", "open the alpha to main pull request", or "write the PR description". Covers which branches (usually alpha into main), the title convention, filling in every section of .github/PULL_REQUEST_TEMPLATE.md from the commits' own messages (type of change, the issues it resolves, changes, testing, screenshots, dependencies, breaking changes), creating it with gh pr create --body-file, the GitHub token in .env, and what never to do (push, merge, or leave the template's placeholders in).
---

# Smarter Pull Requests

Every pull request in this repository uses the template in
[.github/PULL_REQUEST_TEMPLATE.md](../../.github/PULL_REQUEST_TEMPLATE.md). GitHub pre-fills it in
the browser, but `gh pr create --body-file` does not, and many past pull requests went in with the
template's placeholders untouched (`Fixes #[Add issue number here.]`, `_Describe what this Pull
Request does_`). Fill in every section, from the commits themselves.

## Rules

- **Create one only when asked.** A pull request is public, and notifies people. Writing the
  description as text, when that is all the user asked for, is fine.
- **Never push, merge, or change a branch.** The user pushes. `gh pr create` only opens a pull
  request for commits that are already on GitHub. If the head branch is behind the local one,
  or not pushed, say so and stop.
- **Never leave a placeholder.** Each section gets real content, or a plain "None.".
- **The repository is public.** No credentials, account ids, private hostnames, customer data,
  or anyone's personal details in the description (see CLAUDE.md, hard rule 7).
- **No bare `@name`** for anything but a real GitHub login you mean to notify.
- **No CI skip instruction**, not even to describe one (see `smarter-git-commits`): GitHub reads
  it in a pull request's commits, and then runs no checks.

## Branches and title

- The usual pull request is **`alpha` into `main`**: everything merged to `alpha` since the last
  release. Its title follows the past ones, `Alpha - <summary>`, where the summary names the one
  or two most important changes, e.g. `Alpha - fix(csrf): renew the csrftoken cookie, pod log
review rework`. Keep it under about 100 characters.
- A pull request from a feature branch (e.g. `claude/pod-log-review/886-...`) goes into `alpha`,
  and its title is its main commit's subject.
- Check first that there isn't one already: `gh pr list --repo smarter-sh/smarter --head <branch>
--state open`. If there is, update its description (`gh pr edit <number> --body-file ...`)
  rather than open another.

## Gather the material

```bash
git fetch origin main alpha
git status -sb                                         # is the local branch ahead of origin? then stop
git log --oneline origin/main..origin/alpha            # the commits
git log --format='### %h %s%n%n%b' origin/main..origin/alpha   # their full messages
git diff --stat origin/main...origin/alpha | tail -1   # files, additions, deletions
```

Leave out `chore(release): ...` commits (semantic-release's) and merge commits, but read a merge
commit's pull request for the issue it fixed. Read every commit's body: the description is built
from them, never from memory, and a commit you didn't write still has to be described accurately.

For each issue that a commit names (`Fixes #885`, `closes #886`), check its state:
`gh issue view <n> --repo smarter-sh/smarter --json state,title`.

## Fill in the template

Keep the template's headings and order, `# Pull Request Template` included, and drop its
`<!-- ... -->` hints and `_placeholder_` lines.

**Type of Change.** Check (`- [x]`) every box that a commit's type earns, and leave the rest
unchecked:

| Commit type                                       | Box           |
| ------------------------------------------------- | ------------- |
| `feat`                                            | New feature   |
| `fix`                                             | Bug fix       |
| `docs`                                            | Documentation |
| `refactor`, or a commit that mostly moves code    | Refactor      |
| `ci`, `build`, `chore` (not release), `test`, ... | Chore         |

**Resolves.** One `- Fixes #<n>` line per issue. GitHub closes them when the pull request merges
into `main`, the default branch. An issue that is already closed gets a note, e.g. `- Fixes #886
(already closed by #887)`. If no commit resolves an issue, write `- None.`

**Changes.** Start with one or two sentences on what the pull request does as a whole. Then one
`###` subsection per commit, most important first, titled with its subject and short hash, e.g.
`### fix(csrf): renew the csrftoken cookie on console pages (df08a9f)`. In each: the problem, in a
sentence or two, then bullets for what changed, naming files and classes. Condense the commit's
body, don't paste it: a reader should get the gist of each commit in under a minute.

**Testing.** What was run, and where (the container, `scripts/tests`, by hand), per commit, with
the numbers the commits report. Then what still needs testing, e.g. "not checked by hand in a
browser", or a workflow that hasn't run yet. Never claim a test that no commit reports.

**Screenshots.** Only for a visible change to the web console or a page. Otherwise `None: no
visible change.`

**Dependencies.** New or changed packages (Python requirements, npm), new settings, secrets or
environment variables that a deployment needs, and other pull requests that must merge first.
Otherwise `None.`

**Breaking Changes.** Anything that changes for an api client, a manifest, a deployment, a
workflow, a script someone runs by hand (e.g. a moved or renamed script), or the database
(migrations). Otherwise `None.`

End the description with the attribution line from the conversation's system context, if there is
one, e.g. `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## Create it

Write the description to a file in your scratchpad, not inline: a long body with backticks, `$`
and `#` breaks shell quoting.

```bash
export GH_TOKEN=$(grep -E '^GH_TOKEN=' .env | cut -d= -f2- | tr -d '"')   # when gh says 401
gh pr create --repo smarter-sh/smarter --base main --head alpha \
  --title "Alpha - <summary>" --body-file <scratchpad>/pr-body.md
```

Give the user the pull request's url, and say what you left out or couldn't verify.
