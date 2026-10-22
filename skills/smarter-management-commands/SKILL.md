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
`add_example_<kinds>`, never `builtin`: `add_example_tools` (all the plugin kinds),
`add_example_llmclients`,
`add_example_custom_domains`, `add_example_guardrails`, `add_example_budgets`, ... Each
belongs to the app that implements the kind. A command that creates nothing is named for
what it does: `deploy_example_llmclients` only deploys the example LLMClients that
`add_example_llmclients` applied, and `verify_stackademy` only prompts the Stackademy LLMClients.

A multi-resource example project lives in its own GitHub repository instead, and
`load_from_github` applies it. Like `initialize_platform` and `initialize_account`, which call it,
it is in the account app (`apps/account/management/commands/`), where all of the platform's
initialization commands belong: put a new one there too, not in the app of a kind that it happens
to create. The reference is the Stackademy project,
[smarter-sh/stackademy](https://github.com/smarter-sh/stackademy) (`STACKADEMY_REPOSITORY_URL` in
`apps/llmclient/const.py`): the Secrets, Connections, plugins, LLMClients and Budget of a
fictional code academy, one folder per kind, with pre-commit hooks that validate each manifest
against its kind's published JSON Schema. `load_from_github` clones it, skips hidden files and
non-manifests, fills in `*.yaml.tpl` templates, and applies the manifests in
`SAMKinds.apply_order()` (`apps/api/v1/manifests/enum.py`), the order of kind dependencies, not in
folder order. Give a new SAM kind its place there, with a line in its docstring that says which kinds
its manifests name: a test in `test_enum.py` fails until you do. A repository's top-level
`scripts/` folder holds no manifests: `--run_scripts`, which only `initialize_platform` passes,
runs the scripts that its `scripts/scripts.yaml` lists, `pre` (before the manifests) or `post`
(after), with a fixed environment (`apps/account/repository_scripts.py`). Keep that scheme
generic: never teach `load_from_github` about one repository's script, folder or file names. It keeps an LLMClient's `deployed`,
`--deploy` deploys the LLMClients, and `--exclude_kind Budget` skips the platform-wide Budget
when an account loads its own copy. Don't put Stackademy manifests back in an app's `data/`
folder: change them in that repository.

1. Put the manifests in `smarter/smarter/apps/<app>/data/<kinds>/*.yaml`, with
   the path in the app's `const.py` (for example `CUSTOM_DOMAINS_PATH`).
2. Subclass `SmarterExamplesCommand` (`smarter/smarter/lib/django/management/examples.py`),
   set `family`, and implement `add_examples(user_profile)` with `apply_all(filespecs,
user_profile)`. It resolves `--username` (default: the Smarter admin), applies
   each file in a transaction with `apply_manifest`, through the real broker, fills
   in `*.yaml.tpl` templates, and returns the failures. Reference:
   `smarter/smarter/apps/llmhost/management/commands/add_example_llmhost.py`.
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

### Initialization lives here, and nowhere else

**Everything about initializing the platform is in `initialize_platform`, and nowhere else.**
Agents have broken this rule repeatedly, so read it before any change that sets something up.

- **What counts as initialization:** example resources, Stackademy, seed data, test databases and
  their users, SQL scripts, anything that a new platform needs before it is ready to use.
- **Where it must not go:** the Helm chart (`job-init.yaml`, a new ConfigMap, a volume, a values
  flag), the Makefile (`docker-init`), docker-compose, a CI workflow, a deploy action, in this
  repository (helm/) or in smarter-deploy. Don't suggest it there either, not even as
  an option.
- **What those may do:** bring up what Django needs to start (the app's own database and its
  user), then run `initialize_platform`, and nothing more.
- **Data from another repository:** the command that handles that repository fetches and
  applies it, and `initialize_platform` calls that command. The Stackademy course database,
  `smarter_test_db`, is the example: its SQL script and loader are in the stackademy
  repository's `scripts/` folder, listed as a `pre` script in `scripts/scripts.yaml`, and
  `load_from_github --run_scripts`, which `initialize_platform` calls, runs them. Never copy a script from another repository into a
  ConfigMap or this repository.
- **Initialization logic that you find outside `initialize_platform`:** propose moving it in. Never
  extend it or duplicate it.

`initialize_platform` creates and deploys the platform's example resources, Stackademy
included. The Helm init job (`job-init.yaml`) and `make docker-init` run it alone, with no
initialization step of their own beside it. It deploys the example and Stackademy
LLMClients everywhere except the local environment, because a deploy creates a real DNS record
and Kubernetes ingress. It reads the admin credentials from `smarter_settings.admin_username`
and `admin_password` (`SMARTER_ADMIN_USERNAME`, `SMARTER_ADMIN_PASSWORD`), so the init job
passes no password on its command line and can run it through `run()`.

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
