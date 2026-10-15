============================================================
Getting Started: Claude Code & Smarter Onboarding for NAPL
============================================================

.. contents:: Table of Contents
   :depth: 2

Goal
====

The objective of this guide is to enable Northern Aurora Power & Light (NAPL)
custom software developers to self-onboard onto **Claude Code** as a virtual
CoPilot coding assistant, routed through **Smarter** as a centralized,
on-premise LLM provider.

Prerequisites
=============

Before proceeding, developers are assumed to possess:

* Basic technical familiarity with Git, GitHub workflows, and YAML syntax.
* Access to an active Smarter user account with developer permissions.
* PyCharm or VS Code installed locally on their workstations.

Setup
=====

To prepare your environment for Claude Code integration:

1. **Obtain Anthropic API Key:** Secure an enterprise API credential from the
   NAPL IT security vault.
2. **Store Secret in Smarter:** Register your API credential in Smarter as an
   encrypted Secret resource (``SAMSecret``).
3. **Smarter Login:** Log into the Smarter Web Console at
   ``http://localhost:9357/login/`` using your enterprise SSO credentials.

Concept Overview
================

Smarter uses a declarative, Kubernetes-inspired YAML manifest framework called
**Smarter API Manifests (SAM)**.

* **SAMProvider:** Connects third-party LLM providers (e.g., Anthropic) to
  Smarter and validates model capabilities.
* **LLMClient / Proxy:** Routes requests from developer IDEs through Smarter,
  applying security guardrails and cost tracking.

Step-by-Step: Adding Anthropic & Claude Code
============================================

1. Create a provider manifest file named ``provider-anthropic.yaml``:

   .. code-block:: yaml

      apiVersion: smarter.sh/v1alpha1
      kind: SAMProvider
      metadata:
        name: anthropic-provider
      spec:
        provider: anthropic
        credentialsSecretRef: anthropic-api-key
        models:
          - name: claude-code
            displayName: "Claude Code (Anthropic)"
            contextWindow: 200000

2. Apply the manifest using the Smarter CLI:

   .. code-block:: bash

      smarter apply -f provider-anthropic.yaml

3. Verify that the provider state reports ``Ready`` in the Smarter Web Console.

Proof of Concept
================

To verify your onboarding setup:

1. Open your terminal and send a test prompt via the Smarter Proxy endpoint:

   .. code-block:: bash

      smarter prompt --provider anthropic-provider --model claude-code "Hello Claude Code"

2. **Expected Output:**

   .. code-block:: text

      [Smarter Proxy] Connection Successful!
      Model: Claude Code (Anthropic)
      Status: 200 OK

Troubleshooting
===============

* **Authentication Error (401):** Verify that your Anthropic API key is
  correctly bound to your ``SAMSecret``.
* **Provider Not Ready:** Ensure the Smarter background worker has finished
  running model compatibility verification checks.

.. note::

   **AI Usage Disclaimer**
   This documentation was created as part of coursework. Generative AI tools (including Claude Code / LLM assistance) were utilized to assist in drafting, structuring, and refining these technical materials in accordance with course guidelines. All content has been reviewed, verified, and edited for technical accuracy.

   