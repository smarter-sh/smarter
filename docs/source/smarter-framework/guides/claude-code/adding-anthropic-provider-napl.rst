.. _napl-anthropic-provider-tutorial:

How-To: Add Anthropic to Smarter for NAPL
=========================================

Goal
----

Register Anthropic and an approved Claude model for Northern Aurora Power &
Light (NAPL), then hand a verified connection to the custom programming team.
Anthropic is the **provider**, Claude is the **model**, and Claude Code is the
**coding client**. A model entry must use an actual model ID, not ``claude-code``.

.. important::

   This is a go-live procedure, not a claim that this checkout already supports
   Claude Code. The repository's :doc:`../claude-code` page identifies that
   integration as prerelease and unverified. Complete the acceptance checks
   below before releasing the programmer tutorial.

Prerequisites
-------------

* A deployed Smarter instance and an account authorized to manage Secrets,
  Providers, and Provider Models in its restricted administration site.
* An organization-owned Anthropic API key with funded API access, obtained
  through the `Anthropic Console <https://platform.claude.com/>`_.
* An approved model ID and provider terms/data-handling approval.
* Familiarity with HTTPS, API authentication, YAML, and Smarter resources.

Infrastructure deployment, IDE integration, and accounting cost-code creation
belong to their respective teams and are outside this tutorial.

Setup and concept overview
--------------------------

Smarter stores a credential in a **Secret**, links that Secret to a **Provider**,
and stores each model in a separate **ProviderModel** record. Multiple models
share one provider; do not create a new provider for every model.

There are two different API paths to validate:

.. code-block:: text

   Smarter Workbench -> OpenAI-compatible completion API -> Claude
   Claude Code -> NAPL Anthropic-compatible gateway -> Claude Messages API

Anthropic offers an `OpenAI SDK compatibility layer
<https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk>`_
that can support a Smarter evaluation at ``https://api.anthropic.com/v1/``.
It has feature limitations and is primarily intended for evaluation. Registering
that URL does not give Smarter an inbound Claude Code endpoint. The application
team must provide and test an Anthropic Messages-compatible route through the
NAPL Smarter service before the coding-client pilot.

Step-by-step
------------

Step 1: Store the credential
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the Smarter console, open the account's Secrets management page and create
``napl_anthropic_api_key``. Enter the organization API key in the secret-value
field and save. Use the NAPL administrator's account scope. Never put the value
in a tutorial, Git commit, prompt, or developer shell profile.

Step 2: Register or update the provider
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Open the deployment's restricted administration site at ``/admin/``. In the
Provider application, select **Providers**. Check for an existing ``anthropic``
record before choosing **Add**; update the intended record instead of duplicating
it. Set these fields and save:

.. list-table:: Provider configuration
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Value or decision
   * - ``name`` / ``description``
     - ``anthropic`` / ``Anthropic Claude for NAPL custom programming``
   * - ``user_profile``
     - The authorized NAPL owner in the correct account.
   * - ``base_url``
     - ``https://api.anthropic.com/v1/`` for the compatibility-layer evaluation;
       use an approved adapter URL if the platform team requires one.
   * - ``api_key``
     - Select the Secret ``napl_anthropic_api_key``; do not paste its value here.
   * - ``default_model``
     - The approved exact model ID, for example ``claude-sonnet-4-6`` if available.
   * - ``connectivity_test_path``
     - A platform-tested GET path that returns 200 with Smarter's authentication.
       A POST-only completion endpoint is not a valid GET health check.
   * - ``website_url`` / ``docs_url``
     - ``https://www.anthropic.com/`` / ``https://platform.claude.com/docs/en/``.
   * - ``logo``, contact/support details, terms/privacy URLs
     - Current provider information approved by the platform owner; use real
       verified contacts, not invented email addresses.
   * - Terms acceptance fields
     - Record acceptance through the authorized deployment workflow.

Leave activation and verification to the approved verification workflow. A saved
record, or manually checking ``is_active``, does not prove that requests work.

.. note::

   The SAM Provider schema nests its configuration under ``spec.provider``
   and uses snake_case fields. For example, the following is a **schema
   reference**, not a deployment command:

   .. code-block:: yaml

      apiVersion: smarter.sh/v1
      kind: Provider
      metadata:
        name: anthropic
        description: Anthropic Claude for NAPL custom programming
        version: 1.0.0
      spec:
        provider:
          name: anthropic
          base_url: https://api.anthropic.com/v1/
          api_key: napl_anthropic_api_key
          website_url: https://www.anthropic.com/
          docs_url: https://platform.claude.com/docs/en/

   In the reviewed checkout, the Provider CLI broker does not implement complete
   new-record creation or Secret-name resolution on apply. Use the administration
   workflow above. ``ProviderModel`` is not a registered CLI manifest kind here;
   do not invent a ``smarter apply`` model manifest.

