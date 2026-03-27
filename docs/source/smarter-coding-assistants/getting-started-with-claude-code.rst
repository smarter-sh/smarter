========================================================
Getting Started with Claude Code on the Smarter Platform
========================================================

.. contents:: Table of Contents
   :depth: 3
   :local:
   :backlinks: none

----

.. _goal:

1. Goal
=======

We will use **Claude Code** with the **Smarter platform** to establish
a fully functional, enterprise-governed AI coding assistant that routes all
LLM traffic through a centrally managed on-premise Smarter gateway.

Concretely, by the end of this tutorial you will have:

* Installed the Smarter CLI and configured it with your personal Smarter
  account credentials.
* Created and verified a dedicated Smarter API key for CLI and Claude Code
  authentication.
* Installed Claude Code and pointed it at the Smarter gateway instead of
  Anthropic's public API endpoint.
* Confirmed the end-to-end path by asking Claude Code to explain a short
  Python function, with all traffic flowing through the Smarter gateway.

.. note::

   This tutorial covers **your individual workstation setup only.**
   Infrastructure provisioning — including the Kubernetes cluster, the
   Smarter Helm deployment, network routing, and the registration of
   Anthropic as an LLM provider at the platform level — was handled by the
   infrastructure team and is already complete.  Cost-tracking code
   assignment is handled by Accounting and is out of scope here.  IDE
   plug-in integration is addressed in a separate tutorial.

   Regarding the Anthropic API key specifically: Smarter's upstream
   connection to Anthropic is a **platform-level configuration** managed
   entirely by the infrastructure team.  You do not supply, store, or manage
   an Anthropic API key.  Your only credential is your personal Smarter API
   key, which authenticates *you* to the Smarter gateway.  The gateway then
   presents its own Anthropic credential for the upstream call.

----

.. _prerequisites:

2. Prerequisites
================

This tutorial assumes you are a working programmer and that you already have
the following knowledge and resources in place.

.. list-table:: Required Knowledge
   :widths: 30 70
   :header-rows: 1

   * - Topic
     - What you need to know
   * - Command-line shell
     - Comfortable with a Unix/macOS terminal or Windows PowerShell; able to
       set environment variables and edit files from the command line.
   * - YAML
     - Able to read and write basic YAML files; understand indentation and
       key-value structure.
   * - JSON
     - Able to read and write basic JSON; understand objects, keys, and
       nested structures.
   * - Node.js / npm
     - Able to install a global npm package (``npm install -g …``).
   * - Smarter account
     - You have already been provisioned a Smarter account and know how to
       log in to the Smarter web console at ``https://smarter.internal``
       (internal URL — VPN required).
   * - Network access
     - Your workstation can reach the internal network (directly or
       via VPN).

.. list-table:: Required Software (pre-installed or installable by you)
   :widths: 30 70
   :header-rows: 1

   * - Software
     - Version requirement
   * - Node.js
     - v18.0 or later (required by Claude Code)
   * - npm
     - Bundled with Node.js; v9 or later recommended
   * - A plain-text editor
     - VS Code, Vim, Notepad++, or any editor of your choice
   * - Smarter CLI
     - Latest release — installation covered in :ref:`setup` below
   * - Claude Code
     - Latest release — installation covered in :ref:`setup` below

Verify your Node.js version before proceeding:

.. code-block:: bash

   node --version
   # Expected output: v18.x.x or higher

----

.. _setup:

3. Setup
========

Complete every step in this section **before** moving on to the tutorial
proper.  These steps need to be performed only once per workstation.

3.1 Install the Smarter CLI
-----------------------------

The Smarter CLI (command: ``smarter``) is the primary tool for creating and
managing AI resources on the platform.  It uses a verb-noun command structure
modelled deliberately after ``kubectl``.  The binary is available for
Windows, macOS, and Linux.

Download it from ``https://smarter.sh/cli`` following the instructions for
your operating system, and place the binary somewhere on your ``PATH``
(e.g., ``/usr/local/bin`` on Linux/macOS, or ``C:\Tools\bin`` on Windows
with that directory added to your ``PATH`` environment variable).

