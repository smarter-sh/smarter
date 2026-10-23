.. Getting Started: Claude Code with Smarter
   NAPL capstone tutorial for the custom programming area.
   Intended location in the docs tree: smarter-platform/
   Created with the assistance of Claude (Anthropic), using our team's original
   ideas to meet the requirements of the capstone project for the AI Integration
   in Enterprise course.

Getting Started: Claude Code with Smarter
==========================================

.. note::

   **Acknowledgment.** This page was created with the assistance of Claude
   (Anthropic), using our team's original ideas to meet the requirements of the
   capstone project for the AI Integration in Enterprise course.

.. contents:: On this page
   :local:
   :depth: 2


Goal
----

**We will use Claude Code with Smarter to implement and test a small function
in a practice repository, with every model request routed through Smarter so
that it is authenticated, budgeted, and audited.**

By the end you will have registered Anthropic as an LLM
:doc:`provider </smarter-resources/smarter-provider>` in Smarter, connected the
Claude Code command-line agent to Smarter, and used it to turn a failing unit
test into a passing one. Expect about 45 minutes.

.. note::

   **Smarter does not ship with Claude Code support.** Out of the box, Smarter
   can register Anthropic as a provider and proxy calls for *Smarter
   resources*, but it does not provide the endpoint that Claude Code itself
   talks to. This tutorial covers the parts you do yourself and tells you
   exactly which piece the platform team supplies. See
   :ref:`napl-concept-gap`.


Prerequisites
-------------

This tutorial assumes you are an experienced programmer. You should already be
comfortable with:

- Working in a terminal (bash, zsh, or PowerShell) and setting environment
  variables.
- Git: cloning, committing, and reading diffs.
- Reading and writing YAML, including indentation rules.
- Basic HTTP and REST ideas: base URLs, bearer tokens, and status codes such as
  401 and 404.
- Running a unit test suite from the command line. This tutorial uses Python
  and ``pytest``, but the skills transfer.
- Logging in to the Smarter web console with your NAPL account.

You do **not** need prior experience with Smarter manifests, Claude Code, or
large language models. Those are taught below.


Setup
-----

Complete everything in this section before you begin the steps.

Access
~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Item
     - Detail
   * - Smarter account
     - You can log in to the Smarter web console.
   * - Administrator rights
     - Registering a provider (Part A) needs an administrator-level Smarter
       account and edit access to the deployment's ``.env`` file. If you are
       not an administrator, ask the platform team to perform Part A and
       resume at step 6.
   * - Anthropic API key
     - Issued to you by NAPL IT, and only needed if you perform Part A. Do not
       create a personal key for this purpose.
   * - Gateway URL
     - The address of the Claude Code endpoint published by the platform team,
       written below as ``<SMARTER_GATEWAY_URL>``. See
       :ref:`napl-concept-gap` for why it is needed. If it has not been
       published, stop and ask. Do not guess an address.

Tools
~~~~~

**Smarter CLI.** Install it by following the :doc:`CLI documentation
</smarter-platform/cli>`, then confirm it works:

.. code-block:: console

   smarter --help

**Claude Code.**

.. code-block:: console

   # macOS, Linux, WSL
   curl -fsSL https://claude.ai/install.sh | bash

   # Windows (PowerShell)
   irm https://claude.ai/install.ps1 | iex

   # Verify
   claude --version

If those installers are blocked on your workstation image, use
``npm install -g @anthropic-ai/claude-code`` or see the `official setup guide
<https://docs.claude.com/en/docs/claude-code/setup>`_.

**An editor with YAML support.** VS Code with the `Smarter manifest extension
<https://marketplace.visualstudio.com/items?itemName=querium.smarter-manifest>`_
validates Smarter manifests as you type.

Practice repository
~~~~~~~~~~~~~~~~~~~

Create a throwaway repository containing one stub function and one test file.
Never use a production repository for this tutorial.

.. code-block:: console

   mkdir napl-claude-demo && cd napl-claude-demo
   git init
   python3 -m venv .venv && source .venv/bin/activate
   pip install pytest

