ADR-006: Rest API
=================

ADR-006: Rest API
=================

Status
------
Accepted

Context
-------
The primary purpose of the platform is to implement a REST API. Any features that include UI elements are facilitated by the Smarter REST API, ensuring that all interactions go through a consistent interface.

Decision
--------
The Smarter REST API will serve as the main interface for all platform features. Where possible, the REST API will use the broker model as an abstraction layer for resource management. Views for REST API URL endpoints are intended to be overtly simple in implementation, ideally not exceeding a dozen lines of code.

Alternatives Considered
-----------------------
- Implementing complex logic directly in REST API views.
- Allowing UI elements to bypass the REST API for certain operations.
- Using alternative abstractions instead of the broker model.

Consequences
------------
- **Positive:**
  - Promotes a clear separation of concerns between API and UI.
  - Simplifies maintenance and testing by keeping views minimal.
  - Ensures consistency and reusability through the broker model.
- **Negative:**
  - May require additional abstraction layers for complex features.
  - Limits flexibility for implementing advanced view logic directly in endpoints.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
- [ADR-024: Broker Model](024-broker-model)