If the artifact repository mirrors the Smarter CLI releases, download
from there per the instructions provided by the infrastructure team.

Verify the installation:

.. code-block:: bash

   smarter version
   # Expected output: Smarter CLI vX.Y.Z  (exact version will vary)

3.2 Configure the Smarter CLI
-------------------------------

Run the one-time interactive configuration wizard.  You will be prompted for
your Smarter username, password, and the internal Smarter API base URL:

.. code-block:: bash

   smarter configure

When prompted, provide:

* **Username / password:** your SSO or Smarter account credentials.
* **Environment / API base URL:** ``https://smarter.internal``
  (or the URL provided by the infrastructure team if it differs).
* **Environment name:** ``prod`` (this is the default; press Enter to accept).

The CLI stores this configuration at ``~/.smarter/config.yaml`` on
Linux/macOS, or ``%USERPROFILE%\.smarter\config.yaml`` on Windows.  The
``--config`` flag can override this path if needed.

Confirm that the CLI can reach the platform and that your credentials are
accepted:

.. code-block:: bash

   smarter whoami
   # Expected: details about your Smarter user account

3.3 Create a Smarter API Key
------------------------------

The Smarter platform uses **API keys** (distinct from your login password)
to authenticate CLI and programmatic access.  Claude Code will use this key
as its bearer token when sending requests to the gateway.

Generate the example ``ApiKey`` manifest:

.. code-block:: bash

   smarter manifest apikey -o yaml > my-apikey.yml

Open ``my-apikey.yml`` in your editor.  It will look similar to the
following (exact field names may vary slightly across Smarter versions —
your generated output is authoritative):

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: ApiKey
   metadata:
     name: my-apikey
     version: 1.0.0
     description: An example API key manifest.
   spec: {}

Edit the file to give your key a meaningful, unique name.  Replace
``my-apikey`` with a name that identifies you and the purpose, for example:

.. code-block:: yaml

   apiVersion: smarter.sh/v1
   kind: ApiKey
   metadata:
     name: jsmith-claudecode-workstation
     version: 1.0.0
     description: >
       Personal API key for jsmith workstation — used by Smarter CLI
       and Claude Code to authenticate to the Smarter gateway.
   spec: {}

Apply the manifest:

.. code-block:: bash

   smarter apply -f my-apikey.yml

Expected output:

.. code-block:: text

   ApiKey "jsmith-claudecode-workstation" created successfully.

Retrieve the key value — you will need it in step 3.5.  Use ``smarter get``
to list your keys, then ``smarter describe`` to retrieve the manifest for
the specific key (the token value appears in the ``status`` section of the
described manifest, or is returned immediately after creation):

.. code-block:: bash

   smarter get apikeys
   smarter describe apikey jsmith-claudecode-workstation -o yaml

.. warning::

   Copy the API key token to a secure location as soon as you create it.
   Treat it like a password.  Do **not** check it into source control, paste
   it into Slack or Teams, or share it with colleagues.  Each developer must
   use their own personal key.

3.4 Install Claude Code
------------------------

Claude Code is distributed as a global npm package:

.. code-block:: bash

   npm install -g @anthropic-ai/claude-code

Verify the installation:

.. code-block:: bash

   claude --version
   # Expected output: claude/X.Y.Z  (exact version will vary)

.. note::

   **macOS users:** if you encounter a permission error during the global
   install, use ``nvm`` to manage your Node.js installation rather than a
   system-level Node.  See
   `nvm installation instructions <https://github.com/nvm-sh/nvm#installing-and-updating>`_.

   **Windows users:** install Git for Windows before installing Claude Code
   if it is not already present.  Run the install from a standard Command
   Prompt or PowerShell session (not Git Bash).

3.5 Configure Claude Code to Use the Smarter Gateway
------------------------------------------------------

Claude Code must be redirected from Anthropic's public API endpoint to the
Smarter gateway.  Two environment variables control this:

