---
name: smarter-code-quality
description: Use before finishing any Smarter code change, to lint and format Python, Markdown, YAML and JSON with the repository's pre-commit hooks (black, flake8, isort, autoflake, bandit, mypy, pyright and complexity on new findings, codespell, pyupgrade, pydocstringformatter, Prettier). Explains which tools are authoritative and how to run them on changed files under zsh.
---

# Smarter Code Quality

`.pre-commit-config.yaml` at the repository root is the authoritative standard.
If a hook passes, the code meets the standard. If it fails, fix the code. Never
bypass a hook (`--no-verify`, `SKIP=`, blanket `# noqa`) to make a change pass.

## What the hooks enforce

**Python**

| Hook                      | Configuration                                 | Notes                                                                                  |
| ------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------- |
| black                     | `pyproject.toml`, line length 120             | Formatter. Let it reformat.                                                            |
| isort                     | `pyproject.toml`, `profile = black`           | Import order.                                                                          |
| autoflake                 | `--in-place`, `--remove-all-unused-imports`   | Removes unused imports, except in `__init__.py` files and migrations.                  |
| flake8                    | `.flake8`                                     | pyflakes (F) and pycodestyle (E, W), minus the checks black disagrees with. See below. |
| complexity-new-violations | `.flake8`'s `max-complexity`                  | Fails on the functions that a change makes too complex, compared with HEAD. See below. |
| bandit                    | `-ll`                                         | Medium or high severity security findings fail.                                        |
| mypy                      | `mypy.ini`, django-stubs and pydantic plugins | Checks the whole package, test bodies included, in the project's `venv`. See below.    |
| pyright-new-errors        | `pyproject.toml`'s `[tool.pyright]`           | Fails on the pyright errors that a change adds, compared with HEAD. See below.         |
| pyupgrade                 |                                               | Modern syntax for Python 3.14.                                                         |
| pydocstringformatter      |                                               | Normalizes docstring layout.                                                           |
| codespell                 | `codespell.txt` ignore list                   | Also runs on docs and skills. Add real project words to `codespell.txt`.               |

autoflake keeps the imports of a package's `__init__.py`, which re-export its
modules' names (`--ignore-init-module-imports`), and doesn't touch migrations.
An import kept only for its side effects, e.g. of a module of signal receivers,
needs a `# noqa` comment, or autoflake removes it.

**ruff is not configured.** A repository-wide `ruff check` reports a large
backlog (unused imports, E402) that is not the project's standard. Don't report
ruff output as lint debt, and don't "fix" it.

**Prettier** formats the Markdown, YAML and JSON outside `smarter/` (the skills, the
workflows, the root's files). The React code, and its Prettier, ESLint and TypeScript
checks, are in smarter-sh/smarter-console, whose own pre-commit hooks and `make lint`
check it.

**Everything**: trailing whitespace, end-of-file newline, YAML, JSON, TOML and
XML syntax, merge conflict markers, private keys, AWS credentials, debug
statements, and commitlint on commit messages.

## flake8

flake8 runs pyflakes (unused and undefined names, unused variables, redefinitions, f-strings
without placeholders) and pycodestyle (blank lines, `x not in y`, imports at the top, ...), at
line length 120. The pycodestyle checks that disagree with black are off (E203, E501, E701, E704,
W503): black owns the formatting, and line length. Migrations and `__version__.py` are excluded,
and two exceptions are narrow and commented in `.flake8`: the settings modules' star imports
(F403, F405) and `docs/source/conf.py`'s imports after its `sys.path` and Django setup (E402).
The whole repository has no findings: keep it that way.

```console
source venv/bin/activate
git ls-files '*.py' | xargs flake8      # everything, as the hook sees it
```

Fix the cause. An unused variable that holds the result of a call with side effects loses the
variable, not the call. A `# noqa` is for code that is right as it is, names its code, and says
why, e.g. `# noqa: E402` on an import that must follow a `sys.path` change or
`os.environ.setdefault("DJANGO_SETTINGS_MODULE", ...)`.

## Complexity (mccabe, C901)

`.flake8` sets `max-complexity = 10`, mccabe's cyclomatic complexity. The repository has a backlog
of functions above it (`flake8 --select=C901 smarter` lists them), so the flake8 hook leaves C901
out, and the `complexity-new-violations` hook checks only what a change makes worse, on the
changed files:

```console
python3 -I scripts/complexity_new_violations.py --python venv/bin/python               # changed since HEAD
python3 -I scripts/complexity_new_violations.py --python venv/bin/python --base alpha  # ... since another commit
```

It runs flake8's C901 check on the files in the working tree and as they were at the base, and
matches functions by file and qualified name (`Class.method`), not line. A function fails when it
is above 10 and wasn't at the base (a new function, or one the change pushed over the limit), or
when a function of the backlog got more complex. Leaving a backlog function as it is, or making it
simpler, passes. Fix a failure by splitting the function into named steps; don't raise the limit.
The hook installs its own flake8 (`additional_dependencies`), so pre-commit.ci runs it too.
`pre-commit autoupdate` doesn't change that pin: keep it at the flake8 hook's `rev`.

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

## Type errors (mypy)

The mypy hook checks the whole package with `mypy.ini` (the django-stubs plugin, which imports
`smarter.settings.local`, and the pydantic plugin, which types a model's constructor by its field
names), so it runs in the project's `venv`, not an environment of its own. `check_untyped_defs` is
on, so mypy checks the bodies of functions without annotations too, every test method among them,
as Pylance does. The package has no mypy errors: keep it that way. To run it by hand:

```console
cd smarter && ../venv/bin/python -m mypy --config-file ../mypy.ini smarter
```

The first run takes a minute or two, later ones about ten seconds. Fix an error the way
`smarter-python-typing` describes, not with `Any` or a bare `# type: ignore`. In a test, narrow an
Optional with `assert value is not None` (bandit's `-ll` allows asserts), declare a fixture that
`setUpClass` sets on the class (`guardrail: Guardrail`), and narrow parsed JSON and responses with
`json_object()`, `json_list()` and `http_response()` from `smarter.lib.unittest.narrowing`. If mypy reports an
error that a run with a new `--cache-dir` doesn't, e.g. `'Settings' object has no attribute`, its
cache in `smarter/.mypy_cache` is stale: delete it.

## Type errors (pyright and Pylance)

mypy and pyright don't agree on everything, so a change could pass mypy and still show type errors
in VS Code, whose Pylance is built on pyright. The repository has a backlog of pyright errors, so the
`pyright-new-errors` hook checks only the errors that a change adds, on the changed files. It needs
Node.js (`npx`), and pre-commit.ci skips it. To run it by hand:

```console
python3 -I scripts/pyright_new_errors.py                 # Python files changed since HEAD
python3 -I scripts/pyright_new_errors.py --base alpha    # ... since another commit
```

The git side of both ratchet hooks (changed files, exporting the base with `git archive`) is in
`scripts/new_findings.py`. A new hook of this kind uses it too.

It runs pyright (pinned, with `npx`) on the files in the working tree and as they were at the
base, matches errors by file, rule and message (lines move), and prints only the new ones, with
their lines. Exit code 1 means the change added an error: fix it before finishing. It also says
how many old errors the change fixed.

- The rules are in `pyproject.toml`'s `[tool.pyright]`, which Pylance reads too. The two override
  checks are off, because they fire on correct idioms: every nested `class Meta`, and SAM brokers
  that narrow `AbstractBroker`'s attributes to their own kind's types.
- Fix a type error properly: narrow with `is None` or `isinstance` on a local variable (pyright
  doesn't narrow properties), correct a wrong annotation, or declare an attribute that Django adds
  at runtime (a foreign key's `<name>_id`) as a bare annotation with a `#:` comment. A model's `id`
  is declared on `TimestampedModel`. Use `cast()` or `# pyright: ignore[<rule>]` only with a
  comment that says why.
- A function decorated with `@cache_results` has no typed `.invalidate()` yet; that is fixed in
  the cache-results package, not here.

## Principles

- Match the surrounding code: its naming, comment density, logging style
  (`logger = logging.getSmarterLogger(__name__, any_switches=[...])`), and
  error types.
- Fix the cause of a finding. Suppress a finding only with a narrow, commented
  directive that explains why (for example `# pylint: disable=broad-except`
  around code that must not raise).
- Don't reformat code you didn't otherwise change. It buries the real diff.
