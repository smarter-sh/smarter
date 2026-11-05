AI Features in Software: Two-Week Online Course
===============================================

A two-week online course on putting LLMs inside a piece of software, safely, taught on the Doodle
of Smarter's web console: the sign-in page's illustration, which a Smarter LLMClient, the `Doodle
Editor
<https://github.com/smarter-sh/example-manifests/blob/main/smarter/llm-clients/llmclient-smarter-doodle-editor.yaml>`__,
chooses each day, and another, the `Doodle Artist
<https://github.com/smarter-sh/example-manifests/blob/main/smarter/llm-clients/llmclient-smarter-doodle-artist.yaml>`__,
draws. The whole feature is open source, in `apps/doodle/
<https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/doodle>`__, and runs on every
student's own platform. There are six 30-minute recorded lectures and a 90-minute live session
each week. Week 1 covers the feature, its AI parts and the contract with the model, and week 2 the
defenses around them and shipping. See :doc:`../course-formats` for the format, the grading scale
and the course policies, and :doc:`../ai-features` for an overview of the subject.

At a Glance
-----------

.. list-table::
   :widths: 25 75

   * - **Students**
     - Python developers who want to add LLM features to software they build.
   * - **Deployment**
     - Each student runs Smarter from source (``make init``), with the example manifests loaded
       and a superuser login, working **before** the course starts. Students change code and
       approve doodles in the Django admin, so a shared instance doesn't suit this course.
   * - **Models**
     - The models that the Doodle's manifests name, through the instructor's OpenAI key, and
       OpenAI's moderation model.
   * - **Workload**
     - 3 hours of instruction and 4 to 6 hours of assignments each week.
   * - **Cost**
     - Under $5 per student in model charges, capped with a
       :doc:`Budget </smarter-resources/smarter-budget>`.

Learning Objectives
-------------------

By the end of the course, students can:

1. Decide which parts of a feature a model should do and which code should do, and build the
   feature's safe answer first.
2. Declare a feature's AI parts as Smarter LLMClients and Guardrails, and prompt them from Python.
3. Design a model's request and answer as a validated contract with a menu of choices, and check
   every answer in code.
4. Defend a feature against a model's mistakes with a second model as judge, an allowlist
   sanitizer and tests in which the model is patched.
5. Design the human review, audit trail, switches and disclosure that a feature needs before
   its AI output reaches users.

Technical Prerequisites
-----------------------

- **Required:** Python: functions, classes, exceptions and type hints, and JSON.
- **Required:** Git, GitHub and pull requests, with a fork of `smarter
  <https://github.com/smarter-sh/smarter>`__.
- **Required:** Docker, and Smarter installed from source with a superuser login, showing the
  sign-in page's doodle, before Live session 1. See the :doc:`Smarter Instructor Guide
  </smarter-instructor>`.
- **Helpful:** `Pydantic <https://docs.pydantic.dev/>`__ models, Python's ``unittest.mock``,
  reading a Django app, `YAML <https://learnxinyminutes.com/docs/yaml/>`__, and having called an
  LLM API.
- **Not needed:** JavaScript or React, machine learning, or SVG. The course reads the Doodle's
  React app and SVG, but students don't write either.

Schedule
--------

The files that the lectures refer to are listed in full under `Smarter in the Source Code`_.

