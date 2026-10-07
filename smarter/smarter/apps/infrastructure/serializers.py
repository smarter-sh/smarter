"""Serializers of the infrastructure app."""

from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import InfrastructureResource


class InfrastructureResourceSerializer(SmarterCamelCaseSerializer):
    """
    Serializer of the ledger of cloud resources, :class:`InfrastructureResource`, with camelCase field names.

    **Example usage**::

        from smarter.apps.infrastructure.serializers import InfrastructureResourceSerializer
        data = InfrastructureResourceSerializer(resource).data
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = InfrastructureResource
        fields = "__all__"
