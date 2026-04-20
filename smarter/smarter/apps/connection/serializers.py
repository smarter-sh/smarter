"""Connection serializers."""

import sys

from rest_framework import serializers

from smarter.apps.account.serializers import (
    MetaDataWithOwnershipModelSerializer,
)
from smarter.apps.connection.models import (
    ApiConnection,
    SqlConnection,
)


def is_sphinx_build():
    return "sphinx" in sys.modules


class SqlConnectionSerializer(MetaDataWithOwnershipModelSerializer):
    """
    Serializer for the SqlConnection model.

    This serializer exposes SQL connection configuration fields in camelCase format, including
    connection details and optional proxy settings. It is used to serialize and deserialize
    SQL connection information.

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

        from smarter.apps.connection.serializers import SqlConnectionSerializer
        from smarter.apps.connection.models import SqlConnection

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


class ApiConnectionSerializer(MetaDataWithOwnershipModelSerializer):
    """
    Serializer for the ApiConnection model.

    This serializer exposes API connection configuration fields, including user_profile, name, description,
    base URL, API key, authentication method, timeout, and optional proxy settings. It is used to
    serialize and deserialize API connection information.

    :param user_profile: The user profile associated with the API connection (read-only).
    :type user_profile: AccountMiniSerializer
    :param name: The name of the API connection.
    :type name: str
    :param description: A brief description of the API connection.
    :type description: str
    :param base_url: The base URL for API requests.
    :type base_url: str
    :param api_key: The API key for authentication (read-only).
    :type api_key: smarter.apps.secret.serializers.SecretSerializer
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
    :type proxy_password: smarter.apps.secret.serializers.SecretSerializer

    :return: Serialized API connection configuration.
    :rtype: dict

    .. note::

        Sensitive fields such as `api_key` and `proxy_password` are handled as Smarter Secret instances
        and are read-only for security.

    .. seealso::

        - :class:`ApiConnection`
        - :class:`AccountMiniSerializer`
        - :class:`smarter.apps.secret.serializers.SecretSerializer`

    **Example usage**:

    .. code-block:: python

        from smarter.apps.connection.serializers import ApiConnectionSerializer
        from smarter.apps.connection.models import ApiConnection

        api_conn = ApiConnection.objects.first()
        serializer = ApiConnectionSerializer(api_conn)
        print(serializer.data)
        # Output: {
        #   "userProfile": {...},
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

    user_profile = serializers.SlugRelatedField(slug_field="name", read_only=True)
    api_key = serializers.SlugRelatedField(slug_field="name", read_only=True)
    proxy_password = serializers.SlugRelatedField(slug_field="name", read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = ApiConnection
        fields = [
            "user_profile",
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