Step 3: Register the model separately
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In ``/admin/``, open **Provider Models**, select an existing entry for the approved
model or choose **Add**, and set:

* ``provider``: the ``anthropic`` record created above.
* ``name``: the exact approved model ID; preserve its hyphens and spelling.
* ``description``: ``NAPL coding pilot model``.
* ``is_default``: true for the team's selected default.
* ``max_completion_tokens``: ``4096`` for the introductory evaluation.
* ``temperature``: ``0.7`` and ``top_p``: ``1.0`` for this evaluation, subject to
  the chosen model's supported parameters.
* ``supports_text_input`` and ``supports_text_generation``: true.
* ``supports_tools`` and ``supports_streaming``: enable only after these features
  pass tests through the configured route; leave unrelated capabilities disabled.

Save the record. Claude Code executes local tools on the programmer's machine;
this does not by itself justify setting ``supports_code_interpreter`` on the model.

Step 4: Verify both paths
~~~~~~~~~~~~~~~~~~~~~~~~~

Ask the platform owner to run the deployment's provider/model verification
workflow and inspect its verification records. This checkout queues model checks on
creation; provider checks require an explicit verification request. Both
verification paths are still under development. Investigate failures rather
than assuming that waiting will resolve them.

In a test LLMClient configured with ``provider: anthropic`` and the approved
``defaultModel``, send this Workbench prompt:

.. code-block:: text

   Write a Python function add(a, b) that returns their sum.
   Return only the function, without markdown fences.

Expect an ordinary completion containing a working ``add`` function. Then have
the application team verify the separate Claude Code gateway contract: bearer
credentials mapped to the correct NAPL user, ``POST /v1/messages``, Anthropic
version/beta headers, streaming, and a complete tool-use/tool-result round trip.
The `Claude Code gateway protocol guide
<https://code.claude.com/docs/en/llm-gateway-protocol>`_ defines that contract.

Proof of concept and go-live handoff
------------------------------------

Release :doc:`getting-started-claude-code-napl` only when all of these pass:

* Provider and model records exist in the intended account, with successful
  verification evidence and authorized activation.
* The Workbench smoke test succeeds and the gateway coding exercise succeeds.
* Requests appear in the approved audit trail with user and token attribution;
  the accounting team confirms its supplied cost codes.
* A revoked developer credential is rejected without affecting another user.

The application owner supplies the tested gateway base URL, credential mechanism,
allowed model ID, supported Claude Code version, and support contact. The project
manager starts with a small volunteer pilot, reviews errors and completed coding
exercises, and expands only after acceptance. If routing, authorization, or tool
use fails, pause onboarding and revoke pilot gateway access while retaining
existing approved coding workflows. No infrastructure redeployment is prescribed.

Troubleshooting
---------------

**401 or 403**
   Check Secret ownership, expiration, provider billing, and authentication header.
   Smarter's generic connectivity check sends a GET with a Bearer token; native
   Anthropic API checks may need different headers. The platform owner must use
   a tested adapter or provider-specific check rather than a guessed path.

**Verification fails although a record saved**
   Inspect connectivity, URL/contact checks, terms acceptance, and model test
   results. Registration and verification are separate. Escalate errors in the
   prerelease verifier to the application owner; do not mark them passed manually.

**Model not found or missing from the Workbench**
   Confirm exact model ID, provider association, approved activation, account
   access, and the test LLMClient's provider/model settings.

**Workbench works but Claude Code returns 404 or malformed responses**
   The coding client needs Anthropic Messages and streaming. An OpenAI-compatible
   chat-completion endpoint alone is insufficient. Complete the gateway acceptance
   tests before onboarding developers.

References and version
----------------------

Reviewed against repository commit ``8016b7cfc63ed8ccb3b7a77cf5a959e8f166a148``
on 1 October 2026. Model IDs and deployed interfaces must be checked at rollout.

* :doc:`/smarter-resources/smarter-provider`
* :doc:`/smarter-resources/provider/manifest/models`
* :doc:`/smarter-resources/provider/models`
* :doc:`/smarter-resources/smarter-secret`
