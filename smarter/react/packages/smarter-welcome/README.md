# Smarter Welcome React App

The welcome dialog, and short tour, that the Smarter web console shows to a new
user. It opens by itself on the first console page that the user visits, until
they close it once, and again whenever they choose **Welcome Tour** in the user
menu. Its text follows the welcome email that the new user received,
[templates/account/email/welcome.html](../../../smarter/templates/account/email/welcome.html).

In the web console, `@smarter/console` imports this package (`src/index.ts`) and renders `Welcome` in
its frame, with a context built from the console's session (`src/lib/welcome.ts` there), including the
session's onboarding state for the sidebar hint, which points at the console sidebar's LLM Clients link.
The package has no build of its own: its `index.html` and `src/main.tsx` are a development page only
(`npm run dev`), which renders the example context of `src/mocks/fixtures.ts`. See also:

- [smarter.apps.dashboard.views.views.api.welcome](../../../smarter/apps/dashboard/views/views/api/welcome.py),
  the api that returns the dialog's links and records that the user has been welcomed, in
  `UserProfile.welcomed_at`

The illustrations are the Keen theme's `dozzy-1` set, in
`smarter/static/assets/media/illustrations/dozzy-1/`, each with a version for the dark theme.

## Setup

### Storybook

```console
make react-storybook APP=smarter-welcome
```

### Running Locally

The development page calls the Django dev server's api, through `vite.config.ts`'s proxy, so Django
should be running at http://localhost:9357.

```console
npm run dev
```

### Running Locally From Django

```console
cd to/the/root/of/this/repo/

# builds ALL React apps, including the console that imports this one, collects the static files,
# and builds the Django Docker container.
make react-build

# Starts the Django app container
make run
```

To see the dialog again with an account that has closed it, choose **Welcome
Tour** in the user menu, or clear the user's `welcomed_at` in the Django admin.
