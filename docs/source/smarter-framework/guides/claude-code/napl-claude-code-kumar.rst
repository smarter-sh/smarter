Getting started with Claude Code at NAPL
========================================

Goal
----

We will use Claude Code with Smarter to implement and test a small electricity
usage helper, then review its changes as a human and AI programming pair
The finished function totals synthetic kWh readings accurately and rejects
negative or non-finite readings

Prerequisites
-------------

* Your existing NAPL Smarter account and access to its web console
* The administrator's tested Proxy URL and approved Claude model ID from
  :doc:`Adding Anthropic <napl-anthropic-provider-kumar>`
* Claude Code installed through NAPL's approved software process
* Python 3.11 or later, git, curl, a text editor and a Bash terminal
* Familiarity with Python functions, unit tests and reviewing a git diff

On Windows use Bash in WSL, with these tools installed in that environment
Platform installation, IDE extensions and accounting setup are handled by the
other project teams

Setup
-----

1. In the Smarter account dashboard, use **New API Key**, give it a description
   such as ``NAPL Claude Code pilot``, keep it active, and save it
   Copy the key into your approved password manager when it is displayed
   If key creation is restricted, obtain an individual key from the administrator
2. Open a Bash terminal and check the tools

   .. code-block:: console

      claude --version
      python3 --version
      git --version
      curl --version

3. Replace the example address below with the exact Proxy URL the administrator
   supplied, without a trailing slash
   The model is an example — use the exact approved identifier if it differs
   The hidden prompt expects your Smarter key, not the Anthropic provider key

   .. code-block:: bash

      export ANTHROPIC_BASE_URL="https://YOUR-SMARTER-HOST/api/v1/proxy/napl_claude"
      export ANTHROPIC_MODEL="claude-sonnet-4-6"
      unset ANTHROPIC_API_KEY CLAUDE_CODE_OAUTH_TOKEN
      unset CLAUDE_CODE_USE_BEDROCK CLAUDE_CODE_USE_VERTEX CLAUDE_CODE_USE_FOUNDRY
      read -r -s -p "Smarter API key: " ANTHROPIC_AUTH_TOKEN
      printf '\n'
      export ANTHROPIC_AUTH_TOKEN

   These exports apply to this terminal session and its child processes
   Keep credentials out of project files and shell commands saved in git
   If NAPL distributes managed settings, follow those settings and ask the
   administrator to resolve conflicts instead of trying to override them

Concept overview
----------------

Claude Code runs on your workstation and can propose file edits and commands
It sends native Anthropic requests to the configured Smarter Proxy, which
authenticates your Smarter key and forwards them with the server's provider key
Anthropic runs the selected Claude model and returns the response through Smarter

``ANTHROPIC_AUTH_TOKEN`` supplies a bearer credential to Smarter
``ANTHROPIC_BASE_URL`` chooses the endpoint, while ``ANTHROPIC_MODEL`` chooses
the model — changing one does not set the other
Creating an LLMClient or selecting a Workbench model is not required for this
native Proxy workflow

You own the requirements, review and test results
Use Claude Code to propose an implementation, inspect the diff, and run the
tests yourself before accepting it

Step-by-step
------------

1. Confirm routing and model access
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

From the same terminal, request the model list through Smarter

.. code-block:: bash

   curl --fail-with-body --silent --show-error \
     "$ANTHROPIC_BASE_URL/v1/models" \
     -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
     -H "anthropic-version: 2023-06-01"

Expect a successful JSON response with a ``data`` array of model IDs
Confirm that the approved model is available, following pagination if needed
Then make a small inference request

.. code-block:: bash

   curl --fail-with-body --silent --show-error \
     -D /tmp/napl-proxy-headers.txt \
     "$ANTHROPIC_BASE_URL/v1/messages" \
     -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
     -H "anthropic-version: 2023-06-01" \
     -H "Content-Type: application/json" \
     --data "{\"model\":\"$ANTHROPIC_MODEL\",\"max_tokens\":32,\"messages\":[{\"role\":\"user\",\"content\":\"Reply with NAPL_READY\"}]}"

Expect a successful message response with a text content block containing
``NAPL_READY`` and usage information
The response headers saved in ``/tmp/napl-proxy-headers.txt`` should include
``X-Smarter-Proxy: napl_claude`` — header names are case-insensitive
Do not proceed if authentication or routing fails

2. Create a small practice repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Choose a new directory, then create an isolated exercise

.. code-block:: console

   mkdir napl-energy-pilot
   cd napl-energy-pilot
   git init

Save this starter as ``energy.py``

.. code-block:: python

   def total_kwh(readings):
       raise NotImplementedError

Save these acceptance tests as ``test_energy.py``

.. code-block:: python

   import unittest
   from decimal import Decimal

   from energy import total_kwh


   class TestTotalKwh(unittest.TestCase):
       def test_exact_total(self):
           result = total_kwh(["12.5", "7.25", "0.1"])
           self.assertIsInstance(result, Decimal)
           self.assertEqual(result, Decimal("19.85"))

       def test_empty(self):
           self.assertEqual(total_kwh([]), Decimal("0"))

       def test_zero(self):
           self.assertEqual(total_kwh(["0", "0.00"]), Decimal("0"))

       def test_decimal_precision(self):
           self.assertEqual(total_kwh(["0.1", "0.2"]), Decimal("0.3"))

       def test_negative(self):
           with self.assertRaises(ValueError):
               total_kwh(["2", "-0.01"])

       def test_non_finite(self):
           for value in ("NaN", "Infinity", "-Infinity"):
               with self.subTest(value=value), self.assertRaises(ValueError):
                   total_kwh([value])

       def test_invalid_number(self):
           with self.assertRaises(ValueError):
               total_kwh(["not-a-number"])


   if __name__ == "__main__":
       unittest.main()

Run ``python3 -m unittest -v`` once to confirm the starter fails with
``NotImplementedError``, then save the baseline

.. code-block:: console

   git add energy.py test_energy.py
   git commit -m "test: define energy helper acceptance cases"

3. Pair with Claude Code
~~~~~~~~~~~~~~~~~~~~~~~~

Start Claude Code from this directory and check ``/status``
Confirm the NAPL Proxy address, the intended model and the environment-token
authentication source before sharing any code

.. code-block:: bash

   claude --model "$ANTHROPIC_MODEL"

Give it this task

.. code-block:: text

   Read energy.py and test_energy.py
   Explain your plan, then implement total_kwh(readings) in energy.py only
   Input is a list of decimal strings
   Return a Decimal total using direct Decimal conversion, never float
   Return Decimal("0") for an empty list
   Raise ValueError for negative, non-finite or invalid numeric strings
   Keep the supplied tests unchanged and add no dependencies
   Ask before running commands and explain the final diff

Approve the scoped file edit and the test command when prompted
Read the implementation and confirm that it checks finiteness before comparing
a Decimal against zero, and translates invalid numeric conversion into
``ValueError``

4. Verify and review
~~~~~~~~~~~~~~~~~~~~

After leaving the Claude Code session, run these commands yourself

.. code-block:: console

   python3 -m unittest -v
   git diff -- energy.py test_energy.py
   git status --short
   python3 -c 'from energy import total_kwh; print(total_kwh(["12.5", "7.25", "0.1"]))'

Confirm that only ``energy.py`` changed and that the tests were not weakened
Fix any failing case with another focused prompt, then repeat the review

Proof of concept
----------------

The expected outcome is

* The HTTP response identifies ``napl_claude`` and Claude Code's ``/status``
  shows the same gateway
* The test runner reports ``Ran 7 tests`` and ``OK``
* The example command prints ``19.85``
* You can explain the implementation and have reviewed every change

These are acceptance targets, not captured output from a deployed NAPL system
Report the versions and results to the pilot owner, including any failure
When the checks pass, commit the reviewed implementation

.. code-block:: console

   git add energy.py
   git commit -m "feat: total validated electricity readings"

Troubleshooting
---------------

.. list-table:: Common onboarding failures
   :header-rows: 1
   :widths: 30 70

   * - Symptom
     - Action
   * - ``claude`` is not found
     - Use the approved installation and reopen the terminal so PATH is refreshed
   * - Wrong endpoint or login in ``/status``
     - Launch from the terminal where the exports were set and check managed
       settings with the administrator
   * - 401
     - Check that the hidden prompt received your active Smarter key, not the
       upstream Anthropic key or a browser session cookie
   * - 403 or 404
     - Confirm the Proxy name, account access and allowed paths — do not append
       ``/v1`` to the configured base URL
   * - Unknown model, 402 or 429
     - Confirm model access or contact the administrator about budget and rate
       limits, using the error body to distinguish the cause
   * - CLI hangs or tool calls fail
     - Give the administrator the versions and redacted error — a successful
       text request alone does not prove streaming or tool-call compatibility
   * - Tests fail
     - Keep the original assertions and have Claude inspect the failing case,
       especially float conversion, invalid strings and non-finite Decimals

For client configuration details, see
`Connect Claude Code to a gateway
<https://code.claude.com/docs/en/llm-gateway-connect>`_
When finished with this terminal session, remove the temporary credential

.. code-block:: bash

   unset ANTHROPIC_AUTH_TOKEN
