Prompt Engineering
==================

**Why Smarter.** Students change a model's behavior by editing a manifest, with no code, and see
the result straight away in the prompt engineering :doc:`workbench </smarter-framework/smarter-chat>`,
whose Console shows the configuration, the API calls and every tool call beside the chat. The same
prompt can be tried against several providers and models by changing two lines.

**Read.** :doc:`/smarter-resources/smarter-llmclient`, :doc:`/smarter-resources/smarter-plugin`,
:doc:`/smarter-resources/llmclient/styles`, :doc:`/smarter-framework/smarter-manifests`.

**Exercises.**

- Start from the built-in ``simple`` LLMClient. Rewrite its ``defaultSystemRole`` to give it a
  persona and a narrow job, then write test prompts that it should answer and prompts that it
  should decline.
- Run the same ten prompts at ``defaultTemperature`` 0 and 1, and on two models. Compare the
  answers, the tokens used and the cost.
- Give an LLMClient knowledge with a :doc:`SkillPlugin </smarter-resources/plugin/plugin/skill>` or
  a :doc:`Static Plugin </smarter-resources/plugin/plugin/static>`, and the ability to act with a
  :doc:`Websearch Plugin </smarter-resources/plugin/plugin/websearch>` or an
  :doc:`API Plugin </smarter-resources/plugin/plugin/api>`. Discuss when the model decides to use a
  tool, and how the plugin's description influences that decision.
- Design an application for a real client (a campus office, a club, a local business), brand its
  chat with ``spec.config.styles``, and present it.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <prompt-engineering/bootcamp>
   Two-week online course: 6 hours <prompt-engineering/two-week>
   Four-week online course: 12 hours <prompt-engineering/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
