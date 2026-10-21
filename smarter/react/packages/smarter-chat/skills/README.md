# smarter-chat Agent Skills

This folder holds the [Agent Skills](https://agentskills.io/specification) for
working on Smarter Chat (`@smarter.sh/ui-chat`) with an AI coding agent such as
Claude Code. This README is written mostly for people.

A skill is a folder of written know-how that an agent loads only when a task
needs it. Each one contains a `SKILL.md` file, and sometimes `references/` and
`scripts/` folders. They are developer tooling, like the `Makefile` and
`.pre-commit-config.yaml`; the npm package never includes them (`files` in
`package.json` is `dist` only).

They are adapted from the skills of the Smarter platform
([smarter-sh/smarter/skills](https://github.com/smarter-sh/smarter/tree/main/skills)),
especially `smarter-react-testing` and `smarter-django-react`, so that every
Smarter repository is developed the same way. The decisions behind the code are
in [`doc/adr/`](../doc/adr/000-intro.md).

## What's here

| Skill                      | Use it when                                                                      |
| -------------------------- | -------------------------------------------------------------------------------- |
| `smarter-chat-development` | You're making any change. Start here.                                            |
| `smarter-chat-testing`     | You're writing or running tests or stories, or raising coverage.                 |
| `smarter-chat-embed`       | You're changing the embed script (`src/embed/`), its options or its build.       |
| `smarter-code-quality`     | You're about to finish a change and need Prettier, ESLint, tsc and the hooks.    |
| `smarter-git-commits`      | You've been asked to write a commit message.                                     |
| `monthly-maintenance`      | It's time to update the dependencies, re-sync the contract and check the budget. |

## Claude Code

Claude Code looks for project skills in `.claude/skills/`, which is a committed
symlink to this folder (`.claude/skills -> ../skills`). Other agents that read
`SKILL.md` folders can be pointed here, or told to read
`skills/smarter-chat-development/SKILL.md` at the start of a session.

## When to add or change a skill

Add to a skill when you've explained the same thing to an agent twice, when a
mistake is costly, or when a pattern isn't obvious from the code. Don't add one
for what the code, the linters or CI already enforce. Prefer editing an
existing skill to adding one, and keep each `SKILL.md` short.

## Security considerations

A skill is a set of instructions that an agent follows, often without asking.
**Review a change to this folder as carefully as a change to CI.** Look for
instructions unrelated to a skill's purpose, new scripts with network calls,
and text that tells an agent to skip confirmations, hooks or safety rules.
Some rules forbid things on purpose, e.g. never running `git commit` or
`npm publish`; don't remove one unless you mean to give agents that power.
This repository is public: no api keys, tokens, account numbers, private
hostnames or customer data in a skill.
