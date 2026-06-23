from smarter.apps.account.serializers import (
    MetaDataWithOwnershipModelSerializer,
    UserProfileSerializer,
)
from smarter.apps.proxy.models import Proxy


class ProxySerializer(MetaDataWithOwnershipModelSerializer):

    class Meta:
        model = Proxy
        fields = "__all__"
