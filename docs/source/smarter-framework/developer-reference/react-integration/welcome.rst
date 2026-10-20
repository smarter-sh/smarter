Welcome Dialog React Component
===================================

The Welcome dialog greets a new user on the first web console page that they
visit, and gives them a short tour of the platform in eight steps: what Smarter
is, what their new account is preloaded with, the generative AI technologies
that they can try with it, connecting MCP servers (MCPClient resources, which
the dialog calls MCP Servers, the name new users know), retrieval-augmented
generation with Vectorstores (whose cloud infrastructure costs real money for as
long as it exists), self-hosting open models from Hugging Face with an
LLMHost (whose cloud infrastructure costs real money for as long as it runs),
how Smarter runs in production on Kubernetes, the cloud orchestration
technology behind platforms such as Netflix, YouTube and TikTok, and where to
start. Its last step links to the Get
Weather example LLMClient, the Prompt Workbench's list of LLMClients, this
documentation, and the project's website. Its text and its orange accent follow
the welcome email that the platform sent the user, so that the dialog reads as
the next page of that email.

The dialog's first step has a **Show at startup** box, which is ticked for a new
user. While it is ticked, the dialog opens by itself on the first web console page
that the user visits each time they sign in. When the user closes the dialog, in
any way, or reaches its last step, the dialog records the box's choice. Unticked,
the date is stored in ``UserProfile.welcomed_at``, so the dialog doesn't open by
itself again, on any device or browser. Ticked, the date is cleared. Either way,
a flag in the user's session keeps it from opening by itself again until they
next sign in. The user can take the tour again at any time from **Welcome Tour**
in the user menu, and tick or untick the box there: any element with the
``data-smarter-welcome-open`` attribute opens it.

Unlike the other React components, which each have their own page,
``@smarter/welcome`` is mounted on every web console page:
``templates/dashboard/base.html`` includes ``templates/react/welcome.html`` for
signed-in users. Its illustrations are the Keen theme's ``dozzy-1`` set, which
has a version of each for the dark theme. The dialog is a modal: Escape, its
close button, Skip tour and a click outside of it close it, the arrow keys move
between its steps, and Tab keeps the focus inside it.

API
---

.. automodule:: smarter.apps.dashboard.views.views.api.welcome
   :members:
   :show-inheritance:
   :no-index:

Template Tags
-------------

.. automodule:: smarter.apps.dashboard.templatetags.react_welcome
   :members:
   :no-index:
