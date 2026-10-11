ADR-031: Pydantic Models Over Raw JSON
======================================

Status
------
Accepted

Context
-------
Much of what Smarter's code builds, returns and reads is JSON: api responses, the configuration of a
chat, an LLM's completion, the rows of a chat session's history. Much of it used to be handled as raw
JSON: nested ``dict`` objects built key by key, renamed by searching for strings in their keys, read
with chains of ``.get()``, and typed, if at all, as ``list[Any]`` or ``dict[str, Any]``.

Raw JSON carries whatever is put into it, and nothing checks what comes out. A review of the Smarter
Chat apis found three disclosures that had gone unnoticed for that reason:

- The configuration that a deployed LLMClient returns to any page that embeds it included its
  owner's profile, because the LLMClient was serialized with every field (``fields = "__all__"``).
- A prompt's result included the complete requests to and responses from the LLM, system prompt and
  tool results included.
- The completion's ``metadata`` described each tool call's plugin with its owner's profile.

The same looseness hid drift between the backend and its clients: the React app's test fixtures,
written by hand, had diverged from what the backend actually returned, and its tests passed anyway.
Raw JSON also leaves type checkers blind. A Django REST Framework serializer's ``.data`` is a
``ReturnDict``, even when it holds a list.

Smarter already validates its manifests with Pydantic (:doc:`ADR-005 <005-manifests>`), and that
approach has proved reliable.

Decision
--------
Any sizable JSON that code builds, returns or reads is modeled with Pydantic.

1. **Build the data from the model**, then dump it (``model.model_dump(mode="json")``). Don't build a
   dict and validate it afterwards, and don't merely document its shape.
2. **No** ``list[Any]`` **or** ``dict[str, Any]``. A list holds a named model. A value that is truly
   arbitrary JSON, such as a tool's result, is ``pydantic.JsonValue``, which is exactly JSON, unlike
   ``Any``.
3. **Serialized Django ORM rows are models of the row.** The model has exactly the row's fields, and
   forbids any other (``extra="forbid"``). A ``from_model(row)`` classmethod builds it from the
   instance, not from a serializer's output. A foreign key is the related row's id. A field with
   ``choices`` is a ``Literal``, and a test fails if the two differ.
4. **Third-party shapes**, such as the OpenAI api's messages, completions and tool calls, are modeled
   with the fields that the code reads. A model allows extra fields only where providers add their
   own, and its docstring says so.
5. **Transformations are methods** of the model, such as a public view of a configuration, or its
   form in an older version of an api, rather than functions that rewrite dumped dicts.
6. **JSON that leaves the repository gets a published schema.** When a client in another language
   reads the data, for example a React app or an npm package, the repository commits the models' JSON
   Schema (``pydantic.json_schema.models_json_schema``), the client generates its types from it, and
   a test fails when the committed schema is out of date.
7. **A tightened type is checked against real data**, the rows of a real database and a real
   response, not only the test fixtures.

The Smarter Chat api contract, :mod:`smarter.apps.prompt.contract`, is the reference implementation:
its models build the responses, its strict models of ORM rows build the configuration's lists, its
schema is ``chat-contract.schema.json``, and Smarter Chat generates its TypeScript types from it
(``make chat-contract``).

Alternatives Considered
-----------------------
- **Django REST Framework serializers.** They suit model CRUD apis, but their output is untyped
  (``ReturnDict``), and ``fields = "__all__"`` exposes whatever a model gains later. They also can't
  describe data that isn't a model, such as an LLM's completion.
- **TypedDict.** It gives type checkers the shape, but validates nothing at runtime, and can't
  produce a JSON Schema for clients.
- **Dataclasses.** Like TypedDict, without validation or schema generation, and with no support for
  extra fields where they're needed.
- **Documenting the shapes.** The documentation drifts from the code, and nothing enforces it.

Consequences
------------
- **Positive:**

  - Data that leaves the platform contains exactly what its model declares: a field that isn't
    declared, such as an owner's profile, is rejected or left out, not carried along.
  - Type checkers and IDEs see real types, and invalid data fails where it is built, not in a client.
  - Clients in other languages generate their types from the same models, and tests catch drift on
    both sides.
  - The models document the data, in docstrings that Sphinx publishes.

- **Negative:**

  - Every change to the data's shape is also a change to its model, and, for published data, to its
    schema and its clients' generated types.
  - A strict model fails on data it doesn't expect, such as legacy rows, so a tightened type must be
    validated against real data before it ships.
  - Models of ORM rows duplicate the rows' fields, so a model's tests must check the parts that can
    drift, such as ``choices``.

Related ADRs
------------
- :doc:`ADR-005: Manifests <005-manifests>`
- :doc:`ADR-006: REST API <006-rest-api>`
- :doc:`ADR-023: API Versioning <023-api-versioning>`
