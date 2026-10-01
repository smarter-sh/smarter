"""
Exceptions of the Proxy passthrough.

Each one is an HTTP error response to the caller: its :attr:`ProxyError.status` and
:attr:`ProxyError.code`. They derive from :class:`Exception`, not
:class:`~smarter.common.exceptions.SmarterException`, which logs every instance as an error:
most of them are the caller's mistakes, e.g. an unknown Proxy, and are logged as warnings.
"""

from http import HTTPStatus


class ProxyError(Exception):
    """Base class of the Proxy passthrough's errors: a 502 Bad Gateway, unless a subclass says otherwise."""

    status: int = HTTPStatus.BAD_GATEWAY
    code: str = "proxy_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

    def to_dict(self) -> dict:
        """The error, in the shape that the OpenAI and Anthropic SDKs report: ``{"error": {...}}``."""
        return {"error": {"message": self.message, "type": "smarter_proxy_error", "code": self.code}}


class ProxyNotFound(ProxyError):
    """No Proxy of that name exists that the caller may use."""

    status = HTTPStatus.NOT_FOUND
    code = "proxy_not_found"


class ProxyInactive(ProxyError):
    """The Proxy is inactive: spec.isActive is false."""

    status = HTTPStatus.FORBIDDEN
    code = "proxy_inactive"


class ProxyPathNotAllowed(ProxyError):
    """The path is not one of the Proxy's spec.allowedPaths, or would leave its base URL."""

    status = HTTPStatus.FORBIDDEN
    code = "path_not_allowed"


class ProxyBudgetExceeded(ProxyError):
    """A budget's resource lock forbids charges to the Proxy, the caller, or the caller's account."""

    status = HTTPStatus.PAYMENT_REQUIRED
    code = "budget_exceeded"


class ProxyConfigurationError(ProxyError):
    """The Proxy cannot forward requests: it has no base URL or API key, or its host is not allowed."""

    status = HTTPStatus.SERVICE_UNAVAILABLE
    code = "proxy_misconfigured"


class ProxyUpstreamError(ProxyError):
    """The provider's API could not be reached."""

    status = HTTPStatus.BAD_GATEWAY
    code = "upstream_unreachable"


class ProxyUpstreamTimeout(ProxyError):
    """The provider's API did not respond within the Proxy's spec.timeout."""

    status = HTTPStatus.GATEWAY_TIMEOUT
    code = "upstream_timeout"


__all__ = [
    "ProxyBudgetExceeded",
    "ProxyConfigurationError",
    "ProxyError",
    "ProxyInactive",
    "ProxyNotFound",
    "ProxyPathNotAllowed",
    "ProxyUpstreamError",
    "ProxyUpstreamTimeout",
]
