Translations
============

The Smarter web console is translated with `gettext <https://www.gnu.org/software/gettext/>`__, the
same way as Django itself. English is the source language of every message and the default. Each
other language is a pair of ``.po`` message catalogs, which a translator fills in. The console is
translated into Spanish and French. The Spanish catalogs are written in Latin American Spanish, under
the generic ``es`` code, so that a browser that asks for any variant of Spanish (``es-MX``,
``es-419``, ``es-ES``) gets them. Django's ``LANG_INFO`` has no ``es-419``, so the language menu
would describe an ``es-419`` language as ``es``, and post ``es`` back. The console's
Django templates, its Python views, its React apps and its plain JavaScript all share this one
pipeline, so a translator works with one set of files, in one format. The documentation at
docs.smarter.sh, and the Smarter api's responses, are not translated.

How a Page Chooses Its Language
-------------------------------

Django's ``LocaleMiddleware`` activates a language for each request: the one in the language cookie,
which the language menu sets, or else the best match for the browser's ``Accept-Language`` header,
or else ``settings.LANGUAGE_CODE``, English. Only the languages in ``settings.LANGUAGES`` can be
chosen. The page then renders in that language:

- **Django templates** mark their text with ``{% translate %}`` and ``{% blocktranslate %}``, after
  ``{% load i18n %}``. ``base.html`` sets ``<html lang="...">`` to the active language.
- **Python code** marks messages that it shows in the console, such as sign-in errors, with
  ``gettext()``, imported as ``_``. Api responses are not marked: their consumers are programs.
- **The React apps** call ``gettext()`` and friends from ``@smarter/common``.
- **Plain JavaScript** in ``smarter/static/js`` calls the global ``gettext()``.

The last two get their messages from Django's
`JavaScriptCatalog <https://docs.djangoproject.com/en/stable/topics/i18n/translation/#module-django.views.i18n>`__
view, at ``/jsi18n/``, which ``base.html`` loads before any other script. It serves the active
language's ``djangojs`` messages, and defines ``window.django.gettext()``, ``ngettext()``,
``pgettext()``, ``interpolate()`` and the global functions of the same names. In tests and in
Storybook there is no catalog, and ``@smarter/common`` falls back to the English source text.

The language menu, in the user menu of the console's navbar, lists each language in its own name,
and posts the choice to Django's ``set_language`` view at ``/i18n/setlang/``. It is shown only when
``settings.LANGUAGES`` has more than one language.

The Message Catalogs
--------------------

The catalogs are in ``smarter/smarter/locale/<language>/LC_MESSAGES/``:

.. list-table::
   :header-rows: 1

   * - File
     - Messages
   * - ``django.po``
     - The Django templates, and the Python code.
   * - ``djangojs.po``
     - The React apps in ``smarter/react/packages``, and ``smarter/static/js``.

Only the ``.po`` files are committed. The Docker image compiles them to the ``.mo`` files that Django
reads, with ``manage.py compilemessages``. The English catalogs have empty translations, because
gettext shows the source text of an untranslated message.

Django's ``makemessages`` finds the messages in templates and Python code. The ``xgettext`` that it
runs can't parse TypeScript and JSX, so ``smarter/react/i18n/extract.ts`` finds the React apps' and
the static scripts' calls with the TypeScript compiler instead, and writes each distinct message as
one plain JavaScript call to ``smarter/react/i18n/messages.js``. ``makemessages`` reads that file for
the ``djangojs`` domain. Each message is preceded by a ``Translators:`` comment that lists the files
that use it, which appears in ``djangojs.po``. A test, ``smarter/react/i18n/extract.test.ts``, fails
when ``messages.js`` is out of date.

Marking Text for Translation
----------------------------

Every message is a complete English sentence or label, written as a string literal, so that it can
be extracted. Put values into it with named placeholders, after translating it, so that a translator
can move them:

.. code-block:: html+django

   {% load i18n %}
   <h1>{% translate "API Keys" %}</h1>
   <p>{% blocktranslate with email=branding.support_email %}Email: {{ email }}{% endblocktranslate %}</p>
   <input placeholder="{% translate "Email address" %}" />

.. code-block:: python

   from django.utils.translation import gettext as _

   error_message = _("Invalid login attempt. Unknown user %(email)s") % {"email": email}

.. code-block:: tsx

   import { gettext, interpolate, interpolateNodes, ngettext } from "@smarter/common";

   <button title={gettext("Rename: Rename this secret resource")} />
   interpolate(gettext("Failed to load budgets (%(status)s)."), { status: response.status });
   interpolate(ngettext("%(count)s path", "%(count)s paths", count), { count });
   // a React element inside a sentence
   interpolateNodes(gettext("Rename secret %(name)s."), { name: <strong>{secret.name}</strong> });

.. code-block:: javascript

   // smarter/static/js
   Swal.fire({ text: gettext("Copied API key to the clipboard."), confirmButtonText: gettext("Ok, got it!") });

Some rules keep the catalogs translatable:

- **Don't build sentences from pieces.** ``"Successfully " + verb + "d"`` can't be translated. Write
  one message for each case, as the list pages' ``actionMessages()`` does for clone, rename and
  delete.
- **Use ngettext() for counts**, never a conditional ``"s"``. Languages have different plural rules.
- **Use pgettext() when one English word has two meanings**, e.g. a verb and a noun.
- **Explain anything ambiguous** with a comment that begins with ``Translators:``, on the line before
  the call, or before the ``{% translate %}`` tag. It is copied into the ``.po`` file.
- **Don't translate** resource kinds in code, manifest field names, commands, product names, log
  messages, or errors that only developers see, such as a missing attribute in ``main.tsx``.

Updating the Catalogs
---------------------

After changing marked text, regenerate the catalogs, with the containers running the current code:

.. code-block:: console

   make build && make run      # in another terminal, or in the background
   make i18n-messages

``make i18n-messages`` runs ``npm run i18n:extract``, then the ``update_console_messages`` management
command in the ``smarter-app`` container, which runs ``makemessages`` for both domains and every
language in ``settings.LANGUAGES``, keeping the translations already in the ``.po`` files, then
``compilemessages``. It copies the catalogs back to the host. Commit the changed ``.po`` files and
``messages.js``. ``make i18n-messages LANGUAGE=es`` updates one language.

Adding a Language
-----------------

1. Add the language to ``LANGUAGES`` in ``smarter/smarter/settings/base.py``, e.g.
   ``("es", "Spanish")``.
2. Add its `date-fns <https://date-fns.org/>`__ locale to ``DATE_FNS_LOCALES`` in
   ``smarter-common/src/lib/formatDateTime.tsx``, for relative times such as "3 minutes ago".
3. Rebuild the containers, then run ``make i18n-messages``. It creates
   ``smarter/smarter/locale/es/LC_MESSAGES/django.po`` and ``djangojs.po``.
4. Translate every ``msgstr``, with a ``.po`` editor such as `Poedit <https://poedit.net/>`__, or by
   hand. Keep each ``%(name)s`` placeholder, and the HTML in ``blocktranslate`` messages.
5. Rebuild the containers, which compile the catalogs. The language menu appears in the console's
   navbar.

Technical Reference
-------------------

- :doc:`smarter-dashboard/management`: the ``update_console_messages`` management command.
- :doc:`smarter-dashboard/templatetags/smarter_i18n`: the ``to_locale`` filter that ``base.html``
  uses for its ``og:locale`` meta tag.
- :doc:`react-integration`: how Django hosts the React apps.
