Smarter API Manifests (SAM)
=============================

Smarter Api Manifests (SAM) are fundamental to the Smarter Framework. Manifests are inspired by `Kubernetes <https://kubernetes.io/>`__
manifests and are used to define configurations for various components within the Smarter ecosystem. They are
written in YAML format and provide a structured way to declare resources, settings, and behaviors.
Smarter Manifests enable developers to easily manage and deploy configurations in a consistent manner across different
environments.

Smarter manifests are utf-8 text documents, formatted as either yaml or json, inspired by Kubernetes’ kubectl, itself modeled on the
`OpenAPI Specification v3.x <https://spec.openapis.org/oas/latest.html>`__. The actual
implementation of this specification is located `here <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/api>`__. The Smarter API can
manage `escaped <https://en.wikipedia.org/wiki/Escape_character>`__ representations of characters outside of the utf-8 standard.

The Smarter API invokes database commands, AWS cloud infrastructure operations, and Kubernetes orchestration tasks
based on the declarations found in Smarter Manifests. SAM manifests provide you and your team with an important
layer of abstraction that enables you to focus on achieving the desired state of your AI resources rather than
on the low-level implementation details of how to get there.

The basic stsructure of a Smarter Api Manifest (SAM) YAML document includes the following key sections:

- **apiVersion**: Specifies the version of the API schema that the manifest adheres to.
- **kind**: Indicates the type of resource being defined (e.g., Account, Plugin, Chatbot).
- **metadata**: Contains metadata about the resource, such as its name, labels, and annotations. Metadata varies by resource kind, but always includes a name, description and version.
- **spec**: Defines the desired state and configuration of the resource. The spec section varies considerably by resource kind.
- **status**: (Optional) Provides information about the current state of the resource. This section is read-only and managed by the system.

In addition to this basic structure, there are also a number of important style conventions that
Pydantic helps to enforce for SAM manifests:

- YAML fields use `camelCase` naming convention.
- Values that are in effect, foreign keys, or references to other resources use `snake_case` naming convention.

Pydantic is also instrumental in validating the rules and relationships between individual fields
within a manifest, ensuring that manifests are well-formed and adhere to the expected structure. The Smarter API
must be able to read, validate, and correctly execute the commands necessary to bring the real-world
resources defined in the manifests in sync to the declaration of the manifest.



The modules and classes below establish the foundation of Smarter's SAM data models.

.. toctree::
   :maxdepth: 2
   :caption: Technical References

   smarter-manifests/example-manifest
   smarter-manifests/enum
   smarter-manifests/pydantic-models
   smarter-manifests/sam-loader
   smarter-manifests/controller
   smarter-manifests/broker-model
   smarter-manifests/error-handling
   smarter-manifests/validation-strategy
