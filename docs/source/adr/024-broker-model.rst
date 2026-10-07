ADR-024: Broker Model
=====================

Status
------
Accepted

Context
-------
The project aims to provide a familiar and consistent experience for users managing resources, similar to Kubernetes. Kubernetes uses a "broker model" for common operations such as get, apply, delete, and example, primarily through the kubectl command-line tool.

Decision
--------
The project will support a "broker model" for resource management, enabling operations like get, apply, delete, and example. The design and behavior will follow the kubectl approach as closely as possible to ensure consistency and ease of use for users familiar with Kubernetes.

Alternatives Considered
-----------------------
- Implementing custom or non-standard resource management operations.
- Using traditional RESTful CRUD operations without a broker abstraction.

Consequences
------------
- **Positive:**
  - Provides a familiar interface for users with Kubernetes experience.
  - Promotes consistency and predictability in resource management.
  - Simplifies automation and scripting by following established patterns.
- **Negative:**
  - May limit flexibility for workflows that differ from the Kubernetes model.
  - Requires contributors to understand the broker model and kubectl conventions.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
- [ADR-005: Manifests](005-manifests)