.. code-block:: python
   :caption: loadstats.py

   def peak_load(readings):
       """Return the highest value in a list of meter readings (kWh).

       Missing readings are given as None and must be ignored.
       Raise ValueError if there are no usable readings.
       """
       raise NotImplementedError

.. code-block:: python
   :caption: test_loadstats.py

   import pytest
   from loadstats import peak_load


   def test_returns_maximum():
       assert peak_load([10.5, 42.0, 7.25]) == 42.0


   def test_ignores_missing_readings():
       assert peak_load([None, 5.0, None, 9.0]) == 9.0


   def test_no_usable_readings_raises():
       with pytest.raises(ValueError):
           peak_load([None, None])

Commit the starting point and confirm the tests fail, as they should:

.. code-block:: console

   git add . && git commit -m "Starting point"
   pytest -q

.. code-block:: text

   FAILED test_loadstats.py::test_returns_maximum - NotImplementedError
   FAILED test_loadstats.py::test_ignores_missing_readings - NotImplementedError
   FAILED test_loadstats.py::test_no_usable_readings_raises - NotImplementedError
   3 failed


Concept Overview
----------------

Smarter manifests
~~~~~~~~~~~~~~~~~

Smarter manages every resource (providers, chatbots, plugins, secrets) the same
way: you describe it in a YAML file called a :doc:`Smarter API Manifest
</smarter-framework/pydantic/smarter-manifests>` and apply it with the CLI.
If you have used ``kubectl apply``, the workflow is familiar. Every manifest
has four top-level keys:

- **apiVersion**: always ``smarter.sh/v1``.
- **kind**: the type of resource, for example ``Provider``.
- **metadata**: the resource's ``name``, ``description``, and ``version``.
- **spec**: the configuration itself.

Providers
~~~~~~~~~

A :doc:`Provider </smarter-resources/smarter-provider>` is Smarter's
registration of an LLM vendor and model. OpenAI, Google AI, and Meta AI are
pre-registered at deployment and need only an API key. Anthropic is an
*additional* provider, so it needs both a key in the deployment environment and
an applied ``Provider`` manifest. When you apply one, Smarter verifies it by
calling the vendor's API and marking it active.

The Smarter Proxy
~~~~~~~~~~~~~~~~~

Smarter resources do not call vendors directly. They route through the
:doc:`Smarter Proxy </smarter-resources/smarter-proxy>`, which holds vendor
credentials, enforces budgets before a call proceeds, and records activity in
the :doc:`Smarter Journal </smarter-framework/smarter-journal>`. As a result
you never see or handle the Anthropic key.

.. note::

   Smarter's :doc:`cost accounting </smarter-platform/cost-accounting>` tracks
   token usage. Setting up NAPL cost-tracking codes for teams and projects is
   handled by Accounting and is outside this tutorial.

How Claude Code connects to a model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Claude Code is an agent that runs in your terminal, reads and edits files in a
repository, and runs commands, asking your permission along the way. It sends
its model requests in Anthropic's *Messages API* format. Claude Code can be
redirected to an enterprise **LLM gateway** using two environment variables:

- **ANTHROPIC_BASE_URL**: where to send requests.
- **ANTHROPIC_AUTH_TOKEN**: the credential presented there.

.. _napl-concept-gap:

The gap this project fills
~~~~~~~~~~~~~~~~~~~~~~~~~~

Putting those ideas together explains why Claude Code is not a one-click
feature in Smarter:

.. code-block:: text

   Claude Code  --(Messages API)-->  [ Gateway endpoint ]  -->  Smarter Proxy
                                       supplied by the           (auth, budget,
                                       platform team              audit, key)
                                                                      |
                                                                      v
                                                                 Anthropic API

- **What Smarter does:** it registers Anthropic, verifies it, and proxies Smarter
  resources to it. That is Part A.
- **What Smarter does not do:** it does not natively expose the Messages API
  endpoint that Claude Code expects. The platform team provides that endpoint, and you
  receive its address as ``<SMARTER_GATEWAY_URL>``. That is why Part B is
  configuration on your side only.

