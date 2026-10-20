Onboarding Hints React Component
================================

``@smarter/onboarding`` holds the web console's onboarding hints, which point a
new user to where to go next. Smarter's users are often students who have never
programmed and know little about generative AI yet, so the hints lead them, one
step at a time, from the welcome tour to their first conversation with an
LLMClient, and explain what they see along the way:

1. **The sidebar's LLM Clients link.** Once the :doc:`welcome dialog <welcome>`
   is closed, a sparkling ring circles the link, with the note "Start building
   your AI masterpiece here." and a **Got it** button. A user who is already
   among their LLMClients, on the list or in the workbench, has got there, and
   the hint is recorded without showing.
2. **The Get Weather LLMClient.** On the list of LLMClients, the same spotlight
   circles the name of the Get Weather example, whose link opens its chat in
   the Prompt Engineer's Workbench. It waits for the list to load, in either
   the list or the thumbnail view.
3. **The workbench's guided tour.** Once the chat is ready, and the welcome
   dialog closed, the workbench opens its Console and starts a tour, step by
   step, in plain words: the chat, the message box, sandbox and production
   modes, the Console and each of its tabs (the manifest, the architecture,
   the server logs, the tool calls, the configuration and the deployment), and
   the **Help** menu, which has the docs and takes the tour again at any time. A step
   about a part that the page doesn't have, e.g. the Server Logs tab when the
   server logs are off, is left out.

Each hint shows by itself until the user has done something with it: clicked
what it points to, clicked **Got it**, finished or skipped the tour, or was
already where it points. The first outcome is recorded once per user, in the
dashboard app's ``OnboardingHint`` model, so that a hint never shows again by
itself, on any device. The ``enable_web_console_onboarding_hints`` waffle
switch, active by default, turns the hints off.

The package is a library, built into its ``dist`` folder like ``@smarter/common``:

- ``Spotlight``: a sparkling ring around one element, which stays clickable,
  and a short note beside it. A click on the element, **Got it** or Escape
  ends it.
- ``Tour``: a guided tour, a modal dialog that dims the page around the part
  that each step is about. Next, Back and the arrow keys move between its steps,
  and Skip tour or Escape ends it. A step can have an icon, and can activate
  its element when it shows, e.g. select a Console tab, so that the page shows
  what the step is about.
- ``useOnboarding()``: which hints show by themselves, and ``record()``, which
  tells the onboarding seen api what the user did with one.
- ``waitForTarget()`` and ``waitUntil()``: wait for an element to come on
  screen, e.g. a row of a list that is still loading, or for the welcome dialog
  to close.

A hint finds what it points to by a ``data-smarter-onboarding`` attribute, e.g.
``data-smarter-onboarding="sidebar-llmclients"`` on the sidebar's link in
``templates/dashboard/sidebar.html``, or by a css selector. Each console page
holds the hints' state as JSON, which ``templates/dashboard/base.html`` writes
with ``templates/react/onboarding.html`` for signed-in users, so that a hint
needs no request before it shows. The rings and notes use the welcome dialog's
orange accent and its warm gradient, with a Keen icon badge, an arrow that
points at the element, and, in a tour, a progress bar. They follow the light
and dark themes, and keep still for users who prefer reduced motion.

To add a hint, add its id to ``OnboardingHints`` in the dashboard app's
``models.py`` and in the package's ``src/lib/const.ts`` (a test checks that the
two match), mark what it points to, and show a ``Spotlight`` or a ``Tour`` in
the page's React app while ``shouldShow()`` is true.

API
---

.. automodule:: smarter.apps.dashboard.views.views.api.onboarding
   :members:
   :show-inheritance:
   :no-index:

Model
-----

.. autoclass:: smarter.apps.dashboard.models.OnboardingHint
   :members:
   :no-index:

Template Tags
-------------

.. automodule:: smarter.apps.dashboard.templatetags.react_onboarding
   :members:
   :no-index:
