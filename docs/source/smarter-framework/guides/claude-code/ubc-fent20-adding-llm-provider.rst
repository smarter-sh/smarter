How-To: Add Anthropic as an LLM Provider
========================================

Goal
----

Configure Anthropic as an LLM provider in Smarter and register a Claude model that authorized programmers can use through a supported integration.

Prerequisites
-------------

You should:

* have a Smarter account with permission to manage providers and models, or have an administrator available to perform those steps
* have an active Anthropic API account and an API key if required by your deployment
* understand API endpoints, authentication, and model identifiers
* know how your Smarter installation manages secrets and provider resources

Setup
-----

Gather the following information before configuring the provider:

* the Anthropic API credential required by your deployment
* the provider endpoint documented for your Smarter version
* the exact Claude model identifier supported by your environment
* the account or scope in which the provider and model should be available
* the documented method for validating provider connectivity

Never place API keys in a manifest committed to Git, a public issue, or a tutorial example. Use Smarter's supported secret-management workflow.

Concept Overview
----------------

A provider represents an external LLM service. A model entry identifies a particular model exposed through that provider. Registering a provider alone does not guarantee that a usable model is available to every account.

The setup has four main parts:

#. **Credential:** the secret used to authenticate with the provider.
#. **Provider:** the configuration that identifies the service and its connection settings.
#. **Provider model:** the model identifier and settings associated with the provider.
#. **Validation:** a check that confirms the configured service and model can be used.

Smarter's resource names, fields, permissions, and configuration interface may vary by version. Use the resource schema and provider documentation for the version deployed by your organization rather than copying guessed fields into a manifest.

Step-by-Step
------------

1. **Confirm the deployment's provider configuration method.**

   Open the Smarter provider documentation for your deployed version and identify the supported way to create a provider and model. Determine whether your environment uses the web console, resource manifests, or another documented workflow.

2. **Prepare the credential securely.**

   Create or obtain the required Anthropic API credential through your organization's approved process. Store it using Smarter's documented secret-management mechanism. Do not commit the secret or paste it into source code.

3. **Create or select the provider.**

   In the documented provider-management interface, create an Anthropic provider or inspect the existing entry. Confirm that the service identity and endpoint match the settings documented for your deployment.

4. **Configure authentication and endpoint settings.**

   Supply the secret reference and endpoint values required by the actual provider schema. Do not assume that a direct Anthropic endpoint, a proxy endpoint, or a credential intended for another service is interchangeable. Use the values specified for your Smarter deployment.

5. **Register a Claude model.**

   Create or select a model associated with the Anthropic provider. Enter the exact model identifier supported by your environment. Use a clear display name so authorized programmers can distinguish the model from other available models.

6. **Set availability and permissions.**

   Check the resource's account or scope and confirm that the intended users have permission to access it. Follow your organization's least-privilege policy.

7. **Save and validate the configuration.**

   Use the validation or connectivity check documented for your deployment. Review the returned status and diagnostic messages. A saved configuration alone does not prove that requests will succeed.

8. **Run a smoke test.**

   Select the model in a supported Smarter workflow and send a harmless test prompt. Confirm that a response is returned without authentication, connectivity, or model-selection errors.

9. **Document the approved integration.**

   Record the provider display name, model identifier, configuration owner, and the location of the relevant internal documentation. Never record the secret value itself.

Proof of Concept
----------------

The provider setup is successful when:

* the Anthropic provider configuration is saved
* the credential is referenced through the approved secret-management method
* a supported Claude model is registered under the provider
* validation succeeds, or any deployment-specific validation limitation is documented
* an authorized user can invoke the model in a supported Smarter workflow
* no secret has been exposed in source control or logs

Troubleshooting
---------------

**Provider authentication fails.**

Check that the credential is valid, the secret reference resolves correctly, and the credential is intended for the configured endpoint. Review error messages without exposing the secret.

**The provider saves but the model fails validation.**

Confirm the exact model identifier, provider association, required configuration fields, and feature support for the deployed version.

**The model is unavailable to a programmer.**

Check account scope, resource ownership, and permissions. Confirm that the model is enabled for the intended workflow.

**Requests fail despite successful configuration.**

Check network connectivity, endpoint settings, provider service status, and the diagnostic information returned by Smarter.

**The documentation does not match the console or schema.**

Use the documentation and resource definitions that match your deployed version. Ask the platform administrator to confirm any version-specific differences instead of guessing field names or values.

Expected Outcome
----------------

An Anthropic provider and a supported Claude model are configured in Smarter, validated using the documented procedure, and available to authorized users through a supported workflow. Credentials remain protected by the platform's approved secret-management process.