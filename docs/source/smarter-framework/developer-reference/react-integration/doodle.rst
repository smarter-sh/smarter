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
   the next seven days, so that a week of content is always ready. For each day and region, the
   due theme of the highest priority wins, and a region's own theme wins over one of every region.
   When nothing is due, the plain default wins. ``manage.py plan_doodles`` does the same by hand.
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
under Doodles: choose another theme, or reject the doodle, and the planner leaves that day alone.
A change shows within ten minutes, the time that a day's doodle is cached.

Waffle switches
---------------

- ``enable_doodle``: shows the doodle of the day. Inactive, the page shows the plain scene,
  without the React app.
- ``enable_doodle_regional``: chooses the doodle by the visitor's region. Inactive, everyone sees
  the global doodle.
- ``enable_doodle_animation``: animates the doodles, e.g. a flickering flame. Inactive, every
  doodle is a still image. Visitors who ask their system for reduced motion always get still images.
- ``enable_doodle_caption``: shows the caption below a themed doodle.
- ``log_doodle``: logs the app's info and debug messages.

All are active by default.

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
