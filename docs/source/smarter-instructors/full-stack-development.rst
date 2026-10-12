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

See the :doc:`Smarter Instructor Guide </smarter-instructor>` to install Smarter and set up
a class.
