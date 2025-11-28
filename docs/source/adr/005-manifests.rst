ADR-005: Manifests
==================

Status
------
Accepted

Context
-------
Smarter's resource management is based on YAML manifests that closely resemble those used by Kubernetes in appearance, behavior, purpose, and functionality. This approach ensures consistency, portability, and declarative resource management across the platform.

Decision
--------
Any new Smarter resource must include a corresponding YAML manifest. All CRUD operations must be implemented using YAML manifests. The project will not accept direct HTTP verb-based CRUD operations. The REST API itself is built on the Broker model, which depends on manifests for all resource management.

Alternatives Considered
-----------------------
- Allowing direct HTTP verb-based CRUD operations.
- Supporting both manifest-based and direct CRUD operations.
- Using alternative formats for resource definitions.

Consequences
------------
- **Positive:**
  - Ensures consistency and declarative management of resources.
  - Aligns with industry standards and Kubernetes best practices.
  - Simplifies auditing, versioning, and automation of resource changes.
- **Negative:**
  - Requires all contributors to work with YAML manifests.
  - May introduce a learning curve for those unfamiliar with manifest-driven workflows.
  - Limits flexibility for clients expecting traditional RESTful CRUD operations.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
