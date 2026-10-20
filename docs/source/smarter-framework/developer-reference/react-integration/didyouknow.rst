Did You Know? React Component
=============================

``@smarter/didyouknow`` holds the **Did you know?** trivia about The Smarter
Project: a couple of dozen facts, such as how the project is coded in part with
agentic AI, its Architecture Decision Records, its SDKs, its MCP server and its
Free Course Catalog. A fact that mentions a resource, such as a documentation
page, a repository or a blog post, links to it, and the link opens in a new tab.
Each fact is something that the project's repositories show, so that it stays
true. The facts are translated, like the rest of the web console.

The package is both a library and a small React app.

As a library, built into its ``dist`` folder like ``@smarter/common``, it exports
the facts, ``didYouKnowFacts()``, and two ways to pick one: ``randomFact()``, and
``factOfTheDay()``, the same fact for everyone from midnight to midnight UTC,
and the next one the next day. It also exports ``DidYouKnow``, the note itself:
its title, the fact and its link. The note has no styles of its own. Each
consumer gives it class names, and may give it an icon before its title and
after its link, so that it looks the part where it is shown:

- The :doc:`Welcome dialog <welcome>` shows a random fact on one of its steps,
  picked at random, as a card below the step's illustration.
- The package's own app shows the fact of the day below the web console's title,
  The Smarter Project, as one line of small text as wide as the title bar,
  because the header has a fixed height. A fact that is still too long is cut
  short with an ellipsis, and shown in full on hover. The title bar,
  ``templates/dashboard/header.html``, includes ``templates/react/didyouknow.html``
  on every console page, which mounts the app only while the
  ``enable_web_console_did_you_know`` waffle switch is active. The switch is
  active by default. Like the title, the note is hidden on a phone.

To add a fact, add it to ``didYouKnowFacts()`` in
``smarter-didyouknow/src/lib/facts.ts``, with its link if it mentions a
resource, then regenerate and translate the message catalogs.

Template Tags
-------------

.. automodule:: smarter.apps.dashboard.templatetags.react_didyouknow
   :members:
   :no-index:
