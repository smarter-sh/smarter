"""
The UserProfile that a signed-in user has chosen for their web console session.

A user can have more than one :class:`~smarter.apps.account.models.UserProfile`, one per account, e.g.
a student who is enrolled in two courses at once. Unless they choose otherwise, the platform acts as
their newest one. The user menu's **Change Profile** item lists their profiles, and choosing one stores
its id in the Django session, under :data:`SELECTED_USER_PROFILE_SESSION_KEY`.

:class:`~smarter.apps.account.middleware.SmarterUserProfileSelectionMiddleware` copies that id into
:data:`selected_user_profile_id` for the length of each request, and the functions that resolve a
user's profile or account from the user alone, :meth:`UserProfile.get_cached_object(user=...)
<smarter.apps.account.models.UserProfile.get_cached_object>` and
:func:`~smarter.apps.account.utils.get_cached_account_for_user`, return the chosen profile, through
:meth:`UserProfile.get_selected_object() <smarter.apps.account.models.UserProfile.get_selected_object>`.

This module imports nothing from Django's models, so that the models and the middleware can both
import it.
"""

from contextvars import ContextVar
from typing import Optional

SELECTED_USER_PROFILE_SESSION_KEY = "smarter_user_profile_id"
"""The session key of the id of the UserProfile that the user chose in the user menu."""

selected_user_profile_id: ContextVar[Optional[int]] = ContextVar("smarter_selected_user_profile_id", default=None)
"""
The id of the UserProfile that the request's user chose, or ``None``.

:class:`~smarter.apps.account.middleware.SmarterUserProfileSelectionMiddleware` sets it for each request.

It is only a preference: :meth:`UserProfile.get_selected_object()
<smarter.apps.account.models.UserProfile.get_selected_object>` ignores an id whose profile doesn't
belong to the user that is being resolved.
"""
