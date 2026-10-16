.. _napl-claude-code-programmer-tutorial:

Getting Started: Claude Code with Smarter at NAPL
=================================================

Goal
----

We will use Claude Code with Smarter to implement and test a small Python energy
calculation. Claude Code acts as a virtual coding partner: it reads the project,
proposes changes, and helps explain tests. You review the code and decide whether
it is correct. The exercise uses synthetic data and no production systems.

Prerequisites
-------------

You already have a Smarter account and know how to log in. You are comfortable
with Git, a terminal, Python functions, unit tests, and reviewing diffs. You need:

* Python 3 and Git installed, plus a terminal using Bash or Zsh. Windows users
  can follow the same commands inside WSL with Python and Git installed there.
* Claude Code installed using NAPL's approved method. If it is not supplied by
  IT, follow the `official installation instructions
  <https://code.claude.com/docs/en/quickstart>`_ using the approved version.
* VPN/network access if required by NAPL.
* The administrator's tested **gateway base URL**, allowed **Claude model ID**,
  personal **gateway credential**, and support contact.

.. important::

   The administrator must first complete :doc:`adding-anthropic-provider-napl`.
   This checkout labels Claude Code integration prerelease and unverified.
   Continue only after NAPL has accepted a working Anthropic-compatible route
   through its Smarter service. A Smarter browser login or registered model
   alone does not establish this connection.

Setup
-----

Confirm your tools:

.. code-block:: bash

   python3 --version
   git --version
   claude --version

For this walkthrough, NAPL's accepted gateway authenticates a personal credential
in the ``Authorization: Bearer`` header. Open a Bash terminal (run ``bash`` first if your current shell is Zsh).
In that terminal, run:

.. code-block:: bash

   read -r -p "NAPL gateway base URL: " ANTHROPIC_BASE_URL
   export ANTHROPIC_BASE_URL
   read -r -s -p "Your NAPL gateway credential: " ANTHROPIC_AUTH_TOKEN
   printf '\n'
   export ANTHROPIC_AUTH_TOKEN
   read -r -p "Approved Claude model ID: " ANTHROPIC_MODEL
   export ANTHROPIC_MODEL

These prompts keep the credential out of shell history. The URL is the
administrator-supplied gateway root, such as ``https://llm.napl.example``;
that address is illustrative. Do not append ``/v1/messages`` or use the
Workbench login URL. The credential is issued for this gateway, not your
Smarter password or the organization's Anthropic API key.

If NAPL's gateway instead uses ``x-api-key``, the administrator must supply
that configuration: use ``ANTHROPIC_API_KEY`` for the gateway credential in
place of ``ANTHROPIC_AUTH_TOKEN``. See the `official gateway connection guide
<https://code.claude.com/docs/en/llm-gateway-connect>`_. Keep credentials out of
tracked settings files. Resolve conflicting provider variables using NAPL's
instructions before starting; do not substitute a personal account.

Concept overview
----------------

Claude Code is a local coding tool, not an LLM model or a Smarter LLMClient.
For the accepted NAPL route, requests travel from Claude Code through the
company's Smarter gateway to Anthropic's Claude API. Smarter runs on NAPL
infrastructure; the Anthropic model remains hosted by Anthropic. Source context
sent for inference therefore leaves the local machine and follows NAPL's
approved data-handling policy.

The gateway must understand Anthropic Messages, streaming, and tool results.
Registering an OpenAI-compatible provider does not automatically satisfy that
contract. Local file edits and test commands are performed by Claude Code;
the gateway routes model requests. Treat generated code like a colleague's
unreviewed patch: inspect it and verify it with your own tests.

Step-by-step
------------

Step 1: Create an isolated exercise
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Choose a new directory outside production repositories:

.. code-block:: bash

   mkdir napl-energy-pairing
   cd napl-energy-pairing
   git init
   cat > energy.py <<'PY'
   def energy_kwh(power_kw, hours):
       """Return energy in kWh for non-negative power and duration."""
       raise NotImplementedError("Implement during the pairing exercise")
   PY
   cat > test_energy.py <<'PY'
   import unittest
   from energy import energy_kwh

   class EnergyTests(unittest.TestCase):
       def test_typical_load(self):
           self.assertEqual(energy_kwh(2.5, 4), 10.0)

       def test_zero_power(self):
           self.assertEqual(energy_kwh(0, 4), 0)

       def test_zero_duration(self):
           self.assertEqual(energy_kwh(2.5, 0), 0)

       def test_fractional_values(self):
           self.assertAlmostEqual(energy_kwh(1.2, 0.5), 0.6)

       def test_negative_power(self):
           with self.assertRaises(ValueError):
               energy_kwh(-1, 4)

       def test_negative_duration(self):
           with self.assertRaises(ValueError):
               energy_kwh(1, -4)

   if __name__ == "__main__":
       unittest.main()
   PY
   git add energy.py test_energy.py
   git commit -m "test: add NAPL energy pairing exercise"
   python3 -m unittest -v

The initial test run should fail with ``NotImplementedError``. That is the
starting condition, not a gateway problem. If Git requests your identity,
configure your approved name/email for this exercise repository and retry.

Step 2: Confirm the route
~~~~~~~~~~~~~~~~~~~~~~~~~

From this directory and the configured terminal, start:

.. code-block:: bash

   claude --model "$ANTHROPIC_MODEL"

Accept the directory trust prompt only after checking it names the exercise
folder. In the session, send ``Reply with NAPL gateway check. Do not use tools.``
and run ``/status``. Confirm the gateway URL, selected model, and gateway
credential source match the administrator's handoff. Have the pilot administrator
confirm the request in the gateway audit trail. Stop and report any mismatch
before submitting source code.

Step 3: Pair on the implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Paste this prompt into Claude Code:

.. code-block:: text

   Read energy.py and test_energy.py. First explain the intended behavior.
   Implement only energy_kwh in energy.py: return power_kw * hours, and
   raise ValueError if either argument is negative. Inputs are finite int
   or float values; booleans and other types are outside this exercise.
   Do not change the tests or add dependencies. Show your proposed change,
   run python3 -m unittest -v, and explain the result.
   Do not commit, push, or access any other project.

Review any proposed tool actions and the resulting diff. Allow only changes
and commands needed for this exercise; keep NAPL's approved permission settings.
Ask for an explanation if the implementation or test results are unclear.

Step 4: Independently verify
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Leave Claude Code with ``/exit``. Run these commands yourself:

.. code-block:: bash

   git status --short
   git diff -- energy.py test_energy.py
   python3 -m unittest -v
   python3 -c "from energy import energy_kwh; print(energy_kwh(2.5, 4))"

Confirm only ``energy.py`` changed and the tests were not weakened. A minimal
correct implementation is:

.. code-block:: python

   def energy_kwh(power_kw, hours):
       """Return energy in kWh for non-negative power and duration."""
       if power_kw < 0 or hours < 0:
           raise ValueError("Power and duration must be non-negative")
       return power_kw * hours

Step 5: Save the reviewed result
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After all checks pass:

.. code-block:: bash

   git add energy.py
   git commit -m "feat: implement validated energy calculation"

For the pilot, record the gateway/model/version, sanitized request identifier,
and test result through the administrator's supplied reporting process. Never
include the credential. No GitHub push is required for this practice repository.

Proof of concept
----------------

A successful exercise has all four results:

* ``/status`` shows the approved NAPL route and gateway credential source.
* The pilot administrator can attribute the request to your gateway identity.
* The independent test run reports ``Ran 6 tests`` followed by ``OK``.
* The calculation prints ``10.0`` and Git records the reviewed implementation.

Passing the tests alone proves the calculation works; the route/audit checks
also demonstrate that the coding session used the intended Smarter service.

Troubleshooting
---------------

**``claude`` is not found**
   Reopen the terminal after installation, check PATH, and follow the official
   installer troubleshooting instructions or contact NAPL desktop support.

**401/403 or an unexpected personal login**
   Confirm the gateway credential, expiry, and required header. Re-enter it
   through the hidden prompt. Use ``/status`` to check the active credential
   source and resolve conflicting settings with the administrator.

**404, an HTML response, or an invalid message format**
   Check the gateway base URL. A console page or OpenAI-only completion endpoint
   cannot serve this client. Give the application team the sanitized error and
   request identifier; do not work around the problem with a personal API key.

**Unknown model, 429, timeout, or incomplete streaming**
   Confirm the approved model ID and VPN. For 429, wait as directed by the
   service response. Persistent timeouts or broken streaming need gateway
   investigation; repeatedly starting sessions can add cost without fixing them.

**Tests still fail or Claude changes the tests**
   Inspect the diff, preserve the six acceptance tests, and ask Claude to correct
   only the implementation. Run the tests independently again before committing.

**Credential or confidential data entered in the wrong place**
   Stop the session and follow NAPL's credential-rotation/data-handling process.
   Supply sanitized diagnostics to the designated support contact.

References and version
----------------------

Prepared for repository commit ``8016b7cfc63ed8ccb3b7a77cf5a959e8f166a148``
on 1 October 2026. The administrator must validate the deployed integration and
approved tool/model versions before releasing this self-onboarding procedure.

* :doc:`adding-anthropic-provider-napl`
* `Claude Code Quickstart <https://code.claude.com/docs/en/quickstart>`_
* `Claude Code gateway configuration <https://code.claude.com/docs/en/llm-gateway-connect>`_
* `Gateway protocol requirements <https://code.claude.com/docs/en/llm-gateway-protocol>`_
