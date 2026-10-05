# Smarter Agent Skills

This folder holds the [Agent Skills](https://agentskills.io/specification) for
working on the Smarter codebase with an AI coding agent such as Claude Code.
But note that this README.md is written (mostly) for human consumption.

A skill is a folder of written know-how that an agent loads only when a task
needs it. Each one contains a `SKILL.md` file, and sometimes `references/` and
`scripts/` folders. These skills cover how this repository is built, tested,
documented and committed. They are developer tooling, like the `Makefile` and
`.pre-commit-config.yaml`. They aren't part of the Smarter product, and no
Smarter code loads them at runtime, unless you've explicitly opted to create
a SAM SkillPlugin consisting of one of these skills for your own instance of
Smarter.

## What's here

Start with `smarter-development`. It sets out the rules that apply to every
change, and its table says which narrower skill to load for each kind of task.

| Skill                           | Use it when                                                                 |
| ------------------------------- | --------------------------------------------------------------------------- |
| `smarter-development`           | You're making any change. Start here.                                       |
| `smarter-sam-resource`          | You're adding or changing a resource kind (manifest, broker, model).        |
| `smarter-django-react`          | You're building a React app that Django hosts, e.g. a console list page.    |
| `smarter-react-testing`         | You're writing Storybook stories, Vitest tests, or fixing ESLint/Prettier.  |
| `smarter-python-testing`        | You're writing or running Django unit tests, or raising coverage.           |
| `smarter-docker-environment`    | Code must run in the containers (tests, migrations, `manage.py`).           |
| `smarter-infrastructure-safety` | Code touches Kubernetes, AWS, Route53, ACM, LLM providers, or Celery tasks. |
| `smarter-migrations`            | A model, or an enum that a model uses, changes.                             |
| `smarter-management-commands`   | You're writing a `manage.py` command or adding built-in data.               |
| `smarter-api-testing`           | You're testing the REST API by hand against the local dev server.           |
| `smarter-docstrings`            | You're writing Python docstrings, which Sphinx publishes.                   |
| `smarter-sphinx-docs`           | You're editing `docs/source`.                                               |
| `smarter-code-quality`          | You're about to finish a change and need to run the pre-commit hooks.       |
| `smarter-git-commits`           | You've been asked to write a commit message.                                |

### Layout of a skill

```text
smarter-sphinx-docs/
├── SKILL.md            # required: YAML frontmatter (name, description) + instructions
├── references/         # optional: longer material the agent reads only if needed
│   └── canonical-sphinx-reference.md
└── scripts/            # optional: helper scripts the agent (or you) can run
    └── check-docs.sh
```

The frontmatter `description` matters most. An agent sees only each skill's
`name` and `description` until it decides a skill is relevant. Only then does
it read the body. A vague description means the skill never gets used. One
that's too broad means it gets loaded for unrelated work.

The bundled scripts are ordinary shell scripts, and you can run them yourself
from the repository root:

- `smarter-docker-environment/scripts/sync-to-containers.sh` copies changed
  host files into the running containers, then **restarts them**.
- `smarter-sphinx-docs/scripts/check-docs.sh` checks toctree entries, `:doc:`
  links and autodoc targets without running the 20-minute Sphinx build.

## Why this folder exists

Smarter is a large and highly patterned code base, built upon a
heterogeneous collection of technology frameworks and sets of best
practices and norms. But much of what you need to know about it isn't
obvious from the code. For example:

- The containers have no bind mount, so edits have to be copied in.
- `docker cp` nests directories and leaves files owned by root.
- The local containers hold **live** EKS, AWS and Route53 credentials.
- The Sphinx build takes about 20 minutes.
- Commit messages follow a particular format.

Before this folder existed, that knowledge was scattered across one developer's
private agent memory. Every new session, and every new contributor, had to
learn it again, often by making the mistake first. Here, it's reviewed in pull
requests and shared by everyone who works on the repository.

The skills are also readable documentation for people. If you're new to the
codebase, `smarter-development` and `smarter-docker-environment` are a good
place to start.

## Getting the most from a coding agent

Skills are only one of the things that decide how well an agent works on this
repository. How you ask, and properties of the codebase such as its tests, CI/CD,
consistency and logging, matter at least as much. See
[Agentic Development](https://docs.smarter.sh/en/latest/smarter-framework/developer-reference/agentic-development.html)
on docs.smarter.sh.

## When to add or change a skill

Consider adding a skill, or adding to an existing one, when:

- **You've explained the same thing to an agent more than once.** If you've
  corrected it twice, the correction belongs here.
- **A mistake is costly or hard to undo.** For example, a test that creates a
  real Route53 record, or a migration that leaves MariaDB half-migrated.
- **There's an established pattern that isn't obvious.** For example, which
  base classes a new resource kind's tests use, or how a list page's React app
  gets its data from Django.
- **Checking a change takes a fragile series of steps.** Put them in a script
  under `scripts/` so they run the same way every time.

Don't add a skill for:

- **Things the code, the linters or the CI already enforce.** A skill that
  repeats `.pre-commit-config.yaml` will drift from it.
- **One-off facts.** Put those in a code comment, a docstring or the docs.
- **Personal preferences.** Those belong in your own agent configuration, for
  example `~/.claude/`, not in a file everyone shares.
- **Secrets, hostnames, account IDs or anything else private.** This
  repository is public.

Prefer editing an existing skill to adding a new one. Several overlapping skills
compete with each other, and an agent may load the wrong one. If you do add one,
add it to the table above and to the index in `smarter-development/SKILL.md`.
Inside this folder, less is more.

### Writing guidelines

- Name the folder `smarter-<topic>`, and set the frontmatter `name` to the same
  value.
- Write the `description` as "Use when ...". Name the concrete situations and
  file types that should trigger it, and keep it under 1,024 characters.
- Keep `SKILL.md` short and specific. Move long examples to `references/`.
- Explain _why_ a rule exists, not just what it is. An agent that knows the
  reason handles the cases you didn't list.
- Point to real files in the repository rather than copying their code. Copies
  go stale.
- Don't add a `README.md` inside a skill's folder. The skill doesn't need one,
  and an agent may read it as extra instructions.

## What uses these skills

### Claude Code

Claude Code supports Agent Skills natively. It doesn't look in a top-level
`skills/` folder, though. It looks for skills in:

| Location                           | Scope                                    |
| ---------------------------------- | ---------------------------------------- |
| `.claude/skills/<name>/SKILL.md`   | This project, for everyone who clones it |
| `~/.claude/skills/<name>/SKILL.md` | You, in every project                    |
| An installed Claude Code plugin    | Wherever the plugin is enabled           |

This repository connects the two with a symlink, `.claude/skills -> ../skills`,
so every Claude Code session started in a clone of this repository sees these
skills. It was created with:

```bash
# from the repository root
mkdir -p .claude
ln -s ../skills .claude/skills
```

Claude Code lists each skill's name and description, loads a skill's body when
a task matches its description, and also lets you invoke one directly as a slash
command, e.g. `/smarter-git-commits`. It notices new and changed skills while a
session is running. If one doesn't show up, start a new session.

Because the symlink is committed, a change to this folder changes what every
contributor's agent does by default. That's why changes here deserve careful
review (see below). If the symlink breaks, for example on a Windows checkout
without symlink support, Claude Code silently stops seeing the skills.

### Other agents

Agent Skills is an open format, and other coding agents and IDE assistants read
`SKILL.md` folders too, each from its own configuration location. Check your
tool's documentation for where it looks. Agents that don't support skills can
still be told to read `skills/smarter-development/SKILL.md` at the start of a
session.

You can also upload a skill to the Claude apps or the Claude API, but these
skills assume a local checkout and running containers, so they're of little use
there.

### Smarter's own SkillPlugin

Smarter has an experimental `SkillPlugin` resource that can import any Agent
Skill, including one from a public GitHub URL. In principle it could point at a
folder here. In practice there's no reason to. These skills describe how to
develop Smarter, not anything a Smarter chatbot's users need, and nothing in the
platform refers to this folder.

## Security considerations and gotchas

A skill is a set of instructions that an agent will follow, often without
asking. Some instructions here tell an agent to run scripts, restart
containers, or run a test suite in an environment with live cloud credentials.
**Review a change to this folder with the same care as a change to CI or a
deploy script.**

### The local environment is live

The `smarter-app`, `smarter-worker`, `smarter-worker-infrastructure` and
`smarter-beat` containers hold a kubeconfig for the **real EKS cluster**, and
working AWS and Route53 credentials. Any code an agent runs there can create
real, billable resources or change production DNS. Several skills tell the agent
to run tests and `manage.py` commands there, on its own.

`smarter-infrastructure-safety` exists to prevent accidents: it describes the
fakes, guards and the `infrastructure` test tag. Don't weaken it. If you add a
skill that runs anything in the containers, refer to it.

### Skills change what an agent does without asking

- **A skill's instructions apply to every task that triggers it.** A rule such
  as "run the tests yourself" is helpful for most changes, and harmful for a
  change whose tests touch real infrastructure. Write rules with their limits
  stated.
- **A description that's too broad has a wide reach.** A skill that is meant
  for migrations but says "use when changing Python" will be loaded, and
  followed, for unrelated work.
- **Scripts run with your permissions.** `sync-to-containers.sh` restarts all
  four containers and changes file ownership inside them. Restarting
  `smarter-beat` or a worker interrupts any Celery task that's running.
- **Some instructions forbid things on purpose.** `smarter-git-commits` tells
  the agent to never run `git commit`, `git add` or `git push`, and only to
  write the command for a person to run. Don't remove a rule like that unless
  you mean to give agents that power.
- **Some agents support frontmatter that grants permissions.** For example,
  Claude Code's `allowed-tools` lets a skill pre-approve tools so the agent
  doesn't ask first. None of the skills here use it. Think carefully before
  adding it, especially for `Bash`.

### Skills can be used for prompt injection

An agent treats a skill as trusted instructions. A change that hides an
instruction in a skill, or in a file under `references/`, could make the agent
of the next contributor who uses it run commands, read credentials, or send
data elsewhere. Look for these when reviewing:

- Instructions unrelated to the skill's stated purpose
- New or changed scripts, and any network calls in them (`curl`, `wget`,
  package installs)
- Text that tells the agent to skip confirmations, hooks, or safety rules
- Links to external pages the agent is told to fetch and follow

Don't link or copy skills from sources you haven't read.

### Stale skills mislead

A skill that describes an old pattern is worse than no skill: the agent follows
it confidently. When you change a convention that a skill describes (a base
class, a make target, a container name, a file path), update the skill in the
same pull request. `smarter-development` says that newer code consistent with
the rest of the codebase wins over the skills, but it's better not to rely on
that.

### Keep secrets out

This repository is public. Never put API keys, tokens, account IDs, private
hostnames or customer data in a skill, an example or a script. Use
placeholders, and tell the agent where to find the real value at run time.
