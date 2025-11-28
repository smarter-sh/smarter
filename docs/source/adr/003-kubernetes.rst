ADR-003: Kubernetes
===================

Status
------
Accepted

Context
-------
The project requires a scalable, reliable, and cloud-native orchestration platform for deploying and managing containerized applications. Kubernetes is the industry standard for container orchestration and is supported by all major cloud providers. However, supporting multiple cloud platforms increases complexity and maintenance overhead.

Decision
--------
Production deployments will use AWS Elastic Kubernetes Service (EKS) as the default and only supported platform. Support for other managed Kubernetes services (such as Azure AKS, Google GKE, Digital Ocean, etc.) may be considered in the future as project needs evolve.

Alternatives Considered
-----------------------
- Supporting multiple cloud providers from the outset.
- Using self-managed Kubernetes clusters.
- Using alternative orchestration platforms.

Consequences
------------
- **Positive:**
  - Simplifies deployment and operational processes by standardizing on AWS EKS.
  - Reduces complexity and maintenance overhead.
  - Leverages AWS’s managed Kubernetes features and integrations.
- **Negative:**
  - Limits production deployments to AWS until support for other providers is added.
  - May require refactoring or additional work to support other cloud providers in the future.

Related ADRs
------------
- [ADR-000: Introduction](000-intro)
- [ADR-002: Docker](002-docker)
