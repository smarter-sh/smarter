.. _napl-grid-maintenance-assistant:

=====================================================
NAPL Grid Maintenance Assistant
=====================================================

.. contents:: Table of Contents
   :local:
   :depth: 2

Goal
====

Use **Claude Code** with **Smarter** to build a Grid Maintenance Assistant
that Northern Aurora Power & Light (NAPL) field technicians can query in
plain English to retrieve equipment history, surface anomalies, and generate
maintenance work orders — without needing to know the underlying database
schema or API.

Prerequisites
=============

- An active Smarter account. Contact your administrator if you don't have one.
- The :doc:`Getting Started with Claude Code on Smarter <claude-code-getting-started-guide>`
  guide completed — your CLI must be installed and configured.
- Comfort writing YAML and working in a terminal.
- Access to the NAPL Equipment API endpoint and credentials. Contact the
  NAPL Systems Integration team if you need these.

.. note::

   Your administrator has already registered Anthropic as an LLM provider.
   You do not need your own Anthropic API key.

Setup
=====

Step 1: Confirm the Anthropic Provider is Active
--------------------------------------------------

.. code-block:: bash

   smarter describe provider anthropic-sonnet

Look for ``verified: true`` in the ``status`` block. If it shows
``pending`` or ``failed``, contact your administrator before continuing.

Step 2: Confirm Your CLI is Authenticated
------------------------------------------

.. code-block:: bash

   smarter status
   smarter get chatbots

Both commands should respond without an authentication error. If you see
``Not authenticated``, run ``smarter configure`` and re-enter your API key.

Step 3: Gather the NAPL Equipment API Details
----------------------------------------------

You will need the following from the NAPL Systems Integration team before
writing your manifests:

- **Base URL** of the NAPL Equipment API (e.g. ``https://api.napl.internal/v1``)
- **API endpoint path** for equipment history (e.g. ``/equipment/history/``)
- **API key** for authenticating requests

Keep these handy — you will use them in Step 5.

Concept Overview
================

This assistant is built from two Smarter resources working together:

**Plugin**
   A Plugin connects a Smarter chatbot to an external data source. In this
   case, the plugin wraps the NAPL Equipment API so that Claude can call it
   as a tool. When a technician asks *"What's the maintenance history on
   transformer T-447?"*, Claude decides to invoke the plugin, passes the
   equipment ID as a parameter, and receives the API response — which it
   then summarises in plain English.

**Chatbot**
   A Chatbot bundles together a provider (Anthropic), a model
   (``claude-sonnet-4-6``), a system prompt that shapes Claude's behaviour
   for the field technician context, and one or more plugins. The chatbot
   is the resource your technicians interact with directly.

**Function Calling**
   Claude does not call the plugin blindly on every message. It reads the
   incoming prompt, decides whether the question requires live equipment
   data, and only invokes the plugin when needed. Questions like
   *"What does NERC CIP stand for?"* are answered from Claude's own
   knowledge; questions about a specific asset ID trigger a plugin call.

**System Role**
   The system prompt tells Claude who it is and how to behave. For this
   assistant, the system role instructs Claude to act as an expert NAPL
   field technician assistant, to always use the plugin when equipment IDs
   are mentioned, and never to guess asset data it does not have.

Step-by-Step: Build the Grid Maintenance Assistant
===================================================

Step 4: Generate Manifest Templates
-------------------------------------

Use the CLI to print starter templates for both resource types:

.. code-block:: bash

   smarter manifest chatbot
   smarter manifest plugin

Keep these open as a reference while writing your own manifests below.

Step 5: Write the Equipment History Plugin Manifest
----------------------------------------------------

Create a file named ``napl-equipment-plugin.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: ApiPlugin
   metadata:
     name: napl_equipment_history
     description: Retrieves maintenance history and anomaly flags for NAPL grid equipment by asset ID.
     pluginClass: api
     version: 1.0.0
     tags:
       - napl
       - equipment
       - maintenance
     annotations:
       - smarter.sh/napl/display-name: NAPL Equipment History
       - smarter.sh/napl/contact-email: systems-integration@napl.example.com
       - smarter.sh/napl/documentation-url: https://docs.napl.example.com/equipment-api
   spec:
     apiData:
       endpoint: /equipment/history/
       method: GET
       headers:
         - name: X-API-Key
           value: your_napl_api_key_here
         - name: Content-Type
           value: application/json
         - name: Accept
           value: application/json
       parameters:
         - name: equipment_id
           description: The unique asset identifier for the piece of grid equipment (e.g. T-447, CB-112).
           type: string
           required: true
         - name: limit
           description: Maximum number of maintenance records to return. Defaults to 10.
           type: integer
           required: false
           default: 10
       testValues:
         - name: equipment_id
           value: T-447
         - name: limit
           value: 5
     connection: napl_equipment_api
     prompt:
       provider: anthropic
       model: claude-sonnet-4-6
       temperature: 0.2
       maxTokens: 1024
       systemRole: >
         You are an expert field technician assistant for Northern Aurora Power & Light.
         Use the equipment history data returned by the API to provide clear,
         accurate summaries. Flag any anomalies or overdue maintenance items.
         Never guess equipment data — if you cannot retrieve it, say so.
     selector:
       directive: search_terms
       searchTerms:
         - equipment
         - transformer
         - circuit breaker
         - maintenance
         - history
         - anomaly
         - work order
         - asset

.. important::

   Replace ``your_napl_api_key_here`` with the API key provided by the
   NAPL Systems Integration team. Never commit credentials to version control
   — consider using a Smarter Secret instead.

Step 6: Apply the Plugin
-------------------------

.. code-block:: bash

   smarter apply -f napl-equipment-plugin.yaml

Confirm it registered:

.. code-block:: bash

   smarter describe plugin napl_equipment_history

Look for ``active: true`` in the output.

Step 7: Write the Chatbot Manifest
------------------------------------

Create a file named ``napl-grid-assistant-chatbot.yaml``:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: Chatbot
   metadata:
     name: napl_grid_assistant
     description: NAPL Grid Maintenance Assistant — natural language access to equipment history and work order support.
     version: 1.0.0
     tags:
       - napl
       - maintenance
       - grid
     annotations:
       - smarter.sh/napl/creator: NAPL Systems Integration Team
       - smarter.sh/napl/purpose: Field technician grid maintenance assistant
   spec:
     config:
       provider: anthropic
       defaultModel: claude-sonnet-4-6
       defaultTemperature: 0.3
       defaultMaxTokens: 2048
       defaultSystemRole: >
         You are the NAPL Grid Maintenance Assistant, an expert in Northern Aurora
         Power & Light grid infrastructure. You help field technicians retrieve
         equipment maintenance history, identify anomalies, and draft work orders.
         When an equipment ID is provided, always query the napl_equipment_history
         plugin to retrieve live data. Do not guess or fabricate equipment records.
         Respond concisely and flag safety-critical findings clearly.
       appName: NAPL Grid Maintenance Assistant
       appAssistant: GridBot
       appWelcomeMessage: >
         Welcome to the NAPL Grid Maintenance Assistant. Provide an equipment ID
         to retrieve maintenance history, or describe what you need help with.
       appExamplePrompts:
         - "What's the maintenance history on transformer T-447?"
         - "Has circuit breaker CB-112 had any anomalies in the last 6 months?"
         - "Draft a work order for a routine inspection of T-447."
         - "Which equipment in Substation 7 is overdue for maintenance?"
       appPlaceholder: "Enter an equipment ID or describe your maintenance query..."
     plugins:
       - napl_equipment_history
     functions: []

Step 8: Apply the Chatbot
--------------------------

.. code-block:: bash

   smarter apply -f napl-grid-assistant-chatbot.yaml

Confirm it registered:

.. code-block:: bash

   smarter describe chatbot napl_grid_assistant

Step 9: Test in the Workbench
------------------------------

1. Navigate to **Workbench** in the Smarter web console sidebar.
2. Select **napl_grid_assistant** from the chatbot list.
3. Type a test query and press Enter.

Use the Workbench to tune the system prompt and temperature before deploying
to technicians. The **side-by-side mode** lets you compare ``claude-opus-4-5``
and ``claude-sonnet-4-6`` responses on the same query.

Proof of Concept
================

Run this sequence end to end from the terminal:

.. code-block:: bash

   smarter status
   smarter describe provider anthropic-sonnet
   smarter describe plugin napl_equipment_history
   smarter chat napl_grid_assistant

In the chat session, type:

.. code-block:: text

   What's the maintenance history on transformer T-447?

Expected response (approximate):

.. code-block:: text

   Transformer T-447 — Substation 7, 138kV transmission line
   ──────────────────────────────────────────────────────────
   Last 5 maintenance records retrieved:

   2026-02-14  Routine inspection          PASSED   Technician: J. Larsen
   2025-11-03  Oil sample analysis         PASSED   No degradation detected
   2025-08-19  Thermal imaging scan        WARNING  Hot spot identified, monitored
   2025-05-01  Routine inspection          PASSED   Technician: M. Okafor
   2024-12-10  Bushing replacement         COMPLETE Parts: BU-4471, BU-4472

   ⚠ Note: The August 2025 hot spot warning has not been followed up with
   a re-inspection. Consider scheduling a thermal re-scan before next
   scheduled outage window.

A structured, accurate summary drawn from live API data — with a proactive
anomaly callout — means the assistant is working correctly.

Troubleshooting
===============

**"Plugin not found: napl_equipment_history"**
   The plugin was not applied successfully. Run
   ``smarter describe plugin napl_equipment_history`` — if it returns
   not found, re-run ``smarter apply -f napl-equipment-plugin.yaml`` and
   check for YAML indentation errors.

**"Equipment ID not recognised" or empty history**
   Confirm the asset ID format matches what the NAPL Equipment API expects
   (e.g. ``T-447`` not ``t447``). Test the API directly with
   ``curl`` or Postman using the same credentials to rule out an API-side issue.

**"Connection refused" or API timeout**
   The NAPL Equipment API may be unreachable from the Smarter host. Verify
   the base URL and that the Smarter server has network access to the
   NAPL internal API. Contact the NAPL Systems Integration team.

**Plugin responds but Claude ignores it**
   Check that the ``selector.searchTerms`` in your plugin manifest include
   the keywords the technician is using. Add any missing domain terms and
   re-apply the manifest.

**"Provider not available"**
   Run ``smarter describe provider anthropic-sonnet`` and check the
   ``status`` block. If ``verified: false``, contact your administrator.

**Responses are too verbose or too terse**
   Adjust ``defaultMaxTokens`` and ``defaultTemperature`` in the chatbot
   manifest, then re-apply. Lower temperature (``0.1``–``0.3``) produces
   more focused, factual responses — appropriate for maintenance data.

.. seealso::

   - :doc:`claude-code-getting-started-guide`
   - :doc:`/smarter-platform/adding-an-llm-provider`
   - :doc:`/smarter-resources/smarter-chatbot`
   - :doc:`/smarter-resources/smarter-plugin`
   - :doc:`/smarter-framework/smarter-cli`
   - `Anthropic Claude Documentation <https://docs.anthropic.com/>`_
