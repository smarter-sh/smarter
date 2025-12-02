Smarter Manifests (SAM)
================================

Smarter Manifests (SAM) are fundamental to the Smarter Framework. Manifests are inspired by `Kubernetes <https://kubernetes.io/>`__
manifests and are used to define configurations for various components within the Smarter ecosystem. They are
written in YAML format and provide a structured way to declare resources, settings, and behaviors.
Smarter Manifests enable developers to easily manage and deploy configurations in a consistent manner across different
environments.

.. code-block:: yaml
   :caption: Example Smarter Manifest

    apiVersion: smarter.sh/v1
    kind: Chatbot
    metadata:
      name: stackademy_sql
      description: Stackademy University course catalogue inquiries using the Stackademy SQL plugin.
      version: 1.0.0
    spec:
      config:
        deployed: false
        provider: openai
        defaultModel: gpt-4o-mini
        defaultSystemRole: >
          You are a helpful assistant. When given the opportunity to utilize
          function calling, you should always do so. This will allow you to
          provide the best possible responses to the user. DO NOT GUESS. IF
            YOU DON'T KNOW THE ANSWER, RESPOND THAT YOU DON'T KNOW.
        defaultTemperature: 0.5
        defaultMaxTokens: 1024
        appName: Stackademy SQL Chatbot
        appAssistant: Stanley
        appWelcomeMessage: Welcome to Stackademy SQL Chatbot! How can I help you today?
        appExamplePrompts:
          - "Do you offer any courses on AI?"
          - "My budget is $1,000. What courses can I take?"
          - "I want to study programming. What do you suggest?"
        appPlaceholder: "Ask me anything about Stackademy courses..."
        appInfoUrl: https://stackademy.edu/online-courses
      plugins:
        - stackademy_sql
      functions:
        - weather

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

SAM Technical References
------------------------

.. toctree::
   :maxdepth: 1

   sam/error-handling
   sam/pydantic-models
   sam/sam-loader
   sam/validation-strategy