Two credentials are involved, and you only ever hold one of them:

- **The Anthropic key**, held by Smarter and never shown to developers.
- **Your Smarter API key**, which identifies you, can be revoked individually,
  and carries your account's budget and audit trail.

Working with an agent
~~~~~~~~~~~~~~~~~~~~~

Three ideas make the difference between a useful agent and a risky one.

- **Project memory.** Claude Code reads a ``CLAUDE.md`` file in your repository
  at the start of each session. It is where you record build commands,
  conventions, and off-limits areas.
- **Plan before acting.** In *plan mode* the agent can read but not change
  files, so you can review its approach before any edit happens.
- **Permissions.** By default Claude Code asks before editing files or running
  commands. Those prompts are your safety net. Read them.

Safe use at NAPL
~~~~~~~~~~~~~~~~

NAPL operates critical energy infrastructure, so treat the agent as a capable
but fallible colleague working through an external service. See also the
platform :doc:`security </smarter-platform/security>` documentation.

.. warning::

   The Claude models are not hosted on-premise. Smarter is the on-premise
   control point, but model calls leave the NAPL network for Anthropic's API.
   Prompts, file contents the agent reads, and command output are sent to the
   provider.

- Follow NAPL data classification policy. If a repository holds data you may
  not send externally, do not run Claude Code in it.
- Keep credentials, tokens, and production connection strings out of reach of
  the agent.
- Use development and test environments only.
- Keep permission prompts on, and read commands before approving them.
- Agent-written code gets the same review, testing, and security scanning as
  any other change. You own what you commit.


Step-by-Step
------------

Part A: Register Anthropic in Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Perform Part A once per Smarter deployment. If Anthropic is already registered,
run step 6 to confirm and continue to Part B.

**1. Obtain the Anthropic API key**

Use the key issued to NAPL IT for the Smarter deployment. If you are creating
it in the `Anthropic Console <https://console.anthropic.com/>`_, choose
**Settings > API Keys > Create Key**, name it descriptively (for example
``smarter-napl-prod``), and copy it immediately, because it is shown only once.

.. danger::

   Never commit an API key to version control, paste it into a ticket, or put
   it in a manifest. Keys belong in the deployment environment only.

**2. Give the key to Smarter**

Smarter reads provider credentials from environment variables. Add this line to
the ``.env`` file at the root of the Smarter deployment:

.. code-block:: bash
   :caption: .env

   SMARTER_ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx

Restart the application so it loads the credential:

.. code-block:: console

   make restart

.. note::

   On the shared NAPL deployment the infrastructure team owns this file and the
   restart procedure. Send them the request instead of editing it yourself.

**3. Generate a manifest template**

Ask the CLI for a known-good example for the Smarter version you are running:

.. code-block:: console

   smarter manifest provider

Keep it open as a reference. Smarter is under active development, so the CLI is
the authoritative source for the current schema.

**4. Write the provider manifests**

Create one manifest per model. Registering two lets you compare cost and
quality later. Start with Sonnet, a balanced default for day-to-day coding:

.. code-block:: yaml
   :caption: anthropic-sonnet.yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-sonnet
     description: Claude Sonnet for NAPL custom programming
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-sonnet-5-5

Then add Opus, the most capable option, for hard debugging and architecture
work:

.. code-block:: yaml
   :caption: anthropic-opus.yaml

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-opus
     description: Claude Opus for NAPL custom programming
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-opus-5-5

.. note::

   Model identifiers are case-sensitive and must match Anthropic's published
   names exactly. Model names change over time, so confirm the current IDs on
   Anthropic's `models overview
   <https://docs.claude.com/en/docs/about-claude/models/overview>`_ page before
   applying.

**5. Apply the manifests**

.. code-block:: console

   smarter apply -f anthropic-sonnet.yaml
   smarter apply -f anthropic-opus.yaml

Smarter registers each provider and starts a verification check: it calls
Anthropic with the stored key and confirms the model is reachable.

**6. Confirm the providers are active**

.. code-block:: console

   smarter describe provider anthropic-sonnet
   smarter describe provider anthropic-opus

Look for a ``status`` block reporting successful verification (see
:ref:`napl-proof-of-concept`). Verification is asynchronous: if the status is
``pending``, wait about 30 seconds and run the command again. The **Providers**
page in the web console should also list both as active. For the full manifest
schema, see the :doc:`Provider reference </smarter-resources/smarter-provider>`.

Part B: Connect Claude Code to Smarter
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**7. Create your Smarter API key**

In the Smarter web console open **API Keys** and create a key for Claude Code
(see :doc:`/smarter-platform/api-keys`). Copy it immediately. This is your
personal credential.

**8. Point Claude Code at the gateway**

For a quick test in the current shell:

.. code-block:: console

   export ANTHROPIC_BASE_URL="<SMARTER_GATEWAY_URL>"
   export ANTHROPIC_AUTH_TOKEN="<your-smarter-api-key>"

On Windows PowerShell, set the same variables like this:

.. code-block:: console

   $env:ANTHROPIC_BASE_URL = "<SMARTER_GATEWAY_URL>"
   $env:ANTHROPIC_AUTH_TOKEN = "<your-smarter-api-key>"

For a persistent setup that keeps secrets out of your shell profile, use Claude
Code's user-level settings file:

.. code-block:: json
   :caption: ~/.claude/settings.json

   {
     "env": {
       "ANTHROPIC_BASE_URL": "<SMARTER_GATEWAY_URL>",
       "ANTHROPIC_AUTH_TOKEN": "<your-smarter-api-key>"
     }
   }

.. code-block:: console

   chmod 600 ~/.claude/settings.json

On Windows, ``chmod`` does not apply. Keep the file in your user profile
folder and do not share it.

Prefer not to hand-write this file? :ref:`Part D <napl-part-d>` generates it
from the manifest you applied in Part A.

To pin a model, add ``ANTHROPIC_MODEL`` set to the model ID the gateway exposes.
Anthropic's `LLM gateway guide
<https://docs.anthropic.com/en/docs/claude-code/llm-gateway>`_ documents
further options, including a helper-script approach for rotating tokens.

.. important::

   Never commit ``settings.json`` or any file containing your token. Keep
   tokens out of any repository-level ``.claude/settings.json``.

**9. Smoke-test the connection**

.. code-block:: console

   cd napl-claude-demo
   claude

At the prompt, ask something harmless and verifiable:

.. code-block:: text

   > Summarize what this repository contains.

A reply that correctly mentions ``loadstats.py`` and its tests confirms the
connection works. Type ``/exit`` or press ``Ctrl+C`` twice to leave.

Part C: Complete the goal with Claude Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**10. Write project memory**

Inside the session, run ``/init`` to draft a ``CLAUDE.md``, then edit it by hand
so it contains at least:

.. code-block:: markdown
   :caption: CLAUDE.md

   # napl-claude-demo

   ## Commands
   - Run tests: `pytest -q`  (all tests must pass before a commit)

   ## Conventions
   - Python 3, type hints on public functions.

   ## Boundaries
   - Do not modify `test_loadstats.py`.
   - Never read or write `.env*` files.

**11. Plan first**

Press ``Shift+Tab`` to cycle into plan mode, then ask:

.. code-block:: text

   > Read loadstats.py and test_loadstats.py. Propose a plan to make all
   > tests pass without changing the tests.

Review the plan. It should describe filtering out ``None`` values and raising
``ValueError`` when nothing remains. If it proposes editing the tests, reject it
and restate the boundary.

**12. Implement and verify**

Leave plan mode (``Shift+Tab``) and ask:

.. code-block:: text

   > Implement the plan, then run pytest and show me the output.

Read each file-edit and command prompt before approving it.

**13. Review and commit**

Exit Claude Code and review the change exactly as you would a colleague's pull
request:

