---
name: smarter-translations
description: Use when adding or changing any text that the Smarter web console shows (Django templates, Python view messages, React apps, smarter/static/js), when a test says smarter/react/i18n/messages.js is out of date, when regenerating the .po message catalogs (make i18n-messages), or when adding a language such as Spanish. Covers the gettext pipeline (django and djangojs domains), gettext/interpolate/interpolateNodes in @smarter/common, the TypeScript extractor, the update_console_messages command, the rules that keep messages translatable, and the steps to add a language.
---

# Smarter Translations (i18n)

The web console is translated with gettext. English is the source language and the default.
The Sphinx docs and the api's responses are not translated. The user-facing explanation is
`docs/source/smarter-framework/developer-reference/translations.rst`: read it first.

## Where things are

| What                                    | Where                                                                           |
| --------------------------------------- | ------------------------------------------------------------------------------- |
| Languages, LocaleMiddleware, catalogs   | `LANGUAGES`, `LOCALE_PATHS`, `MIDDLEWARE` in `smarter/smarter/settings/base.py` |
| Catalogs (`.po` committed, `.mo` not)   | `smarter/smarter/locale/<lang>/LC_MESSAGES/django.po`, `djangojs.po`            |
| `/i18n/setlang/`, `/jsi18n/`            | `smarter/smarter/urls/console.py`                                               |
| JS catalog `<script>`, `<html lang>`    | `smarter/smarter/templates/base.html`                                           |
| Language menu (shown with 2+ languages) | `smarter/react/packages/smarter-dashboard-user-menu` (the user menu)            |
| React runtime                           | `smarter/react/packages/smarter-common/src/lib/i18n.tsx`                        |
| React/static-js extractor               | `smarter/react/i18n/extract.ts` → `smarter/react/i18n/messages.js`              |
| makemessages + compilemessages          | `apps/dashboard/management/commands/update_console_messages.py`                 |
| Tests                                   | `apps/dashboard/tests/test_i18n.py`, `smarter/react/i18n/extract.test.ts`       |

## Marking text

- Templates: `{% load i18n %}` in **every** template that uses the tags (load isn't inherited),
  then `{% translate "Text" %}`, or `{% blocktranslate with name=obj.name trimmed %}...{{ name }}...{% endblocktranslate %}`
  for values and inline HTML. `blocktranslate` takes plain variables only: alias dotted ones with `with`.
  `test_every_template_compiles` catches a missing `{% load i18n %}`.
- Python: `from django.utils.translation import gettext as _`, and `_("... %(name)s") % {...}`,
  only for messages the console shows (auth views, Django messages). Never api payloads or logs.
- React: `gettext`, `ngettext`, `pgettext`, `interpolate`, `interpolateNodes` from `@smarter/common`
  (relative `./i18n` inside smarter-common). A React element inside a sentence goes through
  `interpolateNodes(gettext("Delete %(name)s?"), { name: <strong>{x.name}</strong> })`.
- `smarter/static/js`: the global `gettext()` and `interpolate(fmt, obj, true)`.

## Rules (the extractor enforces the first two)

- The message argument must be a **string literal** (or a concatenation of literals).
  `extract.ts` throws on `gettext(variable)` or a template literal with `${}`, with file:line.
- No HTML entities in a React message: `gettext()` returns a string, and React shows its `&rarr;` literally.
  Write the character itself (`"Build one →"`). `extract.ts` throws on `&name;`, `&#n;` and `&#xn;` in
  `.tsx`/`.ts` files; `smarter/static/js` is exempt, since it may insert messages as HTML.
- Whole sentences, never assembled from pieces (`` `${verb}d` ``, `"Search " + kind + "s"`).
  See `actionMessages()` in every list package's `Toolbar/Component.tsx`.
- Counts use `ngettext`, never `x === 1 ? "" : "s"`.
- Placeholders are named, `%(name)s`, with a meaningful name. Don't put a bare `%` in a message:
  pass `"80%"` as the value.
- A `Translators:` comment on the line before the call (`{/* Translators: ... */}` in JSX) is
  copied into the `.po` file. Add one when a message is ambiguous or a placeholder isn't obvious.
- Don't translate: code samples, manifest keys, CLI commands, product names (Docker, Kubernetes,
  OpenAI), developer-only errors (`main.tsx` attribute checks), console logs.
