ADR-009: Async Tasks
====================

Status
------
Accepted

Context
-------
IO intensive operations, such as database writes, can block application performance and reduce responsiveness if handled synchronously. Asynchronous task processing allows these operations to be handled efficiently in the background.

Decision
--------
Where possible, IO intensive operations like database writes will be implemented as Celery asynchronous tasks, using Django's core feature set for worker threads.

Alternatives Considered
-----------------------
- Handling all IO operations synchronously within the main application process.
- Using alternative asynchronous task processing frameworks.

Consequences
------------
- **Positive:**
  - Improves application responsiveness and scalability.
  - Offloads heavy IO operations to background workers.
  - Leverages Django and Celery’s robust ecosystem and features.
- **Negative:**
  - Adds operational complexity in managing Celery workers.
  - Requires contributors to understand asynchronous task patterns.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
