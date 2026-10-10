---
name: smarter-development
description: Start here for any change to the Smarter repository (Django backend, SAM resources, React web console apps, Sphinx docs, tests, commits). Gives the non-negotiable rules, the pattern-first workflow, and an index of the narrower smarter-* skills to load for each kind of work.
---

# Smarter Development

Smarter is a Django platform for building and running LLM applications. Its
resources (LLMClients, Plugins, Guardrails, Secrets, Custom Domains, ...) are
declared in YAML manifests (SAM, the Smarter Application Manifest), applied with
the `smarter` CLI or the REST API, and managed in a web console whose list
pages are small React apps.

## Repository map

| Path                         | What lives there                                                             |
| ---------------------------- | ---------------------------------------------------------------------------- |
| `smarter/smarter/apps/<app>` | Django apps. One per resource family (guardrail, secret, llmclient, ...)     |
| `smarter/smarter/lib`        | Framework code: manifest brokers, journal, unittest helpers, django helpers  |
| `smarter/react/packages`     | npm workspace of React apps, one per web console page, plus `smarter-common` |
| `docs/source`                | Sphinx documentation, published to docs.smarter.sh                           |
| `.pre-commit-config.yaml`    | The authoritative lint and format standard for Python and React              |
| `.github/workflows/test.yml` | CI: the `python` and `react` jobs                                            |
| `Makefile`                   | Developer commands (`make coverage`, `make react-test`, ...)                 |

Host path `smarter/smarter/<path>` is `/home/smarter_user/smarter/smarter/<path>`
inside the `smarter-app` container.

## Non-negotiable rules

1. **Never execute git write commands.** "Write a git commit" means output the
   command text. Never run `git commit`, `git add`, `git reset`, `git push`, or
   anything else that changes the repository's history or index. See
   `smarter-git-commits`.
2. **Never touch real infrastructure from tests.** The `smarter-app` container's
   kubeconfig points at the real EKS cluster, and its AWS and Route53
   credentials are live. Fake or mock every Kubernetes, DNS, ACM, and AWS call.
   See `smarter-infrastructure-safety`.
3. **Run the tests yourself.** Sync your changes into the containers and run
   the suite. Never ask the user to re-run it. See `smarter-python-testing` and
   `smarter-docker-environment`.
4. **Don't build the Sphinx docs.** The build takes about 20 minutes. Check
   `:doc:` targets by file existence only. See `smarter-sphinx-docs`.
5. **The pre-commit hooks are the lint standard**, not ruff and not a generic
   style guide. See `smarter-code-quality`.
6. **The minimum Code coverage ratio** is 90% at the Django app or subsystem
   module levels. But we'd like at least 95% if that's achievable with moderate
   effort. Exercise common sense when deciding when "enough is enough".

## Pattern-first workflow

Smarter is large and highly consistent. Almost every change has a precedent.

1. Identify what kind of change it is (new SAM resource, list page, Celery task,
   management command, doc page, test module, ...).
2. Find two or three existing implementations of the same kind. Prefer the
   newest: `guardrail`, `secret` and the llmclient Custom Domain are the
   reference SAM resources.
3. Read them in full and copy their structure, naming, docstrings, logging and
   error handling. Don't introduce a new pattern when one exists.
4. Make the change, then add or update its tests, docstrings and Sphinx page.
5. Run the hooks and the tests, and fix what they find.
6. When in doubt, refer to [docs.smarter.sh](https://docs.smarter.sh), which
   is a searchable ReadTheDocs site built from the Sphinx documentation in this repo.

When existing code disagrees with these skills, the code that is newest and
consistent with most of the codebase wins. Say so in your summary.

## Which skill to load

| Task                                                            | Skill                                  |
| --------------------------------------------------------------- | -------------------------------------- |
| Adding or changing a SAM resource (manifest, broker, kind)      | `smarter-sam-resource`                 |
| A web console list page, or any Django-hosted React app         | `smarter-django-react`                 |
| React stories, tests, ESLint, Prettier                          | `smarter-react-testing`                |
| Python unit tests and coverage                                  | `smarter-python-testing`               |
| Syncing code into the Docker containers, running anything there | `smarter-docker-environment`           |
| Code that calls Kubernetes, AWS, Route53, ACM, or Celery        | `smarter-infrastructure-safety`        |
| Model changes and migrations                                    | `smarter-migrations`                   |
| `manage.py` commands, built-in data, `initialize_platform`      | `smarter-management-commands`          |
| Probing the REST API by hand                                    | `smarter-api-testing`                  |
| Python docstrings                                               | `smarter-docstrings`                   |
| Sphinx pages                                                    | `smarter-sphinx-docs`                  |
| Lint, format, pre-commit                                        | `smarter-code-quality`                 |
| Writing a commit message                                        | `smarter-git-commits`                  |
| A release announcement post for blog.smarter.sh                 | `blog.smarter.sh-release-announcement` |

## Definition of done

- The code follows an existing pattern.
- The tests cover it, and you ran them in the container. Report failures
  honestly, including pre-existing ones.
- The pre-commit hooks pass on the changed files.
- Public Python objects have docstrings, and user-facing features have a
  Sphinx page woven into the existing evergreen docs.
- Your summary says what changed, what you verified, and what you skipped.
