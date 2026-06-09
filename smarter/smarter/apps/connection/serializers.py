"""Connection serializers."""

import sys

from rest_framework import serializers

from smarter.apps.account.serializers import (
    MetaDataWithOwnershipModelSerializer,
)
from smarter.apps.connection.models import (
    ApiConnection,
    ConnectionBase,
    SqlConnection,
)


def is_sphinx_build():
    return "sphinx" in sys.modules


class ConnectionSerializer(MetaDataWithOwnershipModelSerializer):

    # pylint: disable=missing-class-docstring
    class Meta(MetaDataWithOwnershipModelSerializer.Meta):
        model = ConnectionBase
        fields = [
            "id",
            "created_at",
            "updated_at",
            "name",
            "user_profile",
            "description",
            "version",
            "annotations",
            "tags",
            "manifest_url",
            "ready",
            "kind",
        ]
        read_only_fields = getattr(MetaDataWithOwnershipModelSerializer.Meta, "read_only_fields", []) + [
            "last_accessed",
            "expires_at",
            "manifest_url",
            "ready",
        ]


class SqlConnectionSerializer(MetaDataWithOwnershipModelSerializer):
    """
    Serializer for the SqlConnection model.

    This serializer exposes SQL connection configuration fields in camelCase format, including
    connection details and optional proxy settings. It is used to serialize and deserialize
    SQL connection information.


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
        #  .....
        # }

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SqlConnection
        fields = [
            "name",
            "description",
            "authentication_method",
            "timeout",
            "use_ssl",
            "ssl_cert",
            "ssl_key",
            "ssl_ca",
            "hostname",
            "port",
            "database",
            "username",
            "password",
            "pool_size",
            "max_overflow",
            "proxy_protocol",
            "proxy_host",
            "proxy_port",
            "proxy_username",
            "proxy_password",
            "ssh_known_hosts",
        ]


class ApiConnectionSerializer(MetaDataWithOwnershipModelSerializer):
    """
    Serializer for the ApiConnection model.

    This serializer exposes API connection configuration fields, including user_profile, name, description,
    base URL, API key, authentication method, timeout, and optional proxy settings. It is used to
    serialize and deserialize API connection information.

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
