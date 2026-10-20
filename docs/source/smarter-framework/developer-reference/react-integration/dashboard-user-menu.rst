User Menu React Component
=========================

The user menu sits at the top right of every web console page. The signed-in
user's profile image opens it, and their email shows when the pointer rests on
it. The menu shows the user's name, email and role (a **Superuser** or **Staff**
badge), and these items:

- **Language**, which lists the console's languages, each in its own name, and
  posts the choice to Django's ``set_language`` view. It is shown when the
  platform's ``LANGUAGES`` setting has more than one. See
  :doc:`../translations`.
- **Change Profile Image** and **Remove Profile Image**, which upload and remove
  the user's own image. See
  :doc:`../smarter-dashboard/views/authentication/profile_image`.
- **Change Profile**, for a user with more than one UserProfile, below.
- **Welcome Tour**, which opens the :doc:`welcome dialog <welcome>`.
- **Sign Out**. An anonymous request gets **Sign In**, and the Language item.

The menu is the ``@smarter/dashboard-user-menu`` React app, which
``templates/dashboard/navbar.html`` includes on every page, through
``templates/react/dashboard-user-menu.html``. It renders the Keen theme's menu
classes itself, rather than through the theme's JavaScript: the profile image is
a button that opens and closes it, and Escape or a click outside it closes it.

Change Profile
--------------

A user can have more than one UserProfile, one per account, e.g. a student who
is enrolled in two courses at once. The web console acts as one of them at a
time: by default, the newest. For such a user, the menu shows the current
profile's account name below their email, and a **Change Profile** item, which
opens a dialog that lists their profiles, newest first, with each one's account
number, account name and creation date. The current one is marked **Current**.
**Switch**, on another one, makes the console act as it for the rest of the
session, and reloads the page, so that everything on it belongs to the chosen
account.

The choice is stored in the Django session, under
:data:`~smarter.apps.account.profile_selection.SELECTED_USER_PROFILE_SESSION_KEY`.
For each request,
:class:`~smarter.apps.account.middleware.SmarterUserProfileSelectionMiddleware`
copies it into the context variable
:data:`~smarter.apps.account.profile_selection.selected_user_profile_id`, and the
functions that resolve a profile or an account from the user alone,
``UserProfile.get_cached_object(user=...)``,
:func:`~smarter.apps.account.utils.get_cached_account_for_user` and
:func:`~smarter.apps.account.utils.get_cached_avatar_url`, return the chosen one,
through :meth:`UserProfile.get_selected_object()
<smarter.apps.account.models.UserProfile.get_selected_object>`. A choice applies
only to the user who made it, and a request that authenticates with an API key
ignores it: the key acts as its own user.

API
---

.. automodule:: smarter.apps.account.views.dashboard.user_profiles
   :members:
   :show-inheritance:
   :no-index:

.. automodule:: smarter.apps.account.profile_selection
   :members:
   :no-index:

.. automodule:: smarter.apps.account.middleware
   :members:
   :show-inheritance:
   :no-index:

Template Tags
-------------

.. automodule:: smarter.apps.dashboard.templatetags.react_dashboard_user_menu
   :members:
   :no-index:
