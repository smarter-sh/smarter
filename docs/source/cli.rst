Smarter API Command-line Interface
==================================

The Smarter cli is a standalone application written in Go lang that runs
on Windows, macOS and Linux. It is separately managed in
`github.com/smarter-sh/smarter-cli <https://github.com/smarter-sh/smarter-cli>`__.
It is a lightweight command-line UI for interacting with the `Smarter
API <../smarter/smarter/apps/api/v0/cli/>`__.

Commands
--------

The cli implements a set of verbs for working with Smarter resources

- `apply <../smarter/smarter/apps/api/v0/cli/views/apply.py>`__:
  executes services as necessary in order to migrate a Smarter resource
  from its present state to that which is described in the provided
  manifest.
- `delete <../smarter/smarter/apps/api/v0/cli/views/delete.py>`__:
  permanently, unrecoverably destroys a Smarter resource.
- `deploy <../smarter/smarter/apps/api/v0/cli/views/delete.py>`__:
  manages the deploy state of a deployable Smarter resource (Plugin and
  ChatBot).
- `describe <../smarter/smarter/apps/api/v0/cli/views/describe.py>`__:
  returns a report in yaml or json format that is a superset of a
  manifest describing the present state of a Smarter resource.
- `logs <../smarter/smarter/apps/api/v0/cli/views/describe.py>`__:
  returns log data in standard console log format for a Smarter resource
- `status <../smarter/smarter/apps/api/v0/cli/views/status.py>`__:
  returns a report in yaml or json format that provides real-time
  information on the state of the Smarter platform.

.. raw:: html

   <!-- markdownlint-disable MD034 -->

Related API endpoints
---------------------

- https://api.smarter.sh/v0/cli/apply/: Apply a manifest
- https://api.smarter.sh/v0/cli/describe/: print the manifest
- https://api.smarter.sh/v0/cli/deploy/: Deploy a resource
- https://api.smarter.sh/v0/cli/logs/: Get logs for a resource
- https://api.smarter.sh/v0/cli/delete/: Delete a resource
- https://api.smarter.sh/v0/cli/status/: Smarter platform status

Manifest Spec
-------------

The cli is designed to work with a manifest utf-8 text document, in yaml
or json format, inspired by Kubernetes’ kubectl, itself modeled on the
`OpenAPI Specification
v3.x <https://spec.openapis.org/oas/latest.html>`__. The actual
implementation of this specification is located
`here <../smarter/smarter/apps/api/v0/cli/>`__. The Smarter API can
manage `escaped <https://en.wikipedia.org/wiki/Escape_character>`__
representations of characters outside of the utf-8 standard.

`Example
manifest <../smarter/smarter/apps/plugin/data/sample-plugins/example-configuration.yaml>`__

Kind
~~~~

- `Account <../smarter/smarter/apps/account/api/v1/manifests/>`__
- `ApiKey <../smarter/smarter/apps/account/api/v1/manifests/>`__
- `Chat <../smarter/smarter/apps/chat/api/v1/manifests/>`__
- `ChatHistory <../smarter/smarter/apps/chat/api/v1/manifests/>`__
- `ChatPluginUsage <../smarter/smarter/apps/chat/api/v1/manifests/>`__
- `ChatToolCall <../smarter/smarter/apps/chat/api/v1/manifests/>`__
- `ChatBot <../smarter/smarter/apps/chatbot/api/v1/manifests/>`__
- `Plugin <../smarter/smarter/apps/plugin/api/v1/manifests/>`__
- `SqlConnection <../smarter/smarter/apps/plugin/api/v1/manifests/>`__
- `ApiConnection <../smarter/smarter/apps/plugin/api/v1/manifests/>`__
- `User <../smarter/smarter/apps/account/api/v1/manifests/>`__
- `Secret <../smarter/smarter/apps/account/api/v1/manifests/>`__

Broker Model
~~~~~~~~~~~~

Manifest processing depends on a abstract broker service. Brokers are
implemented inside of Django Views and are responsible for mapping the
verb of an http request – get, post, patch, put, delete – to the Python
class containing the necessary services for the manifest ``kind``.
Brokers are responsible for the following:

- Defining a manifest file structure using a collection of Python
  enumerated data types along with basic
  `Pydantic <https://pydantic.dev/>`__ features.
- Reading and parsing a manifest document in yaml or json format
- Validating manifests, using `Pydantic <https://pydantic.dev/>`__
  models that enforce format, syntax, and data and business rule
  validations.
- Instantiating the correct Python class for the manifest
- Implementing the services that back http requests: get, post, patch,
  put, delete

A brokered entity consists of the following:

- `Pydantic
  model <../smarter/smarter/apps/account/manifest/models/secret/>`__.
  This is a Pydantic model that describes the Manifest yaml document.
  Smarter manifests closely resemble Kubernetes manifests.
- `Broker <../smarter/smarter/apps/account/manifest/brokers/secret.py>`__.
  Brokers marshal requests to the correct Broker class and method.
- `Transformer <../smarter/smarter/apps/account/manifest/transformers/secret.py>`__.
  Transformers map data to/from a Smarter manifest and a Django object
  relational model (ORM).
- `Docs url endpoints <../smarter/smarter/apps/docs/urls.py>`__.
  Examples: https://platform.smarter.sh/docs/manifest/secret/ and
  https://platform.smarter.sh/docs/json-schema/secret/
- `Kind
  registration <../smarter/smarter/apps/api/v1/manifests/enum.py>`__
- `Broker
  registration <../smarter/smarter/apps/api/v1/cli/brokers.py>`__. The
  Broker class implements an enumeration of all resource ``Kinds``.
- `Json Schema docs
  view <../smarter/smarter/apps/docs/views/json_schema.py>`__. Json
  schemas describe the Pydantic data model for the brokered resource.
  These are used for data-driven apps and services, such as the VS Code
  extension for Smarter manifests
- `Manifest docs
  view <../smarter/smarter/apps/docs/views/manifest.py>`__. All brokers
  implement an ``example_manifest()`` method which, intuitively,
  generates a valid example Smarter yaml manifest for the ``Kind`` of
  resource.

Code samples
^^^^^^^^^^^^

- Abstract
  `broker <../smarter/smarter/apps/api/v0/manifests/broker.py>`__
- Example implementation for Plugin
  `broker <../smarter/smarter/apps/plugin/api/v0/manifests/broker.py>`__

Controller Model
~~~~~~~~~~~~~~~~

In cases where there exist multiple variations of a manifest ``kind``,
we use a Controller pattern to route a Broker to the correct Python
subclass.

- Abstract
  `controller <../smarter/smarter/apps/api/v0/cli/controller.py>`__
- Example implementation for Plugin
  `controller <../smarter/smarter/apps/plugin/controller.py>`__ as an
  example.