.. list-table::
   :header-rows: 1
   :widths: 10 18 72

   * - Week
     - Item
     - Content
   * - 1
     - Lecture 1 (30 min)
     - **The newsroom, and the safe answer first.** A feature as desks: the calendar, the editor,
       the platform's checks, the tone judge, the artist, the sanitizer and a superuser. Phase 1
       (`commit 0df9280ff
       <https://github.com/smarter-sh/smarter/commit/0df9280ff18c1155b6d1b8111a35dd42ec6d3302>`__)
       ships the whole feature with no LLM, and ``planner.py`` is what visitors see when every AI
       part fails.
   * - 1
     - Lecture 2 (30 min)
     - **AI resources as configuration, prompted from code.** The editor's and artist's
       manifests: model, temperature, system prompt, ``staffOnly`` and output Guardrails.
       ``prompting.py``'s ``single_use_api_key()``, ``prompt_llmclient()`` and
       ``assistant_text()``, extracted from ``verify_stackademy`` in phase 2 (`commit d07b91f67
       <https://github.com/smarter-sh/smarter/commit/d07b91f677ff0b8428ac36c62be9b5670f7492b1>`__),
       and why the platform uses its own chat api.
   * - 1
     - Lecture 3 (30 min)
     - **A menu, not a blank page.** ``editor_request()`` and the Pydantic contract (:doc:`ADR
       031 </adr/031-pydantic-over-json>`); ``default`` always on offer; a ``reason`` for every
       choice; ``parse_answer()`` and ``check_decision()``; ``has_blocked_word()``; and the trends
       filter, ``region_trends()``, as an allowlist on the way in.
   * - 1
     - Live session 1 (90 min)
     - The editor in the workbench, live, with its example prompts and a request the class writes
       together to tempt it off the menu. Writing a management command that prompts it. Start
       Assignments 1 and 2.
   * - 2
     - Lecture 4 (30 min)
     - **Judges and sanitizers.** The ``llm_judge`` Guardrail ``upbeat_occasion_input`` and
       ``tone_check()``, which fails closed, from phase 3 (`commit 2e6cb0806
       <https://github.com/smarter-sh/smarter/commit/2e6cb0806c126bcdf064f278d785f2901665aaa8>`__).
       The artist's SVG as untrusted input: ``sanitize.py``'s allowlist, ``<img>`` and the
       artwork's Content-Security-Policy.
   * - 2
     - Lecture 5 (30 min)
     - **Testing with the model patched out.** ``test_editor.py``, saved drawings and saved
       Wikimedia responses, and running the app's tests in the container.
   * - 2
     - Lecture 6 (30 min)
     - **People, paper trails and shipping.** Proposed drawings, *Preview the week*, Approve and
       Reject; ``DoodleEditorRun``; the switches, with ``enable_doodle_auto_approve`` off; the
       credit line on the page; Celery Beat, caching fallbacks, and cost from the journal. The
       blog post's takeaways as a design review checklist.
   * - 2
     - Live session 2 (90 min)
     - Capstone presentations (about 5 minutes each, with 2 minutes of questions).

Assignment 1 is due at the end of week 1, Assignment 2 in the middle of week 2, and Assignment 3
and the capstone at the start of Live session 2.

Smarter in the Source Code
--------------------------

.. include:: source-code.txt

Graded Assignments
------------------

Assignment 1: The Editor's Taste
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students apply a copy of the Doodle Editor's manifest with an editorial policy of their own, such
as science and education only, and run the same requests through both editors, including one
that tempts the model off the menu. They compare the choices and reasons, and say which of them
``check_decision()`` would refuse.

**Turn in:** the manifest, and a two-page Markdown report with each request, both answers and the
analysis.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - A working manifest
     - 4
     - Applies cleanly; the policy is stated in the system prompt, not scattered.
     - Edits that contradict the rest of the prompt.
   * - Evidence
     - 6
     - Real answers from both editors, pasted as they came.
     - Paraphrased, or one editor only.
   * - Analysis
     - 6
     - Explains each difference by a line of the prompts, and reads the reasons.
     - Lists differences without explaining them.
   * - The off-menu attempt
     - 4
     - Shows what the model did, and names the check that would catch it.
     - Assumes the prompt is enough.

Assignment 2: Prompting From Code
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write a management command in their fork that prompts their copy of the editor for a
day, with ``editor_request()`` and the helpers in ``prompting.py``, and prints each decision with
the verdict of ``check_decision()``. The api key it uses must be deleted even when the prompt
fails.

**Turn in:** a pull request against their own fork, and the command's output for two days.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Uses the platform
     - 6
     - Prompts through ``prompting.py``; the prompt shows in the journal.
     - Calls a provider's SDK directly.
   * - Parses and checks
     - 6
     - ``parse_answer()`` and ``check_decision()`` on every decision, refusals printed with why.
     - Prints the raw answer.
   * - Cleans up
     - 4
     - The api key is deleted on success and failure.
     - A key left behind when the prompt fails.
   * - Follows the code base
     - 4
     - A ``SmarterCommand`` with a docstring and prefixed log messages, like ``plan_doodles``.
     - A script outside the app's conventions.

Assignment 3: Trust Nothing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Students write at least six tests that feed crafted answers through ``parse_answer()`` and
``check_decision()`` with the model patched: malformed JSON, a choice off the menu, a holiday
when the catalog has a theme, a bad link, a caption that is too long and a blocked topic in
other words. They look for one answer that passes but shouldn't, and propose a fix.

**Turn in:** a pull request against their own fork with the tests, their output from the
container, and a paragraph on the gap they found, or why they found none.

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Cases covered
     - 7
     - Six or more distinct ways to fail, each asserting the reason given.
     - Only malformed JSON and off-menu.
   * - Isolation
     - 4
     - No real prompts; the model is patched, as in ``test_editor.py``.
     - Tests that call the LLM.
   * - The gap
     - 6
     - A real gap with a failing test and a fix, or a convincing search that found none.
     - "The checks look fine."
   * - Runs as shown
     - 3
     - Output from the container matches the pull request.
     - Took the tests' passing on trust; output not included.

