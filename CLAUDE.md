# CLAUDE.md

Guidance for Claude Code (and other coding agents) working in this repository.

Smarter is a Django platform for building and running LLM applications. Its
resources (LLMClients, Plugins, Guardrails, Secrets, Custom Domains, ...) are
declared in YAML manifests (SAM, the Smarter Application Manifest), applied
through the `smarter` CLI or the REST API, and managed in a web console whose
pages are small React apps that Django hosts.

Detailed know-how lives in the Agent Skills under `skills/` (symlinked to
`.claude/skills`). **Load `smarter-development` first for any change.** Its
table says which narrower `smarter-*` skill covers each kind of work. This file
holds only what applies to nearly every task.

## Hard rules

1. **Never run git write commands.** "Write a git commit" means print the
   command as text. Never run `git commit`, `git add`, `git reset`, `git push`
   or anything else that changes the index or history. Format and authorship
   are in `smarter-git-commits`.
2. **The local containers hold live credentials.** `smarter-app` and the
   worker containers have a kubeconfig for the real EKS cluster and working
   AWS/Route53 credentials. Fake every Kubernetes, DNS, ACM and AWS call in
   tests, and don't run commands that write to real infrastructure; hand the
   user the command instead. See `smarter-infrastructure-safety`.
3. **Run the tests yourself**, in the container, after any change. Never ask
   the user to re-run them. Report failures honestly, including pre-existing
   ones.
4. **Don't build the Sphinx docs** (about 20 minutes). Check `:doc:` targets
   by file existence, or run `skills/smarter-sphinx-docs/scripts/check-docs.sh`.
5. **The pre-commit hooks are the lint standard** (black, flake8, isort,
   autoflake, bandit, codespell, pyupgrade, pydocstringformatter, Prettier,
   ESLint). Ruff is not configured; ignore its backlog.
6. **Coverage:** at least 90% per Django app or subsystem, 95% where that takes
   moderate effort.
7. **This repository is public.** No API keys, tokens, account IDs, private
   hostnames or customer data in code, tests, docs or skills.
8. **live prompt calls during development** It is ok for you to send live
   billable LLM prompt requests when testing your work. Note that unit tests
   do this as well, so, every time you run tests you are also generating
   billable LLM requests, which is fine.

## Repository map

| Path                                  | Contents                                                                 |
| ------------------------------------- | ------------------------------------------------------------------------ |
| `smarter/smarter/apps/<app>`          | Django apps, one per resource family (llmclient, plugin, secret, ...)    |
| `smarter/smarter/apps/infrastructure` | Cloud-agnostic service layer for DNS, certificates, Kubernetes, email    |
| `smarter/smarter/lib`                 | Framework code: django, drf, manifest brokers, journal, unittest helpers |
| `smarter/react/packages`              | npm workspace: one React app per console page, plus `smarter-common`     |
| `docs/source`                         | Sphinx docs, published to docs.smarter.sh                                |
| `skills/`                             | Agent Skills for developing this repository                              |
| `.github/workflows/test.yml`          | CI (`python` and `react` jobs). Tests run on `main`, not on `alpha`      |

Code never calls the AWS SDK directly. Go through the facade
`smarter.apps.infrastructure.services.infrastructure` (`.dns`, `.certificates`,
`.kubernetes`, `.email`, ...). In tests, patch `<module>.infrastructure` or
configure the in-memory provider.

## Containers

Services in `docker-compose.yml`: `smarter-app` (Django dev server on
`localhost:9357`), `smarter-worker`, `smarter-worker-infrastructure`,
`smarter-beat`, `smarter-mariadb`, `smarter-redis`.

- **There is no bind mount.** Host `smarter/smarter/<path>` is
  `/home/smarter_user/smarter/smarter/<path>` in the container, and edits must
  be copied in. Use `skills/smarter-docker-environment/scripts/sync-to-containers.sh`,
  or ask the user to rebuild for large changes.
- Sync the workers too: Celery tasks run there, and `.delay()` is not eager in
  tests.
- `docker cp dir target` nests into `target/dir` when the target exists, and
  leaves files owned by root. Chown them to `smarter_user`.
- Several `docker cp`s in a row can kill the dev server. After syncing,
  `docker restart smarter-app` and wait for `curl localhost:9357/` to return
  302 before running tests.
- Never `rm -rf` a directory inside a container without first checking for
  files that exist only there.

## Common commands

```bash
# Python tests (run in the background; write the log to your scratchpad)
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py test smarter"
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py test smarter.apps.<app>"
make coverage

# Tests that touch real infrastructure are tagged `infrastructure` and skipped
# by default. Don't run them unless the user asks.

# Lint changed files (zsh doesn't word-split $FILES, so use xargs)
source venv/bin/activate && git diff --name-only | xargs pre-commit run --files

# React
make react-test
make react-lint
make react-build   # npm build + collectstatic + image build
```

After React changes, use `make react-build`, not `make build`. `make build`
uses the host's previously collected `smarter/staticfiles/`, so a new React
app has no `manifest.json` and its page renders an empty root with no console
errors. The template tag caches a missing manifest, so restart `smarter-app`
after fixing staticfiles.

## Conventions

- **Pattern first.** Find two or three existing implementations of the same
  kind of change (prefer the newest: `guardrail`, `secret`, the llmclient
  Custom Domain), read them in full, and copy their structure, naming,
  docstrings, logging and error handling.
- **Migrations:** when an app's models change, prefer regenerating a single
  `0001_initial.py` over adding `0002_...`. Ask first for released apps that
  hold production data. See `smarter-migrations`.
- **Tests:** one test module per source module; fixtures built once in
  `setUpClass`; test data as YAML under `tests/data/`. `SmarterTestBase` has no
  transaction rollback, so delete everything you create. Traps are listed in
  `smarter-python-testing`.
- **API testing by hand:** POST to `http://localhost:9357/api/v1/cli/<command>/`
  with a throwaway `SmarterAuthToken` you create and delete. Don't use the
  `smarter` CLI. See `smarter-api-testing`.
- **Docstrings** are reStructuredText (`:param:`, `:returns:`, `:raises:`);
  Sphinx autodoc publishes them.
- **Docs are evergreen.** Weave new features into the existing prose. No
  "What's new in vX" sections.
- **DNS:** the root domain's A record points to the marketing CDN, not the
  platform load balancer. Never copy it onto platform or chatbot hosts.

## Definition of done

- The change follows an existing pattern.
- Tests cover it, and you ran them in the container.
- Pre-commit hooks pass on the changed files.
- Public Python objects have docstrings; user-facing features are documented.
- Your summary says what changed, what you verified, and what you skipped.
