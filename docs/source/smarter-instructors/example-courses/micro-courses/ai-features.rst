AI Features in Software
=======================

**Why Smarter.** Courses on building with LLMs usually end where the hard part starts: a model
answers a prompt in a notebook, and the answer is printed. Putting that model inside a product,
where its answer decides what thousands of people see, raises questions a notebook never does.
What may the model choose from? Who checks its answer, and what happens when it's wrong? Where
does its prompt live, who pays for it, and who can turn it off? Smarter's web console answers all
of them in one small, cheerful, fully open source feature: the Doodle, the illustration on the
sign-in page, which two Smarter LLMClients choose and draw every day. `How Two Smarter LLMClients
Create the Sign-in Page's Daily Doodle
<https://blog.smarter.sh/2026/11/04/smarter-doodle-llm-editor-artist/>`__ tells its story. The
stakes are low enough to let the models make real decisions, and visible enough that each one has
to be right:

- **The feature works without the AI.** A calendar of reviewed artwork chooses each region's
  doodle a week ahead, and the LLMs only improve on it: `planner.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/doodle/planner.py>`__.
- **The AI parts are configuration.** The editor, the artist and their judge are SAM resources
  in YAML, with their own models, prompts and Guardrails, which the platform's code prompts
  through the chat api like any client: `prompting.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/prompting.py>`__.
- **A menu, not a blank page.** The editor chooses from a JSON list of candidates, and code checks
  every choice again: `editor.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/doodle/editor.py>`__.
- **A second model as judge.** An ``llm_judge`` Guardrail checks the tone that word lists can't,
  and fails closed: `upbeat-occasion-input.yaml
  <https://github.com/smarter-sh/example-manifests/blob/main/smarter/guardrails/upbeat-occasion-input.yaml>`__.
- **Generated output is untrusted.** The artist's SVG is cleaned against an allowlist before
  anyone sees it: `sanitize.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/doodle/sanitize.py>`__.
- **A person has the last word.** New drawings wait for a superuser's approval in the admin, every
  prompt is kept, each part has a switch, and the page says when an AI chose its doodle:
  `admin.py <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/doodle/admin.py>`__.

.. image:: https://cdn.smarter.sh/docs/smarter-instructors/example-courses/micro-courses/ai-features/signin-panel.png
   :alt: The Doodle on the production sign-in page: an LLMClient chat window joined to icons for a Plugin, a Guardrail, a database and a Secret, with fireworks and confetti, the caption Happy Independence Day!, and the note Drawn by a Smarter AI application. Learn how
   :width: 100%

**What the course covers.** Deciding which parts of a feature belong to a model and which to
code; building the feature's safe answer first; declaring the AI parts as LLMClients and
Guardrails, and prompting them from code; designing the request and the answer as a contract,
with a menu of choices and a reason for each; checking every answer in code; filtering what goes
into a prompt; judging what code can't check with a second model; treating generated markup as
untrusted; human review, audit trails, switches and disclosure; scheduling, caching and cost;
and testing a feature whose models are patched out.

**Look at.**

- `apps/doodle/ <https://github.com/smarter-sh/smarter/tree/main/smarter/smarter/apps/doodle>`__,
  the whole feature.
- `llmclient-smarter-doodle-editor.yaml
  <https://github.com/smarter-sh/example-manifests/blob/main/smarter/llm-clients/llmclient-smarter-doodle-editor.yaml>`__,
  the editor's manifest, and its `artist
  <https://github.com/smarter-sh/example-manifests/blob/main/smarter/llm-clients/llmclient-smarter-doodle-artist.yaml>`__.
- `prompting.py
  <https://github.com/smarter-sh/smarter/blob/main/smarter/smarter/apps/llmclient/prompting.py>`__,
  how the platform's own code prompts an LLMClient.
- `smarter-doodle <https://github.com/smarter-sh/smarter/tree/v0.42.10/smarter/react/packages/smarter-doodle>`__,
  the React app on the sign-in page.

Each course plan lists every file that it uses under *Smarter in the Source Code*.

**Read.** :doc:`/smarter-framework/developer-reference/react-integration/doodle`,
:doc:`/smarter-resources/smarter-llmclient`, :doc:`/smarter-resources/smarter-guardrail`,
`How Two Smarter LLMClients Create the Sign-in Page's Daily Doodle
<https://blog.smarter.sh/2026/11/04/smarter-doodle-llm-editor-artist/>`__, `LLM Guardrails in YAML:
How Smarter Declares, Orders and Audits Them
<https://blog.smarter.sh/2026/06/11/smarter-llm-guardrails-yaml/>`__, `Django-React Integration
<https://blog.smarter.sh/2026/05/29/react-integration/>`__.

**Exercises.**

- Open the Smarter Doodle Editor in the workbench, click one of its example prompts, then edit
  the request to tempt it off the menu. Which of your attempts would ``check_decision()`` have
  caught?
- Read the three Doodle commits in order, and list what the feature could do after each one
  without any LLM at all.
- Feed ``sanitize_svg()`` the saved ``dangerous.svg`` from the tests, and explain what each removed
  element or attribute could have done on the sign-in page.
- Write an ``llm_judge`` Guardrail for a feature of your own, and find an input that it gets
  wrong. Should the feature fail open or closed?
- Turn the Doodle's switches off one at a time on your own platform, and describe what visitors
  see each time.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common. The :doc:`ai-applications` course
builds LLMClients without code, and this one puts them into code. The
:doc:`../master-classes/ai-application-development` goes further, into the platform that runs
them.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <ai-features/bootcamp>
   Two-week online course: 6 hours <ai-features/two-week>
   Four-week online course: 12 hours <ai-features/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