.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Variable
     - What to set it to
   * - ``ANTHROPIC_BASE_URL``
     - ``https://smarter.internal``
   * - ``ANTHROPIC_AUTH_TOKEN``
     - The Smarter API key token from step 3.3

The recommended way to set these is in Claude Code's persistent settings
file so the configuration survives across terminal sessions.  The file
location depends on your OS:

* **Linux / macOS:** ``~/.claude/settings.json``
* **Windows:** ``%USERPROFILE%\.claude\settings.json``

Create the ``.claude`` directory if it does not exist, then create (or
edit) ``settings.json`` with the following content.  Replace
``<YOUR_SMARTER_API_KEY_TOKEN>`` with the token value from step 3.3:

.. code-block:: json

   {
     "env": {
       "ANTHROPIC_BASE_URL": "https://smarter.internal",
       "ANTHROPIC_AUTH_TOKEN": "<YOUR_SMARTER_API_KEY_TOKEN>"
     }
   }

If the file already exists and contains other settings, merge the ``"env"``
block into the existing top-level JSON object without removing any other keys.

.. important::

   ``ANTHROPIC_AUTH_TOKEN`` here is your **Smarter API key token** — not an
   Anthropic key.  Smarter exposes an Anthropic-compatible API surface;
   Claude Code will send your Smarter token as its bearer credential, and
   the gateway will use its own centrally managed Anthropic key for the
   upstream call.  You never possess or manage an Anthropic credential.

3.6 Pre-accept the Claude Code Onboarding
-------------------------------------------

When Claude Code detects a custom ``ANTHROPIC_BASE_URL`` it may attempt
an initial connectivity check against ``api.anthropic.com`` and stall the
first-run wizard.  Pre-mark onboarding as complete to bypass this:

Create (or edit) ``~/.claude.json`` (Linux/macOS) or
``%USERPROFILE%\.claude.json`` (Windows):

.. code-block:: json

   {
     "hasCompletedOnboarding": true
   }

If the file already has content, add ``"hasCompletedOnboarding": true`` to
the existing JSON object without removing other keys.

----

.. _concept-overview:

4. Concept Overview
===================

Before running anything, spend a few minutes understanding the three
components that compose the complete picture.

4.1 Smarter — the Enterprise LLM Gateway
------------------------------------------

Smarter is an on-premise, Kubernetes-native platform that acts as a managed
proxy layer between developer tools (such as Claude Code) and upstream LLM
providers (such as Anthropic).  Think of it as air-traffic control
for all AI requests: every prompt flows through Smarter, which enforces
authentication, applies cost-accounting codes, writes audit logs, and routes
traffic to the correct upstream model.

Smarter is LLM provider-agnostic.  Its connection to each upstream vendor
is a **platform-level concern** — configured once by the infrastructure team
and shared across all users.  As a developer, you authenticate to Smarter
with your personal API key; Smarter handles the upstream Anthropic
credential entirely behind the scenes.

4.2 The Smarter Manifest System
---------------------------------

Smarter resources — ChatBots, Plugins, API keys, data connectors, and more
— are described using **YAML manifest files**, a design deliberately modelled
after the Kubernetes ``kubectl`` workflow.  If you have used
``kubectl apply``, the pattern is immediately familiar.

Every manifest shares the same four-section skeleton:

.. code-block:: yaml

   apiVersion: smarter.sh/v1   # Identifies the Smarter API version
   kind: <ResourceKind>         # The type of resource being described
   metadata:                    # Identity: name, version, description
     name: <resource-name>
     version: 1.0.0
     description: <human-readable description>
   spec:                        # Resource-specific configuration fields
     <field>: <value>
   # status:                    # Read-only; populated by Smarter, not by you

The ``status`` section appears in manifests returned by the API and
describes the current live state of the resource; you never write to it.

You interact with manifests through the Smarter CLI using a verb-noun
command structure:

