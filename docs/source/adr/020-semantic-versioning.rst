ADR-020: Semantic Versioning
============================

Status
------
Accepted

Context
-------
Consistent versioning is important for release management, automation, and communication with users. Semantic versioning provides a standardized approach to versioning software releases
including across disparate platforms and package managers like GitHub, PyPi, DockerHub and ArtifactHUB.

Decision
--------
The project leverages the GitHub Action, `cycjimmy/semantic-release-action`, for managing semantic version bumps. This currently resides in `pushMain.yml`, which runs on pushes to the main branch in GitHub.

File modifications due to version bumps are implemented in `scripts/bump_version.py`, which is itself triggered by the semantic-release configuration in the root of this repo (`./release.config.js`).

Alternatives Considered
-----------------------
- Manual version bumping.
- Using other versioning tools or workflows.

Consequences
------------
- **Positive:**
  - Automates and standardizes version management.
  - Reduces manual errors and streamlines release processes.
- **Negative:**
  - Requires maintenance of automation scripts and configuration.
  - Contributors must understand the automated versioning workflow.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
