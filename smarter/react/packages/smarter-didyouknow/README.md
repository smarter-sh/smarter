# Smarter Did You Know?

Did you know? trivia about The Smarter Project. The package is both:

- a library, built into `dist/` like `@smarter/common`: the facts (`didYouKnowFacts()`), a random fact
  (`randomFact()`), the fact of the day (`factOfTheDay()`, the same from midnight to midnight UTC), and
  `DidYouKnow`, an unstyled note whose consumers style it with class names. The
  [welcome dialog](../smarter-welcome) uses it.
- the tip in the web console's header: `@smarter/console` renders `DidYouKnow` there, with the fact of
  the day and its own class names, while its session's `flags.didYouKnow` is on, i.e. while the
  `enable_web_console_did_you_know` waffle switch is active. `src/App.tsx` and `src/main.tsx` are a
  development page only (`npm run dev`), which shows the same note below a title.

Each fact is something that the project's repositories show, so that it stays true. A fact that
mentions a resource links to it.

## Setup

```console
npm run build:lib                                   # the library, for @smarter/welcome and @smarter/console
npm run dev                                         # the development page
make react-storybook APP=smarter-didyouknow         # Storybook
make react-build                                    # everything, for Django
```