.. list-table:: Core Smarter CLI Commands
   :widths: 40 60
   :header-rows: 1

   * - Command
     - What it does
   * - ``smarter configure``
     - One-time interactive setup; writes ``~/.smarter/config.yaml``
   * - ``smarter manifest <kind> -o yaml``
     - Emits an annotated example manifest for the given resource kind
   * - ``smarter apply -f <file.yml>``
     - Creates or updates the resource described by the manifest.
       Pass ``--dry-run`` to preview the change without applying it.
   * - ``smarter get <kind>``
     - Lists resources of the given kind in your account
   * - ``smarter describe <kind> <name> -o yaml``
     - Returns the live manifest (including ``status``) for a specific resource
   * - ``smarter delete <kind> <name>``
     - Permanently removes a resource
   * - ``smarter deploy <kind> <name>``
     - Deploys a deployable resource (ChatBot, Plugin)
   * - ``smarter whoami``
     - Shows account information for the configured API key
   * - ``smarter version``
     - Prints the installed CLI version
   * - ``smarter status``
     - Returns real-time status of the Smarter platform itself

For a complete list of subcommands under any verb, run
``smarter <verb> --help``.  Full CLI reference:
``https://docs.smarter.sh/en/latest/smarter-framework/smarter-cli.html``

4.3 Resource Kinds Relevant to This Tutorial
---------------------------------------------

<cite name="4-1">The Smarter CLI interacts with a range of resource kinds
including ChatBots, Plugins, SqlConnections, Users, and ApiKeys.</cite>  The
kinds most relevant to your initial setup are:

.. list-table::
   :widths: 20 80
   :header-rows: 1

   * - Kind
     - Purpose in this tutorial
   * - ``ApiKey``
     - A personal Smarter authentication token.  This is what Claude Code
       sends as its bearer token to the gateway.  Each developer creates
       their own.
   * - ``ChatBot``
     - A deployable conversational AI resource.  Not used directly in this
       tutorial, but it is the principal resource kind you will work with
       once you move beyond basic Claude Code usage.
   * - ``Plugin``
     - Extends a ChatBot's knowledge domain using function-calling and data
       connectors (SQL, REST API, static data).  Out of scope for this
       tutorial but documented at
       ``https://docs.smarter.sh/en/latest/smarter-resources/plugins/``

Regarding the **Provider** resource kind: this is a platform-level resource
managed by the infrastructure team through Smarter's administrative interface.
It stores upstream vendor credentials (including the Anthropic API key) and
maps them to the LangChain-managed request pipeline inside Smarter.  Developers
do not create or modify Provider resources — that is an infrastructure concern.
The authoritative technical reference for the Provider manifest is at
``https://docs.smarter.sh/en/latest/smarter-resources/smarter-provider.html``
and is provided here for completeness; your infrastructure team will have
already applied the relevant configuration.

4.4 Claude Code and the LLM Gateway Pattern
---------------------------------------------

Claude Code is an agentic coding assistant that runs in your terminal.  By
default it calls ``https://api.anthropic.com`` directly.  In our case, we
override that endpoint using two environment variables that Claude Code reads
at startup:

.. list-table:: Claude Code Gateway Environment Variables
   :widths: 35 65
   :header-rows: 1

   * - Variable
     - Purpose
   * - ``ANTHROPIC_BASE_URL``
     - Overrides the API base URL; set to the internal Smarter gateway URL
   * - ``ANTHROPIC_AUTH_TOKEN``
     - The bearer token in every outbound API request; set to your Smarter
       API key token (not an Anthropic key)

These variables are set in ``~/.claude/settings.json`` under the ``"env"``
key as shown in :ref:`setup`.

The full data-flow, from your terminal to Anthropic and back, is:

.. code-block:: text

   ┌───────────────────────────────────────────────────────────────────┐
   │                     Developer Workstation                         │
   │                                                                   │
   │   Claude Code (terminal)                                          │
   │     ANTHROPIC_BASE_URL   → https://smarter.internal               │
   │     ANTHROPIC_AUTH_TOKEN → <your personal Smarter API key>        │
   └───────────────────────┬───────────────────────────────────────────┘
                           │  HTTPS  (internal network / VPN)
                           ▼
   ┌───────────────────────────────────────────────────────────────────┐
   │                Internal Smarter Gateway                           │
   │                                                                   │
   │   1. Authenticates your Smarter API key                           │
   │   2. Resolves your user to a cost-accounting code                 │
   │   3. Writes an audit log entry                                    │
   │   4. Substitutes the platform-level Anthropic API key             │
   │   5. Forwards the request upstream via LangChain                  │
   └───────────────────────┬───────────────────────────────────────────┘
                           │  HTTPS  (internet egress)
                           ▼
   ┌───────────────────────────────────────────────────────────────────┐
   │              Anthropic API  (api.anthropic.com)                   │
   │   claude-sonnet-4-6  (or whichever model is configured)          │
   └───────────────────────────────────────────────────────────────────┘

----

.. _step-by-step:

5. Step-by-Step
===============

.. note::

   The steps below assume you have completed all of :ref:`setup`.  All
   manifest YAML files can live anywhere on your filesystem.  We suggest
   creating a dedicated folder for Smarter work:

   .. code-block:: bash

      mkdir ~/smarter
      cd ~/smarter

5.1 Verify the Smarter CLI Configuration
-----------------------------------------

Confirm the CLI is connected to the internal gateway and your credentials are
valid:

.. code-block:: bash

   smarter whoami

Expected output (values will reflect your account):

.. code-block:: text

   username:    jsmith
   account:     Custom-Programming
   environment: prod
   api_base:    https://smarter.internal

If you see an authentication error instead, revisit step 3.2 and re-run
``smarter configure``.

5.2 Confirm Your API Key Is Active
------------------------------------

List the API keys registered to your account:

.. code-block:: bash

   smarter get apikeys

Your key from step 3.3 should appear in the list.  If the list is empty
and you have not yet created a key, return to step 3.3.

Retrieve the full manifest for your key (the ``status`` section will confirm
whether the key is active):

.. code-block:: bash

   smarter describe apikey jsmith-claudecode-workstation -o yaml

Look for ``status.active: true`` (or equivalent) in the output.  If the key
is inactive or its token needs to be rotated, delete it and recreate it:

.. code-block:: bash

   smarter delete apikey jsmith-claudecode-workstation
   smarter apply -f my-apikey.yml   # re-apply the manifest from step 3.3

5.3 Validate the Claude Code Settings File
-------------------------------------------

Before starting Claude Code, verify that ``settings.json`` is well-formed
JSON and contains the correct values.

On Linux/macOS:

.. code-block:: bash

   python3 -m json.tool ~/.claude/settings.json

On Windows (PowerShell):

.. code-block:: powershell

   Get-Content $env:USERPROFILE\.claude\settings.json | python -m json.tool

Expected output (token value masked here for illustration):

.. code-block:: json

   {
     "env": {
       "ANTHROPIC_BASE_URL": "https://smarter.internal",
       "ANTHROPIC_AUTH_TOKEN": "smarter_****"
     }
   }

If the command reports a JSON syntax error, open the file in your editor,
fix the error (the most common causes are a missing comma between fields or
a mismatched brace), and re-validate.

5.4 Start Claude Code and Confirm the Gateway Endpoint
-------------------------------------------------------

Open a **new** terminal window to ensure the settings file is freshly
loaded, then start Claude Code:

.. code-block:: bash

   claude

Once the Claude Code prompt appears, run the built-in status command:

.. code-block:: text

   /status

Claude Code prints a status report.  Locate the lines that show the API
endpoint and authentication token.  The endpoint line **must** read
``https://smarter.internal`` — not ``api.anthropic.com``:

.. code-block:: text

   API endpoint : https://smarter.internal
   Auth token   : *** (configured via settings.json)
   Model        : claude-sonnet-4-6

If you see ``https://api.anthropic.com`` instead, Claude Code is not reading
the settings file.  See :ref:`troubleshooting` section 7.4.

To exit the ``/status`` view and return to the prompt, press ``q`` or
``Escape``.

