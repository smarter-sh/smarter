"""knox TokenAuthentication subclass that checks if the token is active."""

import logging
import time

from knox.auth import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import SmarterAuthToken


logger = logging.getLogger(__name__)


class SmarterTokenAuthentication(TokenAuthentication):
    """
    Custom token authentication for smarter.
    This is used to authenticate API keys. It is a subclass of the default knox
    behavior, but it also checks that the API key is active.
    """

    model = SmarterAuthToken

    def authenticate_credentials(self, token):
        # authenticate the user using the normal token authentication
        # this will raise an AuthenticationFailed exception if the token is invalid
        user, auth_token = super().authenticate_credentials(token)

        # next, we need to ensure that the token is active, otherwise
        # we should raise an exception that exactly matches the one
        # raised by the default token authentication
        if not auth_token.is_active:
            raise AuthenticationFailed

        # update the last used time for the token
        auth_token.last_used_at = time.time()
        auth_token.save()

        # if the token is active, we can return the user and token as a tuple
        # exactly as the default token authentication does.
        return (user, auth_token)
