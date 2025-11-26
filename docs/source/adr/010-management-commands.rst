ADR-010: Management Commands
============================

Status
------
Accepted

Context
-------
Creation of Django `manage.py` commands is generally discouraged since these are only available to admins with direct access to Kubernetes pods. This limits their usefulness for most operational and user-facing tasks.

Decision
--------
We generally limit the use of `manage.py` commands to deployment activities, as found in the `Makefile` and the Helm chart for jobs.

Alternatives Considered
-----------------------
- Allowing widespread use of `manage.py` commands for various tasks.
- Implementing alternative interfaces for operational tasks.

Consequences
------------
- **Positive:**
  - Reduces reliance on commands only accessible within Kubernetes pods.
  - Encourages more accessible and automated operational workflows.
- **Negative:**
  - May require additional tooling for tasks traditionally handled by management commands.
  - Limits flexibility for quick, ad-hoc administrative actions.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
