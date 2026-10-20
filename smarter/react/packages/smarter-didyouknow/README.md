# Smarter Did You Know?

Did you know? trivia about The Smarter Project. The package is both:

- a library, built into `dist/` like `@smarter/common`: the facts (`didYouKnowFacts()`), a random fact
  (`randomFact()`), the fact of the day (`factOfTheDay()`, the same from midnight to midnight UTC), and
  `DidYouKnow`, an unstyled note whose consumers style it with class names. The
  [welcome dialog](../smarter-welcome) uses it.
- an app, `src/main.tsx`, that shows the fact of the day below the web console's title. See:
  - [templates/react/didyouknow.html](../../../smarter/templates/react/didyouknow.html), which
    [templates/dashboard/header.html](../../../smarter/templates/dashboard/header.html) includes
  - [smarter.apps.dashboard.templatetags.react_didyouknow](../../../smarter/apps/dashboard/templatetags/react_didyouknow.py)
  - the `enable_web_console_did_you_know` waffle switch, which turns the note on and off

Each fact is something that the project's repositories show, so that it stays true. A fact that
mentions a resource links to it.

## Setup

```console
npm run build:lib                                   # the library, for @smarter/welcome
make react-storybook APP=smarter-didyouknow         # Storybook
make react-build                                    # everything, for Django
```
