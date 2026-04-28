"""PluginMeta serializers."""

import sys

from rest_framework import serializers

from smarter.apps.account.serializers import (
    MetaDataWithOwnershipModelSerializer,
    UserProfileSerializer,
)
from smarter.apps.connection.models import ApiConnection, SqlConnection
from smarter.apps.plugin.models import (
    PluginDataApi,
    PluginDataSql,
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .manifest.enum import (
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
)


def is_sphinx_build():
    return "sphinx" in sys.modules


class PluginMetaSerializer(MetaDataWithOwnershipModelSerializer):
    """
    Serializer for the PluginMeta model.

    This serializer provides a camelCase API for plugin metadata, including fields for name, account,
    description, plugin class, version, user_profile, and tags. It is used to serialize and deserialize
    plugin metadata for API responses and requests.

    :param tags: List of tags associated with the plugin.
    :type tags: TagListSerializerField
    :param user_profile: The user profile of the plugin user_profile (read-only).
    :type user_profile: UserProfileSerializer

    :return: Serialized plugin metadata.
    :rtype: dict

    .. important::

        The `user_profile` field is read-only and cannot be modified via API requests.

    .. seealso::

        - :class:`PluginMeta`
        - :class:`TagListSerializerField`
        - :class:`UserProfileSerializer`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.plugin.serializers import PluginMetaSerializer
        from smarter.apps.plugin.models import PluginMeta

        plugin = PluginMeta.objects.first()
        serializer = PluginMetaSerializer(plugin)
        print(serializer.data)
        # Output: {
        #   "name": "...",
        #   "userProfile": {...},
        #   "description": "...",
        #   "pluginClass": "...",
        #   "version": "...",
        #   "userProfile": {...},
        #   "annotations": {...},
        #   "tags": ["tag1", "tag2"]
        # }

    """

    user_profile = UserProfileSerializer(read_only=True)
    annotations = serializers.JSONField()

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginMeta
        fields = ["name", "user_profile", "description", "plugin_class", "version", "annotations", "tags"]
        read_only_fields = ["user_profile"]


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

    if is_sphinx_build():
        queryset = []
    else:
        queryset = SqlConnection.objects.all()

    connection = serializers.SlugRelatedField(slug_field="name", queryset=queryset)

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

    if is_sphinx_build():
        queryset = []
    else:
        queryset = ApiConnection.objects.all()

    connection = serializers.SlugRelatedField(slug_field="name", queryset=queryset)

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