5.5 Confirm the Model
----------------------

Verify that Claude Code is using the approved model.  At the Claude
Code prompt:

.. code-block:: text

   /model

The current model should be ``claude-sonnet-4-6``.  If a different model is
shown, set it explicitly:

.. code-block:: text

   /model claude-sonnet-4-6

Claude Code will confirm the model selection.  The ``/model`` setting
persists for the session; to make it permanent across sessions, add a
``"model"`` key to ``~/.claude/settings.json``:

.. code-block:: json

   {
     "model": "claude-sonnet-4-6",
     "env": {
       "ANTHROPIC_BASE_URL": "https://smarter.internal",
       "ANTHROPIC_AUTH_TOKEN": "<YOUR_SMARTER_API_KEY_TOKEN>"
     }
   }

You are now ready to run the proof-of-concept test.

----

.. _proof-of-concept:

6. Proof of Concept
===================

The following exercise provides a concrete, verifiable end-to-end test.
Completing it confirms that your workstation is correctly configured and
that the full chain — Claude Code → Smarter gateway → Anthropic API — is
operational.

6.1 The Test Function
----------------------

Create a new file called ``power_utils.py`` in any convenient directory
with the following content:

.. code-block:: python

   # power_utils.py
   # Northern Aurora Power & Light — Custom Programming Area
   # Sample utility: AC power triangle calculations.

   import math


   def calculate_reactive_power(apparent_power_kva: float,
                                 power_factor: float) -> float:
       """
       Calculate reactive power (kVAR) from apparent power and power factor.

       Uses the AC power triangle relationship:
           Q = S * sin(arccos(PF))

       where S is apparent power (kVA), PF is the power factor,
       and Q is reactive power (kVAR).

       Parameters
       ----------
       apparent_power_kva : float
           Apparent power in kVA.  Must be strictly greater than zero.
       power_factor : float
           Dimensionless power factor.  Must be in the closed interval
           [0.0, 1.0].

       Returns
       -------
       float
           Reactive power in kVAR.

       Raises
       ------
       ValueError
           If apparent_power_kva <= 0 or power_factor is outside [0, 1].
       """
       if apparent_power_kva <= 0:
           raise ValueError(
               f"apparent_power_kva must be > 0; got {apparent_power_kva}"
           )
       if not 0.0 <= power_factor <= 1.0:
           raise ValueError(
               f"power_factor must be in [0, 1]; got {power_factor}"
           )
       theta = math.acos(power_factor)
       return apparent_power_kva * math.sin(theta)

6.2 Ask Claude Code to Explain the Function
--------------------------------------------

Navigate to the directory containing ``power_utils.py`` and start Claude
Code (open a new terminal if needed):

.. code-block:: bash

   cd /path/to/directory/containing/power_utils.py
   claude

At the Claude Code prompt, type:

.. code-block:: text

   Explain the calculate_reactive_power function in power_utils.py,
   including the mathematical relationship it implements and a worked
   numerical example.

Claude Code will read the file, analyze the code, and respond.

6.3 Expected Result
--------------------

A response confirming successful end-to-end operation will look similar to
the following (exact wording will vary):

.. code-block:: text

   The calculate_reactive_power function computes reactive power Q in kVAR
   from apparent power S (kVA) and power factor PF using the AC power
   triangle relationship:

       Q = S · sin(θ)     where  θ = arccos(PF)

   The power triangle has three sides:
     • S (apparent power, kVA)  — the hypotenuse
     • P (real power, kW)       — the adjacent side,  P = S · cos(θ)
     • Q (reactive power, kVAR) — the opposite side,  Q = S · sin(θ)

   The function first validates its inputs:
     • apparent_power_kva must be strictly positive (a zero or negative
       apparent power has no physical meaning in this context).
     • power_factor must be in [0, 1]; values outside this range are
       undefined for the AC power factor.

   It then derives the phase angle θ from math.acos(power_factor) and
   returns the product apparent_power_kva * math.sin(θ).

   Worked example — a 100 kVA transformer at 0.85 power factor:
     θ = arccos(0.85) ≈ 31.79°
     Q = 100 × sin(31.79°) ≈ 52.68 kVAR

