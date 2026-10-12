Full Stack Development with Django and React
============================================

**Why Smarter.** Django hosts each React app: a view and a template render a root element, React
mounts on it, and calls back into Django's REST API with the user's session. It is a clear,
complete example of a pattern that many real applications use, and students can follow a feature
from database column to pixel.

**Read.** :doc:`/smarter-framework/developer-reference/react-integration`,
:doc:`/smarter-framework/smarter-chat/web-console-hosting`,
:doc:`/smarter-framework/smarter-chat/api-contract`.

**Exercises.**

- Follow one list page from the Django URL, view and template, through the Vite build manifest, to
  the React component and the API it calls.
- Add a new list page for a resource, end to end, with Django and React tests.
- Study how the chat API contract is published as a JSON Schema from Pydantic models, and how
  the React side's types are generated from it. Discuss what this prevents.

**Course plans.** Three complete, ready-to-teach plans, each with a schedule, graded assignments
and rubrics, two capstone projects, recommended texts, further study and technical prerequisites.
See :doc:`course-formats` for what the formats have in common.

.. toctree::
   :maxdepth: 1

   Classroom bootcamp: 8 hours <full-stack-development/bootcamp>
   Two-week online course: 6 hours <full-stack-development/two-week>
   Four-week online course: 12 hours <full-stack-development/four-week>

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
