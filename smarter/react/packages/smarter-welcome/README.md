# Smarter Welcome React App

The welcome dialog, and short tour, that the Smarter web console shows to a new
user. It opens by itself on the first console page that the user visits, until
they close it once, and again whenever they choose **Welcome Tour** in the user
menu. Its text follows the welcome email that the new user received,
[templates/account/email/welcome.html](../../../smarter/templates/account/email/welcome.html).

This component is served by Django, on every console page. See also:

- [templates/react/welcome.html](../../../smarter/templates/react/welcome.html), which
  [templates/dashboard/base.html](../../../smarter/templates/dashboard/base.html) includes
- [smarter.apps.dashboard.templatetags.react_welcome](../../../smarter/apps/dashboard/templatetags/react_welcome.py)
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

### Running Locally From Django

```console
cd to/the/root/of/this/repo/

# builds ALL React apps, collects the static files, and builds the Django Docker container.
make react-build

# Starts the Django app container
make run
```

To see the dialog again with an account that has closed it, choose **Welcome
Tour** in the user menu, or clear the user's `welcomed_at` in the Django admin.
