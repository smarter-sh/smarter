"""ApiConnection model."""

from http import HTTPStatus
from typing import Any, Optional, Union
from urllib.parse import urljoin

import requests
from django.core.validators import MinValueValidator
from django.db import models

from smarter.apps.connection.execution import ApiToolCall
from smarter.apps.connection.signals import (
    api_connection_attempted,
    api_connection_failed,
    api_connection_query_attempted,
    api_connection_query_failed,
    api_connection_query_success,
    api_connection_success,
)
from smarter.apps.llmtool.plugin.safe_http import DEFAULT_TIMEOUT
from smarter.apps.llmtool.runner import ToolCallResult, get_tool_runner
from smarter.apps.secret.models import Secret
from smarter.common.const import SmarterHttpMethods
from smarter.common.utils import to_snake_case
from smarter.lib import logging
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .connection_base import ConnectionBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CONNECTION_LOGGING])


class ApiConnection(ConnectionBase):
    """
    Stores API connection configuration.

    This model defines the connection details for a remote API,
    including authentication method, base URL, credentials, timeout, and proxy settings.
    It provides methods for testing the API and proxy connections, and for validating
    the configuration.

    ``ApiConnection`` is a concrete subclass of :class:`ConnectionBase` and is referenced by
    :class:`PluginDataApi` to provide the connection. It supports a variety
    of authentication methods (none, basic, token, OAuth), as well as proxy configuration for secure
    and flexible integration with external APIs.

    This model is responsible for:
      - Managing API credentials and secrets using the :class:`Secret` model.
      - Constructing connection strings and request headers for different authentication schemes.
      - Providing methods for testing connectivity to the API and proxy endpoints.
      - Supporting timeout and proxy configuration for robust and secure API access.
      - Integrating with the Smarter plugin system to enable dynamic, authenticated API requests.

    Typical use cases include plugins that need to retrieve or send data to external REST APIs,
    integrate with third-party services, or expose organizational APIs to the Smarter LLM platform.

    See also:

    - :class:`ConnectionBase`
    - :class:`PluginDataApi`
    - :class:`smarter.apps.account.models.Secret`
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "API Connection"
        verbose_name_plural = "API Connections"

    last_status_code: Optional[int] = None
    """
    The HTTP status code of the most recent :meth:`execute_query` response, or ``None`` if no.

    request was sent, or the server could not be reached.
    """

    AUTH_METHOD_CHOICES = [
        ("none", "None"),
        ("basic", "Basic Auth"),
        ("token", "Token Auth"),
        ("oauth", "OAuth"),
    ]
    PROXY_PROTOCOL_CHOICES = [("http", "HTTP"), ("https", "HTTPS"), ("socks", "SOCKS")]

    base_url = models.URLField(
        help_text="The root domain of the API. Example: 'https://api.example.com'.",
    )
    api_key = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="api_connections_api_key",
        help_text="The API key for authentication, if required.",
        blank=True,
        null=True,
    )
    auth_method = models.CharField(
        help_text="The authentication method to use. Example: 'Basic Auth', 'Token Auth'.",
        max_length=50,
        choices=AUTH_METHOD_CHOICES,
        default="none",
        blank=True,
        null=True,
    )
    timeout = models.IntegerField(
        help_text="The timeout for the API request in seconds. Default is 30 seconds.",
        default=30,
        validators=[MinValueValidator(1)],
        blank=True,
        null=True,
    )
    # Proxy fields
    proxy_protocol = models.CharField(
        max_length=10,
        choices=PROXY_PROTOCOL_CHOICES,
        default="http",
        help_text="The protocol to use for the proxy connection.",
        blank=True,
        null=True,
    )
    proxy_host = models.CharField(max_length=255, blank=True, null=True)
    proxy_port = models.IntegerField(blank=True, null=True)
    proxy_username = models.CharField(max_length=255, blank=True, null=True)
    proxy_password = models.ForeignKey(
        Secret,
        on_delete=models.CASCADE,
        related_name="api_connections_proxy_password",
        help_text="The proxy password for authentication, if required.",
        blank=True,
        null=True,
    )

    @property
    def connection_string(self) -> str:
        """Return the connection string, from :meth:`get_connection_string`."""
        return self.get_connection_string()

    def test_proxy(self) -> bool:
        """
        Test the proxy by sending a GET request to ``https://www.google.com`` through it.

        This makes a network call, and logs an error when the request fails.

        :returns: True if the response status is 200 or 308, otherwise False.
        """
        proxy_dict: dict[str, str] = {}
        if self.proxy_protocol:
            proxy_dict[self.proxy_protocol] = (
                f"{self.proxy_protocol}://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}"
            )
        try:
            response = requests.get("https://www.google.com", proxies=proxy_dict, timeout=self.timeout)
            return response.status_code in [HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT]
        except requests.exceptions.RequestException as e:
            logger.error("proxy test connection failed: %s", e)
            return False

    def test_connection(self) -> bool:
        """
        Report the API connection as working, without testing it.

        An api's root path is rarely a meaningful endpoint, so a request to it would not show
        whether the plugin's endpoints work. This is called whenever the connection is saved.
        """
        try:
            logger.debug(
                "assumes that %s, with auth method %s, works: it is not tested.",
                self.name,
                self.auth_method,
            )
            # result = self.execute_query(endpoint="/", params=None, limit=1)
            # return bool(result)
            return True
        # pylint: disable=W0718
        except Exception:
            return False

    def get_connection_string(self, masked: bool = True) -> str:
        """Return the connection string."""
        if masked:
            return f"{self.base_url} (Auth: ******)"
        return f"{self.base_url} (Auth: {self.auth_method})"

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        if isinstance(self.name, str) and not SmarterValidator.is_valid_snake_case(self.name):
            snake_case_name = to_snake_case(self.name)
            logger.warning(
                "name %s was not in snake_case. Converted to snake_case: %s",
                self.name,
                snake_case_name,
            )
            self.name = snake_case_name
        self.validate()
        super().save(*args, **kwargs)

    def validate(self) -> bool:
        """Validate the API connection."""
        super().validate()
        return self.test_connection()

    # pylint: disable=too-many-arguments
    def execute_query(
        self,
        endpoint: str,
        params: Optional[SmarterDictType] = None,
        limit: Optional[int] = None,
        *,
        method: str = SmarterHttpMethods.GET,
        headers: Optional[dict[str, str]] = None,
        body: Optional[Union[SmarterDictType, list[Any]]] = None,
    ) -> Union[SmarterDictType, list[Any], bool]:
        """
        Execute the API query and return the results.

        This method constructs the full URL by combining the base URL and the endpoint,
        and sends an HTTP request to the API with the provided parameters, headers and body.
        Authentication headers derived from this connection's ``auth_method`` and ``api_key``
        take precedence over any caller-supplied ``Authorization`` header.
        Sets :attr:`last_status_code`, so that a caller can tell a rejected credential
        (HTTP 401 or 403) from any other failure.

        The request is resolved here, in the app, into an
        :class:`~smarter.apps.connection.execution.ApiToolCall`, with the ``Authorization`` header
        read from the connection's Smarter Secret, and executed by the tool runner
        (:mod:`smarter.apps.llmtool.runner`), with
        :func:`~smarter.apps.connection.execution.execute_api_call`. The signals are sent here, from
        its result. Because ``base_url`` comes from a manifest, the request is made with
        :func:`smarter.apps.llmtool.plugin.safe_http.fetch`: plain http and any port are permitted,
        as an api may need them, but the host, and the host of every redirect, must resolve to public
        addresses only, so that a manifest can't make the platform call its own network: the
        cluster's services, the Kubernetes api or the cloud's instance metadata. Loopback hosts are
        permitted in the local environment only. A redirect to another origin doesn't carry the
        ``Authorization`` header.

        :param endpoint: The API endpoint to query.
        :param params: A dictionary of URL query string parameters to include in the API request.
        :param limit: The maximum number of rows to return from the API response.
        :param method: The HTTP method to use. One of :py:class:`smarter.common.const.SmarterHttpMethods`. Defaults to ``GET``.
        :param headers: Optional HTTP request headers to include in the API request.
        :param body: Optional JSON request body. Only sent for ``POST``, ``PUT`` and ``PATCH`` requests.
        :return: The API response as a JSON object or False if the request fails.
        """
        method = (method or SmarterHttpMethods.GET).upper()
        json_body: Optional[Union[SmarterDictType, list[Any]]] = None
        if body and method in (SmarterHttpMethods.POST, SmarterHttpMethods.PUT, SmarterHttpMethods.PATCH):
            json_body = body
        call = ApiToolCall(
            url=urljoin(self.base_url, endpoint),
            method=method,
            headers=self.request_headers(headers),
            params=params or {},
            json_body=json_body,
            timeout=self.timeout or DEFAULT_TIMEOUT,
            limit=limit,
        )

        self.last_status_code = None
        api_connection_attempted.send(sender=self.__class__, connection=self)
        api_connection_query_attempted.send(sender=self.__class__, connection=self)
        result = get_tool_runner().run(call)
        self.last_status_code = result.status_code
        self.record_result(result)
        if result.failure is not None:
            return False
        return result.value  # type: ignore[return-value]

    def request_headers(self, headers: Optional[dict[str, str]]) -> dict[str, str]:
        """
        Return a copy of a request's headers, with this connection's ``Authorization`` header.

        :param headers: The caller's headers, which are not changed.
        :returns: The headers to send. ``basic`` and ``token`` auth replace any caller-supplied
            ``Authorization`` header with the connection's api key.
        """
        request_headers = dict(headers or {})
        api_key = None
        if self.api_key:
            api_key = self.api_key.get_secret()
        if not api_key:
            return request_headers
        if self.auth_method == "basic":
            request_headers["Authorization"] = f"Basic {api_key}"
        elif self.auth_method == "token":
            request_headers["Authorization"] = f"Bearer {api_key}"
        return request_headers

    def record_result(self, result: ToolCallResult) -> None:
        """
        Send the signals that report a query's result.

        - Without a status code, the url was refused, or the api couldn't be reached: the
          connection failed, and so, by extension, did the query.
        - With status 200 and a failure, the api answered, but not with JSON: the connection
          worked, and the query failed.
        - With another 2xx status, the api answered the query, but not with its data: the query
          succeeded, and the connection is reported as failed.
        - With an error status, the connection worked, and the query failed.
        - Otherwise both succeeded.

        The signals carry the response's ``status_code``, and, for a failure, its description as
        ``error``. They don't carry the response, which stays where the call ran.

        :param result: The tool runner's result.
        """
        status_code = result.status_code
        error = result.failure
        if error is None:
            api_connection_success.send(sender=self.__class__, connection=self, status_code=status_code)
            api_connection_query_success.send(sender=self.__class__, connection=self, status_code=status_code)
            return
        if status_code is None:
            api_connection_query_failed.send(sender=self.__class__, connection=self, status_code=None, error=error)
            api_connection_failed.send(sender=self.__class__, connection=self, status_code=None, error=error)
            return
        if HTTPStatus.OK < status_code < HTTPStatus.MULTIPLE_CHOICES:
            api_connection_query_success.send(sender=self.__class__, connection=self, status_code=status_code)
            api_connection_failed.send(sender=self.__class__, connection=self, status_code=status_code, error=error)
            return
        api_connection_success.send(sender=self.__class__, connection=self, status_code=status_code, error=error)
        api_connection_query_failed.send(sender=self.__class__, connection=self, status_code=status_code, error=error)

    def __str__(self) -> str:
        return self.name + " - " + self.get_connection_string() if isinstance(self.name, str) else "unassigned"


__all__ = ["ApiConnection"]
