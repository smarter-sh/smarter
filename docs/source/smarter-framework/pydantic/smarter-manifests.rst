Smarter API Manifests (SAM)
=============================

Smarter Api Manifests (SAM) are fundamental to the Smarter Framework. Manifests are inspired by `Kubernetes <https://kubernetes.io/>`__
manifests and are used to define configurations for various components within the Smarter ecosystem. They are
written in YAML format and provide a structured way to declare resources, settings, and behaviors.
Smarter Manifests enable developers to easily manage and deploy configurations in a consistent manner across different
environments.

.. toctree::
   :maxdepth: 1
   :caption: Smarter API Manifests Technical References

   smarter-manifests/pydantic-models
   smarter-manifests/sam-loader
   smarter-manifests/broker-model
   smarter-manifests/error-handling
   smarter-manifests/validation-strategy

.. literalinclude:: ../../../../smarter/smarter/apps/plugin/data/stackademy/chatbot-stackademy-sql.yaml
   :language: yaml
   :caption: Example Smarter Manifest


The point of using YAML manifest files is to facilitate a human readable way to define complex
AI resources and their configurations, taking into consideration that something systematic on
the backend will ulimately need to be able to read, validate and correctly execute the commands
necessary to bring those resources to life. By ‘resource’ we mean to say anything from an AI Model,
to a Data Pipeline, to an entire Application. Persisting such resources may involve any number
of kinds of technologies, 3rd party services, and infrastructure.

The authors saw first hand how effectively the `Kubernetes <https://kubernetes.io/>`__ project
was able to solve similar
problems in the DevOps space by defining a systematic way to describe infrastructure resources
using YAML manifest files, and then building a robust ecosystem of tools around those manifests
to validate, deploy, and manage those resources. Inspired by this success, the authors designed
the Smarter Api Manifest (SAM) specification to bring similar benefits to the AI development space.

Example Manifests
-----------------

See the `Smarter Cloud Platform Docs <https://platform.smarter.sh/docs/manifests/>`__ for a
complete set of example manifests.

Json Schemas
------------

Developers can build on top of the Smarter Manifest framework by leveraging our prebuilt Smarter
JSON Schemas, See the `Smarter Json Schemas Docs <https://platform.smarter.sh/docs/json-schemas/>`__ for details.
