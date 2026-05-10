"""
PluginDataApi model for storing API-based plugin data configuration.
"""

import re
from typing import Optional, Union
from urllib.parse import urljoin

import requests
from django.core.validators import MinValueValidator
from django.db import models
from pydantic import ValidationError

from smarter.apps.connection.models import ApiConnection
from smarter.apps.plugin.manifest.models.common import (
    RequestHeader,
    TestValue,
    UrlParam,
)
from smarter.common.const import SmarterHttpMethods
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.logger_helpers import formatted_text
from smarter.lib import json, logging
from smarter.lib.cache import cache_results
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .plugin_data_base import PluginDataBase
from .plugin_meta import PluginMeta

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])
logger_prefix = formatted_text(f"{__name__}")


class PluginDataApi(PluginDataBase):
    """
    Stores API-based data configuration for a Smarter plugin.

    This model is used to store the connection endpoint details for a REST API remote data source.
    It defines the API connection, endpoint, parameters, headers, body, test values, and result limits.
    The model provides methods for preparing and executing API requests, as well as validating
    the structure of parameters, headers, and test values.

    ``PluginDataApi`` is a concrete subclass of :class:`PluginDataBase` and is referenced by :class:`PluginMeta`
    to provide the data payload for API-type plugins. It is tightly integrated with :class:`ApiConnection` for
    managing API connectivity and request execution, and supports advanced features such as parameterized endpoints,
    dynamic placeholder validation, and flexible request construction.

    This model is responsible for:
      - Storing the API endpoint path, HTTP method, parameter schema, headers, and request body.
      - Validating that all placeholders in the endpoint are defined in the parameters.
      - Ensuring that test values, headers, and URL parameters are provided and conform to the expected structure.
      - Preparing and executing API requests with runtime parameters, including safe substitution of placeholders.
      - Enforcing result limits to prevent excessive data retrieval.
      - Providing methods for returning sanitized API responses for use in LLM responses.

    Typical use cases include plugins that need to retrieve or send data to external REST APIs,
    integrate with third-party services, or expose organizational APIs to the Smarter LLM platform.

    See also:

    - :class:`PluginDataBase`
    - :class:`ApiConnection`
    - :class:`PluginMeta`
    """

    # pylint: disable=C0115
    class DataTypes:
        INT = "int"
        FLOAT = "float"
        STR = "str"
        BOOL = "bool"
        LIST = "list"
        DICT = "dict"
        NULL = "null"

        @classmethod
        def all(cls) -> list:
            return [cls.INT, cls.FLOAT, cls.STR, cls.BOOL, cls.LIST, cls.DICT, cls.NULL]

    connection = models.ForeignKey(
        ApiConnection,
        on_delete=models.CASCADE,
        related_name="plugin_data_api_connection",
        help_text="The API connection associated with this plugin.",
    )
    method = models.CharField(
        max_length=10,
        choices=[
            (SmarterHttpMethods.GET, SmarterHttpMethods.GET),
            (SmarterHttpMethods.POST, SmarterHttpMethods.POST),
            (SmarterHttpMethods.PUT, SmarterHttpMethods.PUT),
            (SmarterHttpMethods.DELETE, SmarterHttpMethods.DELETE),
        ],
        default=SmarterHttpMethods.GET,
        help_text="The HTTP method to use for the API request. Example: 'GET', 'POST'.",
        blank=True,
        null=True,
    )
    endpoint = models.CharField(
        max_length=255,
        help_text="The endpoint path for the API. Example: '/v1/weather'.",
    )
    url_params = models.JSONField(
        help_text="A JSON dict containing URL parameters. Example: {'city': 'San Francisco', 'state': 'CA'}",
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )
    headers = models.JSONField(
        help_text="A JSON dict containing headers to be sent with the API request. Example: {'Authorization': 'Bearer <token>'}",
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )
    body = models.JSONField(
        help_text="A JSON dict containing the body of the API request, if applicable.",
        blank=True,
        null=True,
        encoder=json.SmarterJSONEncoder,
    )
    limit = models.IntegerField(
        help_text="The maximum number of rows to return from the API response.",
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
    )

    @property
    def url(self) -> str:
        """Return the full URL for the API endpoint."""
        return urljoin(self.connection.base_url, self.endpoint)

    def data(self, params: Optional[dict] = None) -> dict:
        return {
            "parameters": self.parameters,
            "endpoint": self.endpoint,
            "headers": self.headers,
            "body": self.body,
        }

    def prepare_request(self, params: Optional[dict]) -> dict:
        """Prepare the API request by merging parameters, headers, and body."""
        params = params or {}
        self.validate_url_params()

        request_data = {
            "url": f"{self.connection.base_url}{self.endpoint}",
            "headers": self.headers or {},
            "params": params,
            "json": self.body or {},
        }
        return request_data

    def execute_request(self, params: Optional[dict]) -> Union[dict, bool]:
        """Execute the API request and return the results."""
        request_data = self.prepare_request(params)
        try:
            response = requests.get(**request_data, timeout=self.connection.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("%s.execute_request() API request failed: %s", self.formatted_class_name, e)
            return False

    def test(self) -> Union[dict, bool]:
        """Test the API request using the test_values in the record."""
        return self.execute_request(self.test_values)

    def sanitized_return_data(self, params: Optional[dict] = None) -> Union[dict, bool]:
        """Return a dict by executing the API request with the provided params."""
        logger.info("%s.sanitized_return_data called. - %s", self.formatted_class_name, params)
        return self.execute_request(params)

    def validate_endpoint(self) -> None:
        """Validate the endpoint format."""
        if not SmarterValidator.is_valid_url_endpoint(self.endpoint):
            raise SmarterValueError("Endpoint must be a valid cleanstring.")

    def validate_url_params(self) -> None:
        """Validate the URL parameters format."""
        if self.url_params is None:
            return None
        if not isinstance(self.url_params, list):
            raise SmarterValueError(f"url_params must be a list of dictionaries but got: {type(self.url_params)}")

        for url_param in self.url_params:  # type: ignore  # pylint: disable=not-an-iterable
            try:
                # pylint: disable=E1134
                UrlParam(**url_param)
            except (ValidationError, SmarterValueError) as e:
                raise SmarterValueError(
                    f"Invalid url_param structure. Should match the Pydantic model structure, UrlParam: {e}"
                ) from e

    def validate_headers(self) -> None:
        """Validate the headers format."""
        if self.headers is None:
            return None
        if not isinstance(self.headers, list):
            raise SmarterValueError(f"headers must be a list of dictionaries but got: {type(self.headers)}")

        # pylint: disable=E1133
        for header_dict in self.headers:  # type: ignore  # pylint: disable=not-an-iterable
            try:
                # pylint: disable=E1134
                RequestHeader(**header_dict)
            except (ValidationError, SmarterValueError) as e:
                raise SmarterValueError(
                    f"Invalid header structure. Should match the Pydantic model structure, RequestHeader {e}"
                ) from e

    def validate_body(self) -> None:
        """
        Validate the body format. Currently nothing to do here.
        """
        if self.body is None:
            return None
        if not isinstance(self.body, dict) and not isinstance(self.body, list):
            raise SmarterValueError(f"body must be a dict or a list but got: {type(self.body)}")

    def validate_test_values(self) -> None:
        """Validate the test values format."""
        if self.test_values is None:
            return None
        if not isinstance(self.test_values, list):
            raise SmarterValueError(f"test_values must be a list of dictionaries but got: {type(self.test_values)}")

        # pylint: disable=E1133
        for test_value in self.test_values:
            try:
                # pylint: disable=E1134
                TestValue(**test_value)
            except (ValidationError, SmarterValueError) as e:
                raise SmarterValueError(
                    f"Invalid test value structure. Should match the Pydantic model structure, TestValue {e}"
                ) from e

    def validate_all_placeholders_in_parameters(self) -> None:
        """
        Validate that all placeholders in the SQL query string are present in the parameters.
        """
        placeholders = re.findall(r"{(.*?)}", self.endpoint) or []
        parameters = self.parameters or {}
        properties = parameters.get("properties", {})
        logger.info(
            "%s.validate_all_placeholders_in_parameters() Validating all placeholders in SQL query parameters: %s\n properties: %s, placeholders: %s",
            self.formatted_class_name,
            self.endpoint,
            properties,
            placeholders,
        )
        for placeholder in placeholders:
            if self.parameters is None or placeholder not in properties:
                raise SmarterValueError(f"Placeholder '{placeholder}' is not defined in parameters.")

    def validate(self) -> bool:
        super().validate()
        self.validate_test_values()
        self.validate_all_parameters_in_test_values()
        self.validate_all_placeholders_in_parameters()
        self.validate_endpoint()
        self.validate_url_params()
        self.validate_headers()
        self.validate_body()
        return True

    def save(self, *args, **kwargs):
        """Override the save method to validate the field dicts."""
        self.validate()
        super().save(*args, **kwargs)
        self.get_cached_data_by_plugin(self.plugin, invalidate=True)

    @classmethod
    def get_cached_data_by_plugin(cls, plugin: PluginMeta, invalidate: bool = False) -> Union["PluginDataApi", None]:
        """
        Return a single instance of PluginDataApi by plugin.

        This method caches the results to improve performance.

        :param plugin: The plugin whose data should be retrieved.
        :type plugin: PluginMeta
        :return: A PluginDataApi instance if found, otherwise None.
        :rtype: Union[PluginDataApi, None]
        """

        @cache_results()
        def data_by_plugin_id(plugin_id: int) -> Union["PluginDataApi", None]:
            try:
                return cls.objects.select_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginDataApi not found for plugin_id: {plugin_id}") from e

        if invalidate:
            data_by_plugin_id.invalidate(plugin.id)  # type: ignore[union-attr]

        return data_by_plugin_id(plugin.id)  # type: ignore[return-value]

    # pylint: disable=W0221
    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        plugin: Optional[PluginMeta] = None,
        **kwargs,
    ) -> Optional["PluginDataBase"]:
        """
        Retrieve a model instance by primary key, using caching to
        optimize performance. This method is selectively overridden in
        models that inherit from MetaDataModel to provide class-specific
        function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)

        :param invalidate: If True, invalidate the cache for this query before retrieving the object.
        :type invalidate: bool
        :param pk: The primary key of the model instance to retrieve.
        :type pk: int
        :param plugin: The PluginMeta instance associated with the data to retrieve.
        :type plugin: PluginMeta

        :returns: The model instance if found, otherwise None.
        :rtype: Optional["PluginDataBase"]
        """
        # pylint: disable=W0621
        logger_prefix = formatted_text(f"{__name__}.{PluginDataApi.__name__}.get_cached_object()")
        logger.debug(
            "%s called with pk: %s, plugin: %s",
            logger_prefix,
            pk,
            plugin,
        )

        @cache_results()
        def _get_model_by_plugin_meta(plugin_id: int) -> Optional["PluginDataBase"]:
            try:
                logger.debug(
                    "%s._get_model_by_plugin_meta() cache miss for plugin_id: %s",
                    logger_prefix,
                    plugin_id,
                )
                return cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginDataApi not found for plugin_id: {plugin_id}") from e

        if invalidate and plugin:
            _get_model_by_plugin_meta.invalidate(plugin.id)  # type: ignore[union-attr]

        if pk:
            return super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return-value]

        if plugin:
            return _get_model_by_plugin_meta(plugin.id)  # type: ignore[return-value]
