Doodle React Component
======================

``@smarter/doodle`` is the left panel of the web console's sign-in pages: the logo, the
**doodle of the day**, and the project's name and description. The doodle is a small, flat
illustration of a Smarter LLMClient's chat window, with the plugin, guardrail, vectorstore and
secret that it uses, and its manifest. On days worth celebrating, the illustration is decorated
for the day: lanterns for the Lunar New Year, diyas for Diwali, a menorah for Hanukkah, gears for
Ada Lovelace Day, fireworks for Canada Day. On other days it is the plain scene.

Visitors in different regions can see different doodles on the same day. The browser sends its
time zone, e.g. ``Asia/Kolkata``, which gives the visitor's local date, so a holiday starts at local
midnight, and, through the time zone database, the country and the region. No IP address is
looked up, and nothing about the visitor is stored. The regions are ``global``, ``us``, ``ca``,
``mx``, ``latam``, ``europe``, ``africa``, ``middle-east``, ``south-asia``, ``east-asia``,
``southeast-asia`` and ``oceania``.

How it works
------------

The Django app ``smarter.apps.doodle`` does the work, and the React app only shows the result.

1. **The theme catalog.** Each theme is a YAML file in ``smarter/apps/doodle/data/themes/``: what
   it celebrates, its caption and link, the regions that see it, its priority, its schedule, and an
   SVG of its *props*, the decorations that are drawn on the base scene. A schedule is a fixed date
   (Pi Day, March 14), the nth weekday of a month (Ada Lovelace Day, the second Tuesday of
   October), or a country's holiday by name, which the
   `holidays <https://pypi.org/project/holidays/>`__ package dates, including the moving ones such
   as Diwali, Eid al-Fitr and Thanksgiving. The catalog's ``README.md`` explains how to add a theme
   and draw its props. ``manage.py load_doodle_themes``, which ``initialize_platform`` runs, loads
   the catalog and draws each theme's artwork.
2. **The planner.** A Celery Beat task, ``plan_doodles``, chooses the doodle of every region for
   the next seven days, so that a week of content is always ready, then asks the Smarter Doodle
   Editor about each new day (below). For each day and region, the due theme of the highest
   priority wins, and a region's own theme wins over one of every region. When nothing is due, the
   plain default wins. ``manage.py plan_doodles`` does the same by hand, and asks the editor too
   with ``--editor``.
3. **The api.** ``GET /api/v1/doodles/today/?tz=<time zone>`` returns the doodle of the day as
   JSON, and ``GET /api/v1/doodles/artwork/<sha256>.svg`` its artwork. Both are public, because
   the page shows the doodle before anyone signs in. An artwork's url is its content's hash, so a
   browser caches it for a year. Both are internal to the sign-in page, and not part of the
   :doc:`api contract <../../smarter-api/api-contract>`.
4. **The app.** The page shows the plain scene at once, from the static files, and the app replaces
   it with the doodle of the day when it arrives. It shows the artwork with ``<img>``, in which an
   SVG can run no scripts and load nothing, and the caption, e.g. *Happy Diwali!*, below it, linked
   to a page about the day. Without JavaScript, or if the api fails, the page keeps the plain scene.

A superuser can override a day's doodle in the :doc:`Django admin <../../../smarter-platform/django-admin>`,
under Doodles: choose another theme, and neither the planner nor the editor changes that day again.
The list's actions approve or reject doodles, and its **Preview the week** button shows every
region's doodle of every planned day as a grid, with its caption, whether a Smarter AI application
chose or drew it, and why, and an Approve and a Reject button on each. A change shows within ten minutes, the time that a
day's doodle is cached.

The Smarter Doodle Editor and Artist
------------------------------------

The doodle is itself a Smarter AI application. Two staff-only LLMClients of the Smarter account,
from the `example manifests <https://github.com/smarter-sh/example-manifests>`__, choose and draw
it, and the platform's own code prompts them through the chat api, with
:mod:`smarter.apps.llmclient.prompting`, so their system prompts, guardrails, journal and cost
accounting apply as they would to anyone's prompt.

- **smarter_doodle_editor** chooses each region's doodle of each new day. The planner prompts it
  once a day, with JSON: for each region, the catalog themes that are due, and the region's other
  holidays that day, from the ``holidays`` package. It answers with JSON: for each region, a catalog
  theme, one of the holidays, or the plain scene. The day before, it looks at the day once more,
  with what each region is reading about too (Trends, below), and may choose a trend. Its guardrails strip a code fence from its answer,
  and check it with OpenAI's moderation model.
- **smarter_doodle_artist** draws a holiday that the editor chose and the catalog has no theme for.
  It answers with the SVG of the decorations, and its guardrail removes scripts.

