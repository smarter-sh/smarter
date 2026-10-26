---
name: smarter-code-quality
description: Use before finishing any Smarter code change, to lint and format Python and React with the repository's pre-commit hooks (black, flake8, isort, autoflake, bandit, codespell, pyupgrade, pydocstringformatter, Prettier, ESLint). Explains which tools are authoritative and how to run them on changed files under zsh.
---

# Smarter Code Quality

`.pre-commit-config.yaml` at the repository root is the authoritative standard.
If a hook passes, the code meets the standard. If it fails, fix the code. Never
bypass a hook (`--no-verify`, `SKIP=`, blanket `# noqa`) to make a change pass.

## What the hooks enforce

**Python**

| Hook                 | Configuration                       | Notes                                                                          |
| -------------------- | ----------------------------------- | ------------------------------------------------------------------------------ |
| black                | `pyproject.toml`, line length 120   | Formatter. Let it reformat.                                                    |
| isort                | `pyproject.toml`, `profile = black` | Import order.                                                                  |
| autoflake            | `--remove-all-unused-imports`       | **No-op**: `args` drops `--in-place`. Remove unused imports yourself.          |
| flake8               | `.flake8`                           | Selects **only C101** (coding magic comment). It is not a general style check. |
| bandit               | `-ll`                               | Medium or high severity security findings fail.                                |
| pyupgrade            |                                     | Modern syntax for Python 3.14.                                                 |
| pydocstringformatter |                                     | Normalizes docstring layout.                                                   |
| codespell            | `codespell.txt` ignore list         | Also runs on docs and React. Add real project words to `codespell.txt`.        |

autoflake's hook puts `--in-place` in its default `args`, which the `args`
here replace, so it prints a diff, changes nothing and passes. flake8 (C101
only) doesn't catch unused imports either.

**ruff is not configured.** A repository-wide `ruff check` reports a large
backlog (unused imports, E402) that is not the project's standard. Don't report
ruff output as lint debt, and don't "fix" it.

**React (`smarter/react`)**

| Hook             | Runs                                                          |
| ---------------- | ------------------------------------------------------------- |
| `react-prettier` | the workspace's Prettier, `npx --no-install prettier --write` |
| `react-eslint`   | the workspace's ESLint flat config, `--max-warnings=0`        |

These are `language: system` hooks that use `npx --no-install`. They need
`smarter/react/node_modules`, so run `make react-install` first. See
`smarter-react-testing` for the ESLint rules.

**Everything**: trailing whitespace, end-of-file newline, YAML, JSON, TOML and
XML syntax, merge conflict markers, private keys, AWS credentials, debug
statements, and commitlint on commit messages.

## How to run

From the repository root, with the virtual environment active:

```console
source venv/bin/activate
git diff --name-only | xargs pre-commit run --files
git ls-files --others --exclude-standard | xargs pre-commit run --files   # new files
```

- Use `xargs`. Under zsh, `pre-commit run --files $FILES` passes one argument
  rather than a list, so pre-commit reports "no files to check" and checks
  nothing.
- Hooks that modify files (black, isort, autoflake, Prettier, end-of-file-fixer)
  fail the first run, then pass. Run the hooks twice, and read the diff of what
  they changed.
- `make pre-commit-run` runs every hook on every file. It is slower, and it
  touches files you didn't change.
- **`--all-files` (and so `make pre-commit-run`) skips untracked files**: it
  uses `git ls-files`. Check a new file with `--files`.
- **The prettier hook can leave a `node_modules/.cache/` folder** in the
  repository root. It is git-ignored. Don't pass it to the hooks.
- `make pre-commit-init`, and so `make init`, runs `pre-commit autoupdate`,
  which edits `.pre-commit-config.yaml`. That change is a commit of its own
  (`build:`): don't fold it into an unrelated one.
- For React alone: `make react-lint` (Prettier check, ESLint, `tsc`), as CI's
  `react` job does.

## Principles

- Match the surrounding code: its naming, comment density, logging style
  (`logger = logging.getSmarterLogger(__name__, any_switches=[...])`), and
  error types.
- Fix the cause of a finding. Suppress a finding only with a narrow, commented
  directive that explains why (for example `# pylint: disable=broad-except`
  around code that must not raise).
- Don't reformat code you didn't otherwise change. It buries the real diff.
