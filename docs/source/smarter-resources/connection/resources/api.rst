API Connection
================

An API Connection represents a connection to an external API service within the Smarter platform.
It encapsulates the necessary configuration and credentials (``Smarter Secret``) required to interact with the API,

.. code-block:: yaml
   :caption: Example API Connection Manifest

   # The api of this platform, whose /api/v1/demos/stackademy/course-catalogue/ is the Stackademy course catalogue.
   #
   # This file is a template. When a Smarter platform loads this repository, it fills in the two placeholders
   # of baseUrl below with its own address, e.g. https://alpha.platform.example.com, or
   # http://localhost:9357 in local development, so that the Stackademy ApiPlugin queries the api of its own
   # platform. To apply this file yourself, save a copy as a .yaml file with your platform's address in baseUrl.
   #
   # The course catalogue is password protected: this connection sends its apiKey Secret as a bearer
   # token, and the course catalogue accepts the apiKey Secret of the Smarter account's smarter_test_api.
   apiVersion: smarter.sh/v1
   kind: ApiConnection
   metadata:
     description: Api connection to this platform's Stackademy course catalogue, /api/v1/demos/stackademy/course-catalogue/
     name: smarter_test_api
     version: 0.1.0
     tags:
       - test
       - api
       - sample
     annotations:
       - smarter.sh/smarter-test-api/creator: QA Team
       - smarter.sh/smarter-test-api/purpose: unit testing
       - smarter.sh/smarter-test-api/release-date: 2024-06-15
       - smarter.sh/smarter-test-api/backward-compatibility: true
   spec:
     connection:
       baseUrl: ${environment_platform_scheme}://${environment_platform_domain}
       timeout: 30
       authMethod: token
       apiKey: smarter_test_api

From `connections/api/smarter-test-api.yaml.tpl <https://github.com/smarter-sh/stackademy/blob/main/connections/api/smarter-test-api.yaml.tpl>`__ in the :doc:`Stackademy example project </smarter-framework/smarter-manifests/stackademy>`.

Technical References
--------------------

- Django ORM Model: :py:class:`smarter.apps.connection.models.ApiConnection`
- :doc:`SAM Broker <../manifest/brokers/api-connection>`
- :doc:`SAM Pydantic Class Reference <../manifest/models/api-connection>`
