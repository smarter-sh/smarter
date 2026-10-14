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

.. code-block:: typescript

   import { Smarter } from "@smarter.sh/api";

   const client = new Smarter();

   await client.manifests.validate("pii-redactor.yaml"); // without applying it
   await client.manifests.apply("pii-redactor.yaml"); // create or update
   (await client.manifests.get("Guardrail")).names; // every Guardrail's name
   const manifest = await client.manifests.describe("Guardrail", "pii_redactor");
   await client.manifests.delete("Guardrail", "pii_redactor");

   await client.manifests.exampleManifest("LLMClient"); // a valid manifest to start from
   await client.manifests.jsonSchema("LLMClient"); // the kind's JSON Schema
   await client.kinds(); // every kind, and which are deployable

``apply()`` and ``validate()`` accept a manifest in any form: the path or ``file:`` url of a YAML or
JSON file, YAML text, a plain object, a ``Manifest``, or a typed SAM object (see below).

``deploy()`` and ``undeploy()`` deploy a deployable resource, such as an LLMClient on its own host
name. Deploying creates real, possibly billable, infrastructure in the platform's cloud: DNS
records, TLS certificates and Kubernetes ingresses.

Each resource's own methods
---------------------------

Each resource family has the same operations, bound to its kind:

.. code-block:: typescript

   await client.guardrails.apply("pii-redactor.yaml"); // refuses a manifest of another kind
   await client.guardrails.describe("pii_redactor");
   await client.guardrails.delete("pii_redactor");
   await client.guardrails.exampleManifest();
   await client.guardrails.jsonSchema();

Typed manifests
---------------

``describe()`` returns a ``Manifest``, whose ``spec`` is a plain JSON object, because its fields
depend on the kind. ``toSam(kind)`` validates it against the kind's JSON Schema and returns it as
the kind's TypeScript type, with your editor's completion:

.. code-block:: typescript

   const guardrail = (await client.guardrails.describe("pii_redactor")).toSam("Guardrail"); // a SAMGuardrail
   console.log(guardrail.spec.config.action, guardrail.status?.created);

The types build manifests in code, too:

.. code-block:: typescript

   import type { SAMSecret } from "@smarter.sh/api";

   const secret: SAMSecret = (await client.secrets.exampleManifest()).toSam("Secret");
   secret.metadata.name = "stripe_api_key";
   secret.spec.config.value = process.env["STRIPE_API_KEY"] ?? "";
   await client.secrets.apply(secret);

``toYaml()`` writes a manifest as YAML, without its read-only ``status``, ready to apply. There is a
type of every kind: see :doc:`Models <models>`.

Manifests in CI/CD
------------------

Because manifests are files, the usual way to manage production resources is to keep them in a
repository, review changes in pull requests, and apply them from CI/CD:

.. code-block:: typescript

   import { readdirSync } from "node:fs";
   import { join } from "node:path";
   import { Smarter } from "@smarter.sh/api";

   const client = new Smarter();
   const paths = readdirSync("manifests").filter((name) => name.endsWith(".yaml")).sort().map((name) => join("manifests", name));
   for (const path of paths) {
     const result = await client.manifests.validate(path);
     if (!result.valid) throw new Error(`${path}: ${JSON.stringify(result.errors)}`);
   }
   for (const path of paths) console.log((await client.manifests.apply(path)).message);
