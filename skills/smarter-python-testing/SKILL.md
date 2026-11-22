---
name: smarter-python-testing
description: Use when writing, fixing, or running Smarter's Django unit tests, or raising coverage. Covers where tests run (the smarter-api container), the base classes (SmarterTestBase, TestAccountMixin, TestSAMBrokerBaseClass, ResourceViewsTestMixin), fixtures and cleanup without transaction rollback, Celery and infrastructure mocking, the infrastructure tag, and the coverage workflow.
---

# Smarter Python Testing

## Where tests run

Tests run in Docker, never on the host, which has no runnable test
environment. There is one way to run them, `make docker-test`, in the
background, with its output in your scratchpad:

```console
make docker-test                                                    # verifying a change: the whole suite
make docker-test LABELS=smarter.apps.llmclient.tests.test_custom_domain_views   # iterating on one module
```

It builds the image from your working tree, then runs the tests in shards,
each in a Docker stack of its own (see [Sharded runs](#sharded-runs)). The
whole suite runs in as many shards as Docker has room for; `LABELS` runs in one.

- **Verify every change with the whole suite.** No threshold, no exceptions:
  not for a one-line fix, not for a rename, not for "just the apps I
  touched". `LABELS` is for iterating on one test module, never for
  verifying.
- **Never `docker exec smarter-api ... manage.py test`.** It runs on one core,
  against the dev container's stale copy of the code (it has no bind mount),
  with Celery Beat changing the rows of running tests. The user has called
  this out repeatedly. The only exception is the `infrastructure`-tagged
  tests, and only when the user asks (see
  [Real infrastructure](#real-infrastructure-never-by-default)).
- **There is no sync step.** `make docker-test` builds the image from the host's
  tree, so it always tests the code you edited.
- **Run the tests yourself, every time.** Don't ask the user to re-run. Run long
  suites in the background, with output written to a log file in your
  scratchpad, and read the summary at the end.
- **`make coverage` runs serially**: run it only when the user asks for a
  coverage report.
- A log that stops partway through usually means an earlier session ran out of
  context. It doesn't mean the tests crashed.
- **Save the complete output, then grep it with `-a`.** Smarter's logs contain
  ANSI color codes, so `grep` treats the output as binary, prints only
  "binary file matches", and silently drops the `Ran N tests`, `OK`, `FAILED`
  and `FAIL:`/`ERROR:` lines. Write the whole run to a file, then search it with
  `grep -a`, rather than piping the test run straight into `grep`. A
  coverage report alone is not a result: always confirm the pass and fail counts.

  `make docker-test` does this for you: each shard's whole output is in
  `.test-shards/shard-<n>.log`, and its report lists every `FAIL:` and
  `ERROR:`. To read a shard's log yourself:

  ```console
  grep -aE '^Ran |^OK|^FAILED|^(ERROR|FAIL):' .test-shards/shard-1.log
  ```

## Decide what to test from the user's path, not from your code

Coverage measures which lines ran, not whether the data they ran on looks like
production. When you write both the code and its fixtures, both come from the
same assumption about the input, and the tests can only confirm that
assumption. A suite can cover 99% of a feature and prove nothing about it.

Before you write the tests for any change:

1. **Name the user's path.** Write down the first thing a user will do with
   the change: apply a manifest with the cli, send a prompt from the console,
   open a page in the admin, wait for a scheduled task to run. The first test
   exercises that path, through the view, broker, command or task the user
   reaches, not the helper you wrote.
2. **List every producer of the data your code reads.** Grep for every caller,
   view, serializer, task or manifest that creates it. Different producers
   often make different shapes (an envelope, a legacy version, a JSON string
   instead of a dict, an error variant). Each shape gets a test. If you can't
   list them, you don't understand the change yet.
3. **Build fixtures with the code that produces the data, or from a real
   one.** Call the builder, serializer, `model_dump()`, broker or test client
   POST that makes it in production, load an example manifest, or save a
   document from a real run into `tests/data/`. A dict you typed yourself tests
   only your own idea of the data.
4. **Check every fallback assertion against the producers.** A test that
   expects `""`, `None`, `[]` or an error for some input claims that input is
   invalid. Make sure it isn't one that a real producer sends.
5. **Run the user's path once, end to end, before you say "done".** Send the
   request to the local dev server, or drive the view with Django's test
   client, and look at what the user will see. Green tests don't replace this.
   If you can't run it, say so, and don't claim the change works.

Example: the journal admin's "Response text" shipped with 99% coverage and
showed nothing for the first prompt a user sent from the console. Its fixture
was a hand-written bare `ChatCompletion`, the passthrough api's shape. LLMClient
prompts journal `{"data": {"completion": ...}}`, and one test even asserted
that a `{"data": ...}` document returns "". Rules 2, 3 and 4 would each have
caught it, and rule 5 would have caught it in a minute.

## Layout and conventions

- One test module per source module (`test_custom_domain_broker.py` for
  `brokers/custom_domain.py`), in the app's `tests/` folder, or a `tests/`
  folder next to the code (`manifest/brokers/tests/`).
- Test data lives as YAML (or JSON) in a `tests/data/` folder, not as inline
  dicts. Load it with `get_readonly_yaml_file()` or
  `get_data_full_filepath()`.
- Setup is expensive (accounts, users, profiles, cache), so each module puts
  its tests in one class, with shared fixtures built once in `setUpClass`.
  Mutating tests use throwaway objects plus `addCleanup`.
- Test names say what's being proven: `test_shared_with_the_account`,
  `test_list_api_reports_llmclient_and_dns_records`. Each gets a one-line
  docstring when the name alone isn't enough.

## Base classes

| Class                    | Module                                                   | Gives you                                                                                                        |
| ------------------------ | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `SmarterTestBase`        | `smarter/smarter/lib/unittest/base_classes.py`           | `hash_suffix`, `name`, `uid`, a cleared cache, YAML/JSON/CSV loaders, `create_generic_request()`                 |
| `TestAccountMixin`       | `smarter/smarter/apps/account/tests/mixins.py`           | `account`, `admin_user`, `user_profile`, `non_admin_user`, `non_admin_user_profile`, torn down after the class   |
| `TestSAMBrokerBaseClass` | `smarter/smarter/lib/manifest/tests/test_broker_base.py` | A request and loader for a broker test. Subclass, then set `SAMBrokerClass` and the manifest file                |
| `ResourceViewsTestMixin` | `smarter/smarter/lib/unittest/resource_views.py`         | The standard list page, list api (owned/shared), clone, rename, delete, and detail view tests for a SAM resource |

`ResourceViewsTestMixin` needs `model`, `reverse_names`, `id_kwarg`,
`resource_name_prefix` and `create_resource()`. When the app's `ReverseNames`
class names its views differently, add a small adapter class (see
`CustomDomainReverseNames` in
`smarter/smarter/apps/llmclient/tests/test_custom_domain_views.py`).

## Things that will bite you

- **No transaction rollback.** `SmarterTestBase` is a plain
  `unittest.TestCase`. Everything a test creates stays in the database until
  you delete it, and `transaction.on_commit` callbacks fire immediately. Delete
  explicitly in `tearDownClass` or with `addCleanup`.
- **`admin_user` is a superuser.** Ownership and read-permission queries return
  every account's rows for a superuser. Use `non_admin_user` to prove that
  another account gets a 404.
- **Never purge test data mid-run.** `purge_test_artifacts()` deletes every
  `is_test=True` profile, your own class's fixtures included, so only the test
  runner calls it, before and after each run. `factory_account_teardown()`
  deletes only what it's given, so it's safe for a secondary account.
- **Celery is not eager.** `.delay()` sends the task to the live worker
  container. Patch the task where the code under test imports it, or call the
  task function directly (it runs synchronously, and exceptions re-raise
  without retries).
- **Saving can have side effects.** For example, `LLMClient.save()` sends
  signals that can deploy. Use `Model.objects.filter(pk=...).update(...)` to set
  up state without them.
- **The cache holds sessions.** `lazy_cache.clear()` logs out a test client.
  Call `force_login()` again afterwards.
- **`get_cached_user_for_username()` raises `DoesNotExist`** rather than
  returning `None`.
- **`SmarterCommand.handle_completed_failure(err, msg)`** exits with
  `SystemExit` only when `err` is set. Assert command failures with
  `assertRaises(SystemExit)`.
- **`call_command("<name>")` runs whichever app's command Django finds first.**
  Command names are unique across the project, and
  `smarter/smarter/apps/secret/management/tests/test_commands.py` guards its
  commands with `get_commands()`. Test a command by name, as `manage.py` runs it.
- **`smarter.lib.django.shortcuts.reverse(ns, name, kwargs=...)` is broken with
  kwargs.** Use Django's `reverse(f"{ns}:{name}", kwargs=...)`.
- **GitHub rate limits.** Tests that load plugins from GitHub must wrap them in
  `mock_remote_skills()` (`smarter/smarter/apps/llmtool/plugin/tests/base_classes.py`).
- **Deployed LLMClient hosts don't resolve locally.** A request with
  `HTTP_HOST=<name>.<account>.api...` never finds its LLMClient in the dev stack
  (see `smarter-docker-environment`). To test what a deployed host serves, call
  the view with `RequestFactory`, `override_settings(ALLOWED_HOSTS=["*"])`, and
  `get_cached_llmclient_by_request` patched where the view imports it. Set
  `deployed=True` with `LLMClient.objects.filter(pk=...).update(...)`, never
  `save()`. See `TestPromptConfigViewForDeployedHosts` in
  `smarter/smarter/apps/prompt/tests/test_views.py`.
- **`get_cached_llmclient_by_request` caches `None`**, per url, in Redis, across
  runs. A probe that reuses an LLMClient's name, and so its host, can be refused
  by `SmarterSecurityMiddleware` long after the LLMClient exists. Give throwaway
  LLMClients unique names.
- **Live provider calls.** `test_passthrough_templates` calls every provider for
  real. Provider-side errors are logged at ERROR and skipped, not failed. Read
  the skip reasons. A provider's `base_url` is its SDK's root (the client
  appends `chat/completions`), not an endpoint url, and provider rows change
  only after `manage.py initialize_providers`, which reads the keys from `.env`.
- **`PluginController(manifest=...)` prefers an existing `PluginMeta`** over the
  manifest, and doesn't update it. To apply a manifest to an existing plugin,
  instantiate `PLUGIN_MAP[kind](manifest=..., user_profile=...)`.
- **`ApiConnectionTestMixin` and `SqlConnectionTestMixin` can't share a class.**
  Both set `cls.connection_django_model` and use the secret name
  `test_secret_{hash_suffix}`, which `secret_factory` silently overwrites.
- **A cleanup that re-creates a fixture** through a helper that registers its own
  `addCleanup` leaks: cleanups added during `doCleanups` run too, deleting it
  again, or never.

## Real infrastructure: never by default

Any code path that reaches Kubernetes, Route53, ACM, or other AWS APIs must be
faked in tests. See `smarter-infrastructure-safety`. Tests that truly need real
infrastructure are tagged and skipped by default by `SmarterTestRunner`:

```python
from django.test import tag
from smarter.lib.unittest.runner import INFRASTRUCTURE

@tag(INFRASTRUCTURE)
class TestDeploy(TestAccountMixin): ...
```

Run them only on purpose, with `--tag infrastructure` or
`SMARTER_TEST_INFRASTRUCTURE=true`.

## Coverage

**Target:**

- in smarter.apps at least 90% overall for each Django app or subsystem module.
- in smarter.common and smarter.lib at least 95% overall for each subsystem.

Higher is better. Use judgment about when enough is enough. Large blocks
of coverage misses in a module are frowned upon. Individual module with coverage ratios far
below the 90% target are also frowned upon. (see `smarter-development`).

```console
make coverage
# = docker exec smarter-api bash -c "coverage run --source=smarter manage.py test smarter && coverage report -m && coverage xml"
#   with smarter-beat stopped while it runs
```

### Sharded runs

CI's `python` job (`.github/workflows/test.yml`) runs the same command as eight
shards on eight runners, each with `SMARTER_TEST_SHARD=<n>/8` (see
`smarter/lib/unittest/runner.py`: every shard discovers the whole suite, and
TestCases are never split). The `python-report` job combines the shards'
coverage data and uploads one `coverage.xml` to Codecov. To reproduce one
shard locally, pass the same variable to `docker exec -e`.

`make docker-test` (`scripts/run_test_shards.py`) runs every shard at once, each in a Docker stack
of its own (`docker-compose.shard.yml`, a copy of the local database, no Beat),
and prints each shard's result and the failing tests; logs in `.test-shards/`.
Never run two shards in the one dev stack: the tests share its database,
Redis, dev server and workers without rollback, and break each other. It
chooses the number of shards itself, from `docker info`'s CPUs and memory
(`ideal_shards()`: about 3.75 GB and 1 CPU per shard, after a reserve for the
dev stack), and prints it on its first line. Don't pass `SHARDS=`: a number
larger than Docker has room for runs out of memory, and shards killed that way
end without a result. With `LABELS`, it runs one shard. The shards run the
whole suite several times faster than one process runs a few apps, and they
check everything, not only the apps you guessed.

Don't use `manage.py test --parallel` instead: Django's parallel runner pickles
each failure's traceback, and with this suite it fails with "cannot pickle
'traceback' object", which hides the real failures.

A full run takes a long time, so to raise coverage efficiently:

1. Work from an existing report (`coverage report -m` output) rather than
   re-running the suite.
2. Rank modules by the number of missed lines, not the percentage. Large
   uncovered blocks in small, pure modules (serializers, utils, brokers'
   describe/get, management commands) are the cheapest wins.
3. Test behavior through the public interface: the broker, the view, the
   command, the task function. Don't call private helpers just to touch lines.
4. Iterate with `make docker-test LABELS=<module>`, and verify with the
   whole suite (`make docker-test`). Do one full coverage run at
   the end.

## Reporting

Report pass, fail, error, and skip counts honestly. Name pre-existing failures
and separate them from anything your change caused. Several suites have known,
order-dependent pre-existing failures. Confirm "pre-existing" by running the
test on unchanged code. Don't assume it.

See [references/canonical-test-reference.md](references/canonical-test-reference.md)
for annotated examples.
