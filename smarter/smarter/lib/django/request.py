"""Django request helper class."""

import logging

from smarter.apps.account.models import Account, UserProfile
from smarter.lib.django.validators import SmarterValidator


logger = logging.getLogger(__name__)


class SmarterRequestHelper:
    """
    Helper class for the Django request object that enforces authentication and
    provides lazy loading of the user, account, and user profile.
    """

    _request = None
    _user = None
    _user_profile: UserProfile = None
    _url: str = None

    def __init__(self, request):
        if request.user.is_authenticated:
            self._request = request
        else:
            logger.warning("request.user is not authenticated.")

    @property
    def request(self):
        return self._request

    @property
    def user(self):
        if self._user:
            return self._user
        if self.request:
            self._user = self.request.user if self.request else None
        return self._user

    @property
    def ip_address(self):
        if self.request:
            return self.request.META.get("REMOTE_ADDR", "")
        return None

    @property
    def user_agent(self):
        if self.request:
            return self.request.META.get("HTTP_USER_AGENT", "")
        return None

    @property
    def account(self) -> Account:
        return self.user_profile.account if self.user_profile else None

    @property
    def url(self):
        if self.request:
            self._url = self.request.build_absolute_uri()
            self._url = SmarterValidator.urlify(self._url)
        return self._url

    @property
    def user_profile(self) -> UserProfile:
        if self._user_profile:
            return self._user_profile

        if self.user:
            try:
                self._user_profile = UserProfile.objects.get(user=self.request.user)
            except UserProfile.DoesNotExist:
                self._user_profile = None
        return self._user_profile
