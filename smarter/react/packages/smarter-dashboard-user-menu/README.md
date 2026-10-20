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
- **Sign Out**, or **Sign In** for an anonymous request

This component is served by Django, on every console page. See also:

- [templates/react/dashboard-user-menu.html](../../../smarter/templates/react/dashboard-user-menu.html), which
  [templates/dashboard/navbar.html](../../../smarter/templates/dashboard/navbar.html) includes
- [smarter.apps.dashboard.templatetags.react_dashboard_user_menu](../../../smarter/apps/dashboard/templatetags/react_dashboard_user_menu.py)
- [smarter.apps.account.views.dashboard.profile_image](../../../smarter/apps/account/views/dashboard/profile_image.py)
- [smarter.apps.account.views.dashboard.user_profiles](../../../smarter/apps/account/views/dashboard/user_profiles.py)
  and [smarter.apps.account.profile_selection](../../../smarter/apps/account/profile_selection.py), which
  explains how the chosen profile applies to each request

## Setup

### Storybook

```console
make react-storybook APP=smarter-dashboard-user-menu
```

### Running Locally From Django

```console
cd to/the/root/of/this/repo/

# builds ALL React apps, collects the static files, and builds the Django Docker container.
make react-build

# Starts the Django app container
make run
```
