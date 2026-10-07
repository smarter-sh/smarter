Getting Started with Claude Code in Smarter
===========================================

Goal
----

Use Claude Code through Smarter to support virtual coding-pair workflows for the custom programming team.

Prerequisites
-------------

This guide assumes that the reader:

* already has a Smarter account and can log in
* already has access to an Anthropic-backed Claude model in Smarter
* understands basic software development workflow concepts
* can work with source control and a local terminal
* can interpret LLM output critically rather than accepting it blindly

Setup
-----

Before starting, confirm the following:

* your Smarter account is active
* Anthropic has been added as a provider in Smarter
* a Claude model has been registered and validated
* your local development project is available in git
* you understand your team's coding, security, and review standards

Concept Overview
----------------

Smarter acts as the managed platform layer for LLM access. It centralizes model access, credentials, and model availability. Claude Code is the model-assisted coding experience used by the programming team.

In practical terms, programmers are not onboarding a raw model directly. They are using a Claude model that has already been exposed through Smarter.

This matters because it gives the team:

* a common entry point for approved models
* centralized credential handling
* repeatable onboarding
* a shared way to test and compare model behavior

Step-by-Step
------------

1. Sign in to Smarter.

2. Confirm that the approved Claude model is visible in the model or provider selection area.

3. Open the relevant authoring, prompt, or coding workflow in Smarter.

4. Select the approved Claude model.

5. Define a small, low-risk programming task for your first run. Good examples include:

   * generate a utility function
   * refactor a small method
   * write unit-test scaffolding
   * explain an unfamiliar code block

6. Give the model enough technical context to do useful work. Include:

   * the programming language
   * the desired output format
   * constraints such as style, framework, and security requirements
   * a short success criterion

7. Review the output carefully. Do not treat the first answer as production-ready.

8. Test the generated code locally.

9. Refine the prompt and rerun as needed.

10. Commit only the code that passes your normal engineering review standard.

Prompt Pattern
--------------

A simple starter pattern is:

::

   Task: Write a Python helper function.
   Context: This function will be used in our internal service.
   Requirements:
   - Python 3.13
   - add docstring
   - handle invalid input safely
   - include one example test case
   Output: code only

Proof of Concept
----------------

Use a concrete coding task such as the following:

* ask Claude to generate a small helper function
* copy the result into your local project
* run the code or test
* confirm that it behaves as expected

A successful proof of concept is not just "the model answered." A successful proof of concept means the model produced code that is understandable, testable, and usable after human review.

Troubleshooting
---------------

**Problem: The Claude model is missing.**

Confirm that the Anthropic provider and Claude model were created and validated in Smarter.

**Problem: The output is too vague.**

Add more context. State the language, framework, expected format, and acceptance criteria.

**Problem: The code looks correct but fails locally.**

Treat the output as a draft. Debug it, add tests, and rerun with tighter constraints.

**Problem: Different developers get inconsistent results.**

Standardize prompts, define shared model defaults, and keep proof-of-concept tasks narrowly scoped.

**Problem: The model suggests insecure or non-compliant code.**

Reject the output, restate your security constraints explicitly, and apply normal peer review before merging any change.

Best Practices
--------------

* start with small tasks
* prefer explicit prompts over vague requests
* verify every code suggestion
* keep humans in the review loop
* use git normally: branch, test, review, commit, and push

Expected Outcome
----------------

At the end of this tutorial, a programmer should be able to sign in to Smarter, select the approved Claude model, complete a small coding task, validate the output locally, and continue using the workflow as a virtual coding pair.
