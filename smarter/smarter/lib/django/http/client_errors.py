"""
The exceptions that a client can cause, and the message of each one that a view may send back.

A view that catches an exception must not send the exception's text to the client. A database
error names tables, columns and constraints, e.g. ``(1062, "Duplicate entry 'x-5' for key
'unique_name_user_profile'")``, and other errors carry file paths and values from the code.
CodeQL reports each one (``py/stack-trace-exposure``).

A view therefore handles exceptions in two steps:

1. ``except CLIENT_ERROR_TYPES``: an error that the client caused and can correct, e.g. the
   :class:`~django.core.exceptions.ValidationError` of a name that isn't valid, which a model's
   ``full_clean()`` raises when the web console renames a resource. The view logs a warning and
   answers 400 with :func:`client_error_message`.
2. ``except Exception``: the catch-all, for anything else, which is a fault of the server. The
   view logs an error, with its stack trace, and answers 500 with a fixed message.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError, RestrictedError
from rest_framework.exceptions import ParseError, UnsupportedMediaType

from smarter.common.exceptions import SmarterBusinessRuleViolation, SmarterValueError
from smarter.lib.manifest.exceptions import SAMBadRequestError, SAMValidationError

SMARTER_CLIENT_ERROR_TYPES = (SmarterValueError, SmarterBusinessRuleViolation, SAMValidationError, SAMBadRequestError)
"""
Smarter's exceptions whose message is written for the client: a value, a policy or a manifest.

that the client can change.
"""

CLIENT_ERROR_TYPES = (
    ValidationError,
    IntegrityError,
    ProtectedError,
    RestrictedError,
) + SMARTER_CLIENT_ERROR_TYPES
"""
The exceptions that a client's request can cause, and that the client can correct.

- :class:`~django.core.exceptions.ValidationError`: a value, e.g. a new name, is not valid.
- :class:`~django.db.IntegrityError`: the change conflicts with another row, e.g. a clone or a
  rename whose name the user already has.
- :class:`~django.db.models.ProtectedError` and :class:`~django.db.models.RestrictedError`:
  other resources still refer to the one being deleted.
- :data:`SMARTER_CLIENT_ERROR_TYPES`: a value, a policy or a manifest that the client can change.
"""

REQUEST_DATA_ERROR_TYPES = CLIENT_ERROR_TYPES + (ParseError, UnsupportedMediaType, TypeError, ValueError)
"""
The exceptions of a try block that reads the client's data and builds a model from it.

To :data:`CLIENT_ERROR_TYPES`, it adds what parsing the body and ``Model.objects.create(**data)``
raise for the client's mistakes: Django REST framework's
:class:`~rest_framework.exceptions.ParseError` and
:class:`~rest_framework.exceptions.UnsupportedMediaType` for a body that it cannot parse,
:class:`TypeError` for a field that the model doesn't have, and :class:`ValueError` (which
includes :class:`json.JSONDecodeError`) for a value of the wrong type. Use it only around code
that handles the client's data: elsewhere, a :class:`TypeError` or :class:`ValueError` is a bug,
which the catch-all must answer with a 500.
"""

INTEGRITY_ERROR_MESSAGE = "The change conflicts with an existing resource, e.g. one with the same name."
"""The message of an :class:`~django.db.IntegrityError`, whose own text names the database's tables and keys."""

PROTECTED_ERROR_MESSAGE = "Other resources still refer to this one, so it cannot be deleted."
"""The message of a :class:`~django.db.models.ProtectedError` or :class:`~django.db.models.RestrictedError`."""


def client_error_message(e: Exception, fallback: str) -> str:
    """
    The message of an exception that is safe to send to the client.

    A :class:`~django.core.exceptions.ValidationError` gives its messages, joined by spaces. An
    :class:`~django.db.IntegrityError` gives :data:`INTEGRITY_ERROR_MESSAGE`, and a
    :class:`~django.db.models.ProtectedError` or :class:`~django.db.models.RestrictedError`
    gives :data:`PROTECTED_ERROR_MESSAGE`. One of :data:`SMARTER_CLIENT_ERROR_TYPES` gives its
    message, without the label that its ``str()`` adds. Any other exception gives ``fallback``:
    its text may describe the server's internals. The caller logs the exception itself.

    :param e: The exception that the view caught.
    :param fallback: The message to send when the exception's own message is not safe, e.g.
        ``"An error occurred while renaming the Secret."``
    :returns: The message for the response.

    **Example:**

    .. code-block:: python

        except CLIENT_ERROR_TYPES as e:
            logger.warning("%s.post() could not rename %s: %s", self.formatted_class_name, secret_id, e)
            message = client_error_message(e, "An error occurred while renaming the Secret.")
            return JsonResponse({"error": message}, status=HTTPStatus.BAD_REQUEST)
        # pylint: disable=broad-except
        except Exception:
            logger.error("%s.post() could not rename %s", self.formatted_class_name, secret_id, exc_info=True)
            return JsonResponse(
                {"error": "An unknown error occurred while renaming the Secret."},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
    """
    if isinstance(e, ValidationError):
        messages = e.messages
        message = " ".join(messages)
        return message
    # ProtectedError and RestrictedError are IntegrityErrors, so they are checked first.
    if isinstance(e, (ProtectedError, RestrictedError)):
        return PROTECTED_ERROR_MESSAGE
    if isinstance(e, IntegrityError):
        return INTEGRITY_ERROR_MESSAGE
    if isinstance(e, SMARTER_CLIENT_ERROR_TYPES):
        return e.message
    return fallback


__all__ = [
    "CLIENT_ERROR_TYPES",
    "INTEGRITY_ERROR_MESSAGE",
    "PROTECTED_ERROR_MESSAGE",
    "REQUEST_DATA_ERROR_TYPES",
    "SMARTER_CLIENT_ERROR_TYPES",
    "client_error_message",
]
