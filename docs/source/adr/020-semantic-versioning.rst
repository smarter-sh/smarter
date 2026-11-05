ADR-020: Semantic Versioning
============================

Status
------
Accepted. Amended to state what the product's version promises from version 1.0.0 on.

Context
-------
Consistent versioning is important for release management, automation, and
communication with users. Semantic versioning provides a standardized approach
to versioning software releases including across disparate platforms and
package managers like GitHub, PyPi, DockerHub and ArtifactHUB.

Before 1.0.0, Smarter changed quickly, and its 0.x versions promised nothing: a minor release could
rename a Django app, regenerate an app's ``0001_initial`` migration, or rename a setting. That was
the right trade while the feature roadmap was being built. Once the roadmap is complete and running
in production, the people who self-host Smarter need to know which upgrades are safe to take without
reading every commit. Version 1.0.0 is that promise.

:doc:`ADR-023 <023-api-versioning>` versions the public interfaces (the REST api, the manifests and
the Smarter Chat contract) separately from the product. This ADR covers the product itself: the
Docker image, the Helm chart, the settings and the database.

Decision
--------

1. **How a version is cut.** The GitHub Action ``cycjimmy/semantic-release-action`` runs
   semantic-release after every merge into main, from the build workflow, and as prereleases on
   ``alpha`` and ``beta``. Its configuration is ``release.config.js`` in the root of this repo, and
   ``scripts/bump_version.py`` writes the new version into the files that carry it. The Conventional
   Commits type of each commit decides the bump:

   - ``fix`` and ``perf``: patch,
   - ``feat``: minor,
   - ``docs``, ``test``, ``style`` and ``refactor``: no release,
   - a ``!`` after the type or scope, or a ``BREAKING CHANGE:`` footer: major.

2. **What a major version promises.** From 1.0.0 on, an upgrade from any release to a later one with
   the same major version needs no manual steps. ``helm upgrade``, whose init Job runs
   ``manage.py migrate`` and ``manage.py initialize_platform``, is the whole procedure, and skipping minor
   releases is supported. In particular, within a major version:

   - **Database migrations are append-only.** A migration that has been released is never edited,
     deleted or regenerated. A schema change is a new migration, with a data migration for the rows
     that already exist, and it runs unattended on a production-sized database.
   - **Settings and Helm values are kept.** A ``SMARTER_`` environment variable or a value in the
     Helm chart's ``values.yaml`` is not removed, renamed or given a new meaning. A rename keeps the
     old name working as a deprecated alias that logs a warning, until the next major version. A new
     setting has a default that keeps the behavior of existing installations.
   - **Supported infrastructure is kept.** The supported versions of Python, MariaDB, Redis,
     Kubernetes and Helm are not narrowed.
   - **Public interfaces don't break**, under the rules and the deprecation window of
     :doc:`ADR-023 <023-api-versioning>`. Resources that were applied under an earlier release keep
     working.

   Internal Python modules, Celery task names, log messages, the Django admin and the web console's
   pages and urls are not part of the promise, unless the documentation says otherwise.

3. **A breaking change is anything that needs a manual step on upgrade**: a migration that can't
   run unattended, a removed or renamed setting or Helm value, a dropped version of a supported
   dependency, or the removal of a deprecated interface. Its commit carries a ``BREAKING CHANGE:``
   footer that says what an operator must do, and the release notes of the major release repeat
   it. A breaking change is batched with others where possible, so that major releases stay rare.

4. **Fixes, including security fixes, are released on the latest version only.** Smarter is a
   community project, without the people to backport fixes to older minor or major versions. An
   installation gets a fix by upgrading, which rule 2 makes safe within a major version.

5. **The road to 1.0.0.** Before 1.0.0 is cut:

   - each Django app's migrations are consolidated one last time, and those files become the
     baseline that rule 2 protects,
   - the commit that starts 1.0.0 carries a ``BREAKING CHANGE:`` footer with the steps to upgrade a
     0.x database. semantic-release turns a breaking change on 0.x into 1.0.0, and on ``alpha``
     into ``1.0.0-alpha.N`` prereleases, so the footer lands when the release-candidate period
     starts, not before,
   - the release-candidate period on ``alpha`` takes only fixes, until production has run a
     ``1.0.0-alpha`` prerelease without new failures.

   An upgrade to 1.0.0 is supported from the last 0.x release only.

6. **Other repositories version themselves.** The cli, the Python, Node.js and Go SDKs, the VS Code
   extension and each Smarter Extension follow semantic versioning on their own, independently of
   the platform, as :doc:`ADR-023 <023-api-versioning>` versions the interfaces they call. Each
   one's documentation states the platform and api versions that it supports.

Alternatives Considered
-----------------------
- **Manual version bumping.** Error-prone, and it separates the version from the commits that
  justify it.
- **Calendar versioning** (e.g. ``2026.11.0``). It suits the frequent releases, but says nothing
  about compatibility, which is what an operator needs to know before upgrading.
- **Staying on 0.x.** It keeps every option open for the maintainers, and leaves every operator
  guessing.

Consequences
------------
- **Positive:**

  - Automates and standardizes version management.
  - An operator can tell from the version number alone whether an upgrade is safe to take
    unattended.
  - Breaking changes are visible in review, as a ``!`` or a ``BREAKING CHANGE:`` footer, and in the
    release notes, with their upgrade steps.

- **Negative:**

  - Requires maintenance of automation scripts and configuration.
  - Contributors must understand the automated versioning workflow, and mark breaking changes
    themselves: semantic-release can't detect one that isn't marked.
  - Append-only migrations accumulate, and renames take a deprecation cycle instead of a single
    commit.
  - Without backports, an installation that can't upgrade doesn't get fixes.

Related ADRs
------------
- :doc:`ADR-000: Introduction <000-intro>`
- :doc:`ADR-010: Management Commands <010-management-commands>`
- :doc:`ADR-014: CI/CD <014-ci-cd>`
- :doc:`ADR-017: Database <017-database>`
- :doc:`ADR-023: API Versioning <023-api-versioning>`
