"""
The contract of the console's account api, ``/api/web/account/``: its request bodies and responses, as Pydantic models.

Signing in, signing out and activating an account answer with the new
:class:`~smarter.apps.api.web.session.contract.ConsoleSession`, so that the console needn't ask again.
Signing up, asking for a new activation link and the password reset endpoints answer with an
:class:`AccountMessage`. A refused request answers with an
:class:`AccountErrors`: a message for the whole form, and one or more messages per field, which the
console shows beside the fields. The JSON is camelCase.

The models are part of the console's schema, ``console-session.schema.json``: see
:func:`smarter.apps.api.web.session.contract.contract_schema`.
"""

from pydantic import Field

from smarter.apps.api.web.session.contract import ConsoleSessionModel


class SignInRequest(ConsoleSessionModel):
    """The body of ``POST /api/web/account/login/``."""

    email: str = Field(..., description="The email address.")
    password: str = Field(..., description="The password.")


class SignUpRequest(ConsoleSessionModel):
    """The body of ``POST /api/web/account/register/``."""

    email: str = Field(..., description="The email address, which is also the username.")
    password: str = Field(..., description="The password, which Django's password validators must accept.")


class PasswordResetRequest(ConsoleSessionModel):
    """The body of ``POST /api/web/account/password-reset-request/``."""

    email: str = Field(..., description="The email address to send the link to.")


class ActivationResendRequest(ConsoleSessionModel):
    """The body of ``POST /api/web/account/activation-resend/``."""

    email: str = Field(..., description="The email address to send a new activation link to.")


class NewPasswordRequest(ConsoleSessionModel):
    """The body of ``POST /api/web/account/password-reset/<uidb64>/<token>/``."""

    password: str = Field(..., description="The new password, which Django's password validators must accept.")
    password_confirm: str = Field(..., description="The new password again.")


class AccountMessage(ConsoleSessionModel):
    """A request that succeeded, with a message for the user."""

    detail: str = Field(..., description="What happened, in the session's language.")


class AccountErrors(ConsoleSessionModel):
    """A request that was refused, with why."""

    detail: str = Field(..., description="Why, for the whole form, in the session's language.")
    field_errors: dict[str, list[str]] = Field(
        ...,
        description="The messages of each field that was refused, by its camelCase name; empty when none was.",
    )


REQUEST_MODELS = (SignInRequest, SignUpRequest, ActivationResendRequest, PasswordResetRequest, NewPasswordRequest)
"""What the console sends."""

RESPONSE_MODELS = (AccountMessage, AccountErrors)
"""What the views send, besides the console session."""

__all__ = [
    "AccountErrors",
    "ActivationResendRequest",
    "AccountMessage",
    "NewPasswordRequest",
    "PasswordResetRequest",
    "REQUEST_MODELS",
    "RESPONSE_MODELS",
    "SignInRequest",
    "SignUpRequest",
]
