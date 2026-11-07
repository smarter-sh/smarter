# Smarter Dashboard User Menu React App

The user menu at the top right of every Smarter web console page. The user's
profile image opens it. It shows their name, email and role, and has these items:

- **Language**, with two or more languages in `settings.LANGUAGES`, which posts
  the choice to Django's `set_language` view
- **Change Profile Image** and **Remove Profile Image**
- **Change Profile**, for a user with more than one UserProfile, e.g. a student
  who is enrolled in two courses at once. It opens a dialog that lists their
  profiles, with each one's account number, account name and creation date, and
  makes the console act as the chosen one for the rest of the session.
- **Welcome Tour**, which opens the welcome dialog, `@smarter/welcome`
- **Sign Out** (a POST to `/api/web/account/logout/`), or **Sign In** for an anonymous request

In the web console, `@smarter/console` imports this package (`src/index.ts`) and renders `UserMenu` in
its header, with a context built from the console's session (`src/lib/userMenu.ts` there). The package has
no build of its own: its `index.html` and `src/main.tsx` are a development page only (`npm run dev`), which
renders the example context of `src/mocks/fixtures.ts`. See also:

- [smarter.apps.account.api.web.profile_image](../../../smarter/apps/account/api/web/profile_image.py)
- [smarter.apps.account.api.web.user_profiles](../../../smarter/apps/account/api/web/user_profiles.py)
  and [smarter.apps.account.profile_selection](../../../smarter/apps/account/profile_selection.py), which
  explains how the chosen profile applies to each request

## Setup

### Storybook

```console
make react-storybook APP=smarter-dashboard-user-menu
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