.. code-block:: console

   git diff
   pytest -q
   git add -A && git commit -m "Implement peak_load"

.. _napl-part-d:

Part D: Generate the settings from your manifest (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Part B had you type the model and gateway into ``settings.json`` by hand. That
duplicates information Smarter already holds: the ``Provider`` manifest from
step 4 names the model. The ``claude_code_settings`` helper reads that manifest
and writes the matching Claude Code settings, so the model is defined in one
place. The full class and function reference is on the
:doc:`Claude Code settings API </smarter-resources/claude-code-settings-api>`
page.

The helper takes the **model** from the manifest. It cannot take the gateway
URL from there, because the manifest does not contain it, so you pass in the
``<SMARTER_GATEWAY_URL>`` from Setup.

**14. Install the helper's dependency**

Place ``claude_code_settings.py`` and your ``anthropic-sonnet.yaml`` from
step 4 in one folder, then install the YAML reader it uses:

.. code-block:: console

   pip install pyyaml

**15. Generate the settings file**

Create a small script, replacing the example URL with your real
``<SMARTER_GATEWAY_URL>``:

.. code-block:: python
   :caption: make_settings.py

   from claude_code_settings import (
       ClaudeCodeSettings,
       load_provider_manifest,
       write_settings,
   )

   manifest = load_provider_manifest("anthropic-sonnet.yaml")
   settings = ClaudeCodeSettings(
       manifest,
       gateway_url="https://smarter.napl.example/claude",
   )
   print(settings.env)
   print("Wrote", write_settings(settings, "~/.claude/settings.json"))

Run it:

.. code-block:: console

   python make_settings.py

.. code-block:: text

   {'ANTHROPIC_BASE_URL': 'https://smarter.napl.example/claude', 'ANTHROPIC_MODEL': 'claude-sonnet-5-5'}
   Wrote /home/you/.claude/settings.json

The helper validates the manifest before writing anything. It stops with a
clear ``ValueError`` if the file is not a Smarter ``Provider``, if the provider
is not ``anthropic``, or if the model is missing.

.. note::

   By default the helper does **not** write your API key into the file. Export
   it in your shell instead, as shown in step 8. If you accept the risk of a
   token on disk, pass ``include_token=True`` along with an ``api_key``.

**16. Check the result**

The generated file contains only the non-secret values:

.. code-block:: json
   :caption: ~/.claude/settings.json

   {
     "env": {
       "ANTHROPIC_BASE_URL": "https://smarter.napl.example/claude",
       "ANTHROPIC_MODEL": "claude-sonnet-5-5"
     }
   }

Export ``ANTHROPIC_AUTH_TOKEN`` as in step 8, then repeat the smoke test from
step 9. Because the model comes from the manifest, changing the model in Smarter
and re-running ``make_settings.py`` keeps Claude Code in step with it.


.. _napl-proof-of-concept:

Proof of Concept
----------------

You are done when you can show all four of the following.

**1. Smarter reports Anthropic as verified**

.. code-block:: console

   smarter describe provider anthropic-sonnet

.. code-block:: yaml
   :caption: Expected output (trimmed)

   apiVersion: smarter.sh/v1
   kind: Provider
   metadata:
     name: anthropic-sonnet
     description: Claude Sonnet for NAPL custom programming
     version: 1.0.0
   spec:
     provider:
       name: anthropic
       model: claude-sonnet-5-5
   status:
     verified: true
     active: true

Exact field names in ``status`` can vary by Smarter version. What matters is
that verification succeeded.

**2. Claude Code answers through Smarter**

The smoke test in step 9 returns a correct summary of your repository.

**3. The tests pass**

.. code-block:: console

   pytest -q

.. code-block:: text

   ...                                                                [100%]
   3 passed

**4. Smarter saw the work**

In the Smarter console, the :doc:`journal </smarter-framework/smarter-journal>`
or logs show requests attributed to your account from the time of your session.
This is the evidence that model traffic was authenticated and audited by
Smarter, not sent around it.

**Optional.** If you completed Part D, ``~/.claude/settings.json`` contains the
model named in your Smarter ``Provider`` manifest, and ``/model`` inside a
Claude Code session shows the same model.


Troubleshooting
---------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Symptom
     - Likely cause and fix
   * - ``API key not found`` at Smarter startup
     - ``SMARTER_ANTHROPIC_API_KEY`` is missing from ``.env``, or the
       application was not restarted. Add it and run ``make restart``.
   * - Provider status ``verification failed``
     - The Anthropic key is invalid or revoked. Obtain a new key, update
       ``.env``, and restart.
   * - ``Model not found`` on apply
     - The ``model`` value does not exactly match Anthropic's published ID.
       Identifiers are case-sensitive.
   * - Manifest validation error
     - Almost always YAML indentation. Compare your file with the output of
       ``smarter manifest provider``.
   * - Status stuck on ``pending``
     - Verification is asynchronous. Wait 30 seconds and re-run
       ``smarter describe provider <name>``.
   * - ``smarter: command not found``
     - The Smarter CLI is not installed or not on your ``PATH``. Reinstall it
       and open a new terminal.
   * - Claude Code returns ``401`` or an authentication error
     - Your Smarter API key is wrong, expired, or revoked. Create a new one
       (step 7) and update ``ANTHROPIC_AUTH_TOKEN``.
   * - Claude Code returns ``404``, a connection error, or an unexpected
       response format
     - ``ANTHROPIC_BASE_URL`` is wrong, the gateway is unreachable, or the
       endpoint does not speak the Messages API. Re-check the URL from the
       internal wiki and your VPN or network access, then ask the platform team
       to confirm the endpoint.
   * - Certificate or TLS errors
     - The gateway uses an internal certificate authority. Point Node at the
       NAPL root certificate, for example
       ``export NODE_EXTRA_CA_CERTS=/path/to/napl-root-ca.pem``.
   * - Requests rejected for budget reasons
     - Smarter enforces budgets before forwarding a call. Contact the platform
       team about your account's allowance.
   * - Claude Code keeps asking permission for the same command
     - This is expected. Review the command, and use ``/permissions`` only to
       allow commands you have deliberately decided are safe.
   * - The agent edits files you told it not to touch
     - Add the path to *Boundaries* in ``CLAUDE.md``, deny it in
       ``/permissions``, and reject the edit. Report persistent cases to the
       platform team.
   * - ``ModuleNotFoundError: No module named 'yaml'``
     - The helper's dependency is missing. Run ``pip install pyyaml`` in the
       same environment you run the script from.
   * - ``ValueError: gateway_url must be an http(s) URL``
     - The placeholder ``<SMARTER_GATEWAY_URL>`` is still in the script.
       Replace it with the real address from the internal wiki.
   * - ``ValueError: plain http is only allowed for localhost``
     - The gateway address starts with ``http://``. Use the ``https://``
       address, or ask the platform team if only plain http is available.
   * - ``ValueError: spec.provider.name must be 'anthropic'``
     - The manifest describes a different provider. Point the script at the
       Anthropic manifest from step 4.
   * - ``ValueError: unsupported apiVersion`` or ``expected kind 'Provider'``
     - The file is not a Smarter ``Provider`` manifest, or was written for a
       different schema version. Compare it with ``smarter manifest provider``.

For Smarter issues beyond this tutorial, see the platform
:doc:`troubleshooting guide </smarter-platform/trouble-shooting>`. If you remain
stuck, ask in the custom programming team channel and include the exact
command, the full error text, and the output of ``claude --version``. **Never
paste an API key or token into a message.**

.. seealso::

   - :doc:`/smarter-resources/smarter-provider`
   - :doc:`/smarter-resources/smarter-proxy`
   - :doc:`/smarter-resources/FENT20_claude-code-settings-api`
   - `Claude Code documentation
     <https://docs.claude.com/en/docs/claude-code/overview>`_
   - `Claude Code LLM gateway guide
     <https://docs.anthropic.com/en/docs/claude-code/llm-gateway>`_
