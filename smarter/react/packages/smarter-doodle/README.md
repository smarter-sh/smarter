# Smarter Doodle

The Doodle: the illustration of the day on the web console's sign-in pages. It shows a Smarter
LLMClient and the resources around it, decorated for holidays and days worth celebrating, e.g.
Diwali, Pi Day or Canada Day. Visitors in different regions can see different doodles on the same
day, by their browser's time zone.

The app fetches `GET /api/v1/doodles/today/?tz=<time zone>`, and shows the artwork with `<img>`.
Until it arrives, and if it fails, the page shows the plain base scene. The package is a library:
`src/index.ts` exports the component as `Doodle`, which `@smarter/console` imports and renders beside its
sign-in forms (`packages/smarter-console/src/components/AuthCard.tsx`). `npm run dev` shows it on its own.
See:

- [smarter.apps.doodle](../../../smarter/apps/doodle), the Django app that plans the doodles a week
  ahead and serves them, and its theme catalog, `data/themes/`
- the `enable_doodle` waffle switch, which turns the app on and off, and `enable_doodle_animation`,
  `enable_doodle_caption` and `enable_doodle_regional`

## Setup

```console
make react-storybook APP=smarter-doodle   # Storybook
npm run dev -w @smarter/doodle            # the Doodle on its own, at http://localhost:5173/
```
