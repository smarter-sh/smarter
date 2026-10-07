ADR-002: Docker
===============

Status
------
Accepted

Context
-------
The project needs a consistent and reproducible environment for development, testing, and production. Supporting multiple deployment methods increases complexity and maintenance overhead. Docker is widely adopted, well-supported, and enables seamless environment parity across all stages of the software lifecycle.

Decision
--------
The project will run natively on Docker for all environments, including development, testing, and production. We do not support any alternative means of build or deployment.

Alternatives Considered
-----------------------
- Supporting local (non-Docker) development environments.
- Using other containerization or virtualization technologies.
- Allowing manual or custom deployment processes.

Consequences
------------
- **Positive:**
  - Consistent environments across all stages.
  - Simplified onboarding and setup for new developers.
  - Easier automation of builds, tests, and deployments.
  - Reduced risk of "works on my machine" issues.
- **Negative:**
  - Requires all contributors and users to have Docker installed.
  - May limit flexibility for those preferring alternative workflows.
  - Potential performance overhead in some development environments.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
