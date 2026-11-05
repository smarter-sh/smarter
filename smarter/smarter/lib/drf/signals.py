"""Signals of token authentication: a request, a success and a failure."""

from django.dispatch import Signal

smarter_token_authentication_request = Signal()
smarter_token_authentication_success = Signal()
smarter_token_authentication_failure = Signal()