- Module-level constants may call `gettext()`: the catalog `<script>` runs before the apps' module
  scripts. Tests and Storybook have no catalog and get the English text, so tests keep asserting English.

## Regenerating the catalogs

After changing marked text (otherwise `extract.test.ts` fails in `make react-test`):

```console
make build && make run      # run_in_background: true, then wait for the 302
make i18n-messages          # or LANGUAGE=es for one language
```

It runs `npm run i18n:extract`, copies `messages.js` into smarter-app, runs
`manage.py update_console_messages` there (makemessages for `django` from the project root, and for
`djangojs` from `react/i18n` only, then compilemessages), and copies `smarter/smarter/locale` back.
A second run changes only `POT-Creation-Date`. Commit the `.po` files and `messages.js`; `*.mo` is
gitignored and the Dockerfile compiles it.

## Adding a language

1. `LANGUAGES` in `settings/base.py`: add e.g. `("fr", "French")`. Use a code that Django's
   `django.conf.locale.LANG_INFO` knows. The language menu calls `get_language_info_list`, which describes
   an unknown regional code such as `es-419` as its generic language (`code: "es"`), so the menu would
   post `es` back. That's why Latin American Spanish is the generic `es`.
   A regional code (`es-MX`) is only needed alongside a second variant of the same language, or when
   LANG_INFO only knows the regional one: Brazilian Portuguese is `pt-br`. Its catalogs live in
   `locale/pt_BR` (the locale name, `to_locale("pt-br")`); `update_console_messages` converts the codes,
   and `make i18n-messages LANGUAGE=pt-br` works. LocaleMiddleware gives `pt-br` to `pt` and `pt-PT` too.
2. `DATE_FNS_LOCALES` in `smarter-common/src/lib/formatDateTime.tsx`: add e.g. `es` from `date-fns/locale`,
   or `"pt-br": ptBR` for a regional code (the key is the lowercase `<html lang>`).
3. Rebuild the containers, `make i18n-messages`.
4. Fill in every `msgstr` of the new `django.po` and `djangojs.po`. Keep `%(name)s` placeholders and
   the HTML inside `blocktranslate` messages exactly; plural entries need every `msgstr[n]`.
   Check with `msgfmt --check -o /dev/null <file>.po` on the host. `test_message_catalogs_are_translated`
   fails on an empty `msgstr` or a `#, fuzzy` flag (makemessages marks a new catalog's header fuzzy).
   The two domains share many msgids: translate the distinct set once (polib in a scratch script works
   well) and write it into both files, so the same text reads the same everywhere. About 360 msgids
   differ only by resource kind (`Clone %(kind)s`'s per-kind variants: clone, delete, rename, ready,
   failed to ...): generate those from one rule per pattern and a kind → (noun, gender) table, rather
   than by hand. Follow the existing catalogs: CamelCase kinds stay English (LLMClient, AuthToken), common
   nouns are translated (secret, connection, orchestrator, provider, budget, vectorstore).
5. Rebuild, then check a page with `curl -H "Accept-Language: es" localhost:9357/login/`, and the
   catalog with `curl -b django_language=es localhost:9357/jsi18n/`.
6. `test_lists_every_language_in_its_own_name` already covers a second language in the menu.

## Known gaps

- `templates/account/email/welcome.html` (sent outside a request), the Keen demo bodies of
  `account/dashboard/activity.html`, `statements.html` and `logs.html`, unused templates, and the
  Django admin (which Django translates) are not marked.
- Smarter Chat (`packages/smarter-chat`) is its own repository, with its own gettext catalogs in the same
  languages (`locale/`, `npm run i18n`, its `doc/adr/018-translations.md`). Its messages aren't extracted here.
  A language added here must be added there too (`LANGUAGES` in its `scripts/i18n.mjs`).

- Resource kind names inside sentences (`"Search %(objects)s"`, `"Clone %(kind)s"`) stay English.
