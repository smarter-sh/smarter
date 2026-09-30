from django.urls import reverse
from rest_framework import serializers

from smarter.apps.account.serializers import (
    MetaDataWithOwnershipModelSerializer,
    UserProfileSerializer,
)
from smarter.apps.proxy.models import Proxy


class ProxySerializer(MetaDataWithOwnershipModelSerializer):

    manifest_url = serializers.SerializerMethodField()

    class Meta:
        model = Proxy
        fields = "__all__"

    def get_manifest_url(self, obj: Proxy) -> str:
        """The URL of the Proxy's detail view, which renders its manifest."""
        # pylint: disable=C0415
        from .urls import ProxyReverseNames

        return reverse(
            f"{ProxyReverseNames.namespace}:{ProxyReverseNames.detailview}", kwargs={"hashed_id": obj.hashed_id}
        )
