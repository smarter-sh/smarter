---
name: smarter-management-commands
description: Use when writing or changing a Smarter manage.py command, adding or changing example data (the example manifests that every platform loads), or wiring a step into initialize_platform. Covers SmarterCommand, load_from_github and the two repositories of example manifests (smarter-sh/example-manifests and smarter-sh/stackademy), failure handling and exit codes, and how to test commands.
---

# Smarter Management Commands

## SmarterCommand

Every command subclasses `SmarterCommand`
(`smarter/smarter/lib/django/management/base.py`), not Django's `BaseCommand`:

```python
from smarter.lib.django.management.base import SmarterCommand


class Command(SmarterCommand):
    """Django manage.py get_widgets command."""

    help = "List the Widgets of a user."

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

## Example data: `load_from_github` and its two repositories

Resources that ship with the platform are **example resources**, declared as **YAML
manifests**, not Python fixtures, and **not kept in this repository**. There is no app `data/`
folder of example manifests, and no `add_example_<kinds>` command: `add_example_budgets`,
`add_example_custom_domains`, `add_example_guardrails`, `add_example_llmclients`,
`add_example_llmhost`, `add_example_llmhost_compute`, `add_example_mcpclients`,
`add_example_proxies`, `add_example_tools`, `add_example_vectorstores`,
`deploy_example_llmclients`, their base class `SmarterExamplesCommand`, and the
`/api/v1/plugins/add-example-plugins/<user_id>/` endpoint were all deleted. Don't bring any of
them back. `install_official_extensions` (formerly `add_example_extensions`) installs the official
Smarter Extensions from the registry; it applies no manifests.

The example manifests live in two GitHub repositories, and `manage.py load_from_github` applies
both:

- **[smarter-sh/example-manifests](https://github.com/smarter-sh/example-manifests)**
  (`EXAMPLE_MANIFESTS_REPOSITORY_URL` in `apps/llmclient/const.py`): the community-supported
  collection of every kind's examples, one folder per kind (`llm-clients/`, `plugins/static/`,
  `plugins/skill/`, `plugins/websearch/`, `plugins/image-search/`, `guardrails/`,
  `mcp-clients/`, `proxies/`, `llmhosts/`, `llmhost-computes/`, `vectorstores/`,
  `custom-domains/`, `budgets/`).
- **[smarter-sh/stackademy](https://github.com/smarter-sh/stackademy)**
  (`STACKADEMY_REPOSITORY_URL`, same file): the Secrets, Connections, plugins, LLMClients and
  Budget of a fictional code academy, plus the scripts that create its course database.

**To add or change an example, open a pull request on that repository, not this one.** Put the
manifest in the folder of its kind; its pre-commit hooks, which CI runs too, validate each
manifest against its kind's published JSON Schema. If the example needs a new kind, the kind must
exist in the platform first (see `smarter-sam-resource`), and its JSON Schema must be published.
Every platform picks the change up the next time `initialize_platform` runs. A local checkout of
each repository usually sits next to this one (see `smarter-project-repositories`).

`load_from_github` and the other initialization commands (`initialize_platform`,
`initialize_account`) are in the account app (`apps/account/management/commands/`), where all of
the platform's initialization commands belong: put a new one there too, not in the app of a kind
that it happens to create. What `load_from_github` does:

- It clones the repository's default branch, skips hidden files and non-manifests, fills in
  `*.yaml.tpl` templates, and applies the manifests in `SAMKinds.apply_order()`
  (`apps/api/v1/manifests/enum.py`), the order of kind dependencies, not in folder order. Give a
  new SAM kind its place there, with a line in its docstring that says which kinds its manifests
  name: a test in `test_enum.py` fails until you do.
- Each manifest is applied in its own transaction. One that fails is reported and doesn't stop
  the rest; the command fails at the end with the list.
- It keeps an existing LLMClient's `deployed` (applying never undeploys), and `--deploy` deploys
  the LLMClients.
- `--include_kind` (repeatable) applies only those kinds; `--exclude_kind` skips a kind, e.g.
  `Budget`, which only a superuser may apply.
- `--skip_missing_references` skips, with a warning, a manifest whose broker raises
  `SAMBrokerErrorNotFound` on apply: it names a resource this platform doesn't have, e.g. an
  MCPClient's credentials Secret. `initialize_platform` and `initialize_account` pass it for
  example-manifests only; Stackademy brings its own Secrets, so it stays strict.
- A Budget whose manifest has no `spec.resources` is created detached, once: if it exists, it is
  left as it is, so a superuser's attachments survive the next initialization.
- A repository's top-level `scripts/` folder holds no manifests: `--run_scripts`, which only
  `initialize_platform` passes, runs the scripts that its `scripts/scripts.yaml` lists, `pre`
  (before the manifests) or `post` (after), with a fixed environment
  (`apps/account/repository_scripts.py`). Keep that scheme generic: never teach `load_from_github`
  about one repository's script, folder or file names.

Who loads what:

- `initialize_platform` applies the whole example-manifests repository, owned by the Smarter
  admin, so every account may use it, after `initialize_providers`, `install_official_extensions`
  and `initialize_vectorstore_providers`, and before Stackademy. It deploys the LLMClients
  except in the local environment. The example CustomDomain is applied without starting its
  verification.
- `load_from_github` never deletes anything. When an example's manifest is removed from its
  repository, add it to `RETIRED_EXAMPLES` in `delete_retired_examples` (account app), which
  `initialize_platform` runs right after the example manifests: it deletes the Smarter admin's
  resource of that model and name, and its LLMClient links cascade. Otherwise the stale resource
  lives on every platform, e.g. `smarter_project_github_chat`, which failed its hourly refresh for
  weeks after the server stopped serving `smarter-chat` (issue #882).
- `initialize_account` gives each account its own copy of the example plugins and LLMClients:
  `load_from_github --include_kind <each plugin kind> --include_kind LLMClient --deploy`
  (`EXAMPLE_KINDS_PER_ACCOUNT`), and loads Stackademy with `--exclude_kind Budget`.
- The LLMHost discovery's built-in catalog (`apps/llmhost/services/discovery.py`) lists the
  LLMHosts that the Smarter admin owns, i.e. those applied from `llmhosts/`, rather than reading
  files.

A command that creates nothing is named for what it does: `verify_stackademy` only prompts the
Stackademy LLMClients.

## initialize_platform

`smarter/smarter/apps/account/management/commands/initialize_platform.py` sets
up a new platform: the admin user and account, then each built-in data command
in order. Add a new step as its own `try`/`except` block, so one failing
component doesn't stop the others:

```python
try:
    # Before the example manifests, whose LLMClients list the official extensions.
    call_command("install_official_extensions")
except (Exception, SystemExit) as e:
    logger.error("Failed to install the official extensions: %s", e)
```

Catch `SystemExit` too: `handle_completed_failure(err)` exits. `initialize_account` loads
the examples that each account gets its own copy of (the plugins and LLMClients, and
Stackademy) for the account's admin, with `load_from_github`.

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

`initialize_platform` creates and deploys the platform's example resources, from
example-manifests and Stackademy. The Helm init job (`job-init.yaml`) and `make docker-init` run it alone, with no
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
docker exec smarter-app bash -c "cd /home/smarter_user/smarter && python manage.py load_from_github --url https://github.com/smarter-sh/example-manifests --include_kind Guardrail"
```

Applying or deploying infrastructure kinds queues Celery tasks that the
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

Reference: `smarter/smarter/apps/account/management/tests/test_load_from_github.py`, which
patches `Command.clone_repo()` to copy a local temporary folder, so tests never reach GitHub.