The editor can't invent a topic, and nothing it says is trusted. The platform
(:mod:`smarter.apps.doodle.editor`) checks every choice again:

- A choice must be one of the region's candidates, and a holiday only when the region has no
  catalog theme that day.
- A holiday about mourning, war, politics, a monarchy or a single religion's holy day is never a
  candidate, and the editor's caption and subject for the artist may not be about one either. The
  match uses the plugin selectors' language matching: plurals, typos and WordNet synonyms, e.g.
  *bereavement* for *mourning*.
- The category, the caption's length and the alt text are checked, and the caption's link must be
  a Wikipedia article. A trend's link is always its own article's.
- Last, the ``upbeat_occasion_input`` Guardrail, a small LLM judge from the example manifests, must
  find the occasion plainly fun and upbeat. Word lists can't tell a solemn anniversary or sad news
  from a festival; a judge of tone can, and moderation models, which look for harm, don't. Without
  the Guardrail, or when it fails, nothing is drawn.

The artist's SVG goes through an allowlist sanitizer (:mod:`smarter.apps.doodle.sanitize`): only
the shapes of a flat drawing, no text, images, links, scripts, ids or ``url()``, and css that only
animates its own classes. A drawn doodle is *proposed*: visitors see the calendar's choice until a
superuser approves it, unless ``enable_doodle_auto_approve`` is on.

Each prompt of the editor is recorded, under Doodle Editor Runs in the admin: what it was asked,
what it answered, and which of its choices were refused. A day is asked once, or until it has
failed three times, after which the calendar's choice stays. On a platform without the
example manifests, the calendar alone chooses.

Trends
~~~~~~

Holidays are planned a week ahead; what people care about, e.g. a World Cup, isn't. So the editor
looks at today and tomorrow once more, while the ``enable_doodle_trends`` switch is on, and is told
what each region is reading about, from Wikipedia (:mod:`smarter.apps.doodle.trends`):

- Wikimedia publishes the most viewed articles of each language edition every day, an official,
  free and anonymous signal. Each region stands for its languages' editions, e.g. Spanish and
  Portuguese for Latin America.
- Each article is judged by its Wikidata item's English label and description, whatever its
  edition's language, with one Wikidata request per edition. An article about a person (years of
  life, or an occupation in its description), a date, or with a blocked word is left out, and its
  description must name an occasion (a tournament, a festival, an eclipse, a launch...): an
  allowlist, since a blocklist can't keep up with the news.
- A trend is chosen only when the region has no catalog theme that day, and it is always drawn,
  so it waits for a superuser's approval, unless auto-approve is on. A doodle that the artist drew
  for a region is kept on the second look.

When a Smarter AI application chose or drew the day's doodle, the panel says so, in place of the
project's description: *Chosen by a Smarter AI application*, or *Drawn by a Smarter AI
application*, with a Learn how link to
`An LLM Editor and an SVG Artist <https://blog.smarter.sh/2026/11/04/smarter-doodle-llm-editor-artist/>`__,
the blog post that walks through how the doodle is chosen and drawn.

Waffle switches
---------------

- ``enable_doodle``: shows the doodle of the day. Inactive, the page shows the plain scene,
  without the React app.
- ``enable_doodle_regional``: chooses the doodle by the visitor's region. Inactive, everyone sees
  the global doodle.
- ``enable_doodle_animation``: animates the doodles, e.g. a flickering flame. Inactive, every
  doodle is a still image. Visitors who ask their system for reduced motion always get still images.
- ``enable_doodle_caption``: shows the caption below a themed doodle.
- ``enable_doodle_llm_editor``: lets the Smarter Doodle Editor choose the doodles of each new day.
  Inactive, the calendar alone chooses.
- ``enable_doodle_llm_artwork``: lets the editor choose a holiday that the catalog has no theme
  for, which the Smarter Doodle Artist draws.
- ``enable_doodle_trends``: tells the editor what each region is reading about, on its second look
  at today and tomorrow.
- ``enable_doodle_auto_approve``: shows a drawn doodle without a superuser's approval. It is the
  only one that is inactive by default.
- ``enable_doodle_ai_credit``: shows the credit of a Smarter AI application below its doodle.
- ``log_doodle``: logs the app's info and debug messages.

All but ``enable_doodle_auto_approve`` are active by default.

Technical Reference
-------------------

.. automodule:: smarter.apps.doodle
   :no-index:

.. automodule:: smarter.apps.doodle.regions
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.schedule
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.artwork
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.themes
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.planner
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.models
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.editor
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.trends
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.sanitize
   :members:
   :no-index:

.. automodule:: smarter.apps.llmclient.prompting
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.caching
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.api.v1.views
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.contract.models
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.tasks
   :members:
   :no-index:

.. automodule:: smarter.apps.doodle.templatetags.react_doodle
   :members:
   :no-index:
