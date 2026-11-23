Manifests
=========

Every Smarter resource is declared in a :doc:`Smarter Application Manifest </smarter-framework/smarter-manifests>`
(SAM), and the SDK writes resources exactly as the :doc:`CLI </smarter-framework/smarter-cli>` does: through the
brokered :doc:`manifest API </smarter-framework/smarter-api/cli>`. The platform's broker for the manifest's kind
validates it with the kind's Pydantic models and applies its business rules, so a manifest that the
CLI accepts, the SDK accepts, and the other way round.

The manifest API
----------------

``client.manifests`` has the CLI's verbs, for any kind:

.. code-block:: python

   from smarter import Smarter

   client = Smarter()

   client.manifests.validate("pii-redactor.yaml")              # without applying it
   client.manifests.apply("pii-redactor.yaml")                 # create or update
   client.manifests.get("Guardrail").names                     # every Guardrail's name
   manifest = client.manifests.describe("Guardrail", "pii_redactor")
   client.manifests.delete("Guardrail", "pii_redactor")

   client.manifests.example_manifest("LLMClient")              # a valid manifest to start from
   client.manifests.json_schema("LLMClient")                   # the kind's JSON Schema
   client.kinds()                                              # every kind, and which are deployable

``apply()`` and ``validate()`` accept a manifest in any form: the path of a YAML or JSON file, YAML
text, a ``dict``, a :external+smarter_python:py:class:`~smarter.models.manifest.Manifest`, or a typed SAM model (see below).

``deploy()`` and ``undeploy()`` deploy a deployable resource, such as an LLMClient on its own host
name. Deploying creates real, possibly billable, infrastructure in the platform's cloud: DNS
records, TLS certificates and Kubernetes ingresses.

Each resource's own methods
---------------------------

Each resource family has the same operations, bound to its kind:

.. code-block:: python

   client.guardrails.apply("pii-redactor.yaml")     # refuses a manifest of another kind
   client.guardrails.describe("pii_redactor")
   client.guardrails.delete("pii_redactor")
   client.guardrails.example_manifest()
   client.guardrails.json_schema()

Typed manifests
---------------

``describe()`` returns a :external+smarter_python:py:class:`~smarter.models.manifest.Manifest`, whose ``spec`` is a plain JSON
object, because its fields depend on the kind. ``to_sam()`` turns it into the kind's typed model,
with your editor's completion and Pydantic's validation:

.. code-block:: python

   guardrail = client.guardrails.describe("pii_redactor").to_sam()     # a SAMGuardrail
   print(guardrail.spec.config.action, guardrail.status.created)

The typed models build manifests in code, too:

.. code-block:: python

   import os

   from smarter.models.sam import SAMSecret

   secret: SAMSecret = client.secrets.example_manifest().to_sam()
   secret.metadata.name = "stripe_api_key"
   secret.spec.config.value = os.environ["STRIPE_API_KEY"]
   client.secrets.apply(secret)

There is a model of every kind: see :doc:`Models <models>`.

Annotations
-----------

A manifest's ``metadata.annotations`` are :doc:`annotations as in Kubernetes </smarter-framework/smarter-manifests>`: a map of string
keys to string values that your own software attaches to a resource, e.g. to associate an LLMClient
with an account in a CRM. A key is an optional DNS-subdomain prefix that names its owner, then a
slash and a name, e.g. ``acme.com/crm-account-id``. The prefix ``smarter.sh`` and its subdomains are
reserved for the platform.

.. code-block:: yaml

   metadata:
     name: customer_support
     annotations:
       acme.com/crm-account-id: A-10042
       acme.com/active: "true"

Every model of a resource or a manifest has its annotations as a ``dict[str, str]``. Manifests of
Smarter 0.37 and earlier wrote them as a list of one-key maps, which the platform still accepts on
apply. So does the SDK: it converts the list, and values that YAML reads as booleans, numbers or
dates, to the map of strings that the platform stores
(``normalize_annotations()``).

.. code-block:: python

   manifest = client.llm_clients.describe("customer_support")
   manifest.metadata.annotations["acme.com/crm-account-id"]     # "A-10042"

``get()`` takes an annotation selector, in the syntax of Kubernetes label selectors: ``key`` (the
resource has the key), ``!key`` (it hasn't), ``key=value`` and ``key!=value``, which also matches
resources without the key. Pass one requirement, or a list of them that must all match:

.. code-block:: python

   client.manifests.get("LLMClient", annotation="acme.com/crm-account-id=A-10042").names
   client.manifests.get("LLMClient", annotation=["acme.com/crm-account-id", "!acme.com/archived"])

The platform validates the selector, and an invalid one raises
:external+smarter_python:py:class:`~smarter.core.exceptions.BadRequestError`.

Manifests in CI/CD
------------------

Because manifests are files, the usual way to manage production resources is to keep them in a
repository, review changes in pull requests, and apply them from CI/CD.

Resources refer to one another by name: a SqlPlugin names its SqlConnection, which names the
Secret that holds its password. The platform resolves each name when it applies the manifest, so
the resource that is named must already exist. ``SAMKinds`` gives the
order that always works, each kind after the kinds that it may name. Sort by
``SAMKinds.apply_rank()``, not by file name:

.. code-block:: python

   from pathlib import Path

   from smarter import Manifest, SAMKinds, Smarter

   paths = sorted(Path("manifests").rglob("*.yaml"))
   manifests = sorted(
       ((path, Manifest.from_file(path)) for path in paths),
       key=lambda item: SAMKinds.apply_rank(item[1].kind),
   )

   with Smarter() as client:
       for path, manifest in manifests:
           result = client.manifests.validate(manifest)
           if not result.valid:
               raise SystemExit(f"{path}: {result.errors}")
       for path, manifest in manifests:
           print(path, client.manifests.apply(manifest).message)

``SAMKinds.apply_order()`` returns the whole order, and a kind that isn't a SAM kind ranks last.
