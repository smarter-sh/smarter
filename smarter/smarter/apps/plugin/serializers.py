"""PluginMeta serializers."""

from rest_framework import serializers
from taggit.models import Tag

from smarter.apps.account.serializers import (
    AccountMiniSerializer,
    SecretSerializer,
    UserProfileSerializer,
)
from smarter.apps.plugin.models import (
    ApiConnection,
    PluginDataApi,
    PluginDataSql,
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
    SqlConnection,
)
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .manifest.enum import (
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
)


class TagListSerializerField(serializers.ListField):
    """
    Serializer for a list of tags.

    This field serializes a list of tag names to strings and deserializes them to `Tag` model instances.
    It supports both direct lists and Django taggable manager objects.

    :param child: The serializer field used for each tag (defaults to `CharField`).
    :type child: serializers.CharField

    :return: A list of tag names (for serialization) or a list of `Tag` objects (for deserialization).
    :rtype: list[str] or list[Tag]

    .. important::

        When deserializing, tags are created if they do not already exist.

    .. seealso::

        - :class:`taggit.models.Tag`
        - :class:`rest_framework.serializers.ListField`

    .. versionadded:: 3.0.0

    **Example usage**:

    .. code-block:: python

        class MySerializer(serializers.Serializer):
            tags = TagListSerializerField()

        # Serializing
        serializer = MySerializer({'tags': ['foo', 'bar']})
        print(serializer.data)  # {'tags': ['foo', 'bar']}

        # Deserializing
        serializer = MySerializer(data={'tags': ['foo', 'bar']})
        serializer.is_valid()
        print(serializer.validated_data['tags'])  # [<Tag: foo>, <Tag: bar>]

    """

    child = serializers.CharField()

    def to_representation(self, data):
        if hasattr(data, "all"):
            tags = data.all()
        else:
            tags = data
        return [str(tag) for tag in tags]

    def to_internal_value(self, data):
        return [Tag.objects.get_or_create(name=name)[0] for name in data]


class PluginMetaSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the PluginMeta model.

    This serializer provides a camelCase API for plugin metadata, including fields for name, account,
    description, plugin class, version, author, and tags. It is used to serialize and deserialize
    plugin metadata for API responses and requests.

    :param tags: List of tags associated with the plugin.
    :type tags: TagListSerializerField
    :param author: The user profile of the plugin author (read-only).
    :type author: UserProfileSerializer
    :param account: The account associated with the plugin (read-only).
    :type account: AccountMiniSerializer

    :return: Serialized plugin metadata.
    :rtype: dict

    .. important::

        The `author` and `account` fields are read-only and cannot be modified via API requests.

    .. seealso::

        - :class:`PluginMeta`
        - :class:`TagListSerializerField`
        - :class:`UserProfileSerializer`
        - :class:`AccountMiniSerializer`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.serializers import PluginMetaSerializer
        from smarter.apps.plugin.models import PluginMeta

        plugin = PluginMeta.objects.first()
        serializer = PluginMetaSerializer(plugin)
        print(serializer.data)
        # Output: {
        #   "name": "...",
        #   "account": {...},
        #   "description": "...",
        #   "pluginClass": "...",
        #   "version": "...",
        #   "author": {...},
        #   "tags": ["tag1", "tag2"]
        # }

    """

    tags = TagListSerializerField()
    author = UserProfileSerializer(read_only=True)
    account = AccountMiniSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginMeta
        fields = ["name", "account", "description", "plugin_class", "version", "author", "tags"]


class PluginSelectorSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the PluginSelector model.

    This serializer exposes plugin selector directives and search terms in camelCase format for API responses.
    It is used to serialize and deserialize plugin selector configuration, typically for UI or API integration.

    :param directive: The selector directive for the plugin.
    :type directive: str
    :param searchTerms: The search terms associated with the selector.
    :type searchTerms: str

    :return: Serialized plugin selector data.
    :rtype: dict

    .. important::

        The `searchTerms` field is derived from the plugin specification and may be required for search-based selection.

    .. seealso::

        - :class:`PluginSelector`
        - :class:`SAMPluginCommonSpecSelectorKeyDirectiveValues`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.serializers import PluginSelectorSerializer
        from smarter.apps.plugin.models import PluginSelector

        selector = PluginSelector.objects.first()
        serializer = PluginSelectorSerializer(selector)
        print(serializer.data)
        # Output: {
        #   "directive": "...",
        #   "searchTerms": "..."
        # }

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginSelector
        fields = ["directive", SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value]


class PluginPromptSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the PluginPrompt model.

    This serializer exposes prompt configuration fields for plugins, including provider, system role,
    model, temperature, and max tokens (mapped from `max_completion_tokens`). It is used to serialize
    and deserialize prompt settings for plugin APIs.

    :param provider: The name of the prompt provider (e.g., "openai").
    :type provider: str
    :param system_role: The system role for the prompt context.
    :type system_role: str
    :param model: The model name used for the prompt.
    :type model: str
    :param temperature: The temperature setting for prompt generation.
    :type temperature: float
    :param max_tokens: The maximum number of completion tokens (from `max_completion_tokens`).
    :type max_tokens: int

    :return: Serialized plugin prompt configuration.
    :rtype: dict

    .. note::

        The `max_tokens` field is mapped from the model's `max_completion_tokens` attribute.

    .. seealso::

        - :class:`PluginPrompt`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.serializers import PluginPromptSerializer
        from smarter.apps.plugin.models import PluginPrompt

        prompt = PluginPrompt.objects.first()
        serializer = PluginPromptSerializer(prompt)
        print(serializer.data)
        # Output: {
        #   "provider": "...",
        #   "systemRole": "...",
        #   "model": "...",
        #   "temperature": ...,
        #   "maxTokens": ...
        # }

    """

    # TODO: this temporarily deals with a breaking change in gpt 5
    max_tokens = serializers.IntegerField(source="max_completion_tokens")

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginPrompt
        fields = ["provider", "system_role", "model", "temperature", "max_tokens"]


class PluginStaticSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the PluginDataStatic model.

    This serializer handles static plugin data, exposing fields for description and static_data.
    It is used to serialize and deserialize static plugin configuration for API endpoints.

    :param description: A brief description of the static plugin.
    :type description: str
    :param static_data: Arbitrary static data associated with the plugin.
    :type static_data: dict or str

    :return: Serialized static plugin data.
    :rtype: dict


    .. seealso::

        - :class:`PluginDataStatic`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.serializers import PluginStaticSerializer
        from smarter.apps.plugin.models import PluginDataStatic

        static_plugin = PluginDataStatic.objects.first()
        serializer = PluginStaticSerializer(static_plugin)
        print(serializer.data)
        # Output: {
        #   "description": "...",
        #   "staticData": {...}
        # }

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginDataStatic
        fields = ["description", "static_data"]


class SqlConnectionSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the SqlConnection model.

    This serializer exposes SQL connection configuration fields in camelCase format, including
    connection details and optional proxy settings. It is used to serialize and deserialize
    SQL connection information for plugin APIs.

    :param name: The name of the SQL connection.
    :type name: str
    :param description: A brief description of the connection.
    :type description: str
    :param hostname: The database server hostname.
    :type hostname: str
    :param port: The port number for the database server.
    :type port: int
    :param database: The database name.
    :type database: str
    :param username: The username for authentication.
    :type username: str
    :param password: The password for authentication.
    :type password: str
    :param proxy_protocol: The protocol used for proxying (optional).
    :type proxy_protocol: str
    :param proxy_host: The proxy server hostname (optional).
    :type proxy_host: str
    :param proxy_port: The proxy server port (optional).
    :type proxy_port: int
    :param proxy_username: The proxy username (optional).
    :type proxy_username: str
    :param proxy_password: The proxy password (optional).
    :type proxy_password: str

    :return: Serialized SQL connection configuration.
    :rtype: dict

    .. note::

        `password` and `proxy_password` are references to Smarter Secrets instances.
        These do not expose raw passwords.

    .. seealso::

        - :class:`SqlConnection`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.serializers import SqlConnectionSerializer
        from smarter.apps.plugin.models import SqlConnection

        conn = SqlConnection.objects.first()
        serializer = SqlConnectionSerializer(conn)
        print(serializer.data)
        # Output: {
        #   "name": "...",
        #   "description": "...",
        #   "hostname": "...",
        #   "port": ...,
        #   "database": "...",
        #   "username": "...",
        #   "password": "...",
        #   "proxyProtocol": "...",
        #   "proxyHost": "...",
        #   "proxyPort": ...,
        #   "proxyUsername": "...",
        #   "proxyPassword": "..."
        # }

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SqlConnection
        fields = [
            "name",
            "description",
            "hostname",
            "port",
            "database",
            "username",
            "password",
            "proxy_protocol",
            "proxy_host",
            "proxy_port",
            "proxy_username",
            "proxy_password",
        ]


class PluginSqlSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the PluginDataSql model.

    This serializer exposes SQL plugin configuration fields, including the connection, description,
    parameters, SQL query, test values, and result limit. It is used to serialize and deserialize
    SQL plugin settings for API endpoints.

    :param connection: The name of the SQL connection to use.
    :type connection: str
    :param description: A brief description of the SQL plugin.
    :type description: str
    :param parameters: Parameters for the SQL query.
    :type parameters: dict or list
    :param sql_query: The SQL query string to execute.
    :type sql_query: str
    :param test_values: Example values for testing the query.
    :type test_values: dict or list
    :param limit: The maximum number of results to return.
    :type limit: int

    :return: Serialized SQL plugin configuration.
    :rtype: dict

    .. note::

        The `connection` field uses a slug related to the connection name and must reference an existing `SqlConnection`.

    .. seealso::

        - :class:`PluginDataSql`
        - :class:`SqlConnection`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.serializers import PluginSqlSerializer
        from smarter.apps.plugin.models import PluginDataSql

        sql_plugin = PluginDataSql.objects.first()
        serializer = PluginSqlSerializer(sql_plugin)
        print(serializer.data)
        # Output: {
        #   "connection": "...",
        #   "description": "...",
        #   "parameters": {...},
        #   "sqlQuery": "...",
        #   "testValues": {...},
        #   "limit": ...
        # }

    """

    connection = serializers.SlugRelatedField(slug_field="name", queryset=SqlConnection.objects.all())

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginDataSql
        fields = [
            "connection",
            "description",
            "parameters",
            "sql_query",
            "test_values",
            "limit",
        ]


class ApiConnectionSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the ApiConnection model.

    This serializer exposes API connection configuration fields, including account, name, description,
    base URL, API key, authentication method, timeout, and optional proxy settings. It is used to
    serialize and deserialize API connection information for plugin APIs.

    :param account: The account associated with the API connection (read-only).
    :type account: AccountMiniSerializer
    :param name: The name of the API connection.
    :type name: str
    :param description: A brief description of the API connection.
    :type description: str
    :param base_url: The base URL for API requests.
    :type base_url: str
    :param api_key: The API key for authentication (read-only).
    :type api_key: SecretSerializer
    :param auth_method: The authentication method used (e.g., "Bearer", "Basic").
    :type auth_method: str
    :param timeout: The request timeout in seconds.
    :type timeout: int
    :param proxy_protocol: The protocol used for proxying (optional).
    :type proxy_protocol: str
    :param proxy_host: The proxy server hostname (optional).
    :type proxy_host: str
    :param proxy_port: The proxy server port (optional).
    :type proxy_port: int
    :param proxy_username: The proxy username (optional).
    :type proxy_username: str
    :param proxy_password: The proxy password (read-only, optional).
    :type proxy_password: SecretSerializer

    :return: Serialized API connection configuration.
    :rtype: dict

    .. note::

        Sensitive fields such as `api_key` and `proxy_password` are handled as Smarter Secret instances
        and are read-only for security.

    .. seealso::

        - :class:`ApiConnection`
        - :class:`AccountMiniSerializer`
        - :class:`SecretSerializer`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.serializers import ApiConnectionSerializer
        from smarter.apps.plugin.models import ApiConnection

        api_conn = ApiConnection.objects.first()
        serializer = ApiConnectionSerializer(api_conn)
        print(serializer.data)
        # Output: {
        #   "account": {...},
        #   "name": "...",
        #   "description": "...",
        #   "baseUrl": "...",
        #   "apiKey": "...",
        #   "authMethod": "...",
        #   "timeout": ...,
        #   "proxyProtocol": "...",
        #   "proxyHost": "...",
        #   "proxyPort": ...,
        #   "proxyUsername": "...",
        #   "proxyPassword": "..."
        # }

    """

    account = AccountMiniSerializer(read_only=True)
    api_key = SecretSerializer(read_only=True)
    proxy_password = SecretSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = ApiConnection
        fields = [
            "account",
            "name",
            "description",
            "base_url",
            "api_key",
            "auth_method",
            "timeout",
            "proxy_protocol",
            "proxy_host",
            "proxy_port",
            "proxy_username",
            "proxy_password",
        ]


class PluginApiSerializer(SmarterCamelCaseSerializer):
    """
    Serializer for the PluginDataApi model.

    This serializer exposes API plugin configuration fields, including the connection, HTTP method,
    endpoint, URL parameters, headers, body, and result limit. It is used to serialize and deserialize
    API plugin settings for API endpoints.

    :param connection: The name of the API connection to use.
    :type connection: str
    :param method: The HTTP method for the API request (e.g., "GET", "POST").
    :type method: str
    :param endpoint: The API endpoint path.
    :type endpoint: str
    :param url_params: URL parameters for the API request.
    :type url_params: dict or list
    :param headers: HTTP headers for the API request.
    :type headers: dict
    :param body: The request body for the API call.
    :type body: dict or str
    :param limit: The maximum number of results to return.
    :type limit: int

    :return: Serialized API plugin configuration.
    :rtype: dict

    .. note::

        The `connection` field uses a slug related to the connection name and must reference an existing `ApiConnection`.

    .. seealso::

        - :class:`PluginDataApi`
        - :class:`ApiConnection`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.serializers import PluginApiSerializer
        from smarter.apps.plugin.models import PluginDataApi

        api_plugin = PluginDataApi.objects.first()
        serializer = PluginApiSerializer(api_plugin)
        print(serializer.data)
        # Output: {
        #   "connection": "...",
        #   "method": "...",
        #   "endpoint": "...",
        #   "urlParams": {...},
        #   "headers": {...},
        #   "body": {...},
        #   "limit": ...
        # }
    """

    connection = serializers.SlugRelatedField(slug_field="name", queryset=ApiConnection.objects.all())

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginDataApi
        fields = [
            "connection",
            "method",
            "endpoint",
            "url_params",
            "headers",
            "body",
            "limit",
        ]
