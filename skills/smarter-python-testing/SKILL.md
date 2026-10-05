---
name: smarter-python-testing
description: Use when writing, fixing, or running Smarter's Django unit tests, or raising coverage. Covers where tests run (the smarter-app container), the base classes (SmarterTestBase, TestAccountMixin, TestSAMBrokerBaseClass, ResourceViewsTestMixin), fixtures and cleanup without transaction rollback, Celery and infrastructure mocking, the infrastructure tag, and the coverage workflow.
---

# Smarter Python Testing

## Where tests run

Tests run inside the `smarter-app` Docker container, against its MariaDB,
Redis, and live dev server on port 9357. The host has no runnable test
environment.

```console
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py test smarter.apps.llmclient"
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py test smarter.apps.llmclient.tests.test_custom_domain_views"
```

- **The container has no bind mount of the source.** Sync your edited files
  first, or you're testing stale code. See `smarter-docker-environment`.
- **Run the tests yourself, every time.** Don't ask the user to re-run. Run long
  suites in the background, with output written to a log file in your
  scratchpad, and read the summary at the end.
- A log that stops partway through usually means an earlier session ran out of
  context. It doesn't mean the tests crashed.

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
- **`factory_account_teardown()` sweeps every `is_test=True` account**,
  including your own class's fixtures. Never call it mid-class. Delete a
  secondary account's objects directly.
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
  `mock_remote_skills()` (`smarter/smarter/apps/plugin/plugin/tests/base_classes.py`).
- **Live provider calls.** `test_passthrough_templates` calls every provider for
  real. Provider-side errors are logged at ERROR and skipped, not failed. Read
  the skip reasons.

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

**Target:** at least 90% for each Django app or subsystem module, and 95% where
that takes moderate effort. Use judgment about when enough is enough (see
`smarter-development`).

```console
make coverage
# = docker exec smarter-app bash -c "coverage run --source=smarter manage.py test smarter && coverage report -m && coverage xml"
```

CI's `python` job (`.github/workflows/test.yml`) runs the same command and
uploads `coverage.xml` to Codecov. A full run takes a long time, so to raise
coverage efficiently:

1. Work from an existing report (`coverage report -m` output) rather than
   re-running the suite.
2. Rank modules by the number of missed lines, not the percentage. Large
   uncovered blocks in small, pure modules (serializers, utils, brokers'
   describe/get, management commands) are the cheapest wins.
3. Test behavior through the public interface: the broker, the view, the
   command, the task function. Don't call private helpers just to touch lines.
4. Run only the modules you touched while iterating. Do one full coverage run at
   the end.

## Reporting

Report pass, fail, error, and skip counts honestly. Name pre-existing failures
and separate them from anything your change caused. Several suites have known,
order-dependent pre-existing failures. Confirm "pre-existing" by running the
test on unchanged code. Don't assume it.

See [references/canonical-test-reference.md](references/canonical-test-reference.md)
for annotated examples.