If Claude Code returns a substantive analysis of the function along these
lines, your setup is working end-to-end:

* Claude Code is routing through the internal Smarter gateway.
* The gateway is authenticating your Smarter API key.
* The gateway is forwarding the request to Anthropic using the
  platform-level Anthropic credential.
* The response is returned to your terminal through the same path.

**Congratulations — you are fully onboarded.**

----

.. _troubleshooting:

7. Troubleshooting
==================

7.1 ``smarter whoami`` Returns a 401 Authentication Error
----------------------------------------------------------

**Symptom:**

.. code-block:: text

   Error: 401 Unauthorized — invalid credentials

**Cause:** The credentials entered during ``smarter configure`` are
incorrect, expired, or the API base URL is wrong.

**Fix:**

#. Re-run ``smarter configure`` and re-enter your Smarter username,
   password, and the correct base URL (``https://smarter.internal``).
#. If you have changed your password recently, make sure you use the
   updated password.
#. Re-run ``smarter whoami`` to confirm.

7.2 ``smarter apply`` Fails with a YAML Parsing Error
------------------------------------------------------

**Symptom:**

.. code-block:: text

   Error: could not parse manifest — invalid YAML at line N

**Cause:** YAML is whitespace-sensitive; the most common causes are
mixed tabs/spaces or inconsistent indentation depth.

**Fix:**

* Open the file in an editor that can display whitespace characters.
* Use **spaces only** — no tabs — throughout the file.
* Validate the file before applying it:

.. code-block:: bash

   python3 -c "import yaml, sys; yaml.safe_load(open('my-apikey.yml'))" \
     && echo "YAML is valid" || echo "YAML has errors"

7.3 ``smarter get apikeys`` Shows No Keys / API Key Is Missing
---------------------------------------------------------------

**Symptom:** The ``smarter get apikeys`` command returns an empty list,
or the key name you expect does not appear.

**Cause:** The ``smarter apply`` step from section 3.3 did not complete
successfully, or the manifest was applied under a different account.

**Fix:**

#. Re-run ``smarter whoami`` to confirm you are logged in as the correct
   user.
#. Reapply the key manifest: ``smarter apply -f my-apikey.yml``
#. Re-run ``smarter get apikeys`` to confirm the key appears.

7.4 Claude Code Shows ``api.anthropic.com`` in ``/status`` Instead of the Gateway URL
---------------------------------------------------------------------------------------

**Symptom:** After starting Claude Code and running ``/status``, the API
endpoint shows ``https://api.anthropic.com`` rather than
``https://smarter.internal``.

**Possible causes and fixes:**

.. list-table::
   :widths: 45 55
   :header-rows: 1

   * - Possible cause
     - Fix
   * - ``~/.claude/settings.json`` was not saved, or contains a JSON
       syntax error
     - Validate the file: ``python3 -m json.tool ~/.claude/settings.json``
       Fix any reported errors (missing commas, mismatched braces, etc.)
   * - Terminal session predates the settings file creation; the file was
       not loaded
     - Close all terminals and open a fresh one before running ``claude``
   * - ``ANTHROPIC_BASE_URL`` is set in your shell profile (e.g.,
       ``~/.bashrc``, ``~/.zshrc``) to a different value, overriding
       ``settings.json``
     - Check your shell profile and remove or correct the conflicting
       export.  Alternatively, unset it in the current session:
       ``unset ANTHROPIC_BASE_URL ANTHROPIC_AUTH_TOKEN`` then restart
       ``claude``
   * - VPN is not connected; the gateway hostname cannot be resolved
     - Connect to VPN and retry

7.5 Claude Code Returns a 401 Error After Starting
----------------------------------------------------

**Symptom:**

.. code-block:: text

   API Error: 401 {"type":"error","error":{"type":"authentication_error",
   "message":"Invalid bearer token"}}

**Cause:** The ``ANTHROPIC_AUTH_TOKEN`` in ``settings.json`` does not
match an active Smarter API key on your account.  Common reasons: the key
was deleted and not recreated, or the token value was pasted incorrectly
(e.g., with surrounding whitespace).

**Fix:**

#. Run ``smarter get apikeys`` to confirm the key is listed and active.
#. If the key is missing, recreate it (step 3.3) and copy the new token
   carefully.
#. Update ``~/.claude/settings.json`` with the correct token value —
   ensure there are no leading or trailing spaces inside the JSON string.
#. Open a new terminal and restart ``claude``.

7.6 Claude Code Returns a 403 or "Model Not Available" Error
-------------------------------------------------------------

**Symptom:**

.. code-block:: text

   API Error: 403 — model "claude-sonnet-4-6" is not available on
   this endpoint, or you do not have permission to use it.

**Cause:** Either the requested model is not configured at the platform
level, or your Smarter account does not have access to it.

**Fix:**

* Use ``/model`` inside Claude Code to check or change the active model.
* If the model you need is not available, contact the IT Department to
  request it be enabled on the internal Smarter gateway.
* Do not attempt to access Anthropic models outside the list of
  approved models — direct calls to ``api.anthropic.com`` bypass
  all governance controls and are not permitted per IT policy.

7.7 ``smarter apply`` Reports a Dry-Run Diff That Looks Unexpected
-------------------------------------------------------------------

**Symptom:** Running ``smarter apply --dry-run -f my-apikey.yml`` shows
changes you did not intend — for example, a version downgrade or an
unexpected field deletion.

**Cause:** The manifest on disk has drifted from the live resource state,
or a ``version`` field was edited accidentally.

**Fix:**

#. Retrieve the current live manifest: ``smarter describe apikey <name> -o yaml > current.yml``
#. Diff your local file against it: ``diff my-apikey.yml current.yml``
#. Reconcile the differences.  Increment ``metadata.version`` in your
   local file if you intend to update the resource.
#. Re-run with ``--dry-run`` to confirm the preview looks correct, then
   apply without the flag.

7.8 Getting Further Help
-------------------------

If you have worked through the troubleshooting steps above and still cannot
resolve the issue, contact the IT helpdesk and include:

* The exact error message (copy-paste the text; do not send a screenshot).
* The output of ``smarter whoami``.
* The output of ``/status`` from within Claude Code.
* The contents of ``~/.claude/settings.json`` — **redact** the
  ``ANTHROPIC_AUTH_TOKEN`` value before sharing.

----

.. _references:

8. References
=============

.. list-table:: Smarter Platform Documentation
   :widths: 45 55
   :header-rows: 1

   * - Resource
     - URL
   * - Smarter documentation home
     - ``https://docs.smarter.sh/en/latest/``
   * - Smarter CLI reference
     - ``https://docs.smarter.sh/en/latest/smarter-framework/smarter-cli.html``
   * - Smarter manifest overview
     - ``https://platform.smarter.sh/docs/manifests/``
   * - Smarter CLI download
     - ``https://smarter.sh/cli``
   * - Smarter Provider manifest reference (infrastructure team)
     - ``https://docs.smarter.sh/en/latest/smarter-resources/smarter-provider.html``
   * - Smarter Plugin documentation
     - ``https://docs.smarter.sh/en/latest/smarter-resources/plugins/``
   * - VS Code extension for Smarter manifests
     - ``https://marketplace.visualstudio.com/items?itemName=Querium.smarter-manifest``

.. list-table:: Claude Code Documentation (Anthropic)
   :widths: 45 55
   :header-rows: 1

   * - Resource
     - URL
   * - Claude Code overview
     - ``https://docs.anthropic.com/en/docs/claude-code/overview``
   * - Claude Code LLM gateway / custom endpoint configuration
     - ``https://docs.anthropic.com/en/docs/claude-code/llm-gateway``
   * - Claude Code npm package
     - ``https://www.npmjs.com/package/@anthropic-ai/claude-code``
