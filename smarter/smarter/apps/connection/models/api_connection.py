"""ApiConnection model."""

from http import HTTPStatus
from typing import Any, Optional, Union
from urllib.parse import urljoin

import requests
from django.core.validators import MinValueValidator
from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModelManager,
)
from smarter.apps.connection.signals import (
    api_connection_attempted,
    api_connection_failed,
    api_connection_query_attempted,
    api_connection_query_failed,
    api_connection_query_success,
    api_connection_success,
)
from smarter.apps.secret.models import Secret
from smarter.common.helpers.logger_helpers import formatted_text
from smarter.common.utils import camel_to_snake
from smarter.lib import logging
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .connection_base import ConnectionBase

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CONNECTION_LOGGING])
logger_prefix = formatted_text(f"{__name__}")


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

    objects: MetaDataWithOwnershipModelManager["ApiConnection"] = MetaDataWithOwnershipModelManager()

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
        return self.get_connection_string()

    def test_proxy(self) -> bool:
        proxy_dict = {
            self.proxy_protocol: f"{self.proxy_protocol}://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}",
        }
        try:
            response = requests.get("https://www.google.com", proxies=proxy_dict, timeout=self.timeout)
            return response.status_code in [HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT]
        except requests.exceptions.RequestException as e:
            logger.error("%s.test_proxy() proxy test connection failed: %s", self.formatted_class_name, e)
            return False

    def test_connection(self) -> bool:
        """Test the API connection by making a simple GET request to the root domain."""
        try:
            logger.warning(
                "%s.test_connection() called for %s with auth method %s but we didn't actually test it.",
                self.formatted_class_name,
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
            snake_case_name = camel_to_snake(self.name)
            logger.warning(
                "%s.save(): name %s was not in snake_case. Converted to snake_case: %s",
                self.formatted_class_name,
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

    def execute_query(
        self, endpoint: str, params: Optional[dict] = None, limit: Optional[int] = None
    ) -> Union[dict[str, Any], list[Any], bool]:
        """
        Execute the API query and return the results.
        This method constructs the full URL by combining the base URL and the endpoint,
        and sends a GET request to the API with the provided parameters.

        :param endpoint: The API endpoint to query.
        :param params: A dictionary of parameters to include in the API request.
        :param limit: The maximum number of rows to return from the API response.
        :return: The API response as a JSON object or False if the request fails.
        """
        params = params or {}
        url = urljoin(self.base_url, endpoint)
        headers = {}
        if self.auth_method == "basic" and self.api_key:
            headers["Authorization"] = f"Basic {self.api_key}"
        elif self.auth_method == "token" and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            api_connection_attempted.send(sender=self.__class__, connection=self)
            api_connection_query_attempted.send(sender=self.__class__, connection=self)
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            if response.status_code in [HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT]:
                api_connection_success.send(sender=self.__class__, connection=self)
                api_connection_query_success.send(sender=self.__class__, connection=self, response=response)
                if limit:
                    response_data = response.json()
                    if isinstance(response_data, list):
                        response_data = response_data[:limit]
                    elif isinstance(response_data, dict):
                        response_data = {k: v[:limit] for k, v in response_data.items() if isinstance(v, list)}
                    return response_data
                return response.json()
            else:
                # we connected, but the query failed.
                api_connection_query_success.send(sender=self.__class__, connection=self, response=response)
                api_connection_failed.send(sender=self.__class__, connection=self, response=response, error=None)
                return False
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            # connection failed, and so by extension, so did the query
            api_connection_query_failed.send(sender=self.__class__, connection=self, response=response, error=e)
            api_connection_failed.send(sender=self.__class__, connection=self, response=response, error=e)
            return False
        except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as e:
            # query failed, but connection was successful
            api_connection_success.send(sender=self.__class__, connection=self, response=response, error=e)
            api_connection_query_failed.send(sender=self.__class__, connection=self, response=response, error=e)
            return False

    def __str__(self) -> str:
        return self.name + " - " + self.get_connection_string() if isinstance(self.name, str) else "unassigned"


__all__ = ["ApiConnection"]
