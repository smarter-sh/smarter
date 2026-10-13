Manifests
=========

Every Smarter resource is declared in a :doc:`Smarter Application Manifest <../smarter-manifests>`
(SAM), and the SDK writes resources exactly as the :doc:`CLI <../smarter-cli>` does: through the
brokered :doc:`manifest API <../smarter-api/cli>`. The platform's broker for the manifest's kind
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
text, a ``dict``, a :class:`~smarter.models.manifest.Manifest`, or a typed SAM model (see below).

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

``describe()`` returns a :class:`~smarter.models.manifest.Manifest`, whose ``spec`` is a plain JSON
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

Manifests in CI/CD
------------------

Because manifests are files, the usual way to manage production resources is to keep them in a
repository, review changes in pull requests, and apply them from CI/CD:

.. code-block:: python

   from pathlib import Path
   from smarter import Smarter

   with Smarter() as client:
       for path in sorted(Path("manifests").glob("*.yaml")):
           result = client.manifests.validate(path)
           if not result.valid:
               raise SystemExit(f"{path}: {result.errors}")
       for path in sorted(Path("manifests").glob("*.yaml")):
           print(client.manifests.apply(path).message)
