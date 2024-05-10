"""Module exceptions.py"""


class SmarterExceptionBase(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SmarterConfigurationError(SmarterExceptionBase):
    """Exception raised for errors in the configuration."""


class SmarterValueError(SmarterExceptionBase):
    """Exception raised for illegal or invalid values."""


class SmarterIlligalInvocationError(SmarterExceptionBase):
    """Exception raised when the service is illegally invoked."""


class SmarterBusinessRuleViolation(SmarterExceptionBase):
    """Exception raised when policies are violated."""


def error_response_factory(e: Exception) -> dict:
    """Create a standard error response."""
    if isinstance(e, SmarterExceptionBase):
        error_class = "SmarterExceptionBase"
    else:
        error_class = "Exception"

    return {
        "errorClass": error_class,
        "stacktrace": str(e),
        "description": e.args[0] if e.args else "",  # get the error message from args
        "status": e.status if hasattr(e, "status") else "",  # check if status attribute exists
        "args": e.args,
        "cause": str(e.__cause__),
        "context": str(e.__context__),
    }