Capstone Projects
-----------------

Students choose one, and present it in Live session 2.

Capstone A: An AI Feature of Your Own
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Build an AI feature into software, with its AI parts as Smarter resources
and its safety in code.

In their fork of Smarter, or in a Django project of their own that prompts a Smarter platform,
students build a small feature in which an LLMClient makes a choice or writes something that
users see: a tip of the day picked from the documentation, a suggested description for a new
resource, or a summary of an account's week. It must work without the model, give the model a
menu or a schema, check every answer in code, record what was asked and answered, and have a
switch. A feature meant for Smarter itself must be agreed with the maintainers in a GitHub issue
first.

**What students turn in:**

- A pull request against their own fork, with the LLMClient's (and any Guardrail's) manifest.
- Tests with the model patched, and their output.
- A one-page design note: the feature's desks, what each check guards against, and the cost per
  day from the journal.
- A five-minute presentation, including one answer the code refuses.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - A safe answer first
     - 15
     - The feature works, and says nothing wrong, with the model off.
     - Breaks or shows an error without the model.
   * - Contract and checks
     - 25
     - A validated request and answer, and every rule of the prompt enforced in code.
     - Trusts the prompt.
   * - AI parts as resources
     - 15
     - Manifests for the model's taste; prompted through the platform.
     - A prompt string in the code.
   * - Record and control
     - 15
     - What was asked and answered is kept; a switch turns the AI off.
     - No record, or no way to turn it off.
   * - Tests
     - 20
     - Refusals and failures tested, with the model patched.
     - Only the happy path, or tests that prompt a model.
   * - Design note
     - 10
     - Each check tied to the failure it prevents.
     - A description of the code.

Capstone B: Red Team the Newsroom
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Learning objective.** Evaluate an AI feature's defenses with evidence, layer by layer.

On their own platform, students attack the Doodle with at least twenty cases: requests that
tempt the editor off the menu, trend titles written to inject instructions, occasions that are
sad but contain no blocked word, and briefs that ask the artist for scripts, links or a drawing
over the base scene. For each case they record which layer stopped it: the prompt, an output
Guardrail, ``check_decision()``, the judge, the sanitizer, or the person in the admin. They
propose one change, with a test that fails before it.

**What students turn in:**

- A table of the cases, with the input, what each model answered, and the layer that stopped it,
  or none.
- A three-page analysis of where the defenses overlap and where they are thin, citing the code.
- A pull request against their own fork with the proposed change and its test.

**How it is graded (100 points):**

.. list-table::
   :header-rows: 1
   :widths: 22 8 35 35

   * - Criterion
     - Pts
     - Exemplary
     - Developing
   * - Range of attacks
     - 20
     - Every layer is tested, with cases a careful attacker would try.
     - Twenty variants of one attack.
   * - Evidence
     - 20
     - Real answers and editor runs, recorded as they came.
     - Results from memory, or assumed from the code.
   * - Attribution to layers
     - 25
     - Each case traced to the code or resource that stopped it.
     - "It was blocked."
   * - The change
     - 20
     - A failing test, then a fix that makes it pass without breaking the others.
     - A suggestion without a test.
   * - Writing
     - 15
     - Concise, organized and specific.
     - Long or general.

Recommended Texts
-----------------

- **Required:** `How Two Smarter LLMClients Create the Sign-in Page's Daily Doodle
  <https://blog.smarter.sh/2026/11/04/smarter-doodle-llm-editor-artist/>`__ and
  :doc:`/smarter-framework/developer-reference/react-integration/doodle`, in week 1.
- **Required:** :doc:`/smarter-resources/smarter-guardrail` and the `OWASP Top 10 for LLM
  Applications <https://genai.owasp.org/llm-top-10/>`__, in week 2.
- **Reference:** Chip Huyen, *AI Engineering* (O'Reilly, 2025), on evaluation, guardrails and the
  architecture of AI applications.
- **Reference:** John Berryman and Albert Ziegler, *Prompt Engineering for LLMs* (O'Reilly, 2024),
  on designing the prompts and answers that software consumes.
- **In the repository:** `editor.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/doodle/editor.py>`__,
  `prompting.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/prompting.py>`__
  and `sanitize.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/doodle/sanitize.py>`__.

Further Study
-------------

.. include:: further-study.txt
