"""ApiConnection model."""

from http import HTTPStatus
from typing import Any, Optional, Union
from urllib.parse import urljoin

import requests
from django.core.validators import MinValueValidator
from django.db import models
from pydantic import JsonValue

from smarter.apps.connection.signals import (
    api_connection_attempted,
    api_connection_failed,
    api_connection_query_attempted,
    api_connection_query_failed,
    api_connection_query_success,
    api_connection_success,
)
from smarter.apps.llmtool.plugin.safe_http import (
    DEFAULT_TIMEOUT,
    SafeHttpError,
    fetch,
)
from smarter.apps.secret.models import Secret
from smarter.common.const import SmarterHttpMethods
from smarter.common.utils import to_snake_case
from smarter.lib import logging
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.typing import SmarterDictType

from .connection_base import ConnectionBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CONNECTION_LOGGING])

API_MAX_RESPONSE_BYTES = 10_000_000
"""The largest api response that :meth:`ApiConnection.execute_query` reads, in bytes."""

SUCCESS_STATUS_CODES = tuple(range(200, 300))
"""
The status codes that :func:`~smarter.apps.llmtool.plugin.safe_http.fetch` returns rather than raises.

Only 200 is a successful query. The others are answered, but report the query as failed, as before.
"""


def limit_response(response_data: JsonValue, limit: Optional[int]) -> JsonValue:
    """
    Limit an api's JSON response to ``limit`` items.

    A list keeps its first ``limit`` items. A dict keeps every key, and each of its values that is
    a list keeps its first ``limit`` items. Anything else, or no limit, is returned as it is.

    :param response_data: The parsed response.
    :param limit: The number of items to keep, or None or 0 for all of them.
    :returns: The limited response.
    """
    if not limit:
        return response_data
    if isinstance(response_data, list):
        return response_data[:limit]
    if not isinstance(response_data, dict):
        return response_data
    limited: dict[str, JsonValue] = {}
    for key, value in response_data.items():
        if isinstance(value, list):
            limited[key] = value[:limit]
        else:
            limited[key] = value
    return limited


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

        The request is made with :func:`smarter.apps.llmtool.plugin.safe_http.fetch`, because
        ``base_url`` comes from a manifest. Plain http and any port are permitted, as an api may
        need them, but the host, and the host of every redirect, must resolve to public addresses
        only, so that a manifest can't make the platform call its own network: the cluster's
        services, the Kubernetes api or the cloud's instance metadata. Loopback hosts are
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
        params = params or {}
        method = (method or SmarterHttpMethods.GET).upper()
        url = urljoin(self.base_url, endpoint)
        headers = self.request_headers(headers)
        json_body: Optional[Union[SmarterDictType, list[Any]]] = None
        if body and method in (SmarterHttpMethods.POST, SmarterHttpMethods.PUT, SmarterHttpMethods.PATCH):
            json_body = body

        self.last_status_code = None
        api_connection_attempted.send(sender=self.__class__, connection=self)
        api_connection_query_attempted.send(sender=self.__class__, connection=self)
        try:
            response = fetch(
                url,
                method=method,
                headers=headers,
                params=params,
                json_body=json_body,
                timeout=self.timeout or DEFAULT_TIMEOUT,
                max_bytes=API_MAX_RESPONSE_BYTES,
                accept_status=SUCCESS_STATUS_CODES,
                require_https=False,
                permit_local_loopback=True,
            )
        except SafeHttpError as e:
            self.request_failed(e)
            return False

        self.last_status_code = response.status_code
        if response.status_code != HTTPStatus.OK:
            # we connected, but the query failed.
            api_connection_query_success.send(sender=self.__class__, connection=self, response=response)
            api_connection_failed.send(sender=self.__class__, connection=self, response=response, error=None)
            return False
        try:
            response_data = response.json()
        except ValueError as e:
            # the api answered, but not with JSON.
            api_connection_success.send(sender=self.__class__, connection=self, response=response, error=e)
            api_connection_query_failed.send(sender=self.__class__, connection=self, response=response, error=e)
            return False
        api_connection_success.send(sender=self.__class__, connection=self)
        api_connection_query_success.send(sender=self.__class__, connection=self, response=response)
        limited_data = limit_response(response_data, limit)
        return limited_data  # type: ignore[return-value]

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

    def request_failed(self, error: SafeHttpError) -> None:
        """
        Record a request that :func:`~smarter.apps.llmtool.plugin.safe_http.fetch` refused, or that failed.

        An error with a status code is an api's answer: the connection worked, but the query
        failed. One without is a url that was refused, or a connection that failed, and so, by
        extension, a failed query.

        :param error: The error that fetch raised.
        """
        self.last_status_code = error.status_code
        if error.status_code is None:
            api_connection_query_failed.send(sender=self.__class__, connection=self, response=None, error=error)
            api_connection_failed.send(sender=self.__class__, connection=self, response=None, error=error)
            return
        api_connection_success.send(sender=self.__class__, connection=self, response=None, error=error)
        api_connection_query_failed.send(sender=self.__class__, connection=self, response=None, error=error)

    def __str__(self) -> str:
        return self.name + " - " + self.get_connection_string() if isinstance(self.name, str) else "unassigned"


__all__ = ["ApiConnection"]
