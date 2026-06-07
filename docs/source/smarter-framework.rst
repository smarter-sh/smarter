Smarter Development Framework
=============================

The Smarter Development Framework is an opinionated, cloud-native application
framework for building, deploying, and managing AI-powered applications at scale.
It provides a complete development platform that spans the entire lifecycle of
AI resources, from local development and dependency management to deployment,
governance, cost management, versioning, and operations.

At the center of the framework is the principle of declarative resource management.
Developers define AI resources, services, configurations, and dependencies using
Smarter Manifests, a standardized YAML-based specification that abstracts away much
of the complexity of the underlying infrastructure. This approach enables teams to
focus on application design and business logic rather than deployment mechanics and
platform integration.

The framework combines the :doc:`Smarter Manifest Specification <smarter-framework/smarter-manifests>`,
the :doc:`Smarter Broker Model <smarter-framework/smarter-broker-model>`, the :doc:`Smarter API <smarter-framework/smarter-api>`,
and a comprehensive set of developer tools into a cohesive platform
for managing AI workloads. Together, these components provide consistent workflows for
creating, versioning, deploying, discovering, and governing AI resources across
environments.

Built on proven open-source technologies including Kubernetes, Docker, Django, React,
TypeScript, and Pydantic, the Smarter Development Framework extends these technologies
with standardized APIs, automation, and developer tooling designed specifically for
enterprise AI applications. The result is a batteries-included platform that enables
developers to build production-ready AI solutions more quickly, with greater consistency,
reliability, and operational control.

This section of the documentation provides the technical reference for the Smarter
Development Framework, including its architecture, specifications, APIs, command-line
tools, SDKs, and supporting technologies.


.. toctree::
   :maxdepth: 1
   :caption: Technical Reference

   smarter-framework/getting-started
   smarter-framework/guides
   smarter-framework/smarter-manifests
   smarter-framework/smarter-api
   smarter-framework/smarter-cli
   smarter-framework/vs-code-extension
   smarter-framework/developer-reference
   smarter-framework/technologies
