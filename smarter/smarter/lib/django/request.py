"""Django request helper class."""

import logging

from smarter.apps.account.mixins import AccountMixin


logger = logging.getLogger(__name__)


class SmarterRequestHelper(AccountMixin):
    """
    Helper class for the Django request object that enforces authentication and
    provides lazy loading of the user, account, and user profile.
    """

    _request = None
    _url: str = None

    def __init__(self, request):
        self._request = request
        super().__init__(user=request.user)

    @property
    def request(self):
        return self._request

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
    def url(self):
        if self.request:
            self._url = self.request.build_absolute_uri()
        return self._url
