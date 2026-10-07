---
name: smarter-sam-resource
description: Use when adding a new Smarter resource kind, or changing an existing one's manifest, broker, model, ownership, or kind registration. Explains the SAM (Smarter Application Manifest) architecture of Pydantic manifest models plus AbstractBroker, and gives the end-to-end checklist of every file a new kind touches.
---

# Smarter SAM Resources

## What a SAM resource is

Every Smarter resource is declared by a YAML manifest:

```yaml
apiVersion: smarter.sh/v1
kind: CustomDomain
metadata:
  name: example_com
  description: An example custom domain.
  version: 1.0.0
  tags: [example]
spec:
  config:
    domainName: example.com
status: {} # read-only, filled in by describe
```

Users `apply`, `get`, `describe`, `delete`, `deploy`, `undeploy`, and `logs` it
with the `smarter` CLI, which POSTs to `/api/v1/cli/<command>/<kind>/`. Four
layers do the work:

1. **Pydantic manifest models** validate the YAML: `metadata.py`, `spec.py`,
   `status.py`, and `model.py` (the `AbstractSAMBase` subclass), plus `const.py`
   with `MANIFEST_KIND`.
2. **A broker** (an `AbstractBroker` subclass) maps the manifest to and from the
   Django model, and implements each CLI verb. Unsupported verbs raise
   `SAMBrokerErrorNotImplemented`.
3. **A Django model**, owned by a user: `MetaDataWithOwnershipModel`, with
   `unique_together = ("user_profile", "name")`. Ownership is what makes a
   resource "mine", "shared with my account", or invisible. Every resource has
   it. Don't invent a different ownership scheme.
4. **The web console**: a React list page, a manifest detail page, and list,
   clone, rename, and delete APIs.

Every SAM resource is treated the same way. If a new kind lacks something the
others have (an owner, a kind, a manifest, a broker, a list page), that's a
design flaw to fix, not a special case.

## Reference implementations

Copy the newest, most complete examples:

- `smarter/smarter/apps/guardrail/`: a whole app built around one kind.
- `smarter/smarter/apps/llmclient/` **CustomDomain**: a second kind added to an
  existing app, with verification status driven by a Celery task.
- `smarter/smarter/apps/secret/`: a small, simple kind.

## Checklist for a new kind

Read [references/canonical-sam-reference.md](references/canonical-sam-reference.md)
for the full file-by-file list, with the CustomDomain file for each step. In
summary:

1. **Kind registration**
   - `SmarterJournalThings` in `smarter/smarter/lib/journal/enum.py`, including
     its `choices()` entry, plus a `lib/journal` migration for the changed
     choices.
   - `SAMKinds` in `smarter/smarter/apps/api/v1/manifests/enum.py`, imported from
     the kind's `const.py`.
2. **Manifest models**: `<app>/manifest/models/<kind>/{const,metadata,spec,status,model}.py`.
3. **Broker**: `<app>/manifest/brokers/<kind>.py`, registered in
   `smarter/smarter/apps/api/v1/cli/brokers.py`. Add the kind to the user
   broker's dependency list in `smarter/smarter/apps/account/manifest/brokers/user.py`,
   so that deleting a user accounts for it.
4. **Model and migration**: a `MetaDataWithOwnershipModel` subclass, plus a
   migration (see `smarter-migrations`).
5. **Serializer**: a `MetaDataWithOwnershipModelSerializer` subclass with
   `Meta.kind`, which `can_delete` uses to find the broker and check
   dependencies, and a `manifest_url`.
6. **Views and URLs**: `views/detailview.py`, `views/listview/view.py` and
   `views/listview/api.py`, and `urls.py` with a `<App>ReverseNames` class.
7. **React list page**: a templatetag, a Django template, a React package, and
   the sidebar link. See `smarter-django-react`.
8. **Docs app**: a JSON schema view and an example manifest view in
   `smarter/smarter/apps/docs/views/`, routed in `smarter/smarter/apps/docs/urls.py`.
9. **Built-in data** (if any): YAML manifests in `<app>/data/<kinds>/`, an
   `add_builtin_<kinds>` command, and a step in `initialize_platform`. See
   `smarter-management-commands`.
10. **Dashboard counts** (if the dashboard shows them):
    `smarter/smarter/apps/dashboard/views/views/api/my_resources.py`.
11. **Sphinx page**: `docs/source/smarter-resources/smarter-<kind>.rst`, plus the
    toctree in `docs/source/smarter-resources.rst` and the autodoc pages. See
    `smarter-sphinx-docs`.
12. **Tests**: a broker test, view tests via `ResourceViewsTestMixin`, model and
    serializer tests, and a `tests/data/<kind>.yaml` manifest. See
    `smarter-python-testing`.

## Broker conventions

- Logging: `logger = logging.getSmarterLogger(__name__, any_switches=[<app switch>, SmarterWaffleSwitches.MANIFEST_LOGGING])`.
- Responses are `SmarterJournaledJsonResponse`, so every CLI call is journaled.
- `apply` creates or updates inside `transaction.atomic()`. It's idempotent:
  applying the same manifest twice changes nothing.
- `describe` returns a manifest that round-trips. Its output can be applied
  again.
- `delete` calls `self.verify_no_dependencies(command)` first, which raises
  `SAMBrokerErrorDependencies` while other resources depend on the object. The
  broker's dependency list is a `@memoized_dependencies` method. Call
  `self.cache_invalidations()` before changing or deleting the object.
- Errors are the broker's own `SAM<Kind>BrokerError`, raised `from` the
  original exception, with `thing=self.kind` and `command=command`.
- Side effects with infrastructure (DNS, certificates, Kubernetes) happen in
  `deploy` or in a Celery task, never in `apply`. See
  `smarter-infrastructure-safety`.
- Send `broker_ready` when the broker is constructed, as the other brokers do.
