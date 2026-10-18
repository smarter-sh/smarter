---
name: smarter-management-commands
description: Use when writing or changing a Smarter manage.py command, adding example data (manifests that ship with the platform), or wiring a step into initialize_platform. Covers SmarterCommand, the add_example_<kinds> pattern of applying YAML manifests from an app's data folder, failure handling and exit codes, and how to test commands.
---

# Smarter Management Commands

## SmarterCommand

Every command subclasses `SmarterCommand`
(`smarter/smarter/lib/django/management/base.py`), not Django's `BaseCommand`:

```python
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py add_example_widgets command."""

    help = "Apply the built-in Widget manifests, in smarter/apps/widget/data/widgets."

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, help="The user that will own the Widgets.", default=...)

    def handle(self, *args, **options):
        self.handle_begin()
        ...
        self.handle_completed_success()
```

- Call `handle_begin()` first, and `handle_completed_success()` or
  `handle_completed_failure(err, msg)` last. They log the start and end banners.
- **`handle_completed_failure(err, msg)` exits with code 1 only when `err` is
  set.** With `err=None` it logs the failure, and the command carries on. Pass the
  exception, or `raise` after it, when the command must stop.
- Write user-facing output with `self.stdout.write(...)` and
  `self.style.WARNING/SUCCESS`, so tests can capture it.
- Every command accepts `--settings_output`, which prints the Django settings
  first.
- Command names must be unique across apps. If two apps define a command with
  the same name, `manage.py` silently runs only one of them. A command belongs
  to the app whose model it manages: Secret commands (`get_secret`,
  `update_secret`) live in the secret app. Check
  `python manage.py help` before you pick a name.

## Example data: `add_example_<kinds>`

Resources that ship with the platform are **example resources**, declared as **YAML
manifests**, not Python fixtures. Every command that creates them is named
`add_example_<kinds>`, never `builtin`: `add_example_secrets`, `add_example_connections`,
`add_example_tools` (all the plugin kinds), `add_example_llmclients`,
`add_example_custom_domains`, `add_example_guardrails`, `add_example_budgets`, ... Each
belongs to the app that implements the kind. A command that creates nothing is named for
what it does: `deploy_example_llmclients` only deploys the example and Stackademy LLMClients that
`add_example_llmclients` applied, and `verify_stackademy` only prompts them.

1. Put the manifests in `smarter/smarter/apps/<app>/data/<kinds>/*.yaml`, with
   the path in the app's `const.py` (for example `CUSTOM_DOMAINS_PATH`). The
   Stackademy fictional university's manifests are in each app's
   `data/stackademy/` (Secrets in secret, Connections in connection, plugins in
   llmtool, LLMClients in llmclient, the Budget in account).
2. Subclass `SmarterExamplesCommand` (`smarter/smarter/lib/django/management/examples.py`),
   set `family`, and implement `add_examples(user_profile)` with `apply_all(filespecs,
user_profile)`. It resolves `--username` (default: the Smarter admin), applies
   each file in a transaction with `apply_manifest`, through the real broker, fills
   in `*.yaml.tpl` templates, and returns the failures. Reference:
   `smarter/smarter/apps/connection/management/commands/add_example_connections.py`.
3. One bad file doesn't stop the rest. Collect the failures, report them as a
   warning at the end, and keep going.
4. If the kind has an asynchronous lifecycle (verification, deployment), the
   command sets the starting status and queues the task, as
   `add_example_custom_domains` does with `verify_custom_domain.delay(...)`. Never
   undeploy by applying: `add_example_llmclients` keeps an existing LLMClient's
   `deployed`.
5. It must be idempotent. Running it twice is safe, because `apply` updates.

## initialize_platform

`smarter/smarter/apps/account/management/commands/initialize_platform.py` sets
up a new platform: the admin user and account, then each built-in data command
in order. Add a new step as its own `try`/`except` block, so one failing
component doesn't stop the others:

```python
try:
    # applied, not deployed: an example CustomDomain, whose verification fails.
    call_command("add_example_custom_domains")
except (Exception, SystemExit) as e:
    logger.error("Failed to initialize CustomDomains: %s", e)
```

Catch `SystemExit` too: `handle_completed_failure(err)` exits. `initialize_account` runs
the examples that each account gets its own copy of (secrets, connections, tools,
LLMClients) for the account's admin, then `deploy_example_llmclients`.

Place it after the things it depends on. For example, providers come before the
resources that use them. Comment anything surprising, such as example data that
is expected to fail verification locally.

## Running

```console
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py add_example_custom_domains"
```

Built-in commands for infrastructure kinds queue Celery tasks that the
infrastructure worker runs with **live AWS credentials**. Know what the task
does before running it by hand. See `smarter-infrastructure-safety`.

## Testing

Test with `call_command(...)`, with stdout and stderr captured in
`io.StringIO()`, inside a `TestAccountMixin` class. Patch any Celery task the
command queues in the command's module. Assert:

- the objects it created, and who owns them,
- that it's idempotent (run it twice),
- that failures are reported but don't stop it, and
- that a fatal failure raises `SystemExit`.

Reference: `smarter/smarter/apps/llmclient/tests/test_add_example_custom_domains.py`.
