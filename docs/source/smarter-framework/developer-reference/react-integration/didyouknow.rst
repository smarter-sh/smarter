Did You Know? React Component
=============================

``@smarter/didyouknow`` holds the **Did you know?** trivia about The Smarter
Project: a couple of dozen facts, such as how the project is coded in part with
agentic AI, its Architecture Decision Records, its SDKs, its MCP server and its
Free Course Catalog. A fact that mentions a resource, such as a documentation
page, a repository or a blog post, links to it, and the link opens in a new tab.
Each fact is something that the project's repositories show, so that it stays
true. The facts are translated, like the rest of the web console.

The package is a library, built into its ``dist`` folder like ``@smarter/common``.
Its ``main.tsx`` and ``index.html`` are a development page only (``npm run dev``).

It exports the facts, ``didYouKnowFacts()``, and two ways to pick one:
``randomFact()``, and ``factOfTheDay()``, the same fact for everyone from
midnight to midnight UTC, and the next one the next day. It also exports ``DidYouKnow``, the note itself:
its title, the fact and its link. The note has no styles of its own. Each
consumer gives it class names, and may give it an icon before its title and
after its link, so that it looks the part where it is shown:

- The :doc:`Welcome dialog <welcome>` shows a random fact on one of its steps,
  picked at random, as a card below the step's illustration.
- The web console's header, ``src/components/Header.tsx`` in ``@smarter/console``,
  shows the fact of the day, as one line of small text, because the header has
  a fixed height. A fact that is still too long is cut short with an ellipsis.
  The header shows it while the console's session, ``GET /api/web/session/``,
  has ``flags.didYouKnow`` on, which follows the
  ``enable_web_console_did_you_know`` waffle switch. The switch is active by
  default. The note shows from the lg breakpoint up, and is hidden on a phone,
  styled with the theme's utility classes.

To add a fact, add it to ``didYouKnowFacts()`` in
``smarter-didyouknow/src/lib/facts.ts``, with its link if it mentions a
resource, then regenerate and translate the message catalogs.
