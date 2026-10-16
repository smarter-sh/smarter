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
3. **Run the tests yourself.** Get your changes into the containers (`make build
&& make run`) and run the test modules you touched. Never ask the user to
   re-run them. Leave the full suite to the user unless they ask. See
   `smarter-python-testing` and `smarter-docker-environment`.
4. **Don't build the Sphinx docs.** The build takes about 20 minutes. Check
   `:doc:` targets by file existence only. See `smarter-sphinx-docs`.
5. **The pre-commit hooks are the lint standard**, not ruff and not a generic
   style guide. See `smarter-code-quality`.
6. **The minimum Code coverage ratio** is 90% at the Django app or subsystem
   module levels. But we'd like at least 95% if that's achievable with moderate
   effort. Exercise common sense when deciding when "enough is enough".
7. **Long-lived caching goes through `@cache_results`.** For anything cached
   for 600 seconds or longer, use `from smarter.lib.cache import cache_results`.
   Never hand-roll `cache.get()`/`cache.set()` with `django.core.cache`. See
   [Caching](#caching).
8. **Model structured data with Pydantic, not raw JSON.** Any sizable JSON that
   code builds, returns or reads gets a Pydantic model. No `list[Any]` or
   `dict[str, Any]` stand-ins. See [Pydantic over JSON](#pydantic-over-json).
9. **`Any` only when the value really can be anything.** If you can list the
   types a value can have, annotate with them. Repeated constructions use the
   `Smarter...Type` aliases in `smarter.lib.typing` (e.g. `SmarterDictType`
   for `dict[str, Any]`). See `smarter-python-typing`.

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

## Caching

`@cache_results` (`smarter/smarter/lib/cache/decorators.py`) is the one way to
cache results for an hour or longer. It builds a deterministic key from the
module, function name and bound arguments, stores results in Redis through
`lazy_cache` (which avoids Django silently falling back to a local-memory cache
when `django.core.cache` is imported too early), caches `None` correctly, and
gives every decorated function an `.invalidate(*args)`. Outside tests, only `lazy_cache`
and the `reset_cache` management command import `django.core.cache`.

- **Cache the expensive call itself**: the HTTP request, the third-party API
  call or the query, not a wrapper around a whole workflow. Cheap work such as
  filtering and formatting then runs on every call, against the cached raw
  result, so configuration changes apply immediately.
- **The signature is the cache key.** The decorated function's parameters must
  be, explicitly and one by one, everything that can change the result: every
  query parameter, filter and flag. Don't fold them into an opaque JSON string
  or an object id. Use plain values (str, int, bool, tuples), never model
  instances or `self`. `@cache_results` can't decorate an instance method,
  because `self` would be part of the key.
- **Never pass a secret as an argument.** Arguments become the cache key and are
  logged on hits and misses when cache logging is on. The normal pattern is an
  internal function, without the sensitive data, that can be decorated: pass a
  Secret's id, or nothing, and read the API key inside it (e.g.
  `SearchProvider.api_key(secret_id)` in `websearch_providers.py`). For the same
  reason, never decorate a generic transport such as `safe_http.fetch()`, whose
  `headers` carry credentials.
- **Never cache a security check.** `safe_http.validate_public_url()` must
  resolve DNS fresh before every request. Caching it would widen the DNS
  rebinding window from milliseconds to the cache lifetime.
- **A per-object TTL** (e.g. a manifest's `cacheTtl`): decorate a function
  defined inside the method with a plain `@cache_results(timeout=<ttl>)`. A
  timeout of 0 stores nothing, so it needs no special case. See
  `ImageSearchPlugin.brave_images()` in `apps/llmtool/plugin/image_search.py`.
- **Don't cache failures.** Raise inside the cached function and catch outside
  it, so that an error or empty result is never stored. See
  `get_cached_api_response` in `apps/llmtool/plugin/api.py`. To remember a
  failure for less time than a success, wrap a short-TTL function that returns
  the result or the error inside a long-TTL one that raises on the error. See
  `cached_catalog_functions()` in `apps/mcpclient/caching.py`.
- **Invalidating a nested function.** A key depends only on the function's
  module, name and arguments, not its timeout, so rebuilding the same nested
  function and calling `.invalidate()` with the same arguments works. See
  `invalidate_cached_catalog()`.
- **Short-lived values** (seconds to minutes) may still use `@cache_results`
  (e.g. `@cache_results(15)` in `plugin_meta.py`). For raw `get`/`set`, use
  `smarter.lib.cache.lazy_cache`, never `django.core.cache`.
- In tests, `SmarterTestBase` clears the cache. To drop one entry, call the
  decorated function's `.invalidate()` with the same arguments.

## Pydantic over JSON

Smarter prefers Pydantic models to wrangling large pieces of JSON: nested
`dict`s that are built key by key, renamed by string search, or read with
chains of `.get()`. The decision, and the reasons for it, are
[ADR-031](../../docs/source/adr/031-pydantic-over-json.rst). The SAM manifests (`smarter.lib.manifest.models`) and the
Smarter Chat api contract (`smarter.apps.prompt.contract.models`) are the
reference implementations.

- **Build the response from the model**, then dump it
  (`model.model_dump(mode="json")`). Don't assemble a dict and validate it
  afterwards, and don't merely document it.
- **No `list[Any]` or `dict[str, Any]`.** A list holds a named model. A value
  that really is arbitrary JSON, such as a tool's result, is `pydantic.JsonValue`.
  It is exactly JSON, unlike `Any`.
- **Serialized Django ORM rows are models of the row**: exactly its fields, with
  `extra="forbid"`, built by a `from_model(row)` classmethod from the instance,
  not from a DRF serializer's `ReturnDict`. A foreign key is the related row's
  id. A field with `choices` is a `Literal`, plus a test that the `Literal`
  matches the model's choices. See `PromptChatApiOrmModel` and its subclasses.
- **Third-party shapes** (OpenAI messages, completions, tool calls) are modeled
  with the fields that the code reads. Allow extra fields only where providers
  add their own, and say so in the docstring.
- **Transformations are methods** of the model, such as
  `PromptChatApiConfig.public()` and `.to_v1()`, not string-replacing helpers
  that run over dumped dicts.
- **The Python SDK mirrors the contracts.** smarter-python
  (`../smarter-python`) copies the chat and journal contracts' committed JSON
  Schemas and examples, and generates its SAM models from each kind's JSON
  Schema. A change to a contract or a manifest model is a change to the SDK's
  api too: say so in your summary.
- **When a model's JSON leaves the repository**, for example to a React app or
  the npm package, publish its JSON Schema
  (`pydantic.json_schema.models_json_schema`), generate the client's types from
  it, and test that the committed schema is current. See
  `smarter.apps.prompt.contract.schema` and `make chat-contract`.
- **Before tightening a type**, validate it against real data: the rows in the
  local database, and a real response, not only the fixtures.

## Which skill to load

| Task                                                             | Skill                                  |
| ---------------------------------------------------------------- | -------------------------------------- |
| Adding or changing a SAM resource (manifest, broker, kind)       | `smarter-sam-resource`                 |
| A web console list page, or any Django-hosted React app          | `smarter-django-react`                 |
| React stories, tests, ESLint, Prettier                           | `smarter-react-testing`                |
| Python unit tests and coverage                                   | `smarter-python-testing`               |
| Syncing code into the Docker containers, running anything there  | `smarter-docker-environment`           |
| Code that calls Kubernetes, AWS, Route53, ACM, or Celery         | `smarter-infrastructure-safety`        |
| Model changes and migrations                                     | `smarter-migrations`                   |
| `manage.py` commands, built-in data, `initialize_platform`       | `smarter-management-commands`          |
| Probing the REST API by hand                                     | `smarter-api-testing`                  |
| The SAM JSON Schemas, example manifests and cli OpenAPI document | `smarter-api-contract`                 |
| Python docstrings                                                | `smarter-docstrings`                   |
| Logger calls: prefixes, levels, waffle switches, secrets         | `smarter-logging`                      |
| Text the web console shows, .po catalogs, adding a language      | `smarter-translations`                 |
| Type annotations, `Any`, the `smarter.lib.typing` aliases        | `smarter-python-typing`                |
| Sphinx pages                                                     | `smarter-sphinx-docs`                  |
| Lint, format, pre-commit                                         | `smarter-code-quality`                 |
| Writing a commit message                                         | `smarter-git-commits`                  |
| Publishing an extension's release to the extension registry      | `smarter-extension-registry`           |
| Code in the cli, an SDK, vscode-yaml or another smarter-sh repo  | `smarter-project-repositories`         |
| A course design for the Free Course Catalog (instructors docs)   | `smarter-course-design`                |
| A release announcement post for blog.smarter.sh                  | `blog.smarter.sh-release-announcement` |
| Any other article for blog.smarter.sh                            | `blog.smarter.sh-blog-post`            |

## Definition of done

- The code follows an existing pattern.
- The tests cover it, and you ran them in the container. Report failures
  honestly, including pre-existing ones.
- The pre-commit hooks pass on the changed files.
- Public Python objects have docstrings, and user-facing features have a
  Sphinx page woven into the existing evergreen docs.
- Your summary says what changed, what you verified, and what you skipped.
