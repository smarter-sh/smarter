Getting Started with Claude Code through Smarter
================================================

Goal
----

Use Claude Code through Northern Aurora Power & Light's (NAPL) Smarter
platform to calculate electricity consumption from synthetic meter readings.
Build and test a Python function using the CLI, VS Code extension, or
desktop app.

Prerequisites
-------------

* Familiarity with Python, Git, and a terminal.
* Python 3 and Git installed locally.
* Your preferred Claude Code interface installed with gateway support.
* An existing Smarter account and access to NAPL's Smarter service.

Setup
-----

Your administrator must first complete
:doc:`napl-adding-anthropic-provider` and supply:

* The Anthropic proxy URL, such as
  ``https://<NAPL-Smarter-host>/api/v1/proxy/napl_anthropic/``.
* Your personal Smarter API key.
* An approved Claude model ID available through that proxy.

Use managed configuration where provided. Otherwise, choose one setup
below and merge it with your personal settings, replacing the placeholders.
Keep credentials out of project files, prompts, and Git.

CLI
~~~

Add this to your user settings at ``~/.claude/settings.json``
(``%USERPROFILE%\.claude\settings.json`` on Windows). Create the
``.claude`` folder and ``settings.json`` file if they do not exist:

.. code-block:: json

   {
     "env": {
       "ANTHROPIC_BASE_URL": "<Smarter proxy URL>",
       "ANTHROPIC_API_KEY": "<your Smarter API key>"
     }
   }

Restart Claude Code after saving. If asked to approve the API key, first
confirm it is the Smarter key supplied by your administrator.

VS Code extension
~~~~~~~~~~~~~~~~~

Open **Preferences: Open User Settings (JSON)** and add:

.. code-block:: json

   {
     "claudeCode.environmentVariables": [
       { "name": "ANTHROPIC_BASE_URL", "value": "<Smarter proxy URL>" },
       { "name": "ANTHROPIC_API_KEY", "value": "<your Smarter API key>" }
     ]
   }

Reload VS Code and open the Claude Code panel. These are personal user
settings, rather than the repository's ``.vscode/settings.json``.

Desktop app
~~~~~~~~~~~

Desktop uses its third-party inference configuration, rather than the
CLI's connection settings:

1. Open **Help > Troubleshooting > Enable Developer Mode**, then
   **Developer > Configure Third-Party Inference**.
2. Select **Gateway**, **Static API key**, and the ``x-api-key`` auth scheme.
3. Enter the supplied proxy URL and your Smarter API key.
4. Test the connection and select **Apply Changes** to relaunch locally.

Use the **Code** tab with a **Local** session for this exercise. If managed
settings make the form read-only, ask your administrator to correct them.

Concept overview
----------------

.. code-block:: text

   Claude Code -> NAPL Smarter proxy -> Anthropic's Claude API

Claude Code reads and edits local project files using its tools. Smarter
authenticates requests and supplies the organization's Anthropic key;
programmers hold only their own Smarter keys. Claude runs at Anthropic,
so use the synthetic data in this exercise.

Step-by-step
------------

1. Open a practice project
~~~~~~~~~~~~~~~~~~~~~~~~~~

Create an empty folder outside the Smarter repository:

.. code-block:: console

   mkdir napl-meter-demo
   cd napl-meter-demo
   git init

Open that folder in your chosen interface:

* **CLI:** run ``claude`` from the folder.
* **VS Code:** open the folder and the Claude Code panel.
* **Desktop:** select the folder in a Local Code session.

Select the approved model using ``/model <model-ID>`` in the CLI or the
model picker in the graphical interface.

2. Confirm the connection
~~~~~~~~~~~~~~~~~~~~~~~~~

Check the configured gateway address and credential source. In the CLI,
``/status`` should show NAPL's proxy URL and ``ANTHROPIC_API_KEY``. In
graphical interfaces, inspect the connection settings configured above.

Send ``Reply with Hello NAPL.``. Confirm that the request reached Smarter
by matching your user, request time, and proxy in its usage records, with
your administrator's help if needed.
A reply alone does not prove that requests passed through Smarter.

3. Build with your coding partner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Send this prompt in any interface:

.. code-block:: text

   Create meter.py with consumption_kwh(previous, current).
   Readings are non-negative integers representing cumulative kWh.
   Return current - previous. Raise ValueError for a negative reading
   or a decreasing reading; do not assume meter rollover.

   Create test_meter.py using Python's unittest, with six tests:
   normal consumption, equal readings, a zero starting reading,
   negative previous, negative current, and decreasing readings.

   Explain your plan first and wait for my approval. After approval,
   create only these two files. Use no external dependencies. Run tests
   with python -B -m unittest -v test_meter (or python3 -B if needed).

Review the plan before approving it, then inspect both files and any
tool permissions. Ask Claude to explain unfamiliar code.

4. Run and review the tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ask Claude to run the tests using its command tool, then verify
independently in your terminal. ``-B`` prevents Python cache files:

.. code-block:: console

   python -B -m unittest -v test_meter
   python -B -c "from meter import consumption_kwh; print(consumption_kwh(1000, 1250))"
   git status --short

Use ``python3`` if that is your Python 3 command. If a test fails, share
the failure with Claude, review the proposed fix, and rerun the tests.

Proof of concept
----------------

You have completed the exercise when:

* All six tests pass, ending with ``OK``.
* Only ``meter.py`` and ``test_meter.py`` were created in the practice repo.
* A matching request is recorded against the intended Smarter proxy.

Check the function and generated tests against these cases:

.. list-table:: Expected consumption results
   :header-rows: 1

   * - Previous (kWh)
     - Current (kWh)
     - Expected result
   * - 1000
     - 1250
     - ``250`` kWh
   * - 1000
     - 1000
     - ``0`` kWh
   * - 0
     - 250
     - ``250`` kWh
   * - -1
     - 100
     - ``ValueError``
   * - 100
     - -1
     - ``ValueError``
   * - 1250
     - 1000
     - ``ValueError``

This checks basic model access and local tools. Full streaming and
token-counting compatibility require separate validation. Review generated
code before using it.

Troubleshooting
---------------

* **Login prompt or 401:** check the interface's proxy URL and credential
  source for a conflicting token or helper. A Smarter web login does not
  configure Claude Code; use the personal Smarter key supplied for API access.
* **404 or 403:** verify the proxy URL with your administrator; do not
  append ``/v1/messages`` to the configured base URL.
* **Model unavailable:** use the supplied model ID; ask your administrator
  if it is missing from the model picker.
* **No files or tests run:** confirm the practice folder is open and
  review pending tool permissions. Run the test command manually if needed.

If the problem persists, send your administrator the exact error, your
Claude Code interface and version, and the configured proxy URL. Redact
API keys and tokens from any shared output or settings.

References
----------

* :doc:`napl-adding-anthropic-provider`
* `Claude Code gateway connections
  <https://code.claude.com/docs/en/llm-gateway-connect>`_
* `Claude Code in VS Code
  <https://code.claude.com/docs/en/vs-code>`_
* `Desktop gateway settings
  <https://claude.com/docs/third-party/claude-desktop/gateway>`_
* `Desktop in-app configuration
  <https://claude.com/docs/third-party/claude-desktop/in-app-configuration>`_

AI assistance disclosure
------------------------

This tutorial was drafted and revised with assistance from OpenAI Codex.
