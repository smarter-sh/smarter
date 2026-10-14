Smarter CLI
===========

The Smarter cli is a standalone application written in Go lang that runs
on Windows, macOS and Linux. It is separately managed in
`github.com/smarter-sh/smarter-cli <https://github.com/smarter-sh/smarter-cli>`__.
It is a lightweight command-line UI for interacting with the `Smarter
API <../smarter/smarter/apps/api/v0/cli/>`__.

To use the same API from your own software, see the :doc:`Python <smarter-python>`,
:doc:`Node.js <smarter-nodejs>` and :doc:`Go <smarter-golang>` SDKs, which also read the cli's
configuration file.

Installation
------------

See `https://smarter.sh/cli <https://smarter.sh/cli>`__ for download instructions for Windows, macOS and Linux.

Usage
------------

Works like kubectl, the Smarter cli uses a verb-noun command structure to
interact with Smarter resources. The general format is:

.. code-block:: text

  smarter [command] [flags]

  Available Commands:
    apply       Apply a Smarter manifest
    chat        Chat with an LLMClient
    completion  Generate the autocompletion script for the specified shell
    configure   Configure the smarter command-line interface
    delete      Permanently delete a Smarter resource
    deploy      Deploy a resource
    describe    Return a manifest for the resource kind
    get         Generate a list of Smarter resources
    help        Help about any command
    json-schema Retrieve the JSON Schema of a resource kind's manifest
    logs        Returns the logs for a resource
    manifest    Generate an example manifest for the resource kind
    resources   List the resource kinds of the Smarter Platform
    status      Retrieve real-time status of the Smarter Platform
    undeploy    Undo a Smarter resource deployment.
    validate    Validate a Smarter manifest without applying it
    version     Retrieve version information
    whoami      Retrieve information about the api_key owner

  Flags:
        --api_key string         Smarter API key to use
        --config string          config file (default is $HOME/.smarter/config.yaml)
        --environment string     environment to use: local, alpha, beta, next, prod. Default is prod
    -h, --help                   help for smarter
        --max_retries int        how many times to resend a request that failed for a transient reason (default 2)
    -o, --output_format string   output format: json, yaml, tabular (default "json")
        --timeout duration       how long to wait for the Smarter API, e.g. 30s or 5m (default 2m0s)
    -v, --verbose                verbose output

On a new machine, run ``smarter configure`` first. It writes your account
number, api key and root domain to ``~/.smarter/config.yaml``, readable only
by you, with one api key per environment. The Python, Node.js and Go SDKs read
the same file.

Flags override the file, and so do the environment variables that the SDKs
share: ``SMARTER_API_KEY``, ``SMARTER_ENVIRONMENT``, ``SMARTER_BASE_URL`` (a
platform url such as ``http://localhost:9357``, instead of the environment's),
``SMARTER_CONFIG_FILE``, ``SMARTER_TIMEOUT`` (seconds), ``SMARTER_MAX_RETRIES``
and ``SMARTER_LOG`` (``debug`` or ``info`` turns on ``--verbose``). The cli
doesn't read ``SMARTER_ROOT_DOMAIN``, which the platform's own settings use for
its apex domain.

Commands
--------

The cli implements a set of verbs for working with Smarter resources. Each one
is a single request to the platform's cli api, ``/api/v1/cli/``.

- **apply** migrates a Smarter resource from its present state to the one
  described in a manifest. ``--dry-run`` validates the manifest instead, as
  **validate** does, and changes nothing.
- **validate** checks a manifest against the model of its kind, as apply does
  first, without saving it. It prints each error with its path in the
  manifest, and exits 1 when the manifest is invalid, so it can guard a CI
  pipeline.
- **get** lists the resources of a kind, as a table unless ``-o`` says
  otherwise.
- **describe** returns the manifest of a resource, which ``-o yaml`` makes
  ready to edit and apply again.
- **delete** permanently, unrecoverably destroys a Smarter resource.
- **deploy** and **undeploy** manage the deployment of the kinds that have
  one: LLMClient, LLMHost, LLMHostCompute, VectorStore, CustomDomain,
  SmarterAuthToken (``apikey``) and User, which deploying activates.
  ``smarter resources`` reports which kinds deploy. Deploying can create real,
  billable infrastructure, such as an LLMHostCompute's node group.
  CustomDomains and LLMHostComputes can't be undeployed yet.
- **logs** returns the log data of a resource.
- **manifest** generates an example manifest of a kind, as yaml.
- **json-schema** returns the JSON Schema that manifests of a kind are
  validated against, for editors such as VS Code.
- **chat prompt** sends a prompt to an LLMClient and prints its response;
  **chat config** returns the LLMClient's chat configuration. Both take the
  LLMClient's name with ``--llmclient``. Prompts from one machine share a
  session until ``--new_session`` starts another.
- **resources** lists every resource kind of the platform.
- **status**, **version** and **whoami** report on the platform, the cli and
  the owner of the configured api key.

Errors go to stderr, and every failed command exits with status 1. A request
that fails for a transient reason (no response, or a 408, 429, 502, 503 or 504
from a proxy) is sent again, up to ``--max_retries`` times, as the SDKs do.

.. raw:: html

   <!-- markdownlint-disable MD034 -->

Related API endpoints
---------------------

Every command posts to one route of the platform's cli api, under
``/api/v1/cli/``: ``apply/``, ``validate/``, ``get/<kind>/``,
``describe/<kind>/``, ``delete/<kind>/``, ``deploy/<kind>/``,
``undeploy/<kind>/``, ``logs/<kind>/``, ``example-manifest/<kind>/``,
``json-schema/<kind>/``, ``prompt/<name>/``, ``prompt/config/<name>/``,
``resources/``, ``status/``, ``version/`` and ``whoami/``. Their requests and
responses are documented in the platform's :doc:`OpenAPI document
<smarter-openapi>`, which the cli's tests check every command against.

Manifest Spec
-------------

See :doc:`Smarter Manifest Specification <developer-reference/lib/drf/manifest>`


Kind
~~~~

Every command that takes a ``<kind>`` accepts each kind of resource that a
manifest can declare, such as ``llmclient``, ``guardrail``, ``secret``,
``plugin`` or ``vectorstore``. ``smarter resources`` lists them all, and
``smarter get --help`` shows their command names.

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
  Examples: https://docs.smarter.sh/manifest/secret/ and
  https://docs.smarter.sh/json-schema/secret/
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
