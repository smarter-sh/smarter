ADR-023: API Versioning
=======================

Status
------
Accepted. This decision replaces an earlier one, which synced the api version to the repository's
semantic version.

Context
-------
Smarter has several public interfaces, and integrators depend on each of them:

- the REST api, served under ``/api/v1/`` and described by ``openapi.json``,
- the manifests (SAM, :doc:`ADR-005 <005-manifests>`), whose ``apiVersion`` is ``smarter.sh/v1``,
  and whose JSON Schemas are committed in ``smarter.apps.api.v1.contract``,
- the Smarter Chat api contract (:mod:`smarter.apps.prompt.contract`), which the Smarter Chat npm
  package and other clients read.

The earlier decision tied every one of these to the repository's semantic version
(:doc:`ADR-020 <020-semantic-versioning>`). It was never practical, and the code never followed it.
The repository's version changes many times a week, mostly for changes that don't touch any
interface, while the urls and manifests have stayed at ``v1``. If the rule had been followed, Smarter
2.0 would have forced every client onto ``/api/v2/`` and ``smarter.sh/v2``, even for an api that
had not changed, and every caller would have had to update its urls at every major release.

Meanwhile the Smarter Chat contract showed what works: version 2 is the default, version 1 is still
returned to the clients that need it, a client chooses by request header, and version 1 is marked
deprecated in the code and the docs.

Decision
--------
Each public interface is versioned on its own, and independently of the product.

1. **The product version** (``vMAJOR.MINOR.PATCH``, :doc:`ADR-020 <020-semantic-versioning>`)
   versions the platform: the Docker image, the Helm chart, the settings and the database
   migrations. A major release says that upgrading may require manual work, and its release notes
   say what that work is.
2. **The REST api** is versioned by url path, ``/api/v<N>/``. Within a version, a change is
   backward compatible: a new endpoint, a new optional request field, a new response field, or a new
   value that clients are documented to tolerate. Anything else, such as removing or renaming a
   field or an endpoint, changing a field's type or meaning, or making an optional field required,
   is a breaking change, and needs ``/api/v<N+1>/``.
3. **Manifests** are versioned by ``apiVersion``, ``smarter.sh/v<N>``, with the same rules, applied
   to a kind's fields as its JSON Schema declares them. ``SmarterApiVersions`` lists the versions
   that the platform accepts.
4. **Contracts that clients negotiate**, such as the Smarter Chat api contract, have their own
   integer version. The client asks for the version it needs, e.g. with the
   ``X-Smarter-Capabilities`` request header, and the platform keeps a default for clients that
   don't ask.
5. **Deprecation.** A version, endpoint, kind or field is deprecated before it is removed:

   - it is marked deprecated in the code (``typing_extensions.deprecated`` or a
     ``DeprecationWarning``), in its OpenAPI or JSON Schema description, and in the docs, with
     its replacement,
   - it keeps working for at least two minor releases of the product, and for at least six months,
     whichever is longer,
   - it is removed only in a major release of the product, whose release notes list the removal.

6. **Enforcement.** The committed ``openapi.json``, SAM JSON Schemas and chat contract schema are
   the record of each interface. A pull request that changes one of them in a way that breaks
   compatibility must add a new version instead, or carry a ``BREAKING CHANGE`` footer
   (:doc:`ADR-020 <020-semantic-versioning>`), which makes the next release a major one.

Alternatives Considered
-----------------------
- **Sync every interface to the repository's version.** The earlier decision. It versions clients
  out of urls that haven't changed, and the frequent releases make the version meaningless as a
  compatibility signal.
- **Version the REST api by header** (e.g. ``Accept: application/vnd.smarter.v1+json``). It keeps
  the urls stable, but it hides the version from logs, browsers and the cli, and the urls already
  carry ``v1``.
- **One version for all of the interfaces.** It forces a manifest change to bump the REST api, and
  the other way around, though different clients read them.

Consequences
------------
- **Positive:**

  - Clients upgrade the platform without changing their urls or manifests, unless an interface
    they use actually breaks.
  - Each interface states its own compatibility promise, which is what an integrator needs before
    building on it.
  - Breaking changes are visible in review, as a diff to a committed contract, and in the version
    numbers, as a new api version or a major release.

- **Negative:**

  - An interface that has two supported versions has two code paths to maintain and test, as the
    Smarter Chat contract's version 1 and version 2 do.
  - The version of each interface must be documented next to the product version, so that a reader
    knows which platform releases support which api versions.
  - The deprecation window delays the removal of old code.

Related ADRs
------------
- :doc:`ADR-005: Manifests <005-manifests>`
- :doc:`ADR-006: REST API <006-rest-api>`
- :doc:`ADR-020: Semantic Versioning <020-semantic-versioning>`
- :doc:`ADR-031: Pydantic Models Over Raw JSON <031-pydantic-over-json>`
