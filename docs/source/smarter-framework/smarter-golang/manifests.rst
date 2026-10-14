Manifests
=========

Every Smarter resource is declared in a :doc:`Smarter Application Manifest <../smarter-manifests>`
(SAM), and the SDK writes resources exactly as the :doc:`CLI <../smarter-cli>` does: through the
brokered :doc:`manifest API <../smarter-api/cli>`. The platform's broker for the manifest's kind
validates it with the kind's Pydantic models and applies its business rules, so a manifest that the
CLI accepts, the SDK accepts, and the other way round.

The manifest API
----------------

``client.Manifests`` has the CLI's verbs, for any kind:

.. code-block:: go

   manifest, err := smarter.ManifestFromFile("pii-redactor.yaml")
   if err != nil {
       return err
   }
   validation, err := client.Manifests.Validate(ctx, manifest) // without applying it
   if err != nil {
       return err
   }
   if !validation.Valid {
       return fmt.Errorf("invalid manifest: %v", validation.Errors)
   }
   if _, err := client.Manifests.Apply(ctx, manifest); err != nil { // create or update
       return err
   }
   guardrails, err := client.Manifests.Get(ctx, "Guardrail", "")
   if err != nil {
       return err
   }
   fmt.Println(guardrails.Names()) // every Guardrail's name
   described, err := client.Manifests.Describe(ctx, "Guardrail", "pii_redactor")
   if err != nil {
       return err
   }
   fmt.Println(described.Status["created"])
   if _, err := client.Manifests.Delete(ctx, "Guardrail", "pii_redactor"); err != nil {
       return err
   }

``ExampleManifest(ctx, kind)`` returns a valid manifest to start from, ``JSONSchema(ctx, kind)`` the
kind's JSON Schema, and ``client.Kinds(ctx)`` every kind, and which are deployable. A
``*smarter.Manifest`` comes from ``ManifestFromFile``, ``ManifestFromYAML``, ``ManifestFromObject``
or ``ManifestFromSAM``, and keeps every field of the manifest, also those that the SDK doesn't
declare, so describe, change and apply loses nothing.

``Deploy`` and ``Undeploy`` deploy a deployable resource, such as an LLMClient on its own host name.
Deploying creates real, possibly billable, infrastructure in the platform's cloud: DNS records, TLS
certificates and Kubernetes ingresses.

Each resource's own methods
---------------------------

Each resource family has the same operations, bound to its kind:

.. code-block:: go

   client.Guardrails.Apply(ctx, manifest) // refuses a manifest of another kind
   client.Guardrails.Describe(ctx, "pii_redactor")
   client.Guardrails.Delete(ctx, "pii_redactor")
   client.Guardrails.ExampleManifest(ctx)
   client.Guardrails.JSONSchema(ctx)

Typed manifests
---------------

A manifest's ``Spec`` is a ``smarter.JSONObject``, because its fields depend on the kind.
``smarter.ToSAM`` decodes a manifest into the kind's struct, from the ``sam`` package:

.. code-block:: go

   described, err := client.Guardrails.Describe(ctx, "pii_redactor")
   if err != nil {
       return err
   }
   guardrail, err := smarter.ToSAM[sam.Guardrail](described)
   if err != nil {
       return err
   }
   fmt.Println(guardrail.Spec.Config.Action, guardrail.Status.Created)

``manifest.SAM()`` returns the struct of the manifest's own kind, as a ``sam.Manifest``, for a type
switch. The structs build manifests in code, too:

.. code-block:: go

   secret := sam.Secret{
       APIVersion: smarter.APIVersionV1,
       Kind:       "Secret",
       Metadata:   sam.SecretMetadata{Name: "stripe_api_key", Description: "The Stripe api key."},
       Spec:       sam.SecretSpec{Config: sam.SecretSpecConfig{Value: os.Getenv("STRIPE_API_KEY")}},
   }
   manifest, err := smarter.ManifestFromSAM(&secret)
   if err != nil {
       return err
   }
   _, err = client.Secrets.Apply(ctx, manifest)

A struct ignores fields that it doesn't declare, so apply a ``*smarter.Manifest``, not a struct, when
you change a manifest that a newer platform described. ``manifest.ToYAML()`` writes a manifest as
YAML, without its read-only ``Status``, ready to apply. There is a struct of every kind: see
:doc:`Models <models>`.

Manifests in CI/CD
------------------

Because manifests are files, the usual way to manage production resources is to keep them in a
repository, review changes in pull requests, and apply them from CI/CD:

.. code-block:: go

   paths, _ := filepath.Glob("manifests/*.yaml")
   sort.Strings(paths)
   var manifests []*smarter.Manifest
   for _, path := range paths {
       manifest, err := smarter.ManifestFromFile(path)
       if err != nil {
           return err
       }
       result, err := client.Manifests.Validate(ctx, manifest)
       if err != nil {
           return err
       }
       if !result.Valid {
           return fmt.Errorf("%s: %v", path, result.Errors)
       }
       manifests = append(manifests, manifest)
   }
   for _, manifest := range manifests {
       response, err := client.Manifests.Apply(ctx, manifest)
       if err != nil {
           return err
       }
       fmt.Println(response.Message)
   }
