SAM Validation Strategy
=====================

The point of using yaml manifest files is to facilitate a human readable way to define
complex AI resources and their configurations, taking into consideration that something
systematic on the backend will ulimately need to be able to read, validate and correct
execute the commands necessary to bring those resources to life. By 'resource' we mean
to say anything from an AI Model, to a Data Pipeline, to an entire Application. Persisting
such resources may involve any number of kinds of technologies, 3rd party services, and
infrastructure.

The authors saw first hand how effectively the Kubernetes project was able to solve
similar problems in the DevOps space by defining a systematic way to describe infrastructure
resources using YAML manifest files, and then building a robust ecosystem of tools around
those manifests to validate, deploy, and manage those resources. Inspired by this success,
the authors designed the Smarter Api Manifest (SAM) specification to bring similar benefits
to the AI development space.

Validation Strategy
--------------------

`Pydantic Models <https://docs.pydantic.dev/latest/>`_ are the backbone of
the Smarter Api Manifest (SAM) specification. They provide a robust
and flexible way to define the structure and validation rules for each type of SAM resource.
To ensure that SAM manifests are valid and conform to the expected structure, a validation strategy
is implemented using Pydantic's built-in validation capabilities.
