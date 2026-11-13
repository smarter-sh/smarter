---
name: smarter-api-contract
description: Use when maintaining the Smarter api contract in smarter.apps.api.v1.contract - the committed SAM JSON Schemas and example manifests (sam/<Kind>.schema.json, sam/<Kind>.example.json) and the OpenAPI document of the Smarter api (openapi.json), which covers the cli api, the chat api and every family of REST routes under /api/v1, and which each platform serves at /api/v1/openapi.json and renders at /docs/openapi/ - e.g. after changing a SAM model, a broker's example manifest, the journal or chat contract, or a covered route or its response, when a test says the contract is out of date or a route is undocumented, or when adding a kind, a cli command, or a new family of routes. Covers what generates each file, make api-contract, reviewing the diff for breaking changes, the rules for examples, documenting a route or a whole family, streaming responses, the openapi package's modules and its ApiFamily, the design decisions in it, and the downstream SDKs.
---

# The Smarter API Contract

`smarter/smarter/apps/api/v1/contract/` publishes the api as files that clients
in any language generate code from. It is **generated, never edited by hand**,
from the platform's own Pydantic models, and committed, so that it is versioned
with the code and a breaking change shows up in a pull request's diff.

| File or module            | What it is                                                                                                | Generated from                                                                                   |
| ------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `sam/<Kind>.schema.json`  | One JSON Schema per SAM kind. Exactly the `data` of `POST /api/v1/cli/json-schema/<Kind>/`                | The kind's SAM model: `Brokers.get_broker(kind)._pydantic_model.model_json_schema()`             |
| `sam/<Kind>.example.json` | One example manifest per kind, without its read-only `status`                                             | The broker's `example_manifest()`, rendered in-process by the cli's public example-manifest view |
| `openapi.json`            | OpenAPI 3.1 document of the cli api, the chat api, and the REST families in `DOCUMENTED_URLCONFS`         | `openapi/`, from the SAM models, the journal and chat contracts, and `models.py`                 |
| `sam.py`                  | Builds and writes the schemas and examples                                                                |                                                                                                  |
| `models.py`               | `CliApi*`: the `data` of cli responses that aren't manifests. `OpenApi*`: the document itself             |                                                                                                  |
| `openapi/`                | The package that assembles the document. See [The openapi package](#the-openapi-package)                  |                                                                                                  |
| `tests/`                  | Fail when a file is stale, when an example is invalid, or when a real response doesn't match the document |                                                                                                  |

The docs page is `docs/source/smarter-framework/smarter-api/api-contract.rst`.

## When the contract changes

Anything that reaches these files changes the contract:

- a SAM model: a field, its type, default, description, constraint, or a
  nested model (`smarter/apps/*/manifest/models/**`, `smarter/lib/manifest/**`),
- a broker's `example_manifest()`,
- a new, renamed or removed kind (`Brokers._brokers`),
- the journal contract (`smarter/lib/journal/contract/models.py`) or the chat
  contract models the document uses (`PromptChatApiConfigResponse`,
  `PromptChatApiCompletionV1`, `PromptChatApiMessage`, ...),
- a route of a covered family (a urlconf in `DOCUMENTED_URLCONFS`, e.g.
  `smarter/apps/api/v1/cli/urls.py`), or the shape of its view's response,
- `contract/models.py` or the `contract/openapi/` package themselves.

A field description counts too: it's in the schema, and in the SDKs' docstrings.

## Regenerate

The export runs **in the smarter-api container**, which must run your current
code (see `smarter-docker-environment`):

```console
make build && make run                                     # in the background; wait for localhost:9357 to answer 302
make api-contract                                          # export in the container, copy the files back
skills/smarter-api-contract/scripts/check-contract.sh      # 0: current, 1: stale (lists the files), 2: export failed
```

`make api-contract` runs `manage.py export_api_contract` in the container, copies
`openapi.json` back, and replaces the host's `sam/*.json` with the container's,
so a removed kind's files go away. `check-contract.sh` regenerates into a
temporary folder and diffs, without writing to the repository: use it to answer
"is the contract stale?" quickly.

Then run the contract tests:

```console
docker exec smarter-api bash -c "cd /home/smarter_user/smarter && python manage.py test smarter.apps.api.v1.contract"
```

They make one real, billable LLM request (the prompt test), which is fine.

## Review the diff before committing

Read `git diff smarter/smarter/apps/api/v1/contract/` as a client would. Classify
each change:

| Backward compatible                    | Breaking for clients                                           |
| -------------------------------------- | -------------------------------------------------------------- |
| A new optional field, or a new kind    | A removed or renamed field, kind or cli operation              |
| A new cli operation                    | A field that became required, or a narrower type or constraint |
| A relaxed constraint, a new enum value | A removed enum value, a changed default                        |
| A changed description                  | A changed response shape, e.g. `data` from object to list      |

Say which it is in the commit body, and name the files. A breaking change also
needs a note for the SDKs' users (see "Downstream"). Before 1.0.0, never mark it
with a `!` or a `BREAKING CHANGE:` footer: on 0.x that cuts 1.0.0 (see
`smarter-git-commits`). The body says what breaks and how to upgrade.

Unexpected churn means something is wrong, not that the file needs committing:

- **every example changed**: an example has a timestamp, random value or
  environment-specific value outside `status`. Fix the broker's example.
- **`openapi.json` changed but no model did**: a model's import order or name
  changed. Pydantic disambiguates colliding model names with module paths. Two
  models with the same class name in different apps produce long, unstable
  component names. Rename one.

## Rules for example manifests

- **Deterministic.** Only `status` is stripped. Everything else must be the same
  on every run, in every environment, including the test database: no
  `datetime.now()`, no random ids, no values read from the developer's database.
  The platform's built-in account number (`smarter_cached_objects.smarter_account`)
  is the same everywhere.
- **Valid.** Each example must be valid under its kind's schema. A test checks it.
- **Public.** The repository is public. Use placeholders: `example.com`, `sk-xxxx...`,
  the _name_ of a Secret, never a real key, hostname, email or account number.
- An example is built for a request, so `sam_example()` renders the cli's
  public view in-process with `RequestFactory` (host `localhost`). A broker whose
  example needs an authenticated user won't work there: keep examples free of
  the requester.

## Adding a kind

Nothing in the contract package needs editing. Register the broker in
`Brokers._brokers` (see `smarter-sam-resource`), give it an `example_manifest()`,
run `make api-contract`, and commit the two new `sam/` files and `openapi.json`.
`test_every_kind_has_a_model` and `test_every_kind_is_a_manifest` check the rest.

## The openapi package

`contract/openapi/` builds the document, one module per concern. Its
`__init__.py` re-exports the public names (`openapi_document()`, the route
tables, ...), so importers use `smarter.apps.api.v1.contract.openapi`.

| Module        | What it holds                                                                                                                                |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `builders.py` | `ref()`, `json_response()`, `json_body()`, `rest_read()`, `rest_operation()`, parameters, `merge_paths()`, the access notes, and `ApiFamily` |
| `schemas.py`  | `model_schemas()` (every family's `*_API_MODELS`) and `cli_schemas()` (envelopes, `SAMManifest`, ...)                                        |
| `cli.py`      | The cli api: its parameters, `operation()`, `cli_paths()`, and its tags                                                                      |
| `chat.py`     | The chat api: its parameters and `chat_paths()`, under the LLMClients' family                                                                |
| `families/`   | One module per REST family: its `ApiFamily` and its `<family>_paths()`. `FAMILIES` lists them in tag order                                   |
| `routes.py`   | `DOCUMENTED_URLCONFS`, `UNDOCUMENTED_URLCONFS`, `UNDOCUMENTED_ROUTES`, `PATH_PARAMETER_ALIASES`                                              |
| `document.py` | `openapi_document()`, its tags, `openapi_json()` and `write_openapi()`                                                                       |

Each family is an `ApiFamily`, named after its Django app (the app's
`const.namespace`), from which everything else is derived, so that no name is
typed twice: its tag (the name's plural, e.g. `guardrails`), its routes'
prefix (`/<tag>/`, unless `mount` says otherwise, e.g. `llm-clients`), its
operation ids (`family.operation_id("list")` is `guardrail_list`), its paths
(`family.path("{id}/events/")`), its tag's description (a template, in which
`{plural}` is the resource's plural), and the words its descriptions use for its
resource: `family.resource` (its SAM kind, e.g. `Guardrail`, or a lowercase word,
e.g. `vectorstore`), `family.plural`, `family.a` (`a Guardrail`, `an LLMClient`)
and `family.a_capitalized`. Plurals and articles come from inflect; set
`resources` when inflect is wrong (it adds only an s to a capitalized `Proxy`), and
`tag_name` when the tag isn't the name's plural (`journal`, `history`). A
family's `<family>_paths()` writes `family.a`, `family.plural` or
`family.resource` in its descriptions, never the word itself.

## Route coverage

`openapi/routes.py` declares which families of routes the document covers, and
`test_every_route_is_documented` holds it to them:

- `DOCUMENTED_URLCONFS` maps each family's path, relative to `/api/v1`, to its
  urlconf, e.g. `"/llm-clients/": "smarter.apps.llmclient.api.v1.urls"`. It is
  built from `FAMILIES` (each `ApiFamily`'s `prefix` and `urlconf`), the cli's
  and the connections'.
- Every `path()` route of those urlconfs must be in the document, or in
  `UNDOCUMENTED_ROUTES` with a reason. The test also fails when an entry of
  `UNDOCUMENTED_ROUTES` names no route, or a route that is now documented, so
  the list stays honest. `NOT_YET_MODELED` marks the backlog.
- Every family that `smarter.apps.api.v1.urls` mounts must be in
  `DOCUMENTED_URLCONFS`, or in `UNDOCUMENTED_URLCONFS` with a reason
  (`test_every_family_is_covered`). Only `/tests/` is left out. A new app's
  `api/v1/urls.py` therefore fails the tests until it is covered: start with
  "Covering a new family of routes" below.
- `PATH_PARAMETER_ALIASES` renames a route's path parameters for the document,
  e.g. `<int:llmclient_id>` and `<str:hashed_id>` are both `{id}`, because one
  documented path serves both routes.

## Adding or changing a cli route

`test_every_route_is_documented` fails until the route is in the document.

1. **Model the response's `data`** in `contract/models.py`, as a `CliApiModel`
   (`extra="allow"`), with a docstring and field descriptions. Reuse a chat or
   journal contract model when one fits. Add it to `CLI_API_MODELS`.
2. **Build the view's response from the model**:
   `data = {SmarterJournalApiResponseKeys.DATA: Model(...).model_dump(mode="json")}`,
   not a dict that is documented elsewhere. See the status, version, whoami,
   resources and validate views. Let errors raise: `CliBaseApiView.dispatch()`
   returns every exception as the journal's error response, with the status from
   `http_status_for_exception()`. Never return a bare `{"error": ...}`.
3. **Add the operation** to `cli_paths()` in `openapi/cli.py` with `operation(...)`:
   an `operationId` (snake case, unique), a summary, a description, a tag, the
   response schema's name, and its parameters and request body. Add an envelope
   schema in `cli_schemas()`, e.g.
   `schemas["CliApiXResponse"] = envelope(ref(CliApiX.__name__), "...")`.
   A public route gets `security=PUBLIC`, and `test_public_operations` lists it.
4. **Test a real response** against the document in
   `tests/test_openapi.py::TestOpenApiResponses` with `self.assertValid(...)`.
   Patch anything that reaches AWS, Kubernetes or GitHub (see `test_platform`).
5. Run `make api-contract`, the tests, and update `api-contract.rst`.

## Covering a new family of routes

Every family is covered now, so this is for a new app's routes. The chat api
(`chat_paths()`) is the pattern to copy.

1. **Add the family**: a module in `openapi/families/` with its `ApiFamily`
   (see [The openapi package](#the-openapi-package)), added to `FAMILIES`,
   which puts its urlconf in `DOCUMENTED_URLCONFS`. Run the test: it
   lists every route of the family. Add each one to `UNDOCUMENTED_ROUTES` with
   `NOT_YET_MODELED`, and aliases for its path parameters if needed. Now the
   backlog is explicit, and nothing new slips in.
2. **Find the models.** Use the existing contract models when there are some
   (the chat contract, the journal contract). For a REST view that returns a DRF
   serializer's output, write a Pydantic model of the row, as ADR-031 says,
   in the app's own `contract/models.py` (`smarter.apps.llmclient.contract` is
   the reference): `extra="forbid"`, camelCase aliases (base it on
   `AccountApiModel`), built by a `from_model(row)` classmethod, with a test
   that its `Literal`s match the model's choices. Reuse the shared models:
   `AccountApiUserProfile` for an owner, `PluginApiPluginMeta` for a plugin,
   `MetaDataApiAnnotations`, and `user_can_delete()` for `canDelete`.
3. **Prove the model is the serializer's output** before switching: dump every
   real row of the local database with both and compare (see
   `test_*_is_the_serializers_output`). Any difference is either a bug in the
   model or a bug that the serializer had: say which in the commit. Then
   **build the view's response from the model**. A list view mixes in
   `smarter.lib.drf.views.contract.ContractListMixin` and sets `contract_model`
   (or overrides `item()`, e.g. to pass the request's user for `canDelete`).
   Raise DRF's exceptions (`NotFound`, `ParseError`), never return
   `HttpResponseNotFound` or `JsonResponse({"error": ...})`, so every error is
   `{"detail": ...}`.
4. **Publish the reads only** (`GET`): add the family's models to
   `model_schemas()` in `openapi/schemas.py` (a tuple like
   `LLMCLIENT_API_MODELS`), and its operations in the family module's
   `<family>_paths()` function, built with `rest_read()` and the family's
   `operation_id()`, `path()` and resource words, merged by `merge_paths()` in
   `openapi_document()`, whose `tags` gets the family's `openapi_tag()`. Pass `rest_read()` the family's
   access note: `SUPERUSER_ONLY` for `SmarterAdmin*` views, `READ_PERMISSION`
   for `SmarterAuthenticated*` ones. The REST writes stay unpublished: clients
   write through manifests. An action that an SDK uses may be published as a
   POST, e.g. a Guardrail's dry run, or an MCPClient's tool call: say in its
   description what it changes, and who may call it.
   Keep a response's existing key style, even if it isn't camelCase (a
   Guardrail's events and the prompt history are snake_case): clients already
   read it. A paged list (the journal's) is `{"objects": [...], "pagination":
...}`, whose `pagination` is `smarter.lib.django.pagination.ListViewPagination`:
   document its query parameters with `query()`.
5. **Remove the routes from `UNDOCUMENTED_ROUTES`** as they're documented.
6. **Test real responses** of each operation against the document, including
   a 404 and a 403 (see `test_llmclient_reads()`). `OpenApiResponseMixin`, in
   `smarter.apps.api.v1.contract.tests.mixins`, has `assertValidResponse()` and
   `assertValid()`. When the family's fakes live with its app, e.g. the
   vectorstores' in-memory Qdrant and fake Kubernetes, put the test in the
   app's `contract/tests/test_openapi.py` on the app's test base class, with the
   mixin. Use `APIClient` with the headers a real client sends. For other
   success statuses (201, 202) and DELETE, use `rest_operation(status=...)`.
7. **Watch for secrets and permissions.** A foreign key to a `SmarterAuthToken`
   is its digest: publish its `key_id` instead, as `LLMClientApiKey` does. Check
   that each read filters by `with_read_permission_for(user)`: modeling the
   plugins found a retrieve that returned any account's plugin. Rows that
   hold a user's private data, e.g. the prompt history's conversations, filter
   by `with_ownership_permission_for(user)` instead: read permission includes
   the platform account's rows, which every user may read. A non-superuser
   in another account (`mortal_user_factory()`) must get a 404. Never call
   `factory_account_teardown()` in a test: it deletes every test account,
   including the class's own.
   When a service, not the view, builds the response (an LLMHost's report or
   status), build the model in the service, and keep its function's return
   type, so its other callers don't change.
8. Update `api-contract.rst`'s table of covered families, and the SDK: its
   models, its `TestOpenApiContract` calls, and its `TestRecordedResponses`
   fixtures (see "Downstream").

## Streaming responses

OpenAPI 3.1 can't type the events of a `text/event-stream` response. The
stream's media type gets a plain string schema, and an `x-smarter-events`
extension (`OpenApiMediaType.x_smarter_events`) that maps each event's name to
the schema of its JSON data. A test reads the stream (`sse_events()`) and
validates every event's data against the schema that the extension names.

## Design decisions in the openapi package (don't undo them)

- **No `jsonSchemaDialect`.** The document's schemas use OpenAPI 3.1's default
  dialect (JSON Schema 2020-12 with OpenAPI's keywords). Swagger UI and other
  viewers warn about, or reject, any other value, even plain 2020-12.
- **OpenAPI 3.1**, because its schemas are exactly JSON Schema 2020-12, which
  Pydantic generates. Some generators read only 3.0 (oapi-codegen, for Go). Don't
  downgrade the document for them. Publish a converted copy beside it if one is
  ever needed.
- **Each kind's `kind` is a `const` in the document**, added in `cli_schemas()`.
  The SAM models declare `kind: str`, so without it a manifest matches every
  branch of `SAMManifest`'s `oneOf`. The standalone `sam/*.schema.json` files
  stay exactly what the json-schema endpoint returns, without the `const`.
- **`info.version` is the api's version (`v1`)**, not the platform's, which
  would make the committed file stale on every release.
- **No `exclude_none`** when dumping the document. It would also strip the
  `"default": null` inside schemas. `OpenApiModel` drops its own `None` fields
  in a wrap serializer instead.
- **Every error is the `default` response**, with the family's own error
  schema: the journal's error envelope for the cli api, `PromptChatApiErrorResponse`
  for the chat api, and `LLMClientPromptErrorResponse` for a prompt, whose
  failure may be either.
- **Prettier must not format these files.** `.pre-commit-config.yaml` excludes
  `^smarter/` from Prettier. A formatter that rewrote the JSON would make the
  "up to date" tests fail.

## Downstream

The contract is the source the SDKs generate from:

- **smarter-python** (`../smarter-python`): `make contracts SMARTER_REF=<ref>`
  copies `sam/*.json` into `tests/data/sam/` and `openapi.json` into
  `tests/data/contracts/` (`scripts/sync-contracts.sh`, with `git show` at the
  ref), and `make sam-models` regenerates `smarter/models/sam/`. Its
  `tests/test_contracts.py::TestOpenApiContract` fails when a request of the
  SDK to a covered family is not in the document, or the document has an
  operation that the SDK doesn't call. A new operation is SDK work: say so in
  your summary. Extend that test with the SDK's calls of each newly covered family.
  Its `TestRecordedResponses` validates the SDK's recorded fixtures against the
  document: add each new fixture to its `FIXTURES`.
- **smarter-nodejs** (`../smarter-nodejs`) and **smarter-golang**
  (`../smarter-golang`) copy the same files the same way (`make contracts
SMARTER_REF=<ref>`, into `test/data/` and `testdata/`), regenerate their SAM
  types or structs (`make sam-models`), and have the same contract tests
  (`test/contracts.test.ts`, `contracts_test.go`), including the list of
  operations that they don't call. A new operation is work in all three SDKs.
- **smarter-vscode-yaml** reads the live `json-schema` endpoint, which returns
  the same schemas.
- **The weekly API Contract Sync workflow** (in smarter-sh/automation, the
  repository of the project's scheduled jobs: `.github/workflows/apiContractSync.yml`,
  logic in `scripts/api_contract_sync.py`) syncs each of those five repositories'
  `alpha` with the latest release tag on `main`, runs its tests before and after,
  and opens an issue (label `api-contract`) and a pull request (branch
  `api-contract-sync`, a draft when the tests break) in each one that is out of
  date. It posts to #general on Slack. A release that changes the contract
  therefore reaches the SDKs within a week, even if nobody runs `make contracts`.
- A **TypeScript** client: `npx openapi-typescript .../contract/openapi.json -o smarter.d.ts`.
- **Every platform serves the committed `openapi.json`** at `/api/v1/openapi.json`
  (`smarter.apps.api.v1.contract.views`; `/docs/openapi.json` redirects there), with its own `/api/v1` added as the first
  server. The console's OpenAPI page, `/docs/openapi/` (the sidebar's _OpenAPI
  Contract_ link), renders it with Scalar, vendored in the console's
  smarter-console's `packages/smarter-console/public/scalar/` (its README says how to
  upgrade it), and configured in the console's `src/lib/scalar.ts` to call none of
  Scalar's hosted services. It reads the file, so `make api-contract`
  is all it needs.

To check the document with an independent validator, without adding a
dependency to the platform:

```console
python3 -m venv /tmp/oav && /tmp/oav/bin/pip -q install openapi-spec-validator
/tmp/oav/bin/openapi-spec-validator smarter/smarter/apps/api/v1/contract/openapi.json
```
