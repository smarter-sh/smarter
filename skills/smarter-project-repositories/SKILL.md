---
name: smarter-project-repositories
description: Use when a task reaches beyond this repository into another smarter-sh repository - the web console (smarter-console, the React app and Smarter Chat), the smarter-cli (Go), the Python, Node.js or Go SDKs (smarter-python, smarter-nodejs, smarter-golang), smarter-vscode-yaml, smarter-deploy, smarter-infrastructure or stackademy - e.g. to check what a change to a SAM model, an example manifest, the OpenAPI document, or the chat or journal contract breaks downstream, to see how a client calls a route, or to answer a question about one of those repositories. Covers reading their local checkouts next to this one, checking that a checkout is current, each repository's copy of the platform's contracts (make contracts), and the public tools of the platform's MCPServer as a fallback.
---

# The Other Smarter Project Repositories

The platform in this repository is the source of truth for the api. The other
repositories of the [smarter-sh](https://github.com/smarter-sh) organization
consume it, and most of them pin a copy of its contracts. Their list is
`SMARTER_PROJECT_REPOSITORIES` in `smarter/smarter/apps/mcpserver/services/repositories.py`.

## Initialization stays in initialize_platform

smarter-deploy and stackademy are where agents most often break this rule. **Everything
about initializing a platform is in `manage.py initialize_platform`, in this repository, and
nowhere else.** That covers seeding a database, loading a SQL script, creating example
resources or users. Never put it in the Helm chart (`job-init.yaml`, a ConfigMap, a volume, a
values flag) or a deploy workflow, and never suggest that as an option. Those start what Django
needs, then run `initialize_platform`. When a repository such as stackademy holds data that a platform
loads, the command that handles that repository (`load_from_github`) fetches and loads it, and
`initialize_platform` calls the command. See `smarter-management-commands`.

## Where to read them, in order

1. **This repository: always the local tree.** It has the working branch and
   uncommitted changes. Never read it through the MCPServer, whose index is
   GitHub's, rebuilt every hour.
2. **The others: their local checkouts**, beside this one at
   `../<repository>` (e.g. `../smarter-cli`). Grep and read them like any
   local code. Run `skills/smarter-project-repositories/scripts/repos-status.sh`
   first: it shows each checkout's branch, uncommitted changes, and whether it
   matches its remote. A checkout that is behind can mislead you. Say so, and
   give the user the `git -C ../<repository> pull` to run. Don't run it
   yourself: the never-run-git-writes rule applies to every repository, not
   only this one.

   The web console is one of them: `../smarter-console`, the npm workspace of
   the single-page console, its packages, and Smarter Chat
   (`@smarter.sh/ui-chat`, `packages/smarter.sh-chat`), which is read, changed
   and committed there, and published to npm from there with the console's
   version. Its skills (`smarter-console-development` first, then
   `smarter-react-testing`, `smarter-chat-development`, `smarter-chat-testing`
   and `smarter-chat-embed`) are in its `skills/`. The archived
   `smarter-sh/smarter-chat` repository holds only Smarter Chat's history up to
   0.16.2, and this repository's history up to v0.42.10 has the console's
   before it moved.

3. **The MCPServer's public tools**, at its public endpoint
   `/api/v1/mcp/smarter-project/`, only when a checkout is missing or
   hopelessly stale, or to search the published docs by relevance:
   `skills/smarter-project-repositories/scripts/smarter-project-mcp.sh <tool> '<json>'`.
   Its tools are `search_documentation`, `search_code`, `read_file`,
   `list_files` and `get_repository_overview`, each taking an optional
   `repository`, `get_manifest_schema`, which returns a kind's example manifest
   and fields, and `search_blog` and `read_blog_post`, which read the posts of
   blog.smarter.sh. It reads `SMARTER_PROJECT_MCP_URL`, which defaults to the local dev
   server. The user may set it to a deployed platform in their own environment.
   Never write a deployed platform's host into this repository. Its results cite the
   GitHub commit they were indexed at, which can differ from the checkout.

Each of these repositories has its own `CLAUDE.md`. Read it before changing
anything there, and follow its rules, not this repository's.

## The contracts they copy

The SDKs, the cli, smarter-vscode-yaml and smarter-console each have `make contracts`, which runs
their `scripts/sync-contracts.sh ../smarter [git ref]` to copy this repository's
committed contracts into their own tree. Their tests then check their models and
requests against the copy:

| Repository            | Copies                                                         | Into                                       |
| --------------------- | -------------------------------------------------------------- | ------------------------------------------ |
| `smarter-python`      | chat and journal contracts, SAM schemas/examples, openapi.json | `tests/data/contracts/`, `tests/data/sam/` |
| `smarter-nodejs`      | the same                                                       | `test/data/contracts/`, `test/data/sam/`   |
| `smarter-golang`      | the same                                                       | `testdata/contracts/`, `testdata/sam/`     |
| `smarter-cli`         | openapi.json, the authority on its commands' routes and kinds  | `testdata/contracts/`                      |
| `smarter-vscode-yaml` | SAM schemas and examples, openapi.json                         | `contract/`, `contract/sam/`               |
| `smarter-console`     | the console endpoints' JSON Schemas (session, chat, ...)       | `packages/<package>/contract/`             |

smarter-console's copies are the JSON Schemas of what the web console reads: the session, Smarter
Chat's api, the Extensions console, the LLM tool list, a deployed LLMClient's page and the workbench's
Architecture tab. Its `make contracts` regenerates each package's TypeScript types from them. This
repository's `make chat-contract`, `make console-session-contract` and the other `*-contract` targets
regenerate and commit the schemas here; the console copies them. Every week, smarter-sh/automation's
API Contract Sync checks each of these repositories against this one's latest release, and opens a pull
request where a copy is out of date.

The source files are listed in each `sync-contracts.sh`. They're generated here
by `make api-contract` and `make chat-contract` (see `smarter-api-contract`).

**When you change a contract here**, find what it breaks downstream: diff the
changed file against each repository's copy, and grep their code for the changed
field, kind or route. Report which repositories need `make contracts` and which
code there would change. Don't run `make contracts` or edit another repository
unless the user asks: it changes that repository's working tree, and its tests
belong to that repository's own workflow.

The SDKs' Sphinx pages live in this repository, at
`docs/source/smarter-framework/smarter-<python|nodejs|golang>*`, and some
SDKs generate their api reference into them.
