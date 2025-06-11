"""knox TokenAuthentication subclass that checks if the token is active."""

import logging

from django.utils import timezone
from knox.auth import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from smarter.common.classes import SmarterHelperMixin
from smarter.common.exceptions import SmarterException
from smarter.common.utils import mask_string

from .models import SmarterAuthToken
from .signals import (
    smarter_token_authentication_failure,
    smarter_token_authentication_request,
    smarter_token_authentication_success,
)


logger = logging.getLogger(__name__)


class SmarterTokenAuthenticationError(SmarterException):
    """Base class for all SmarterTokenAuthentication errors."""

    @property
    def get_formatted_err_message(self):
        return "Smarter Token Authentication error"


class SmarterTokenAuthentication(TokenAuthentication, SmarterHelperMixin):
    """
    Custom token authentication for smarter.
    This is used to authenticate API keys. It is a subclass of the default knox
    behavior, but it also checks that the API key is active.
    """

    model = SmarterAuthToken

    def authenticate_credentials(self, token):
        # authenticate the user using the normal token authentication
        # this will raise an AuthenticationFailed exception if the token is invalid
        if not isinstance(token, bytes):
            raise AuthenticationFailed("Invalid token type. Expected bytes", 401)
        masked_token = mask_string(string=token)
        smarter_token_authentication_request.send(
            sender=self.__class__,
            token=masked_token,
        )
        logger.info("%s.authenticate_credentials() - %s", self.formatted_class_name, masked_token)
        user, auth_token = super().authenticate_credentials(token)

        # next, we need to ensure that the token is active, otherwise
        # we should raise an exception that exactly matches the one
        # raised by the default token authentication
        smarter_auth_token = SmarterAuthToken.objects.get(token_key=auth_token.token_key)
        if not smarter_auth_token.is_active:
            smarter_token_authentication_failure.send(
                sender=self.__class__,
                user=user,
                token=masked_token,
            )
            raise AuthenticationFailed("Api key is not activated.", 401)

        # update the last used time for the token
        smarter_auth_token.last_used_at = timezone.now()
        smarter_auth_token.save()

        # if the token is active, we can return the user and token as a tuple
        # exactly as the default token authentication does.
        smarter_token_authentication_success.send(
            sender=self.__class__,
            user=user,
            token=masked_token,
        )
        return (user, smarter_auth_token)
